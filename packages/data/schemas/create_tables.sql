-- SET TIMEZONE TO 'Europe/Berlin';
-- SET DateStyle TO ISO, YMD;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- enum for user_role in table users
CREATE TYPE USER_ROLE AS ENUM ('admin', 'tutor', 'host', 'user', 'extern');

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
    verified BOOLEAN DEFAULT FALSE
);

-- table to save login sessions
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    expiration_date TIMESTAMPTZ NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    session_id UUID NOT NULL UNIQUE
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
('maximum_invites_per_user', '2'),
('maximum_guests_per_tutor', '10'),
('reset_code_expiration_minutes', '15'),
('qr_code_expiration_minutes', '10');

CREATE TABLE IF NOT EXISTS verification_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reset_code UUID UNIQUE NOT NULL,
    additional_data JSONB DEFAULT NULL, -- to store optional changes in users
    used BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS websocket_messages (
    id SERIAL PRIMARY KEY,
    -- session_id INTEGER REFERENCES sessions(id) NOT NULL,
    event TEXT NOT NULL,
    data JSONB,
    required_role USER_ROLE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS websockets_affected (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES websocket_messages(id) NOT NULL,
    session_id INTEGER REFERENCES sessions(id) NOT NULL,
    received BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_DATE
);

ALTER TABLE users
ADD CONSTRAINT unique_room_residence UNIQUE (room, residence);
