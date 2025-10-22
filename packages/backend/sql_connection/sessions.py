from psycopg2.extensions import cursor
import pytz
from datetime import datetime, timedelta

from packages.backend.data_types import UserRole
from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.ultimate_functions import clean_single_data

def create_session(cursor: cursor, user_id: int) -> dict:
    """
    creates a session for a user in the table sessions

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occured
    """

    # load the configuration variable for session expiration time in days from table configurations
    result = db.read_table(cursor=cursor, keywords=["value"], table_name="configurations", conditions={"key": "session_expiration_days"}, expect_single_answer=True)
    if result["success"] is False:
        return result
    elif result["data"] is None:
        return {"success": False, "error": "Invalid result data"}

    expiration_time = int(result["data"][0])

    # calculate expiration date
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(tz)
    expiration_date = now + timedelta(days=expiration_time)
    expiration_date = expiration_date.replace(hour=5, minute=30, second=0, microsecond=0)  # set expiration time to 5:30am

    # set the expiration_date
    result = db.insert_table(
        cursor=cursor,
        table_name="sessions",
        arguments={"user_id": user_id, "expiration_date": expiration_date},
        returning_column="session_id")

    # handle error, return result
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    else:
        return {"success": True, "data": list(result["data"]) + [expiration_date]}

def get_session(cursor: cursor, session_id: str) -> dict:
    """
    gets the session of a user from the table sessions
    Parameters:
        cursor: cursor for the connection
        session_id (str): id of the session
    Returns:
        dict: {"success": bool, "data": (session_id, expiration_date)}, {"success": False, "error": e} if error occurred
    """

    # initialize keywords
    keywords = ["expiration_date"]

    # fetch session_id, expiration_date of a session_id
    result = db.read_table(
        cursor=cursor,
        keywords=keywords,
        table_name="sessions",
        expect_single_answer=True,
        specific_where="session_id = %s AND expiration_date > NOW()",
        variables=[session_id])

    # handle error
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no session found"}

    # combine keys and values
    result["data"] = dict(zip(keywords, result["data"]))

    # return data
    return result

def remove_session(cursor: cursor, session_id: str) -> dict:
    """
    removes a session from the table sessions
    Parameters:
        cursor: cursor for the connection
        session_id (str): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    # remove session from sessions table
    result = db.remove_table(
        cursor=cursor,
        table_name="sessions",
        conditions={"session_id": session_id},
        returning_column="session_id")

    # handle error
    if result["success"] is True and result["data"] is None:
        return {"success": False, "error": "no session found"}

    # return result
    return result

def get_user(cursor: cursor, session_id: str, keywords: tuple[str] | list[str] | None = None) -> dict:
    """
    gets the user role of a user from the table users via the sessions table
    Parameters:
        cursor: cursor for the connection
        session_id (str): id of the user
        keywords (tuple[str] | list[str]): list of keywords to be returned
    Returns:
        dict: {"success": bool, "data": user_role}, {"success": False, "error": e} if error occurred
    """

    # set allowed keywords
    allowed_keywords = ["id", "user_role", "user_uuid", "room", "residence", "first_name", "last_name", "email", "user_name"]

    # set default keywords if none were specified
    if keywords is None:
        keywords = ["id", "user_role","user_uuid", "first_name", "last_name"]
    else:
        # set specified keywords and check, whether they're valid
        keywords = list(keywords)
        if not all(map(lambda k: k in allowed_keywords, keywords)):
            return { "success": False, "error": "invalid keywords specified"}

    # fetch data
    result = db.read_table(
        cursor=cursor,
        keywords=["u." + i for i in keywords],
        table_name="sessions s JOIN users u ON s.user_id = u.id",
        expect_single_answer=True,
        conditions={"s.session_id": session_id})

    if result["success"] is True and result["data"] is None:
        return {"success": False, "error": "no matching session and user found"}

    # clean data
    elif len(keywords) == 1:
        result =  clean_single_data(result)

    # match keywords to values
    result["data"] = dict(zip(keywords, result["data"]))

    # return data
    return result

def remove_user_sessions(cursor: cursor, user_id: int) -> dict:
    """
    removes all sessions of a user from the table sessions
    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    # remove session based on user_id
    result = db.remove_table(
        cursor=cursor,
        table_name="sessions",
        conditions={"user_id": user_id},
        returning_column="session_id")

    # handle error
    if result["success"] is True and result["data"] is None:
        return {"success": False, "error": "no sessions found"}

    # return result
    return result

def check_session_id(cursor: cursor, session_id: int) -> dict:
    """
    checks, whether a session_id is valid

    Parameters:
        cursor: cursor for the db connection
        session_id: id of the session
    """

    # get session based on session_id
    result = db.read_table(cursor=cursor, 
                           table_name="sessions", 
                           conditions={"id": session_id}, 
                           expect_single_answer=True)

    # handle error
    if result["success"] is True and result["data"] is None:
        return {"success": True, "data": False}

    # return result
    return {"success": True, "data": True}