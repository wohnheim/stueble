-- Description: create tables, types, check functions for database

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- enum for user_role in table users
CREATE TYPE USER_ROLE AS ENUM ('admin', 'host', 'guest', 'extern');

-- enum for event_type in table events
-- arrive, leave will be handled by python, add, remove, modify by triggers
CREATE TYPE EVENT_TYPE AS ENUM('add', 'remove', 'arrive', 'leave', 'modify');

-- check function for valid invited_by id in users
CREATE FUNCTION is_valid_invited_by_id(INTEGER) RETURNS boolean AS $$
    SELECT $1 FROM users IS NOT NULL;
$$ LANGUAGE SQL;

-- table to save users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_role USER_ROLE NOT NULL,
    room INTEGER CHECK ((user_role = 'extern' AND room IS NULL) OR (user_role != 'guest' AND room > 0)), 
    residence INTEGER CHECK ((user_role = 'extern' AND residence IS NULL) OR (user_role != 'guest' AND residence > 0)),
    first_name TEXT NOT NULL, 
    last_name TEXT NOT NULL, 
    email VARCHAR(255) UNIQUE NOT NULL CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$'),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, 
    personal_hash TEXT DEFAULT encode(gen_random_bytes(16), 'hex') UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS stueble_motto (
    id SERIAL PRIMARY KEY, 
    motto TEXT NOT NULL,
    date_of_time TIMESTAMPTZ NOT NULL, 
    shared_apartment TEXT
);

CREATE TABLE IF NOT EXISTS stueble_codes (
    id SERIAL PRIMARY KEY, 
    userID INTEGER REFERENCES users(id) NOT NULL, 
    code TEXT DEFAULT encode(gen_random_bytes(16), 'hex') UNIQUE NOT NULL, 
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, 
    expiration_date TIMESTAMPTZ NOT NULL, 
    stueble_id INTEGER REFERENCES stueble_motto(id) NOT NULL,
    invited_by INTEGER REFERENCES users(id) CHECK (invited_by IS NULL OR (id != invited_by AND is_valid_invited_by_id(invited_by)))
);

-- table to save login sessions
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    expiration_date TIMESTAMPTZ NOT NULL, 
    userID INTEGER REFERENCES users(id) NOT NULL,
    session_id TEXT DEFAULT encode(gen_random_bytes(16), 'hex') UNIQUE NOT NULL
);

-- table to save user and host events
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY, 
    userID INTEGER REFERENCES users(id) NOT NULL, 
    event_type EVENT_TYPE NOT NULL, 
    affected INTEGER REFERENCES users(id) NOT NULL,
    submitted TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- table to save configuration settings
CREATE TABLE IF NOT EXISTS config (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL
);