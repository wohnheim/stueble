CREATE OR REPLACE FUNCTION set_session_id()
RETURNS trigger AS $$
BEGIN
    IF OLD.session_id IS NULL
    THEN
        NEW.session_id := gen_random_uuid();
    ELSE
        NEW.session_id := OLD.session_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_reset_code()
RETURNS trigger AS $$
BEGIN
    IF OLD.reset_code IS NULL
    THEN
        NEW.reset_code := gen_random_uuid();
    ELSE
        NEW.reset_code := OLD.reset_code;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_user_constants()
RETURNS trigger AS $$
BEGIN
    IF NEW.user_uuid != OLD.user_uuid AND OLD.user_uuid IS NOT NULL
    THEN
        RAISE EXCEPTION 'user_uuid is constant and cannot be changed after being initialized';
    END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- TODO: deprecated
CREATE OR REPLACE FUNCTION check_user_role()
RETURNS trigger AS $$
BEGIN
IF (SELECT user_role FROM users WHERE id = NEW.user_id) = 'admin'
THEN
    RAISE EXCEPTION 'Admins are not allowed to have stueble codes';
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_hosts()
RETURNS trigger AS $$
BEGIN
    IF NEW.user_role = 'host'
    THEN
        RETURN NEW;
    END IF;
    DELETE FROM stueble.hosts
    WHERE user_id = NEW.id
      AND stueble_id = (
        SELECT id
        FROM stueble.motto
        WHERE ((date_of_time >= CURRENT_DATE)
          OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1))
        ORDER BY date_of_time ASC LIMIT 1);
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_websockets_affected()
RETURNS trigger AS $$
DECLARE
    affected_users int[] := NULL; -- array of affected user ids
    user_id int := NULLIF(current_setting('additional.user_id', true), '')::int; -- user_id from additional settings if message is just sent to a specific user like stuebleStatus
    affected RECORD; -- for loop variable
    session_id RECORD; -- for loop variable
BEGIN

    -- get all affected users depending on required_role
    IF COALESCE(NEW.required_role, 'extern') = 'host'
    THEN
        affected_users := ARRAY(SELECT id FROM users WHERE user_role IN ('host', 'tutor', 'admin'));
    ELSIF COALESCE(NEW.required_role, 'extern') = 'tutor'
    THEN
        affected_users := ARRAY(SELECT id FROM users WHERE user_role IN ('tutor', 'admin'));
    ELSIF COALESCE(NEW.required_role, 'extern') = 'admin'
    THEN
        affected_users := ARRAY(SELECT id FROM users WHERE user_role = 'admin');

    -- specific user
    ELSIF NEW.required_role = NULL OR NEW.required_role = 'user'
    THEN
        IF user_id IS NULL
        THEN
            RAISE EXCEPTION 'User ID must be provided in additional.user_id for required_role user or required_role NULL; code: 500';
        END IF;
        affected_users := ARRAY[user_id];
    END IF;

    -- insert into websockets_affected for all affected users for all their sessions
    FOR affected IN (SELECT unnest(affected_users) AS id)
    LOOP
        FOR session_id IN (SELECT id FROM sessions WHERE user_id = affected.id)
        LOOP
            INSERT INTO websockets_affected (message_id, session_id)
            VALUES (NEW.id, session_id.id);
        END LOOP;
    END LOOP;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_messages()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM websockets_affected WHERE message_id = OLD.message_id)
    THEN
        DELETE FROM websocket_messages WHERE id = OLD.message_id;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER check_user_constants
    BEFORE UPDATE ON users -- only on updates
    FOR EACH ROW EXECUTE FUNCTION check_user_constants();

CREATE OR REPLACE TRIGGER remove_hosts_trigger
    AFTER UPDATE OF user_role ON users
    FOR EACH ROW EXECUTE FUNCTION remove_hosts();

CREATE OR REPLACE TRIGGER set_session_id_trigger
    BEFORE INSERT OR UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION set_session_id();

CREATE OR REPLACE TRIGGER set_reset_code_trigger
    BEFORE INSERT ON verification_codes
    FOR EACH ROW EXECUTE FUNCTION set_reset_code();

CREATE OR REPLACE TRIGGER add_websockets_affected_trigger
    BEFORE INSERT ON websocket_messages
    FOR EACH ROW EXECUTE FUNCTION add_websockets_affected();

CREATE OR REPLACE TRIGGER remove_messages_trigger
    AFTER DELETE ON websockets_affected
    FOR EACH ROW EXECUTE FUNCTION remove_messages();
