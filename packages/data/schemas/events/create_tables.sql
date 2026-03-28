-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS events;

CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

INSERT INTO category (name) VALUES
('Sonstiges');


CREATE TABLE IF NOT EXISTS events.events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category CATEGORY NOT NULL,
    location TEXT NOT NULL,
    start_time DATE NOT NULL,
    end_time DATE,
    full_days BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    image TEXT,

    CONSTRAINT unique_event UNIQUE (name, start_time)
);

CREATE TABLE IF NOT EXISTS events.participants (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events.events(id) ON DELETE CASCADE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    UNIQUE (event_id, user_id)
);