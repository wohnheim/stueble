# Login
- Hash will not be using HMAC

# Tables
- Sessions
  - SessionID (int, generated_automatically, primary_key) <- can be deleted
  - expiration_date (timestamptz, !NULL)
  - userID (UnsignedInt, referenced <- Users, !NULL)

- Users
  - ID (int, generated_automatically, primary_key)
  - room (Unsigned Int, !NULL (NULL when extern))
  - residence (Unsigned Int, !NULL (NULL when extern))
  - first_name (text, !NULL)
  - last_name (text, !NULL)
  - email (text, UNIQUE, !NULL, contains '*@*.*')
  - password_hash (text, !NULL (NULL when extern) when initializing, hash using not hmac)
  - user_role (text, !NULL (NULL when extern), default='user') (in python ENUM) -> to frontend host / admin
  - invited_by (ID can't loop, can just reference IDs, that have invited_by == NULL !!!)
When a user is deleted, just the password will be set to null !!!
Externs can be completely deleted before the present

- Events
  - ID (int, generated_automatically, primary_key)
  - userID (referenced <- Users, !NULL)
  - event_type (text, !NULL) (in python ENUM) (add, remove, arrive, leave, modify)
  - affected (UnsignedInt, referenced <- Users, !NULL)
  - submitted (timestamptz, !NULL, default=now())

stueble_motto
  - id SERIAL PRIMARY KEY, 
  - motto TEXT NOT NULL,
  - date_of_time TIMESTAMPTZ NOT NULL, 
  - shared_apartment TEXT

stueble_codes
  - id SERIAL PRIMARY KEY, 
  - userID INTEGER REFERENCES users(id) NOT NULL, 
  - code TEXT DEFAULT encode(gen_random_bytes(16), 'hex') UNIQUE NOT NULL, 
  - created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, 
  - expiration_date TIMESTAMPTZ NOT NULL, 
  - stueble_id INTEGER REFERENCES stueble_motto(id) NOT NULL

## SQL-Functions
- SessionID
  - expiration_date (remove if older than 1 month)
- Guest Lists will be created in Python
- Run SQL code with: psql -d stueble_data -f filename.sql

## Weitere Informationen
- Datenbanktyp: Postgres
- User: stueble
- Further information can be found in [create_tables.sql](../data/create_tables.sql)

# Externe Dienste
strato
