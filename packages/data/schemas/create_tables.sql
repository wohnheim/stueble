-- SET TIMEZONE TO 'Europe/Berlin';
-- SET DateStyle TO ISO, YMD;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- enum for user_role in table users
CREATE TYPE USER_ROLE AS ENUM ('admin', 'tutor', 'host', 'user', 'extern');

-- enum for residence in table users
CREATE TYPE RESIDENCE AS ENUM('altbau', 'neubau', 'anbau', 'hirte');

-- table to save users
BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(), -- added for personal references, not as easy to guess as id
    user_role USER_ROLE NOT NULL,
    room INTEGER CHECK ((user_role = 'extern' AND room IS NULL) OR (user_role != 'extern' AND user_role != 'admin' AND room > 0) OR (user_role = 'admin' AND room = 0)),
    residence RESIDENCE NULL CHECK ((user_role = 'extern') = (residence IS NULL)),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password_hash VARCHAR(255) CHECK ((user_role = 'extern') = (password_hash IS NULL)),
    password_salt VARCHAR(64) CHECK ((password_algorithm = 'bcrypt' OR password_hash IS NULL) = (password_salt IS NULL)),
    password_algorithm VARCHAR(20) CHECK (num_nulls(password_hash, password_algorithm) IN (0, 2)),
    email VARCHAR(255) CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$' OR (password_hash is NULL AND email is NOT NULL)),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    user_name TEXT CHECK ((user_role = 'extern') = (user_name IS NULL)),
    verified BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE
);

CREATE UNIQUE INDEX IF NOT EXISTS users_room_residence_key ON users (room, residence) WHERE (user_role != 'extern' AND NOT deleted);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (email) WHERE (user_role != 'extern' AND NOT deleted);
CREATE UNIQUE INDEX IF NOT EXISTS users_user_name_key ON users (user_name) WHERE (user_role != 'extern' AND NOT deleted);

COMMIT;

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
('maximum_guests', '150'),
('maximum_invites_per_user', '2'),
('maximum_guests_per_tutor', '10');

CREATE TABLE IF NOT EXISTS verification_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    additional_data JSONB, -- to store optional changes in users
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expiration_date TIMESTAMPTZ
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
