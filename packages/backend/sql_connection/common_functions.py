from packages.backend.sql_connection import sessions, motto, database as db
from packages.backend.data_types import *
from packages.backend.main import pool

def get_conn_cursor(pool):
    """
    gets a connection and a cursor from the connection pool
    """
    conn = pool.getconn()
    cursor = conn.cursor()
    return conn, cursor

def close_conn_cursor(pool, connection, cursor):
    """
    closes the cursor and returns the connection to the pool
    """
    cursor.close()
    pool.putconn(connection)

def check_permissions(cursor, session_id: str, required_role: UserRole) -> dict:
    """
    checks whether the user with the given session_id has the required role
    Parameters:
        cursor: cursor for the connection
        session_id (str): session id of the user
        required_role (UserRole): required role of the user
    Returns:
        dict: {"success": bool, "data": {"allowed": bool, "user_id": int, "user_role": UserRole}, {"success": False, "error": e} if error occurred
    """

    # get the user_id, user_role by session_id
    result = sessions.get_user(cursor=cursor, session_id=session_id)

    # if error occurred, return error
    if result["success"] is False:
        return result
    user_id = result["data"][0]
    user_role = result["data"][1]
    user_role = UserRole(user_role)
    user_uuid = result["data"][2]
    if user_role >= required_role:
        return {"success": True, "data": {"allowed": True, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid}}
    return {"success": True, "data": {"allowed": False, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid}}

def get_motto(date: str | None = None):
    """
    returns the motto for the next stueble party

    Parameters:
        date (str | None): the date of the motto
    """
    if date == "":
        date = None

    # get connection and cursor
    conn, cursor = get_conn_cursor(pool)

    # if date is None, return all stuebles
    if date is None:
        result = db.read_table(
            cursor=cursor,
            table_name="stueble_motto",
            keywords=["motto", "date_of_time"],
            order_by=("date_of_time", 0), # descending
            expect_single_answer=False)
        close_conn_cursor(pool, conn, cursor) # close conn, cursor
        if result["success"] is False:
            return result
        data = [{"motto": entry[0], "date": entry[1].isoformat()} for entry in result["data"]]
        return {"success": True, "data": data}

    # get motto from table
    result = motto.get_motto(cursor=cursor, date=date)
    close_conn_cursor(pool, conn, cursor) # close conn, cursor
    if result["success"] is False:
        return result

    data = {"motto": result["data"][0], "date": result["data"][1].isoformat()} if result["data"] is not None else {}
    return {"success": True, "data": data}