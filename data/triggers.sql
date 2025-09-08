
-- when a new user is created, add an event
CREATE OR REPLACE FUNCTION event_add_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO events (user_id, event_type)
    VALUES (NEW.id, 'add');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- when a user is modified or deleted, add an event
CREATE OR REPLACE FUNCTION event_change_user()
RETURNS TRIGGER AS $$
DECLARE event_id INTEGER;
BEGIN
    IF NEW.password_hash IS NULL
    THEN
        INSERT INTO events (user_id, event_type)
        VALUES (NEW.id, 'remove')
        RETURNING id INTO event_id;
    ELSE
        INSERT INTO events (user_id, event_type)
        VALUES (NEW.id, 'modify')
        RETURNING id INTO event_id;
    END IF;
    INSERT INTO events_affected_users (event_id, affected_user_id)
    VALUES (event_id, NEW.id);
    UPDATE users SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- when a guest arrives or leaves, notify all hosts with an event using websocket
CREATE OR REPLACE FUNCTION event_guest_change()
RETURNS TRIGGER AS $$
DECLARE affected RECORD;
BEGIN
    IF NEW.event_type = 'arrive' OR NEW.event_type = 'leave'
    THEN
        IF (SELECT user_role FROM users WHERE id = NEW.user_id) = 'admin'
        THEN
            RAISE EXCEPTION 'Admins are not allowed to arrive / leave stueble';
        END IF;
        IF (SELECT user_id FROM stueble_codes WHERE stueble_id = NEW.stueble_id AND user_id = NEW.user_id) IS NULL
        THEN
            RAISE EXCEPTION 'User has no stueble code to stueble %', NEW.stueble_id;
        END IF;
        IF (SELECT event_type FROM events WHERE ((user_id = NEW.user_id) AND (stueble_id = NEW.stueble_id)) ORDER BY submitted DESC LIMIT 1) = NEW.event_type
            THEN
                RAISE EXCEPTION 'Duplicate event: User % already has an event of type % for stueble %', NEW.user_id, NEW.event_type, NEW.stueble_id;
        END IF;
        PERFORM pg_notify(
            'guest_list_update',
            json_build_object(
            'event', NEW.event_type,
            'user_id', NEW.user_id,
            'stueble_id', NEW.stueble_id -- unnecessary since only for one stueble at a time this method is allowed
            )::text);
        FOR affected IN (SELECT id FROM users WHERE user_role = 'host' OR user_role = 'admin')
        LOOP
            INSERT INTO events_affected_users (event_id, affected_user_id)
            VALUES (NEW.id, affected.id);
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_websocket_sids()
RETURNS trigger AS $$
BEGIN
DELETE FROM websocket_sids WHERE user_id = NEW.id AND ((SELECT user_role FROM users WHERE id = NEW.id) NOT IN ('admin', 'tutor', 'host'));
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

CREATE OR REPLACE TRIGGER event_change_user_delete_trigger
AFTER DELETE ON users
FOR EACH ROW EXECUTE FUNCTION event_change_user();


CREATE OR REPLACE TRIGGER event_change_user_trigger
AFTER UPDATE ON users
FOR EACH ROW
WHEN (OLD.* IS DISTINCT FROM NEW.* AND ((OLD.last_updated IS DISTINCT FROM NEW.last_updated) IS FALSE))
EXECUTE FUNCTION event_change_user();

CREATE OR REPLACE TRIGGER event_add_user_trigger
AFTER INSERT ON users
FOR EACH ROW EXECUTE FUNCTION event_add_user();

CREATE OR REPLACE TRIGGER event_guest_change_trigger
BEFORE INSERT ON events
FOR EACH ROW EXECUTE FUNCTION event_guest_change();

CREATE OR REPLACE TRIGGER update_websocket_sids_trigger
    AFTER INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_websocket_sids();

CREATE OR REPLACE TRIGGER check_user_role_stueble_codes_trigger
    BEFORE INSERT OR UPDATE ON stueble_codes
    FOR EACH ROW EXECUTE FUNCTION check_user_role();