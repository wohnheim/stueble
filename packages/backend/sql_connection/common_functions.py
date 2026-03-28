import datetime
from psycopg import sql

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
    user_id = result.data["id"]
    user_role = result.data["user_role"]
    user_role = UserRole(user_role)
    user_uuid = str(result.data["user_uuid"])
    first_name = result.data["first_name"]
    last_name = result.data["last_name"]
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
