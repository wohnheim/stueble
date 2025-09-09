import backend.sql_connection.database as db

def add_guest(connection, cursor, user_id: int, stueble_id: int) -> dict:
    """
    adds a guest to the table stueble_codes

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int): id of the user
        stueble_id (int): id of the stueble party
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occurred
    """

    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="stueble_codes",
        arguments={"user_id": user_id, "stueble_id": stueble_id},
        returning_column="code")

    # maybe shouldn't be possible, but still left in
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return result