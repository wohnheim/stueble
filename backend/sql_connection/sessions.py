from backend.data_types import *
import database as db
from typing import Annotated
from datetime import datetime, timedelta
import pytz

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

    # load the configuration variable for session expiration time in days from table configurations
    expiration_time = db.read_table(cursor=cursor, keywords=["value"], table_name="configurations", conditions={"key": "session_expiration_days"}, expect_single_answer=True)
    if expiration_time["success"] is False:
        return {"success": False, "error": expiration_time["error"]}
    expiration_time = int(expiration_time["data"][0])

    # calculate expiration date
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(tz)
    expiration_date = now + timedelta(days=expiration_time)

    # set the expiration_date
    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="sessions",
        arguments={"user_id": user_id, "expiration_date": expiration_date},
        returning="session_id")
    if result["success"] is False:
        return {"success": False, "error": result["error"]}

    return {"success": True, "data": result["data"]}