from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_functions import clean_single_data


def add_guest(connection, cursor, user_id: int, stueble_id: int, invited_by: int | None=None) -> dict:
    """
    adds a guest to the table events with event_type "add"

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int): id of the user
        stueble_id (int): id of the stueble party
        invited_by (int | None): id of the invited user
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occurred
    """

    arguments = {"user_id": user_id, "stueble_id": stueble_id, "event_type": "add"}
    if invited_by is not None:
        arguments["invited_by"] = invited_by

    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="events",
        arguments=arguments,
        returning_column="NOW()")

    # maybe shouldn't be possible, but still left in
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return clean_single_data(result)

def remove_guest(connection, cursor, user_id: int, stueble_id: int) -> dict:
    """
    adds a guest to the table events with event_type "remove" effectively removing them from the guest list

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
        table_name="events",
        arguments={"user_id": user_id, "stueble_id": stueble_id, "event_type": "remove"},
        returning_column="NOW()")

    # maybe shouldn't be possible, but still left in
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return clean_single_data(result)