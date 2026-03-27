import datetime

from backend.datatypes.stueble_types import UserRole
from backend.database import database as db
from backend.sql_connection import sessions
from backend.datatypes.funcres import FuncRes, Status, Message


def check_permissions(session_id: str | None, required_role: UserRole) -> FuncRes:
    """
    checks whether the user with the given session_id has the required role
    Args:
        session_id (str): session id of the user
        required_role (UserRole): required role of the user
    Returns:
        FuncRes: {"allowed": bool, "user_id": int, "user_role": UserRole, "user_uuid": str, "first_name": str, "last_name": str} or error data
    """

    if session_id is None:
        return FuncRes(
            error="The session id must be specified",
            status=Status.FULL_ERROR,
            message=Message(name="Permission Check Error",
                            type="error",
                            category="Permission Check",
                            code=400)
        )

    # get the user_id, user_role by session_id
    result = sessions.get_user(session_id=session_id)

    # if error occurred, return error
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Permission Check Error",
                            type="error",
                            category="Permission Check",
                            code=500)
        )
    user_id = result.data[0]
    user_role = result.data[1]
    user_role = UserRole(user_role)
    user_uuid = result.data[2]
    first_name = result.data[3]
    last_name = result.data[4]
    if user_role >= required_role:
        return FuncRes(
            data={"allowed": True, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid, "first_name": first_name, "last_name": last_name},
            status=Status.FULL_SUCCESS,
            message=Message(name="Permission Check Success",
                            type="success",
                            category="Permission Check",
                            code=200)
        )
    return FuncRes(
        data={"allowed": False, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid, "first_name": first_name, "last_name": last_name},
        status=Status.FULL_SUCCESS,
        message=Message(name="Permission Check Success",
                        type="success",
                        category="Permission Check",
                        code=200)
    )

def get_motto(date: datetime.date | None = None) -> FuncRes:
    """
    returns the motto for the next stueble party

    Args:
        date (str | None): the date of the motto
    Returns:
        FuncRes: Return object
    """
    if date == "":
        date = None
    arguments = {"conditions": {"date_of_time": date}} if date is not None else {"specific_where": "date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"}
    result = db.select(
        table="stueble.motto",
        columns=["motto", "date_of_time", "description", "id"],
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        **arguments) # type: ignore
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Motto Error",
                            type="error",
                            category="Get Motto",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no stueble found",
            status=Status.FULL_ERROR,
            message=Message(name="Get Motto Error",
                            type="error",
                            category="Get Motto",
                            code=404)
        )
    return FuncRes(
        data={"motto": result.data[0], "date": result.data[1], "description": result.data[2], "stueble_id": result.data[3]},
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Motto Success",
                        type="success",
                        category="Get Motto",
                        code=200)
    )
