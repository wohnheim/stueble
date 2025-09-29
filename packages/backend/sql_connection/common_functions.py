import datetime
from typing import Literal, TypedDict

from psycopg2.extensions import cursor

from packages.backend.data_types import UserRole
from packages.backend.sql_connection import database as db, motto, sessions
from packages.backend.sql_connection.common_types import GenericFailure
from packages.backend.sql_connection.conn_cursor_functions import (
    close_conn_cursor,
    get_conn_cursor,
)

class PermissionCheckData(TypedDict):
    allowed: bool
    user_id: int
    user_role: UserRole
    user_uuid: str

class PermissionCheckSuccess(TypedDict):
    success: Literal[True]
    data: PermissionCheckData

class GetMottoData(TypedDict):
    motto: str
    date: str

class GetMottoSuccess(TypedDict):
    success: Literal[True]
    data: GetMottoData

def check_permissions(cursor: cursor, session_id: str | None, required_role: UserRole) -> PermissionCheckSuccess | GenericFailure:
    """
    checks whether the user with the given session_id has the required role
    Parameters:
        cursor: cursor for the connection
        session_id (str): session id of the user
        required_role (UserRole): required role of the user
    Returns:
        dict: {"success": bool, "data": {"allowed": bool, "user_id": int, "user_role": UserRole}, {"success": False, "error": e} if error occurred
    """

    if session_id is None:
        return {"success": False, "error": "The session id must be specified"}

    # get the user_id, user_role by session_id
    result = sessions.get_user(cursor=cursor, session_id=session_id)

    # if error occurred, return error
    if (result["success"] is False):
        return result

    user_id = result["data"][0]
    user_role = result["data"][1]
    user_role = UserRole(user_role)
    user_uuid = result["data"][2]
    if user_role >= required_role:
        return {"success": True, "data": {"allowed": True, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid}}
    return {"success": True, "data": {"allowed": False, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid}}

def get_motto(date: datetime.date | None = None) -> GetMottoSuccess | GenericFailure:
    """
    returns the motto for the next stueble party

    Parameters:
        date (str | None): the date of the motto
    """
    if date == "":
        date = None

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    if date is None:
        result = db.read_table(
            cursor=cursor,
            table_name="stueble_motto",
            keywords=["motto", "date_of_time", "id"],
            expect_single_answer=True,
            specific_where="date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1")
        close_conn_cursor(conn, cursor) # close conn, cursor
        if result["success"] is False:
            return result

        return {"success": True, "data": [{"motto": entry[0], "date": datetime.strptime(entry[1], "%Y-%m-%d")} for entry in result["data"]]}

    # get motto from table
    result = motto.get_motto(cursor=cursor, date=date)
    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        return result

    return {"success": True, "data": {"motto": result["data"][0], "date": result["data"][1].isoformat()}}