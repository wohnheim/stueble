import datetime
from psycopg2.extensions import cursor

from packages.backend.data_types import UserRole
from packages.backend.sql_connection import database as db, sessions

def check_permissions(cursor: cursor, session_id: str | None, required_role: UserRole) -> dict:
    """
    checks whether the user with the given session_id has the required role
    Parameters:
        cursor: cursor for the connection
        session_id (str): session id of the user
        required_role (UserRole): required role of the user
    Returns:
        dict: {"success": bool, "data": {"allowed": bool, "user_id": int, "user_role": UserRole}, {"success": False, "error": e} if error occurred
    """

    # if session_id is None, return error
    if session_id is None:
        return {"success": False, "error": "The session id must be specified"}

    # get the user_id, user_role by session_id
    result = sessions.get_user(cursor=cursor, session_id=session_id)

    # if error occurred, return error
    if result["success"] is False:
        return result

    user_id = result["data"][0]
    user_role = result["data"][1]
    user_role = UserRole(user_role)
    user_uuid = result["data"][2]
    first_name = result["data"][3]
    last_name = result["data"][4]
    if user_role >= required_role:
        return {"success": True, "data": {"allowed": True, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid, "first_name": first_name, "last_name": last_name}}
    return {"success": True, "data": {"allowed": False, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid, "first_name": first_name, "last_name": last_name}}

def get_motto(cursor: cursor | None=None, date: datetime.date | None = None) -> GetMottoSuccess | GenericFailure:
    """
    returns the motto for the next stueble party

    Parameters:
        cursor (cursor | None): cursor for the connection, if None a new connection will be created
        date (str | None): the date of the motto
    """
    if date == "":
        date = None
    init_cursor = True if cursor is None else False
    if init_cursor is True:
        # get connection and cursor
        conn, cursor = get_conn_cursor()
    arguments = {"conditions": {"date_of_time": date}} if date is not None else {"specific_where": "date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"}
    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=["motto", "date_of_time", "description", "id"],
        expect_single_answer=True,
        **arguments)
    if init_cursor is True:
        close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no stueble found"}

    return {"success": True, "data": {"motto": result["data"][0], "date": result["data"][1], "description": result["data"][2], "stueble_id": result["data"][3]}}