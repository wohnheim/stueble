# Login
- Hash will be using HMAC

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
  - email (text, !NULL, contains '*@*.*')
  - password (text, !NULL (NULL when extern) when initializing, hash using hmac)
  - role (text, !NULL (NULL when extern), default='user') (in python ENUM) -> to frontend host / admin
  - invited_by (ID can't loop, can just reference IDs, that have invited_by == NULL !!!)
When a user is deleted, just the password will be set to null !!!
Externs can be completely deleted before the present

- Events
  - ID (int, generated_automatically, primary_key)
  - userID (referenced <- Users, !NULL)
  - type (text, !NULL) (in python ENUM) (add, remove, arrive, leave, modify)
  - affected (UnsignedInt, referenced <- Users, !NULL)
  - submitted (timestamptz, !NULL, default=now())


## SQL-Functions
- SessionID
  - expiration_date (remove if older than 1 month)
- Guest Lists will be created in Python

## Weitere Informationen
- Datenbanktyp: Postgres

# Externe Dienste
strato