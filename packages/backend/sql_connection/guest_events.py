from datetime import datetime
from typing import Annotated, Literal, TypedDict
import uuid

from psycopg2.extensions import cursor

from packages.backend.data_types import EventType
from packages.backend.data_types import FrontendUserRole
from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import GenericFailure, SingleSuccess, error_to_failure

class GuestListPresentData(TypedDict):
    first_name: str
    last_name: str
    user_role: FrontendUserRole

class GuestListPresentSuccess(TypedDict):
    success: Literal[True]
    data: list[GuestListPresentData]

class GuestListEvent(TypedDict):
    status: str
    time: datetime

class GuestListData(TypedDict):
    first_name: str
    last_name: str
    user_role: FrontendUserRole
    events: list[GuestListEvent]

class GuestListSuccess(TypedDict):
    success: Literal[True]
    data: list[GuestListData]

def change_guest(cursor: cursor, event_type: EventType, user_uuid: Annotated[uuid.UUID | None, "Explicit with user_id"] = None,
                 user_id: Annotated[int | None, "Explicit with user_uuid"] = None) -> SingleSuccess | GenericFailure:
    """
    add or remove a guest to the guest_list of present people in events for a stueble party \n
    used when a guest arrives / leaves
    Parameters:
        cursor: cursor from connection
        event_type (EventType): type of event
        user_uuid: uuid of guest
        user_id: id of guest
    """

    if (user_uuid is not None and user_id is not None) or (user_uuid is None and user_id is None):
        return {"success": False, "error": "either user_uuid or user_id must be specified"}
    
    if user_id is None:
        # get user id from uuid
        result = db.read_table(
            cursor=cursor,
            keywords=["id"],
            table_name="users",
            expect_single_answer=True,
            conditions={"user_uuid": str(user_uuid)})

        if result["success"] is False:
            return error_to_failure(result)
        if result["data"] is None:
            return {"success": False, "error": "no user found"}

        user_id = result["data"][0]

    # get stueble_id
    result = db.read_table(
        cursor=cursor,
        keywords=["id"],
        table_name="stueble_motto",
        expect_single_answer=True,
        specific_where="date_of_time = CURRENT_DATE OR date_of_time = (CURRENT_DATE - INTERVAL '1 day')")

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no stueble party found for today or yesterday"}

    stueble_id = result["data"][0]

    # add user to events
    result = db.insert_table(
        cursor=cursor,
        table_name="events",
        arguments={"user_id": user_id, "event_type": event_type.value, "stueble_id": stueble_id},
        returning_column="id")

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "error occurred"}

    return result

def guest_list_present(cursor: cursor, stueble_id: int | None = None) -> GuestListPresentSuccess | GenericFailure:
    """
    returns list of all guests that are currently present
    Parameters:
        cursor: cursor from connection
        stueble_id (int | None): id for a specific stueble party, if None the current stueble party is used
    """

    parameters = {}

    if stueble_id is None:
        stueble_info = """(SELECT id FROM stueble_motto WHERE date_of_time = CURRENT_DATE OR date_of_time = (CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time DESC LIMIT 1)"""
    else:
        stueble_info = "%s"
        parameters["variables"] = [stueble_id]

    query = f"""
    SELECT u.first_name, u.last_name, u.user_role, present_users.submitted
    FROM
    (SELECT user_id, submitted
    FROM (SELECT DISTINCT ON (user_id) id, user_id, event_type, submitted
          FROM events
            WHERE stueble_id = {stueble_info}
            ORDER BY user_id, submitted DESC) AS subquery
        WHERE event_type = 'arrive'
        ORDER BY user_id, submitted ASC) AS present_users
    JOIN users u ON present_users.user_id = u.id
    ORDER BY present_users.submitted ASC;
    """

    result = db.custom_call(
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        **parameters)
    if result["success"] is False:
        return error_to_failure(result)

    data = result["data"]

    return {
        "success": True, 
        "data": [{"first_name": i[0], "last_name": i[1], "user_role": FrontendUserRole.EXTERN if i[2] == "extern" else FrontendUserRole.INTERN} for i in data]
    }

def guest_list(cursor: cursor, stueble_id: int | None = None) -> GuestListSuccess | GenericFailure:
    """
    returns list of all guests that have been at the party
    Parameters:
        cursor: cursor from connection
        stueble_id (int | None): id for a specific stueble party, if None the current stueble party is used
    """

    parameters = {}

    if stueble_id is None:
        stueble_info = """(SELECT id FROM stueble_motto WHERE date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1)"""
    else:
        stueble_info = "%s"
        parameters["variables"] = [stueble_id]

    query = f"""
SELECT 
    first_name, 
    last_name, 
    user_role = 'extern' AS extern, 
    user_uuid, 
    verified, 
    room, 
    residence, 
    COALESCE((SELECT event_type FROM events WHERE user_id = id AND event_type IN ('arrive', 'leave', 'remove')), 'leave') = 'arrive' AS present
FROM (
    SELECT
        u.id,
        u.first_name,
        u.last_name,
        u.user_role,
        u.user_uuid,
        u.verified,
        u.room,
        u.residence,
        e.event_type,
        e.submitted,
        ROW_NUMBER() OVER (PARTITION BY e.user_id ORDER BY e.submitted DESC) as rn
    FROM events e
    LEFT JOIN users u ON e.user_id = u.id
    WHERE e.stueble_id = {stueble_info}
      AND e.event_type IN ('add', 'remove')
) AS all_events
WHERE rn = 1
  AND event_type = 'add';
    """

    result = db.custom_call(
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        **parameters)

    if result["success"] is False:
        return error_to_failure(result)

    infos = []

    for guest in result["data"]:
        data_pack = {"firstName": guest[0],
                     "lastName": guest[1],
                     "extern": guest[2],
                     "id": guest[3],
                     "present": guest[7]}
        if data_pack["present"] is True:
            data_pack["roomNumber"] = guest[5]
            data_pack["residence"] = guest[6]
            data_pack["verified"] = guest[4]
        infos.append(data_pack)

    return {"success": True, "data": infos}