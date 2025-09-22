from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.ultimate_functions import clean_single_data

from typing import Annotated


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

def check_guest(cursor, user_id: int, stueble_id: int | None=None) -> dict:
    """
    checks if a user is currently a guest at a stueble party

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
        stueble_id (int | None): id of the stueble party
    Returns:
        dict: {"success": bool, "data": bool} if successful, {"success": False, "error": e} if error occurred
    """

    if stueble_id is None:
        query = """
        SELECT id FROM stueble_motto WHERE date_of_time >= (CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time ASC LIMIT 1"""
        result = db.custom_call(
            connection=None,
            cursor=cursor,
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
        )
        if not result["success"]:
            return result
        if result["data"] is None:
            return {"success": False, "error": "no stueble paruser_ty found"}
        stueble_id = result["data"]


    query = f"""
            SELECT 'add' =
                   COALESCE((SELECT event_type
                             FROM events
                             WHERE user_id = %s
                               AND stueble_id = %s
                               AND event_type IN ('add', 'remove')
                             ORDER BY submitted DESC
                             LIMIT 1), 'remove')
            """
    result = db.custom_call(
        connection=None,
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[user_id, stueble_id]
    )

    if not result["success"]:
        return result

    if result["data"] is None:
        return {"success": False, "error": "user not on guest_list"}

    return result