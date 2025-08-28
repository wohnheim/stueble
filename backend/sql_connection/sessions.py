from backend.data_types import *
import database as db
from typing import Annotated
from datetime import datetime, timedelta
import pytz
import json

def create_session(connection, cursor, user_id: int, expiration_date: str) -> dict:
    """
    creates a session for a user in the table sessions

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int): id of the user
        expiration_date (str): expiration date of the session (YYYY-MM-DD HH:MM:SS)
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occured
    """
    with open("config.json", "r") as file:
        config = json.load(file)
    try:
        expiration_time = config["sessions"]["expirationTime"]
    except KeyError:
        raise KeyError("Session expiration time not found in config.json.")
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(tz)
    expiration_date = now + timedelta(days=expiration_time)

    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="sessions",
        arguments={"user_id": user_id, "expiration_date": expiration_date},
        returning=True)

    # TODO return the session_id if successful
    return result