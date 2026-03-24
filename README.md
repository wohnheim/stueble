# Stüble

This repo manages the automatic access system for the Stüble.
It is split into frontend, backend and data (persistent data management).

## Frontend

The frontend uses the [Yarn Classic](https://classic.yarnpkg.com) package manager.

**Important:** The development shell only serves the frontend. It must be built manually using the command:

```
yarn run build
```

## Backend

The backend can be built using the [Nix](https://nixos.org/nix) package manager.

```
nix build .#backend
```

## Data

As persistent data management a PostgreSQL database is used. The user matches the Linux user (stueble).
Information to the tables can be found in [notes.md](packages/backend/notes.md).

## Environment variables

| <div style="width:250px">Database</div> | <div style="width:250px">Recommended value</div> |
| --------------------------------------- | ------------------------------------------------ |
| PGUSER                                  | stueble                                          |
| PGPASSWORD                              |                                                  |
| PGHOST                                  | 127.0.0.1                                        |
| PGPORT                                  | 5432                                             |
| PGDATABASE                              | stueble_data                                     |

| <div style="width:250px">General</div> | <div style="width:250px">Recommended value</div> |
| --------------------------------------- | ------------------------------------------------ |
| HOST                                    | 127.0.0.1                                        |
| PORT                                    | 3000                                             |
| WS_PORT                                 | 3001                                             |
| EMAIL_ADDRESS                           | stuebleheshirte@gmail.com                        |
| EMAIL_PASSWORD                          |                                                  |
| PRIVATE_KEY                             |                                                  |
| PUBLIC_KEY                              |                                                  |

## Development shell

A development shell with all required dependencies can be started. This requires [Nix](https://nixos.org/nix).

```
nix develop
```

The components contained in this shell can be managed independently using [Overmind](https://github.com/DarthSim/overmind).

```
overmind restart frontend,database,backend,webserver
```

## TODO

- Benutzername ändern (UI)
- Einladende Person anzeigen (UI)
- Wirte-Berechtigung nach einer bestimmten Zeit entfernen (Backend)
