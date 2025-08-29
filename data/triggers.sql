CREATE OR REPLACE FUNCTION event_add_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO events (userID, event_type, affected)
    VALUES (NEW.id, 'add', NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION event_change_user()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.password_hash IS NULL
    THEN
        INSERT INTO events (userID, event_type, affected)
        VALUES (NEW.id, 'delete', NEW.id);
    ELSE
        INSERT INTO events (userID, event_type, affected)
        VALUES (NEW.id, 'modify', NEW.id);
    END IF;
    UPDATE users SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;