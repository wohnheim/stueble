# Stüble
This repo manages the automatic access system for the stueble.
It is splitted into frontend, backend and data (persistent data management).

## Frontend

## Backend

## Data
As persistent data management a postgres database is used. The user matches the Linux user (stueble).
Information to the tables can be found in [notes.md](packages/backend/notes.md).

## ENV-Variables
USERDB: stueble<br>
PASSWORD<br>
HOST: localhost<br>
PORT 5432<br>
DBNAME: stueble_data

## TODO
- Benutzername ändern (UI)
- Einladende Person anzeigen (UI)
- Wirte-Berechtigung nach einer bestimmten Zeit entfernen (Backend)
