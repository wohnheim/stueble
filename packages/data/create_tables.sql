-- Description: create tables, types, check functions for database

-- SET TIMEZONE TO 'Europe/Berlin';
-- SET DateStyle TO ISO, YMD;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- enum for user_role in table users
CREATE TYPE USER_ROLE AS ENUM ('admin', 'tutor', 'host', 'user', 'extern');

-- enum for event_type in table events
-- arrive, leave will be handled by python, add, remove, modify by triggers
CREATE TYPE EVENT_TYPE AS ENUM('add', 'remove', 'arrive', 'leave');

CREATE TYPE ACTION_TYPE AS ENUM('guestArrived', 'guestLeft', 'guestAdded', 'guestRemoved', 'userVerification');

-- CREATE TYPE VERIFICATION AS ENUM('idCard', 'roomKey', 'kolping');

-- enum for residence in table users
CREATE TYPE RESIDENCE AS ENUM('altbau', 'neubau', 'anbau', 'hirte');

-- table to save users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_role USER_ROLE NOT NULL,
    room INTEGER CHECK ((user_role = 'extern' AND room IS NULL) OR (user_role != 'extern' AND room > 0 AND user_role != 'admin') OR (user_role = 'admin' AND room = 0)),
    residence RESIDENCE NULL CHECK ((user_role = 'extern' AND residence IS NULL) OR (user_role != 'extern' AND residence IS NOT NULL)),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password_hash VARCHAR(255) CHECK ((user_role = 'extern' AND password_hash IS NULL) OR user_role != 'extern'),
    email VARCHAR(255) UNIQUE CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$' OR password_hash is NULL),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    user_uuid UUID UNIQUE NOT NULL, -- added for personal references, not as easy to guess as id
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    user_name TEXT CHECK ((user_role = 'extern' AND user_name IS NULL) OR (user_role != 'extern' AND user_name IS NOT NULL)),
    verified BOOLEAN DEFAULT NULL
);

-- table for stueble mottos
CREATE TABLE IF NOT EXISTS stueble_motto (
    id SERIAL PRIMARY KEY,
    motto TEXT NOT NULL,
    date_of_time DATE NOT NULL UNIQUE CHECK (date_of_time >= CURRENT_DATE OR (date_of_time = CURRENT_DATE - 1 AND CURRENT_TIME < '06:00:00')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    shared_apartment TEXT,
    description TEXT
);

-- table to save login sessions
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    expiration_date TIMESTAMPTZ NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    session_id UUID NOT NULL UNIQUE
);

-- table to save user and host events
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    invited_by INTEGER REFERENCES users(id),
    event_type EVENT_TYPE NOT NULL,
    submitted TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stueble_id INTEGER REFERENCES stueble_motto(id) NOT NULL
);

CREATE TABLE IF NOT EXISTS events_affected_users (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) NOT NULL,
    affected_user_id INTEGER REFERENCES users(id) NOT NULL,
    submitted TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
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
('maximum_guests_per_tutor', '10'), 
('reset_code_expiration_minutes', '15'),
('qr_code_expiration_minutes', '10');

CREATE TABLE IF NOT EXISTS allowed_users (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    room INTEGER CHECK (room > 0),
    residence RESIDENCE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reset_code UUID UNIQUE NOT NULL,
    additional_data JSONB DEFAULT NULL, -- to store optional changes in users
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

CREATE TABLE IF NOT EXISTS websocket_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id) NOT NULL,
    action ACTION_TYPE NOT NULL,
    message_content JSONB,
    required_role USER_ROLE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS websockets_affected (
    id SERIAL PRIMARY KEY, 
    message_id INTEGER REFERENCES websocket_messages(id) NOT NULL,
    session_id INTEGER REFERENCES sessions(id) NOT NULL, 
    received BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    stueble_id INTEGER REFERENCES stueble_motto(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, stueble_id)
);

CREATE FUNCTION get_submitted_timestamp(INTEGER) RETURNS timestamptz AS $$
    SELECT submitted FROM events WHERE id = $1 LIMIT 1;
$$ LANGUAGE SQL;

ALTER TABLE users
ADD CONSTRAINT unique_room_residence UNIQUE (room, residence);