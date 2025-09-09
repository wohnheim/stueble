-- when a guest arrives or leaves, notify all hosts with an event using websocket
CREATE OR REPLACE FUNCTION event_guest_change()
RETURNS TRIGGER AS $$
DECLARE inviter_role user_role;
BEGIN
        -- check, whether admins are trying to arrive / leave
        IF (SELECT user_role FROM users WHERE id = NEW.user_id) = 'admin'
        THEN
            RAISE EXCEPTION 'Admins are not allowed to arrive / leave stueble';
        END IF;

        -- check, whether the user is allowed to arrive / leave
        IF NEW.event_type in ('arrive', 'leave')
        THEN
            -- if user is arriving, check if not already arrived
            IF NEW.event_type = 'arrive'
            THEN

                -- check, whether user already arrived
                IF (SELECT event_type
                    FROM events
                    WHERE stueble_id = NEW.stueble_id
                      AND user_id = NEW.user_id
                      AND event_type in ('arrive', 'leave')
                    ORDER BY submitted DESC
                    LIMIT 1) == 'arrive'
                THEN
                    RAISE EXCEPTION 'User % is already marked as arrived for stueble %', NEW.user_id, NEW.stueble_id;
                END IF;

                -- check, whether user is registered for the stueble
                IF (SELECT event_type
                        FROM events
                        WHERE stueble_id = NEW.stueble_id
                          AND user_id = NEW.user_id
                          AND event_type in ('add', 'remove')
                        ORDER BY submitted DESC
                        LIMIT 1) != 'add'
                    THEN
                        RAISE EXCEPTION 'User is not registered for stueble %', NEW.stueble_id;
                    END IF;

            -- if user is leaving, check if not already left and whether they arrived first
            ELSE
                IF (SELECT event_type
                    FROM events
                    WHERE stueble_id = NEW.stueble_id
                      AND user_id = NEW.user_id
                      AND event_type in ('arrive', 'leave')
                    ORDER BY submitted DESC
                    LIMIT 1) != 'arrive'
                THEN
                    RAISE EXCEPTION 'User % is not marked as arrived yet for stueble %', NEW.user_id, NEW.stueble_id;
                END IF;
            END IF;

            -- check, whether the user can be added / removed
            ELSE

                -- check whether add is valid
                IF NEW.event_type = 'add'
                THEN
                    -- check, whether user is extern and needs to be invited
                    IF NEW.invited_by IS NULL AND (SELECT user_role FROM users WHERE id = NEW.user_id) = 'extern'
                    THEN
                        RAISE EXCEPTION 'Externs need to be invited';
                    END IF;

                    -- set inviter_role
                    inviter_role := (SELECT user_role
                                     FROM users
                                     WHERE id = NEW.invited_by);

                    -- if user is being added, check, whether inviter role is allowed
                    IF NEW.invited_by IS NOT NULL AND inviter_role in ('extern', 'admin')
                    THEN
                        RAISE EXCEPTION 'Externs and admins are not allowed to invite users';
                    END IF;
                    IF (SELECT event_type
                        FROM events
                        WHERE stueble_id = NEW.stueble_id
                          AND user_id = NEW.user_id
                          AND event_type in ('add', 'remove')
                        ORDER BY submitted DESC
                        LIMIT 1) == 'add'
                    THEN
                        RAISE EXCEPTION 'User cannot be added to stueble % since already added to stueble %', NEW.stueble_id;
                    END IF;

                -- check whether remove is valid
                ELSE
                    IF (SELECT event_type
                        FROM events
                        WHERE stueble_id = NEW.stueble_id
                          AND user_id = NEW.user_id
                          AND event_type in ('add', 'remove')
                        ORDER BY submitted DESC
                        LIMIT 1) != 'add'
                    THEN
                        RAISE EXCEPTION 'User cannot be removed from stueble % since not registered for stueble % yet', NEW.stueble_id;
                    END IF;
                END IF;
            END IF;
            PERFORM pg_notify(
                    'guest_list_update',
                    json_build_object(
                            'event', NEW.event_type,
                            'user_id', NEW.user_id,
                            'stueble_id', NEW.stueble_id -- unnecessary since only for one stueble at a time this method is allowed
                    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_to_affected_users()
RETURNS trigger AS $$
DECLARE affected RECORD;
BEGIN
    IF NEW.event_type = 'arrive' OR NEW.event_type = 'leave'
    THEN
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

CREATE OR REPLACE FUNCTION set_uuid_hash()
RETURNS trigger AS $$
BEGIN
    NEW.uuid := gen_random_uuid();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

CREATE OR REPLACE TRIGGER event_guest_change_trigger
BEFORE INSERT ON events
FOR EACH ROW EXECUTE FUNCTION event_guest_change();

CREATE OR REPLACE TRIGGER event_guest_change_two_trigger
AFTER INSERT ON events
FOR EACH ROW EXECUTE FUNCTION add_to_affected_users();

CREATE OR REPLACE TRIGGER update_websocket_sids_trigger
    AFTER INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_websocket_sids();

CREATE OR REPLACE TRIGGER set_uuid_hash_trigger
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_uuid_hash();

CREATE OR REPLACE TRIGGER set_session_id_trigger
    BEFORE INSERT OR UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION set_session_id();

CREATE OR REPLACE TRIGGER set_reset_code_trigger
    BEFORE INSERT ON password_resets
    FOR EACH ROW EXECUTE FUNCTION set_reset_code();