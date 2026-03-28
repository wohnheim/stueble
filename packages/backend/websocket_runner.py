import json
import select
import warnings

from psycopg import Connection, Cursor
from psycopg.rows import TupleRow
import requests

from backend.datatypes.stueble_types import Event_Notify
from backend.database import database as db
from backend.sql_connection import users

def is_valid_event_notify(other):
    if isinstance(other, Event_Notify):
        return other in Event_Notify._value2member_map_
    return NotImplemented

cursor = db.connect()

def listen_to_db(connection: Connection, cursor: Cursor[TupleRow]):
    """
    Listens to the database for notifications on the channel 'automatically_removed_users'.
    When a notification is received, it processes the payload and retrieves user information.
    The payload is expected to be a JSON string with keys: event, user_id, stueble_id

    Args:
        Connection: psycopg connection object
        Cursor: psycopg cursor object
    """
    connection.autocommit = True
    cursor.execute("LISTEN automatically_removed_users;")
    while True:
        if select.select([connection], [], [], 0.5) == ([], [], []):
            continue
        connection.poll()
        while connection.notifies:
            notify = connection.notifies.pop(0)
            data = json.loads(notify.payload)
            if not set(data.keys()) == {"event", "user_id", "stueble_id"}:
                # TODO catch this, e.g. by sending an error message to api.py
                warnings.warn("Keys don't match")
                continue
            # event = data["event"]
            # event = Event_Notify(event) # only possible events are arrive and leave for notifications to be sent
            user_id = data["user_id"]
            stueble_id = data["stueble_id"]
            result = users.get_user(user_id=user_id, columns=["first_name", "last_name", "user_uuid"])
            if result.is_error:
                # TODO catch this, e.g. by sending an error message to api.py
                warnings.warn(f"Could not get user with id {user_id}")
                continue
            # NOTE only use user_uuid for the guest_list not publicly available for hosts etc.
            removed_user_data = result.data
            removed_user_data["stueble_id"] = stueble_id
                    # "event": event}
            # TODO configure url
            response = requests.post("http://127.0.0.1:3000/websocket_local", json=removed_user_data)
            if response.status_code != 200:
                warnings.warn(f"Could not send data to websocket server: {response.text}")
                continue
            # TODO handle error

def run_listener():
    listen_to_db(cursor.connection, cursor)
