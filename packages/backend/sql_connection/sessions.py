from datetime import datetime, timedelta
from typing import Literal, TypedDict, cast, overload

import pytz

from backend.data_types import UserRole
from backend.database import database as db
from backend.sql_connection.ultimate_functions import clean_single_data

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

def create_session(user_id: int) -> CreateSessionSuccess | GenericFailure:
    """
    creates a session for a user in the table sessions

    Args:
        user_id (int): id of the user
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occured
    """

    # load the configuration variable for session expiration time in days from table configurations
    expiration_time = db.select(columns=["value"], table="configurations", conditions={"key": "session_expiration_days"}, type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    if expiration_time["success"] is False:
        return error_to_failure(expiration_time)
    elif expiration_time["data"] is None:
        return {"success": False, "error": "Invalid result data"}

    expiration_time = int(expiration_time["data"][0])

    # calculate expiration date
    tz = pytz.timezone("Europe/Berlin")
    now = datetime.now(tz)
    expiration_date = now + timedelta(days=expiration_time)
    expiration_date = expiration_date.replace(hour=5, minute=30, second=0, microsecond=0)  # set expiration time to 5:30am

    # set the expiration_date
    result = db.insert(
        table="sessions",
        values={"user_id": user_id, "expiration_date": expiration_date},
        returning_column="session_id")

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "error occurred"}
    else:
        return {"success": True, "data": list(result["data"]) + [expiration_date]}

def get_session(session_id: str) -> GetSessionSuccess | GenericFailure:
    """
    gets the session of a user from the table sessions
    Args:
        session_id (str): id of the session
    Returns:
        dict: {"success": bool, "data": (session_id, expiration_date)}, {"success": False, "error": e} if error occurred
    """

    result = db.select(
        columns=["session_id", "expiration_date"],
        table="sessions",
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        specific_where="session_id = %s AND expiration_date > NOW()",
        variables=[session_id]
        )
    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no session found"}

    return cast(GetSessionSuccess, cast(object, result))

def remove_session(session_id: str) -> GenericSuccess | GenericFailure:
    """
    removes a session from the table sessions
    Args:
        session_id (str): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    result = db.delete(
        table="sessions",
        conditions={"session_id": session_id},
        returning_column="session_id")
    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no session found"}
    return result

@overload
def get_user(session_id: str, keywords: None = None) -> GetUserSuccess | GenericFailure: ...

@overload
def get_user(session_id: str, keywords: tuple[Literal["id"], Literal["user_role"], Literal["user_uuid"], Literal["room"], Literal["residence"],
             Literal["first_name"], Literal["last_name"], Literal["email"], Literal["user_name"]]) -> GetUserSuccessFull | GenericFailure: ...
@overload
def get_user(session_id: str, keywords: tuple[str] | list[str]) -> SingleSuccess | SingleSuccessCleaned | GenericFailure: ...

def get_user(session_id: str, keywords: tuple[str] | list[str] | None = None) -> SingleSuccess | SingleSuccessCleaned | GenericFailure:
    """
    gets the user role of a user from the table users via the sessions table
    Args:
        session_id (str): id of the user
        keywords (tuple[str] | list[str]): list of keywords to be returned
    Returns:
        dict: {"success": bool, "data": user_role}, {"success": False, "error": e} if error occurred
    """

    allowed_keywords = ["id", "user_role", "user_uuid", "room", "residence", "first_name", "last_name", "email", "user_name"]

    if keywords is None:
        keywords = ["id", "user_role","user_uuid", "first_name", "last_name"]
    else:
        keywords = list(keywords)
        if not all(map(lambda k: k in allowed_keywords, keywords)):
            return { "success": False, "error": "invalid keywords specified"}

    result = db.select(
        columns=["u." + i for i in keywords],
        table="sessions s JOIN users u ON s.user_id = u.id",
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        conditions={"s.session_id": session_id})

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no matching session and user found"}
    elif len(keywords) == 1:
        return clean_single_data(result)

    return result

def remove_user_sessions(user_id: int) -> SingleSuccess | GenericSuccess | GenericFailure:
    """
    removes all sessions of a user from the table sessions
    Args:
        user_id (int): id of the user
    Returns:
        dict: {"success": bool, "data": data}, {"success": False, "error": e} if error occurred
    """

    result = db.delete(
        table="sessions",
        conditions={"user_id": user_id},
        returning_column="session_id")

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no sessions found"}

    return result

def check_session_id(session_id: int) -> CheckSessionIdSuccess | GenericFailure:
    """
    checks, whether a session_id is valid

    Args:
        session_id: id of the session
    """

    result = db.select(table="sessions",
                       conditions={"id": session_id},
                       type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": True, "data": False}

    return {"success": True, "data": True}

def get_session_ids(user_id: int, uuid: bool = False) -> SingleSuccess | GenericFailure:
    """
    gets all session ids of a user from the table sessions
    Args:
        user_id (int): id of the user
        uuid (bool): whether to return the session_id (uuid) or the internal id
    Returns:
        dict: {"success": bool, "data": session_ids}, {"success": False, "error": e} if error occurred
    """

    result = db.select(
        table="sessions",
        columns=["id"] if uuid is False else ["session_id"],
        conditions={"user_id": user_id}, 
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER
    )

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no sessions found"}

    return {"success": True, "data": [row[0] for row in result["data"]]}
