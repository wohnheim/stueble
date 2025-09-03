import select
import json
import backend.sql_connection.database as db
from backend.sql_connection import users
import warnings
from enum import Enum

class Event_Notify(str, Enum):
    ARRIVE = "ARRIVE"
    LEAVE = "LEAVE"

def is_valid_event_notify(other):
    if isinstance(other, Event_Notify):
        return other in Event_Notify._value2member_map_
    return NotImplemented

conn = db.connect()
cursor = conn.cursor()

cursor.execute("LISTEN guest_list_update;")
def listen_to_db(connection, socketio):
    """
    Listens to the database for notifications on the channel 'guest_list_update'.
    When a notification is received, it processes the payload and retrieves user information.
    The payload is expected to be a JSON string with keys: event, user_id, stueble_id

    Parameters:
        connection: psycopg2 connection object
        socketio: SocketIO object to emit events to clients
    """
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
            user_id = data["user_id"]
            stueble_id = data["stueble_id"]
            result = users.get_user(cursor=cursor, user_id=user_id, keywords=["first_name", "last_name", "personal_hash"])
            if result["success"] is False:
                # TODO catch this, e.g. by sending an error message to api.py
                warnings.warn(f"Could not get user with id {user_id}")
                continue
            # NOTE only use personal_hash for the guest_list not publically available for hosts etc.
            first_name, last_name, personal_hash = result["data"]
            data = {"first_name": first_name,
                    "last_name": last_name,
                    "personal_hash": personal_hash}
            socketio.emit("db_event", {"payload": data})
