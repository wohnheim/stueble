CREATE EXTENSION IF NOT EXISTS "pgcrypto";
ALTER TABLE users
ADD COLUMN session_id TEXT DEFAULT encode(gen_random_bytes(16), 'hex') UNIQUE NOT NULL;

INSERT INTO configurations (key, value)
VALUES ('session_expiration_days', '30');