import json
import select
import warnings

import psycopg2
from psycopg2.extensions import connection
import requests

from packages.backend.data_types import Event_Notify
from packages.backend.sql_connection import database as db
from packages.backend.sql_connection import users

def is_valid_event_notify(other):
    if isinstance(other, Event_Notify):
        return other in Event_Notify._value2member_map_
    return NotImplemented

conn, cursor = db.connect()

cursor.execute("LISTEN automatically_removed_users;")
def listen_to_db(connection: connection):
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
            if not set(data[0].keys()) == {"event", "user_id", "stueble_id"}:
                # TODO catch this, e.g. by sending an error message to api.py
                warnings.warn("Keys don't match")
                continue
            # event is always remove
            for removed_user in data:
                event = removed_user["event"]
                event = Event_Notify(event) # only possible events are arrive and leave for notifications to be sent
                user_id = removed_user["user_id"]
                stueble_id = removed_user["stueble_id"]
                result = users.get_user(cursor=cursor, user_id=user_id, keywords=["first_name", "last_name", "user_uuid"])
                if result["success"] is False:
                    # TODO catch this, e.g. by sending an error message to api.py
                    warnings.warn(f"Could not get user with id {user_id}")
                    continue
                # NOTE only use user_uuid for the guest_list not publicly available for hosts etc.
                first_name, last_name, user_uuid = result["data"]
                removed_user_data = {"first_name": first_name,
                        "last_name": last_name,
                        "user_uuid": user_uuid,
                        "stueble_id": stueble_id,
                        "event": event}
                # TODO configure url
                response = requests.post("http://127.0.0.1:3000/websocket_local", json=removed_user_data)
                if response.status_code != 200:
                    warnings.warn(f"Could not send data to websocket server: {response.text}")
                    continue
                # TODO handle error