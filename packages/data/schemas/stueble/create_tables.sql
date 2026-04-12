-- Description: create tables, types, check functions for database

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS stueble;


-- enum for event_type in table events
-- arrive, leave will be handled by python, add, remove, modify by triggers
CREATE TYPE stueble.EVENT_TYPE AS ENUM('add', 'remove', 'arrive', 'leave');


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

CREATE TABLE IF NOT EXISTS stueble.application_groups (
    id SERIAL PRIMARY KEY,
    group_hash TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS stueble.applicants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    application_group INTEGER REFERENCES stueble.application_groups(id) ON DELETE CASCADE NOT NULL,

    UNIQUE (user_id, application_group)
);

CREATE TABLE IF NOT EXISTS stueble.applications (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    motto TEXT NOT NULL,
    description TEXT,
    image TEXT,
    date_of_time DATE NOT NULL CHECK (date_of_time >= CURRENT_DATE),
    application_priority INTEGER NOT NULL CHECK (application_priority > 0),
    application_group INTEGER NOT NULL CHECK (application_group > 0) REFERENCES stueble.application_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (date_of_time, application_group),
    UNIQUE (application_group, application_priority)
);

CREATE TABLE IF NOT EXISTS stueble.available_dates (
    id SERIAL PRIMARY KEY,
    date_of_time DATE NOT NULL CHECK (date_of_time >= CURRENT_DATE) UNIQUE
);

CREATE TABLE IF NOT EXISTS stueble.dates (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES stueble.applications(id) ON DELETE CASCADE NOT NULL UNIQUE
);

CREATE VIEW stueble.motto (id, uuid, motto, description, date_of_time, host_group) AS (
    SELECT id, uuid, motto, description, date_of_time, application_group
    FROM stueble.applications
    WHERE id in (SELECT application_id FROM stueble.dates)
);

CREATE VIEW stueble.hosts (user_id, stueble_id, stueble_uuid) AS (
    WITH stuebles AS (
        SELECT id, uuid, application_group
        FROM stueble.applications
        WHERE id IN (SELECT application_id FROM stueble.dates)
    )
    SELECT h.user_id, a.id, a.uuid
    FROM stueble.applicants h
    JOIN stuebles a ON h.application_group = a.application_group
);

-- table to save user and host events
CREATE TABLE IF NOT EXISTS stueble.events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    invited_by INTEGER REFERENCES users(id),
    event_type stueble.EVENT_TYPE NOT NULL,
    submitted TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stueble_id INTEGER REFERENCES stueble.dates(application_id) NOT NULL
);

CREATE FUNCTION get_submitted_timestamp(INTEGER) RETURNS timestamptz AS $$
    SELECT submitted FROM stueble.events WHERE id = $1 LIMIT 1;
$$ LANGUAGE SQL;

CREATE TABLE IF NOT EXISTS stueble.dates_draft (
    id SERIAL PRIMARY KEY,
    date_of_time DATE NOT NULL CHECK (date_of_time >= CURRENT_DATE),
    automatically_matched BOOLEAN NOT NULL DEFAULT TRUE,
    application_id INTEGER REFERENCES stueble.applications(id) ON DELETE CASCADE NOT NULL
);

CREATE TABLE IF NOT EXISTS stueble.draft_dates_selection (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES stueble.applications(id) ON DELETE CASCADE NOT NULL UNIQUE,
    selected BOOLEAN NOT NULL DEFAULT FALSE,
    changed_by INTEGER REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);