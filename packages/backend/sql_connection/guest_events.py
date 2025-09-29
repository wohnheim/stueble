from datetime import datetime
from typing import Annotated, Literal, TypedDict
import uuid

from psycopg2.extensions import cursor

from packages.backend.data_types import EventType
from packages.backend.data_types import FrontendUserRole
from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import GenericFailure, SingleSuccess

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
            return result
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
        return result
    if result["data"] is None:
        return {"success": False, "error": "no stueble party found for today or yesterday"}

    stueble_id = result["data"][0]

    # add user to events
    result = db.insert_table(
        cursor=cursor,
        table_name="events",
        arguments={"user_id": user_id, "event_type": event_type.value, "stueble_id": stueble_id},
        returning_column="id")

    if result["success"] is True and result["data"] is None:
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
        return result

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
        stueble_info = """(SELECT id FROM stueble_motto WHERE date_of_time = CURRENT_DATE OR date_of_time = (CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time DESC LIMIT 1)"""
    else:
        stueble_info = "%s"
        parameters["variables"] = [stueble_id]

    query = f"""
    SELECT u.id, u.first_name, u.last_name, u.user_role, event_type, submitted, u.user_uuid, u.verified, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY submitted DESC) as rn
    FROM events
    LEFT JOIN users u ON events.user_id = u.id
    WHERE stueble_id = {stueble_info} and event_type in ('arrive', 'leave')
    ORDER BY user_id, submitted ASC;
    """

    result = db.custom_call(
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        **parameters)

    if result["success"] is False:
        return result

    # Group by user_uuid
    infos: dict[str, GuestListData] = {}

    for sub in result["data"]:
        if infos.get(sub[6], None) is None:
            infos[sub[6]] = {"first_name": sub[1], "last_name": sub[2], "user_role": FrontendUserRole.EXTERN if sub[3] == "extern" else FrontendUserRole.INTERN, "events": []}

        infos[sub[6]]["events"].append({"status": sub[4], "time": sub[5]})

    return {"success": True, "data": list(infos.values())}