-- Description: create tables, types, check functions for database

-- SET TIMEZONE TO 'Europe/Berlin';
-- SET DateStyle TO ISO, YMD;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- enum for user_role in table users
CREATE TYPE USER_ROLE AS ENUM ('admin', 'tutor', 'host', 'user', 'extern');

-- enum for event_type in table events
-- arrive, leave will be handled by python, add, remove, modify by triggers
CREATE TYPE EVENT_TYPE AS ENUM('add', 'remove', 'arrive', 'leave', 'modify');

-- enum for residence in table users
CREATE TYPE RESIDENCE AS ENUM('altbau', 'neubau', 'anbau', 'hirte');

-- table to save users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_role USER_ROLE NOT NULL,
    room INTEGER CHECK ((user_role = 'extern' AND room IS NULL) OR (user_role != 'extern' AND room > 0)),
    residence RESIDENCE NULL CHECK ((user_role = 'extern' AND residence IS NULL) OR (user_role != 'extern' AND residence IS NOT NULL)),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password_hash VARCHAR(255) CHECK ((user_role = 'extern' AND password_hash IS NULL) OR user_role != 'extern'),
    email VARCHAR(255) UNIQUE CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$' OR password_hash is NULL),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    personal_hash TEXT GENERATED ALWAYS AS (
        encode(digest(id::text, 'sha256'), 'hex')) STORED UNIQUE NOT NULL, -- added for personal references, not as easy to guess as id
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    user_name TEXT NOT NULL UNIQUE
);

-- table for stueble mottos
CREATE TABLE IF NOT EXISTS stueble_motto (
    id SERIAL PRIMARY KEY,
    motto TEXT NOT NULL,
    date_of_time DATE NOT NULL UNIQUE CHECK (date_of_time > CURRENT_DATE),
    shared_apartment TEXT
);

-- table for stueble codes
CREATE TABLE IF NOT EXISTS stueble_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE NOT NULL,
    code TEXT GENERATED ALWAYS AS (encode(digest(id::text, 'sha256'), 'hex')) STORED UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    date_of_time DATE NOT NULL REFERENCES stueble_motto(date_of_time) ON DELETE CASCADE,
    stueble_id INTEGER REFERENCES stueble_motto(id) NOT NULL, -- references the correct stueble event
    invited_by INTEGER REFERENCES users(id)
);

-- table to save login sessions
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    expiration_date TIMESTAMPTZ NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    session_id TEXT GENERATED ALWAYS AS (
        encode(digest(id::text, 'sha256'), 'hex')) STORED UNIQUE NOT NULL
);

-- table to save user and host events
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    event_type EVENT_TYPE NOT NULL,
    submitted TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stueble_id INTEGER REFERENCES stueble_motto(id) CHECK ((event_type IN ('arrive', 'leave') AND stueble_id IS NOT NULL) OR (event_type NOT IN ('arrive', 'leave') AND stueble_id IS NULL))
);

CREATE TABLE IF NOT EXISTS events_affected_users (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) NOT NULL,
    affected_user_id INTEGER REFERENCES users(id) NOT NULL,
    submitted TIMESTAMPTZ
);

-- table to save configuration settings
CREATE TABLE IF NOT EXISTS configurations (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- set default configuration values
INSERT INTO configurations (key, value) VALUES
('session_expiration_days', '30'),
('maximum_guests', '150'),
('maximum_invites_per_user', '1'),
('reset_code_expiration_minutes', '60');

CREATE TABLE IF NOT EXISTS allowed_users (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    room INTEGER CHECK (room > 0),
    residence RESIDENCE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    reset_code TEXT GENERATED ALWAYS AS (encode(digest(id::text, 'sha256'), 'hex')) STORED UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- saves the specific sids for a websocket connection for a user and their device
CREATE TABLE IF NOT EXISTS websocket_sids (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE UNIQUE NOT NULL,
    sid TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- error table
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    error_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    raised_by INTEGER REFERENCES error_logs(id), -- self reference for errors raised by error handling
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    raised_python TEXT,
    actions_taken BOOLEAN DEFAULT FALSE
);

-- check function for valid invited_by id in users
CREATE FUNCTION is_valid_invited_by_id(INTEGER) RETURNS boolean AS $$
    SELECT COALESCE((SELECT invited_by IS NULL FROM stueble_codes WHERE user_id = $1 LIMIT 1), false) AND
           (
               (SELECT COUNT(*)
                FROM stueble_codes
                WHERE invited_by = $1)
                <  -- really smaller since one is added
               (SELECT
                    CAST(value AS INTEGER)
                FROM configurations
                WHERE key = 'maximum_guests_per_user')
           );
$$ LANGUAGE SQL;

CREATE FUNCTION get_submitted_timestamp(INTEGER) RETURNS timestamptz AS $$
    SELECT submitted FROM events WHERE id = $1 LIMIT 1;
$$ LANGUAGE SQL;

-- CHECK-Constraint for valid invited_by id in stueble_codes
ALTER TABLE stueble_codes
    ADD CONSTRAINT stueble_codes_invited_by_check
    CHECK (invited_by IS NULL OR (id != invited_by AND is_valid_invited_by_id(invited_by)));


CREATE FUNCTION stueble_max_guests(INTEGER) RETURNS boolean AS $$
    SELECT
        (COUNT(*))
        < -- really smaller since one is added
        (SELECT CAST (value AS INTEGER)
        FROM configurations
        WHERE key = 'maximum_guests')
    FROM stueble_codes
    WHERE stueble_id = $1;
$$ LANGUAGE SQL;

ALTER TABLE stueble_codes
    ADD CONSTRAINT stueble_codes_max_guests_check
    CHECK (stueble_max_guests(stueble_id));

ALTER TABLE users
ADD CONSTRAINT unique_room_residence UNIQUE (room, residence);