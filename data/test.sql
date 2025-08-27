CREATE EXTENSION IF NOT EXISTS "pgcrypto";
ALTER TABLE users
ADD COLUMN personal_hash TEXT DEFAULT encode(gen_random_bytes(16), 'hex') UNIQUE NOT NULL;