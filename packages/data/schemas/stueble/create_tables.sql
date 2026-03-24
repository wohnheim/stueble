-- Description: create tables, types, check functions for database

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS stueble;


-- enum for event_type in table events
-- arrive, leave will be handled by python, add, remove, modify by triggers
CREATE TYPE stueble.EVENT_TYPE AS ENUM('add', 'remove', 'arrive', 'leave');


-- CREATE TYPE VERIFICATION AS ENUM('idCard', 'roomKey', 'kolping');

-- table for stueble mottos
CREATE TABLE IF NOT EXISTS stueble.motto (
    id SERIAL PRIMARY KEY,
    motto TEXT NOT NULL,
    date_of_time DATE NOT NULL UNIQUE CHECK (date_of_time >= CURRENT_DATE OR (date_of_time = CURRENT_DATE - 1 AND CURRENT_TIME < '06:00:00')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    shared_apartment TEXT,
    description TEXT
);

-- table to save user and host events
CREATE TABLE IF NOT EXISTS stueble.events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    invited_by INTEGER REFERENCES users(id),
    event_type stueble.EVENT_TYPE NOT NULL,
    submitted TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stueble_id INTEGER REFERENCES stueble.motto(id) NOT NULL
);

CREATE TABLE IF NOT EXISTS stueble.allowed_users (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    room INTEGER CHECK (room > 0),
    residence RESIDENCE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL
);

/*
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
*/

CREATE TABLE IF NOT EXISTS stueble.hosts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    stueble_id INTEGER REFERENCES stueble.motto(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, stueble_id)
);

CREATE FUNCTION get_submitted_timestamp(INTEGER) RETURNS timestamptz AS $$
    SELECT submitted FROM stueble.events WHERE id = $1 LIMIT 1;
$$ LANGUAGE SQL;


CREATE TABLE IF NOT EXISTS stueble.applications (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL,
    motto TEXT NOT NULL,
    date DATE NOT NULL CHECK (date >= CURRENT_DATE),
    application_group INTEGER NOT NULL,
    application_priority INTEGER NOT NULL CHECK (application_priority > 0)
);

CREATE TABLE IF NOT EXISTS stueble.applicants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    application_id INTEGER REFERENCES stueble.applications(id) ON DELETE CASCADE NOT NULL,
    application_group INTEGER NOT NULL CHECK (application_group > 0)
);

-- Avoid undefined relation error
ALTER TABLE stueble.applications
ADD CONSTRAINT application_group_constraint FOREIGN KEY (application_group) REFERENCES stueble.applicants(application_group) ON DELETE CASCADE