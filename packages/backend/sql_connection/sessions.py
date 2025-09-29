from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Literal, TypedDict, cast, overload

from psycopg2.extensions import cursor
import pytz

from packages.backend.data_types import UserRole
from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import (
    GenericFailure,
    GenericSuccess,
    SingleSuccess,
    SingleSuccessCleaned,
    is_single_success,
)
from packages.backend.sql_connection.ultimate_functions import clean_single_data

class CreateSessionSuccess(TypedDict):
    success: Literal[True]
    data: list[str]

class GetSessionSuccess(TypedDict):
    success: Literal[True]
    data: tuple[str, datetime]

class GetUserSuccess(TypedDict):
    success: Literal[True]
    data: tuple[int, UserRole, str]

class GetUserSuccessFull(TypedDict):
    success: Literal[True]
    data: tuple[int, UserRole, str, int, str, str, str, str, str]

class CheckSessionIdSuccess(TypedDict):
    success: Literal[True]
    data: bool

def create_session(cursor: cursor, user_id: int) -> CreateSessionSuccess | GenericFailure:
    """
    creates a session for a user in the table sessions

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occured
    """

    # load the configuration variable for session expiration time in days from table configurations
    expiration_time = db.read_table(cursor=cursor, keywords=["value"], table_name="configurations", conditions={"key": "session_expiration_days"}, expect_single_answer=True)
    if expiration_time["success"] is False:
        return expiration_time
    elif expiration_time["data"] is None:
        return {"success": False, "error": "Invalid result data"}

    expiration_time = int(expiration_time["data"][0])

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

    if is_single_success(result):
        if result["data"] is None:
            return {"success": False, "error": "error occurred"}
        else:
            return {"success": True, "data": list(result["data"]) + [expiration_date]}
    return cast(GenericFailure, result)

def get_session(cursor: cursor, session_id: str) -> GetSessionSuccess | GenericFailure:
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
        specific_where="session_id = %s AND expiration_date > NOW()",
        variables=[session_id]
        )
    if is_single_success(result) and result["data"] is None:
        return {"success": False, "error": "no session found"}
    return cast(GetSessionSuccess | GenericFailure, result)

def remove_session(cursor: cursor, session_id: str) -> GenericSuccess | GenericFailure:
    """
    removes a session from the table sessions
    Parameters:
        cursor: cursor for the connection
        session_id (str): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    result = db.remove_table(
        cursor=cursor,
        table_name="sessions",
        conditions={"session_id": session_id},
        returning_column="session_id")
    if is_single_success(result) and result["data"] is None:
        return {"success": False, "error": "no session found"}
    return result

@overload
def get_user(cursor: cursor, session_id: str, keywords: None = None) -> GetUserSuccess | GenericFailure: ...

@overload
def get_user(cursor: cursor, session_id: str, keywords: tuple[Literal["id"], Literal["user_role"], Literal["user_uuid"], Literal["room"], Literal["residence"],
             Literal["first_name"], Literal["last_name"], Literal["email"], Literal["user_name"]]) -> GetUserSuccessFull | GenericFailure: ...
@overload
def get_user(cursor: cursor, session_id: str, keywords: Sequence[str]) -> SingleSuccess | SingleSuccessCleaned | GenericFailure: ...

def get_user(cursor: cursor, session_id: str, keywords: Sequence[str] | None = None) -> SingleSuccess | SingleSuccessCleaned | GenericFailure:
    """
    gets the user role of a user from the table users via the sessions table
    Parameters:
        cursor: cursor for the connection
        session_id (str): id of the user
        keywords (tuple[str] | list[str]): list of keywords to be returned
    Returns:
        dict: {"success": bool, "data": user_role}, {"success": False, "error": e} if error occurred
    """

    allowed_keywords = ["id", "user_role", "user_uuid", "room", "residence", "first_name", "last_name", "email", "user_name"]

    if keywords is None:
        keywords = ["id", "user_role","user_uuid"]
    else:
        keywords = list(keywords)
        if not all(map(lambda k: k in allowed_keywords, keywords)):
            return { "success": False, "error": "invalid keywords specified"}

    result = db.read_table(
        cursor=cursor,
        keywords=["u." + i for i in keywords],
        table_name="sessions s JOIN users u ON s.user_id = u.id",
        expect_single_answer=True,
        conditions={"s.session_id": session_id})

    if is_single_success(result):
        if result["data"] is None:
            return {"success": False, "error": "no matching session and user found"}
        elif len(keywords) == 1:
            return clean_single_data(result)
    return result

def remove_user_sessions(cursor: cursor, user_id: int) -> SingleSuccess | GenericSuccess | GenericFailure:
    """
    removes all sessions of a user from the table sessions
    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    result = db.remove_table(
        cursor=cursor,
        table_name="sessions",
        conditions={"user_id": user_id},
        returning_column="session_id")
    if is_single_success(result) and result["data"] is None:
        return {"success": False, "error": "no sessions found"}

    # TODO: Improve
    return cast(SingleSuccess | GenericFailure, cast(object, result))

def check_session_id(cursor: cursor, session_id: int) -> CheckSessionIdSuccess | GenericFailure:
    """
    checks, whether a session_id is valid

    Parameters:
        cursor: cursor for the db connection
        session_id: id of the session
    """

    result = db.read_table(cursor=cursor, 
                           table_name="sessions", 
                           conditions={"id": session_id}, 
                           expect_single_answer=True)
    if is_single_success(result) and result["data"] is None:
        return {"success": True, "data": False}
    elif result["success"] is True:
        return {"success": True, "data": True}
    else:
        return result