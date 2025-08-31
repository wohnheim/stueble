
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
        VALUES (NEW.id, 'delete')
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
DECLARE event_id INTEGER;
DECLARE affected RECORD;
BEGIN
    IF NEW.event_type = 'arrive' OR NEW.event_type = 'leave'
    THEN
        INSERT INTO events (user_id, event_type, stueble_id)
        VALUES (NEW.user_id, NEW.event_type, NEW.stueble_id)
        RETURNING id INTO event_id;
    END IF;
    FOR affected IN (SELECT id FROM users WHERE user_role = 'host' OR user_role = 'admin')
    LOOP
        INSERT INTO events_affected_users (event_id, affected_user_id)
        VALUES (event_id, affected.id);
    END LOOP;
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

CREATE TRIGGER event_change_user_trigger
AFTER UPDATE OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION event_change_user();

CREATE TRIGGER event_add_user_trigger
AFTER INSERT ON users
FOR EACH ROW EXECUTE FUNCTION event_add_user();

CREATE TRIGGER event_guest_change_trigger
AFTER INSERT ON events
FOR EACH ROW EXECUTE FUNCTION event_guest_change();