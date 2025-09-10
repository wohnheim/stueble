import uuid

import backend.sql_connection.database as db
from backend.data_types import EventType
from collections import defaultdict
from backend.data_types import FrontendUserRole

def change_guest(connection, cursor, user_uuid: uuid.UUID, event_type: EventType) -> dict:
    """
    add or remove a guest to the guest_list of present people in events for a stueble party \n
    used when a guest arrives / leaves
    Parameters:
        connection: connection to db
        cursor: cursor from connection
        user_uuid: uuid of guest
        event_type (EventType): type of event
    """

    # get user id from uuid
    result = db.read_table(
        cursor=cursor,
        keywords=["id", "user_role"],
        table_name="users",
        expect_single_answer=True,
        conditions={"user_uuid": str(user_uuid)})

    if result["success"] is False:
        return result
    if result["data"] is None:
        return {"success": False, "error": "no user found"}

    user_id, user_role = result["data"]

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
        connection=connection,
        cursor=cursor,
        table="events",
        columns=["user_id", "event_type", "stueble_id"],
        values=[user_id, event_type.value, stueble_id],
        returning_column="id")

    if result["success"] is True and result["data"] is None:
        return {"success": False, "error": "error occurred"}

    return result

def guest_list_present(cursor, stueble_id: int | None=None) -> dict:
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
        connection=None,
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        **parameters)
    if result["success"] is False:
        return result

    data = result["data"]

    data_dict = [{"first_name": i[0], "last_name": i[1], "user_role": FrontendUserRole.EXTERN if i[2] == "extern" else FrontendUserRole.INTERN} for i in data]

    return {"success": True, "data": data_dict}

def guest_list(cursor, stueble_id: int | None=None) -> dict:
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
    SELECT u.id, u.first_name, u.last_name, u.user_role, event_type, submitted, u.user_uuid, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY submitted DESC) as rn
    FROM events
    LEFT JOIN users u ON events.user_id = u.id
    WHERE stueble_id = {stueble_info} and event_type in ('arrive', 'leave')
    ORDER BY user_id, submitted ASC;
    """

    result = db.custom_call(
        connection=None,
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        **parameters)
    if result["success"] is False:
        return result

    data = result["data"]

    groups = defaultdict(list)

    for sub in data:
        key = sub[6]   # group by user_uuid
        groups[key].append(sub)

    # data in clean dict format
    data_dict = {key: [{"status": item[4], "time": item[5]} for item in value] for key, value in groups.items()}

    return {"success": True, "data": list(data_dict.values())}