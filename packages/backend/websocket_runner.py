import select
import json
import psycopg2
import requests
import warnings

from packages import backend as db
from packages.backend.sql_connection import users
from packages.backend.data_types import *

def is_valid_event_notify(other):
    if isinstance(other, Event_Notify):
        return other in Event_Notify._value2member_map_
    return NotImplemented

conn = db.connect()
cursor = conn.cursor()

cursor.execute("LISTEN guest_list_update;")
def listen_to_db(connection):
    """
    Listens to the database for notifications on the channel 'guest_list_update'.
    When a notification is received, it processes the payload and retrieves user information.
    The payload is expected to be a JSON string with keys: event, user_id, stueble_id

    Parameters:
        connection: psycopg2 connection object
    """
    connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)  # autocommit mode
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
            event = data["event"] # only possible events are arrive and leave for notifications to be sent
            event = Event_Notify(event)
            user_id = data["user_id"]
            stueble_id = data["stueble_id"]
            result = users.get_user(cursor=cursor, user_id=user_id, keywords=["first_name", "last_name", "personal_hash"])
            if result["success"] is False:
                # TODO catch this, e.g. by sending an error message to api.py
                warnings.warn(f"Could not get user with id {user_id}")
                continue
            # NOTE only use personal_hash for the guest_list not publicly available for hosts etc.
            first_name, last_name, personal_hash = result["data"]
            data = {"first_name": first_name,
                    "last_name": last_name,
                    "personal_hash": personal_hash,
                    "stueble_id": stueble_id,
                    "event": event}
            response = requests.post("http://127.0.0.1:5000/websocket_local", json=data)
            if response.status_code != 200:
                warnings.warn(f"Could not send data to websocket server: {response.text}")
                continue
            # TODO handle error