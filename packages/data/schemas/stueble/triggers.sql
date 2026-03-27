CREATE OR REPLACE FUNCTION set_application_uuid()
RETURNS trigger AS $$
BEGIN
    NEW.uuid := gen_random_uuid();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- when a guest arrives or leaves, notify all hosts with an event using websocket
CREATE OR REPLACE FUNCTION event_guest_change()
RETURNS trigger AS $$
DECLARE inviter_role USER_ROLE;
DECLARE inviter_users INTEGER;
DECLARE automatically_removed_user INTEGER;
DECLARE present BOOLEAN;
DECLARE all_invitees_absent BOOLEAN;
DECLARE maximum_invitees INTEGER;
BEGIN
    -- skip for force insert
    IF current_setting('additional.skip_triggers', true) = 'on' THEN
        RETURN NEW;
    END IF;
    -- check, whether admins are trying to arrive / leave
    IF COALESCE((SELECT user_role FROM users WHERE id = NEW.user_id), 'extern') = 'admin'
    THEN
        RAISE EXCEPTION 'Admins are not allowed to arrive / leave stueble; code: 400';
    END IF;

    -- check, whether the user is allowed to arrive / leave
    IF NEW.event_type IN ('arrive', 'leave')
    THEN
        -- if user is arriving, check if not already arrived
        IF NEW.event_type = 'arrive'
        THEN

            -- check, whether user already arrived
            IF COALESCE((SELECT event_type
                FROM stueble.events
                WHERE stueble_id = NEW.stueble_id
                  AND user_id = NEW.user_id
                  AND event_type IN ('arrive', 'leave', 'remove') -- remove, since when the user is removed, all past arrived have to be ignored
                ORDER BY submitted DESC
                LIMIT 1), 'leave') = 'arrive'
            THEN
                RAISE EXCEPTION 'User % is already marked as arrived for stueble %; code: 400', NEW.user_id, NEW.stueble_id;
            END IF;

            -- check, whether user is registered for the stueble
            IF COALESCE((SELECT event_type
                FROM stueble.events
                WHERE stueble_id = NEW.stueble_id
                  AND user_id = NEW.user_id
                  AND event_type IN ('add', 'remove')
                ORDER BY submitted DESC
                LIMIT 1), 'remove') != 'add'
            THEN
                RAISE EXCEPTION 'User is not registered for stueble %; code: 400', NEW.stueble_id;
            END IF;

        -- if user is leaving, check if not already left and whether they arrived first
        ELSE
            IF COALESCE((SELECT event_type
                FROM stueble.events
                WHERE stueble_id = NEW.stueble_id
                  AND user_id = NEW.user_id
                  AND event_type IN ('arrive', 'leave')
                ORDER BY submitted DESC
                LIMIT 1), 'leave') != 'arrive'
            THEN
                RAISE EXCEPTION 'User % is not marked as arrived yet for stueble %; code: 400', NEW.user_id, NEW.stueble_id;
            END IF;
        END IF;

    -- check, whether the user can be added / removed
    ELSE

        -- check whether add is valid
        IF NEW.event_type = 'add'
        THEN

            IF COALESCE((SELECT user_role FROM users WHERE id = NEW.user_id), 'extern') = 'host'
            THEN
                RAISE EXCEPTION 'Hosts are not allowed to be added to stueble; code: 400';
            END IF;

            -- check, whether user is extern and needs to be invited
            IF NEW.invited_by IS NULL AND (SELECT user_role FROM users WHERE id = NEW.user_id) = 'extern'
            THEN
                RAISE EXCEPTION 'Externs need to be invited; code: 400';
            END IF;

            IF NEW.invited_by IS NOT NULL AND (SELECT user_role FROM users WHERE id = NEW.user_id) != 'extern'
            THEN
                RAISE EXCEPTION 'Only externs can be invited; code: 400';
            END IF;

            -- set inviter_role
            inviter_role := COALESCE((SELECT user_role
                             FROM users
                             WHERE id = NEW.invited_by), 'extern');

            -- if user is being added, check, whether inviter role is allowed
            IF NEW.invited_by IS NOT NULL AND inviter_role IN ('extern', 'admin')
            THEN
                RAISE EXCEPTION 'Externs and admins are not allowed to invite users; code: 400';
            END IF;

            -- check, whether user is already added
            IF COALESCE((SELECT event_type
                FROM stueble.events
                WHERE stueble_id = NEW.stueble_id
                  AND user_id = NEW.user_id
                  AND event_type IN ('add', 'remove')
                ORDER BY submitted DESC
                LIMIT 1), 'remove') = 'add'
            THEN
                RAISE EXCEPTION 'User cannot be added to stueble % since already added to stueble %; code: 400', NEW.stueble_id, NEW.stueble_id;
            END IF;

            -- check, whether maximum capacity of guests is already reached
            IF (SELECT COUNT(*)
                FROM (SELECT DISTINCT ON (user_id) event_type
                      FROM stueble.events
                      WHERE event_type IN ('add', 'remove') AND stueble_id = NEW.stueble_id
                      ORDER BY user_id, submitted DESC) as last_events
                WHERE event_type = 'add') >=
               (SELECT CAST(value AS INTEGER) FROM configurations WHERE key = 'maximum_guests_per_stueble')
            THEN
                RAISE EXCEPTION 'Maximum capacity of guests for stueble % already reached; code: 400', NEW.stueble_id;
            END IF;

            IF COALESCE((SELECT user_role FROM users WHERE id = NEW.invited_by), 'extern') != 'tutor'
            THEN
                maximum_invitees := COALESCE((SELECT CAST(value AS INTEGER) FROM configurations WHERE key = 'maximum_invites_per_user'), 0);
            ELSE
                maximum_invitees := COALESCE((SELECT CAST(value AS INTEGER) FROM configurations WHERE key = 'maximum_guests_per_tutor'), 0);
            END IF;

            -- check, whether max_number of guests for inviter is already exceeded
            IF NEW.invited_by IS NOT NULL
            THEN
                WITH last_events AS (SELECT DISTINCT ON (user_id) event_type
                                     FROM stueble.events
                                     WHERE (event_type IN ('add', 'remove') AND invited_by = NEW.invited_by AND
                                            stueble_id = NEW.stueble_id)
                                     ORDER BY user_id, submitted DESC)
                SELECT COUNT(*)
                INTO inviter_users
                FROM last_events
                WHERE event_type = 'add';
                IF inviter_users >=
                   maximum_invitees
                THEN
                    RAISE EXCEPTION 'Inviter % has already reached the maximum number of guests; code: 400', NEW.invited_by;
                END IF;
            END IF;

        -- check whether remove is valid
        ELSE
            IF COALESCE((SELECT event_type
                FROM stueble.events
                WHERE stueble_id = NEW.stueble_id
                  AND user_id = NEW.user_id
                  AND event_type IN ('add', 'remove')
                ORDER BY submitted DESC
                LIMIT 1), 'remove') != 'add'
            THEN
                RAISE EXCEPTION 'User cannot be removed from stueble % since not registered for stueble % yet; code: 400', NEW.stueble_id, NEW.stueble_id;
            END IF;

            present := COALESCE((SELECT event_type
                                FROM stueble.events
                                WHERE user_id = NEW.user_id
                                          AND stueble_id = NEW.stueble_id
                                          AND event_type IN ('arrive', 'leave')
                                ORDER BY submitted DESC LIMIT 1), 'leave') = 'arrive';

            IF present
            THEN
                RAISE EXCEPTION 'User cannot be removed from stueble % since already arrived; code: 400', NEW.stueble_id;
            END IF;

            all_invitees_absent := (SELECT (SELECT COUNT(*) FROM
            (SELECT * FROM (SELECT DISTINCT ON (stueble.events.user_id) event_type
                      FROM stueble.events
                      WHERE invited_by = NEW.user_id AND stueble_id = NEW.stueble_id
                      ORDER BY events.user_id, submitted DESC) AS invitees_event
            WHERE event_type = 'arrive') AS arrived_invitees) = 0);

            IF NOT all_invitees_absent
            THEN
                RAISE EXCEPTION 'User cannot be removed from stueble % since some of their invitees are still present; code: 400', NEW.stueble_id;
            END IF;

            -- remove invitees of the removed user if user is not extern
            IF (SELECT user_role FROM users WHERE id = NEW.user_id) != 'extern'
            THEN
                -- if already arrived at stueble forbid removing
                INSERT INTO stueble.events (user_id, stueble_id, event_type)
                (SELECT users_event.user_id, NEW.stueble_id, 'remove' FROM (SELECT DISTINCT ON (stueble.events.user_id) user_id, event_type
                      FROM stueble.events
                      WHERE invited_by = NEW.user_id AND stueble_id = NEW.stueble_id
                      ORDER BY events.user_id, submitted DESC) AS users_event
                WHERE event_type NOT IN ('arrive', 'remove'))
                RETURNING user_id INTO automatically_removed_user;
                PERFORM pg_notify(
                    'automatically_removed_users',
                    json_build_object(
                            'event', 'remove',
                            'user_id', automatically_removed_user,
                            'stueble_id', NEW.stueble_id -- unnecessary since only for one stueble at a time this method is allowed
                    )::text);
            END IF;
            /*
            -- TODO: remove this leave statement and block arriving until stueble begins as well as blocking removing after stueble began
            -- creates a bigger id; shouldn't be problematic since removal by user is banned during stueble, also leave is okay due to the same reason
            INSERT INTO events (user_id, stueble_id, event_type)
            VALUES (NEW.user_id, NEW.stueble_id, 'leave');
             */
        END IF;
    END IF;

    IF NEW.event_type IN ('add', 'arrive')
    THEN
        -- check, whether inviter is still added for stueble
        IF COALESCE((SELECT user_role FROM users WHERE id = NEW.user_id), 'extern') = 'extern'
            AND COALESCE((SELECT event_type
                            FROM stueble.events
                            WHERE user_id = NEW.invited_by
                            AND stueble_id = NEW.stueble_id
                            AND event_type IN ('add', 'remove')
                            ORDER BY submitted
                                DESC
                            LIMIT 1),
                            'remove') != 'add' AND COALESCE((SELECT user_role FROM users WHERE id = NEW.invited_by), 'extern') NOT IN ('admin', 'tutor', 'host')
        THEN
            RAISE EXCEPTION 'Inviter of user % is not registered for stueble % anymore; code: 400', NEW.user_id, NEW.stueble_id;
            END IF;
    END IF;

    IF NEW.event_type = 'remove'
    THEN
        PERFORM pg_notify(
                'automatically_removed_users',
                json_build_object(
                        'event', NEW.event_type,
                        'user_id', NEW.user_id,
                        'stueble_id', NEW.stueble_id -- unnecessary since only for one stueble at a time this method is allowed
                )::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_invited_by()
RETURNS trigger AS $$
BEGIN

    -- check, whether invited_by is specified, though event_type is not 'add'
    IF NEW.event_type != 'add' AND NEW.invited_by IS NOT NULL
    THEN
        RAISE EXCEPTION 'invited_by can only be specified for event_type add; code: 500';
    END IF;

    IF NEW.invited_by IS NULL AND NEW.event_type != 'add' AND (SELECT user_role FROM users WHERE id = NEW.user_id) = 'extern'
    THEN
        NEW.invited_by := (SELECT invited_by
                           FROM stueble.events
                           WHERE user_id = NEW.user_id
                             AND stueble_id = NEW.stueble_id
                             AND event_type = 'add'
                           ORDER BY submitted DESC
                           LIMIT 1);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_hosts()
RETURNS trigger AS $$
BEGIN
IF (SELECT date_of_time FROM stueble.motto WHERE id = NEW.stueble_id) = (SELECT MIN(date_of_time)
                        FROM (
                            SELECT date_of_time
                            FROM stueble.motto
                            WHERE ((date_of_time >= CURRENT_DATE)
                               OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1))))
THEN
    UPDATE users
    SET user_role = 'host'
    WHERE id IN (SELECT user_id FROM stueble.hosts WHERE stueble_id = NEW.stueble_id) AND user_role = 'user';
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPALACE FUNCTION add_group()
RETURN trigger AS $$
    IF NEW.application_group IS NULL
    THEN
      NEW.application_group := (SELECT COALESCE(MAX(application_group), 0) + 1 FROM stueble.applicants);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION delete_application_group()
RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM stueble.applications WHERE application_group = OLD.application_group)
    THEN
        DELETE FROM stueble.applicants WHERE application_group = OLD.application_group;
    END IF;
RETURN OLD;
END;


-- NOTE: DO NOT RENAME THE TRIGGERS, SINCE THEIR ALPHABETICAL ORDER SPECIFIES THE ORDER OF EXECUTION
CREATE OR REPLACE TRIGGER event_add_invited_by_trigger
BEFORE INSERT OR UPDATE ON stueble.events
FOR EACH ROW EXECUTE FUNCTION add_invited_by();

-- NOTE: DO NOT RENAME THE TRIGGERS, SINCE THEIR ALPHABETICAL ORDER SPECIFIES THE ORDER OF EXECUTION
CREATE OR REPLACE TRIGGER event_guest_change_trigger
BEFORE INSERT OR UPDATE ON stueble.events
FOR EACH ROW
EXECUTE FUNCTION event_guest_change();

CREATE OR REPLACE TRIGGER add_hosts
    AFTER INSERT OR UPDATE ON stueble.hosts
    FOR EACH ROW EXECUTE FUNCTION add_hosts();

CREATE OR REPLACE TRIGGER add_application_uuid_trigger
    BEFORE INSERT ON stueble.applications
    FOR EACH ROW EXECUTE FUNCTION set_application_uuid();

CREATE OR REPLACE TRIGGER add_application_group_trigger
    BEFORE INSERT ON stueble.applicants
    FOR EACH ROW EXECUTE FUNCTION add_application_group();

CREATE OR REPLACE TRIGGER delete_application_group_trigger
    AFTER DELETE ON stueble.applications
    FOR EACH ROW EXECUTE FUNCTION delete_application_group();