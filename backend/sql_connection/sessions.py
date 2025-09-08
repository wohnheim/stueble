from backend.data_types import *
import backend.sql_connection.database as db
from backend.data_types import *
from typing import Annotated
from datetime import datetime, timedelta
import pytz

from backend.sql_connection.common_functions import clean_single_data


def create_session(connection, cursor, user_id: int) -> dict:
    """
    creates a session for a user in the table sessions

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int): id of the user
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
        returning_column="session_id")
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return clean_single_data(result)

def get_session(cursor, session_id: str) -> dict:
    """
    gets the session of a user from the table sessions
    Parameters:
        cursor: cursor for the connection
        session_id (str): id of the session
    Returns:
        dict: {"success": bool, "data": (session_id, expiration_date)}, {"success": False, "error": e} if error occurred
    """

    result = db.read_table(
        cursor=cursor,
        keywords=["session_id", "expiration_date"],
        table_name="sessions",
        expect_single_answer=True,
        conditions={"session_id": session_id})
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no session found"}
    return result

def remove_session(connection, cursor, session_id: str) -> dict:
    """
    removes a session from the table sessions
    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        session_id (str): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    result = db.remove_table(
        connection=connection,
        cursor=cursor,
        table_name="sessions",
        conditions={"session_id": session_id},
        returning_column="session_id")
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no session found"}
    return result

def get_user(cursor, session_id: str, keywords: list[str]=["id", "user_role"]) -> dict:
    """
    gets the user role of a user from the table users via the sessions table
    Parameters:
        cursor: cursor for the connection
        session_id (str): id of the user
        keywords (list[str]): list of keywords to be returned
    Returns:
        dict: {"success": bool, "data": user_role}, {"success": False, "error": e} if error occurred
    """

    allowed_keywords = ["id", "user_role", "first_name", "last_name", "email", "room", "residence"]
    result = db.read_table(
        cursor=cursor,
        keywords=["u." + i for i in keywords],
        table_name="sessions s JOIN users u ON s.user_id = u.id",
        expect_single_answer=True,
        conditions={"s.session_id": session_id})
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no matching session and user found"}
    if result["success"] and len(keywords) == 1:
        return clean_single_data(result)
    return result

def remove_user_sessions(connection, cursor, user_id: int) -> dict:
    """
    removes all sessions of a user from the table sessions
    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    result = db.remove_table(
        connection=connection,
        cursor=cursor,
        table_name="sessions",
        conditions={"user_id": user_id},
        returning_column="session_id")
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no sessions found"}
    return result