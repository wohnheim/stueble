from datetime import datetime, timedelta
from typing import Literal, overload
from psycopg import sql

import pytz

from backend.database import database as db
from backend.datatypes.funcres import FuncRes, Status, Message
from backend.sql_connection.ultimate_functions import clean_single_data


def create_session(user_id: int) -> FuncRes:
    """
    creates a session for a user in the table sessions

    Args:
        user_id (int): id of the user
    Returns:
        FuncRes: Return object containing user id or error
    """

    # load the configuration variable for session expiration time in days from table configurations
    expiration_time = db.select(columns=["value"], table="configurations", conditions={"key": "session_expiration_days"}, type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    if expiration_time.is_error:
        return FuncRes(
            error=str(expiration_time.error),
            status=Status.FULL_ERROR,
            message=Message(name="Create Session Error",
                            type="error",
                            category="Create Session",
                            code=500)
        )
    elif expiration_time.data is None:
        return FuncRes(
            error="Invalid result data",
            status=Status.FULL_ERROR,
            message=Message(name="Create Session Error",
                            type="error",
                            category="Create Session",
                            code=500)
        )

    expiration_time = int(expiration_time.data["value"])

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

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Create Session Error",
                            type="error",
                            category="Create Session",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="error occurred",
            status=Status.FULL_ERROR,
            message=Message(name="Create Session Error",
                            type="error",
                            category="Create Session",
                            code=500)
        )
    else:
        return FuncRes(
            data=list(result.data) + [expiration_date],
            status=Status.FULL_SUCCESS,
            message=Message(name="Create Session Success",
                            type="success",
                            category="Create Session",
                            code=200)
        )

def get_session(session_id: str) -> FuncRes:
    """
    gets the session of a user from the table sessions
    Args:
        session_id (str): id of the session
    Returns:
        FuncRes: Return object containing (session_id, expiration_date) or error
    """

    result = db.select(
        columns=["session_id", "expiration_date"],
        table="sessions",
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        specific_where=sql.SQL("session_id = {session_id} AND expiration_date > NOW()").format(session_id=sql.Placeholder()),
        variables=[session_id]
        )
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Session Error",
                            type="error",
                            category="Get Session",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no session found",
            status=Status.FULL_ERROR,
            message=Message(name="Get Session Error",
                            type="error",
                            category="Get Session",
                            code=404)
        )
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Session Success",
                        type="success",
                        category="Get Session",
                        code=200)
    )

def remove_session(session_id: str) -> FuncRes:
    """
    removes a session from the table sessions
    Args:
        session_id (str): id of the user
    Returns:
        FuncRes: Return object containing deleted session_id or error
    """

    result = db.delete(
        table="sessions",
        conditions={"session_id": session_id},
        returning_column="session_id")
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Remove Session Error",
                            type="error",
                            category="Remove Session",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no session found",
            status=Status.FULL_ERROR,
            message=Message(name="Remove Session Error",
                            type="error",
                            category="Remove Session",
                            code=404)
        )
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Remove Session Success",
                        type="success",
                        category="Remove Session",
                        code=200)
    )


def get_user(session_id: str, keywords: tuple[str, ...] | list[str] | None = None) -> FuncRes:
    """
    gets the user role of a user from the table users via the sessions table
    Args:
        session_id (str): id of the user
        keywords (tuple[str, ...] | list[str]): list of keywords to be returned
    Returns:
        FuncRes: Return object containing user data or error
    """

    allowed_keywords = ["id", "user_role", "user_uuid", "room", "residence", "first_name", "last_name", "email", "user_name"]

    if keywords is None:
        keywords = ["id", "user_role","user_uuid", "first_name", "last_name"]
    else:
        keywords = list(keywords)
        if not all(map(lambda k: k in allowed_keywords, keywords)):
            return FuncRes(
                error="invalid keywords specified",
                status=Status.FULL_ERROR,
                message=Message(name="Get User Error",
                                type="error",
                                category="Get User",
                                code=400)
            )

    query = sql.SQL("SELECT {columns} FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.session_id = {session_id}").format(
        columns=sql.SQL(", ").join(sql.Identifier("u") + sql.SQL(".") + sql.Identifier(k) for k in keywords),
        session_id=sql.Placeholder()
    )
    result = db.custom_call(
        query=query,
        variables=[session_id],
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get User Error",
                            type="error",
                            category="Get User",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no matching session and user found",
            status=Status.FULL_ERROR,
            message=Message(name="Get User Error",
                            type="error",
                            category="Get User",
                            code=404)
        )
    
    result._data = {key: value if key != "user_uuid" else str(value) for key, value in zip(keywords, result.data)}

    if len(keywords) == 1:
        return FuncRes(
            data=clean_single_data(result),
            status=Status.FULL_SUCCESS,
            message=Message(name="Get User Success",
                            type="success",
                            category="Get User",
                            code=200)
        )

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get User Success",
                        type="success",
                        category="Get User",
                        code=200)
    )

def remove_user_sessions(user_id: int) -> FuncRes:
    """
    removes all sessions of a user from the table sessions
    Args:
        user_id (int): id of the user
    Returns:
        FuncRes: Return object containing user id of deleted user or error
    """

    result = db.delete(
        table="sessions",
        conditions={"user_id": user_id},
        returning_column="session_id")

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Remove User Sessions Error",
                            type="error",
                            category="Remove User Sessions",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no sessions found",
            status=Status.FULL_ERROR,
            message=Message(name="Remove User Sessions Error",
                            type="error",
                            category="Remove User Sessions",
                            code=404)
        )

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Remove User Sessions Success",
                        type="success",
                        category="Remove User Sessions",
                        code=200)
    )

def check_session_id(session_id: int) -> FuncRes:
    """
    checks, whether a session_id is valid

    Args:
        session_id: id of the session
    Returns:
        FuncRes: Return object containing boolean whether session_id is valid or error
    """

    result = db.select(table="sessions",
                       conditions={"id": session_id},
                       type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Check Session Id Error",
                            type="error",
                            category="Check Session Id",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            data=False,
            status=Status.FULL_SUCCESS,
            message=Message(name="Check Session Id Success",
                            type="success",
                            category="Check Session Id",
                            code=200)
        )

    return FuncRes(
        data=True,
        status=Status.FULL_SUCCESS,
        message=Message(name="Check Session Id Success",
                        type="success",
                        category="Check Session Id",
                        code=200)
    )

def get_session_ids(user_id: int, uuid: bool = False) -> FuncRes:
    """
    gets all session ids of a user from the table sessions
    Args:
        user_id (int): id of the user
        uuid (bool): whether to return the session_id (uuid) or the internal id
    Returns:
        FuncRes: Return object containing list of session ids or error
    """

    result = db.select(
        table="sessions",
        columns=["id"] if uuid is False else ["session_id"],
        conditions={"user_id": user_id}, 
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Session IDs Error",
                            type="error",
                            category="Get Session IDs",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no sessions found",
            status=Status.FULL_ERROR,
            message=Message(name="Get Session IDs Error",
                            type="error",
                            category="Get Session IDs",
                            code=404)
        )

    return FuncRes(
        data=[row["id" if uuid is False else "session_id"] for row in result.data],
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Session IDs Success",
                        type="success",
                        category="Get Session IDs",
                        code=200)
    )