from datetime import datetime
from typing import Literal, TypedDict, cast
from psycopg2.extensions import cursor

from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import (
    GenericFailure,
    error_to_failure,
)
from packages.backend.sql_connection.ultimate_functions import clean_single_data

class AddGuestSuccess(TypedDict):
    success: Literal[True]
    data: int

class RemoveGuestSuccess(TypedDict):
    success: Literal[True]
    data: datetime

class CheckGuestSuccess(TypedDict):
    success: Literal[True]
    data: bool

def add_guest(cursor: cursor, user_id: int, stueble_id: int, invited_by: int | None = None) -> AddGuestSuccess | GenericFailure:
    """
    adds a guest to the table events with event_type "add"

    Parameters:
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
        cursor=cursor,
        table_name="events",
        arguments=arguments,
        returning_column="NOW()")

    if result["success"] is False:
        return error_to_failure(result)
    # maybe shouldn't be possible, but still left in
    if result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return cast(AddGuestSuccess, clean_single_data(result))

def remove_guest(cursor: cursor, user_id: int, stueble_id: int) -> RemoveGuestSuccess | GenericFailure:
    """
    adds a guest to the table events with event_type "remove" effectively removing them from the guest list

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
        stueble_id (int): id of the stueble party, if -1 then removal from all added stueble parties
    Returns:
        dict: {"success": bool} by default, {"success": True, "data": timestamp} if returning is True, {"success": False, "error": e} if error occurred
    """
    if stueble_id == -1:
        # get all stueble ids where the user is currently added
        query = f"""
        INSERT INTO events (user_id, event_type, stueble_id)
        SELECT user_id, 'remove', stueble_id FROM
        (SELECT user_id, stueble_id
        FROM
            (SELECT DISTINCT ON (events.stueble_id) events.*
            FROM events
                LEFT JOIN stueble_motto sm ON sm.id = events.stueble_id
            WHERE ((sm.date_of_time >= CURRENT_DATE)
               OR (CURRENT_TIME <= '06:00:00' AND sm.date_of_time = CURRENT_DATE - 1))
                      AND events.user_id = %s
                      AND events.event_type IN ('add', 'remove')
            ORDER BY events.stueble_id, events.submitted DESC ) AS stuebles
        WHERE stuebles.event_type = 'add') AS to_remove
        RETURNING stueble_id;
        """
        result = db.custom_call(
            cursor=cursor,
            query=query,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
            variables=[user_id]
        )

        if result["success"] is False:
            return error_to_failure(result)
        return result
    else:
        result = db.insert_table(
            cursor=cursor,
            table_name="events",
            arguments={"user_id": user_id, "stueble_id": stueble_id, "event_type": "remove"},
            returning_column="NOW()")
        # maybe shouldn't be possible, but still left in
        if result["success"] is False:
            return error_to_failure(result)
        if result["success"] is True and result["data"] is None:
            return {"success": False, "error": "error occurred"}
        return cast(RemoveGuestSuccess, clean_single_data(result))

# use users.check_user_guest_list for automatic stueble_id handling
def check_guest(cursor: cursor, user_id: int, stueble_id: int | None = None) -> CheckGuestSuccess | GenericFailure:
    """
    checks if a user is currently a guest at a stueble party

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
        stueble_id (int | None): id of the stueble party
    Returns:
        dict: {"success": bool, "data": bool} if successful, {"success": False, "error": e} if error occurred
    """

    # TODO: add 6 o'clock handling
    if stueble_id is None:
        query = """SELECT id FROM stueble_motto WHERE date_of_time >= (CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time ASC LIMIT 1"""
        result = db.custom_call(
            cursor=cursor,
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
        )
        if result["success"] is False:
            return error_to_failure(result)
        if result["data"] is None:
            return {"success": False, "error": "no stueble party_user found"}
        stueble_id = result["data"][0]


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
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[user_id, stueble_id]
    )

    if result["success"] is False:
        return error_to_failure(result)

    if result["data"] is None:
        return {"success": False, "error": "user not on guest_list"}

    return cast(CheckGuestSuccess, clean_single_data(result))