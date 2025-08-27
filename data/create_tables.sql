-- Description: create tables, types, check functions for database

-- enum for user_role in table users
CREATE TYPE USER_ROLE AS ENUM ('admin', 'host', 'guest', 'extern');

-- enum for event_type in table events
-- arrive, leave will be handled by python, add, remove, modify by triggers
CREATE TYPE EVENT_TYPE AS ENUM('add', 'remove', 'arrive', 'leave', 'modify');

-- check function for valid invited_by id in users
CREATE FUNCTION is_valid_invited_by_id(INTEGER) RETURNS boolean AS $$
    SELECT $1 IS NOT NULL;
$$ LANGUAGE SQL;

-- table to save users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_role USER_ROLE NOT NULL,
    room INTEGER CHECK ((user_role = 'extern' AND room IS NULL) OR (user_role != 'guest' AND room > 0)), 
    residence INTEGER CHECK ((user_role = 'extern' AND residence IS NULL) OR (user_role != 'guest' AND residence > 0)),
    first_name TEXT NOT NULL, 
    last_name TEXT NOT NULL, 
    email VARCHAR(255) UNIQUE NOT NULL CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$'),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, 
    invited_by INTEGER REFERENCES users(id) CHECK (invited_by IS NULL OR (id != invited_by AND is_valid_invited_by_id(invited_by)))
);

-- table to save login sessions
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    expiration_date TIMESTAMPTZ NOT NULL, 
    userID INTEGER REFERENCES users(id) NOT NULL
);

-- table to save user and host events
CREATE TABLE events (
    id SERIAL PRIMARY KEY, 
    userID INTEGER REFERENCES users(id) NOT NULL, 
    event_type EVENT_TYPE NOT NULL, 
    affected INTEGER REFERENCES users(id) NOT NULL,
    submitted TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
)