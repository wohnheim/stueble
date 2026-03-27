CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

INSERT INTO category (name) VALUES
('Sonstiges');


CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category CATEGORY NOT NULL,
    location TEXT NOT NULL,
    start DATE NOT NULL,
    end DATE,
    full_days BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    image TEXT,

    CONSTRAINT unique_event UNIQUE (name, start)
);

CREATE TABLE IF NOT EXISTS participants (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    UNIQUE (event_id, user_id)
);