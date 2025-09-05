import backend.sql_connection.database as db
from backend.data_types import EventType
from collections import defaultdict
from backend.data_types import FrontendUserRole

def change_guest(connection, cursor, stueble_code: str, event_type: EventType) -> dict:
    """
    add or remove a guest to the guest_list of present people in events for a stueble party \n
    used when a guest arrives / leaves
    Parameters:
        connection: connection to db
        cursor: cursor from connection
        stueble_code (str): code for a stueble for a guest
        event_type (EventType): type of event
    """

    # get guest and inviter info
    query = """
    SELECT 
        guest.id as guest_id, 
        guest.first_name as guest_first_name,
        guest.last_name as guest_last_name,
        guest.user_role as guest_user_role,
        guest.invited_by as guest_invited_by, 
        
        inviter.id as inviter_id,
        inviter.first_name as inviter_first_name,
        inviter.last_name as inviter_last_name,
        inviter.user_role as inviter_user_role, 
        
        guest.stueble_id as stueble_id
        
        FROM (SELECT users.*, sc.stueble_id
              FROM users 
              JOIN stueble_codes sc ON users.id = sc.user_id
              WHERE code = %s 
                AND (date_of_time = CURRENT_DATE 
                OR date_of_time = (CURRENT_DATE - INTERVAL '1 day'))
              ))
        guest
        LEFT JOIN users inviter ON guest.invited_by = inviter.id;
    """

    result = db.custom_call(
        connection=connection,
        cursor=cursor,
        query=query,
        variables=[stueble_code],
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)

    if result["success"] is False:
        return result

    guest_id, guest_first_name, guest_last_name, guest_user_role, guest_invited_by, inviter_id, inviter_first_name, inviter_last_name, inviter_user_role = result["data"]
    if guest_id is None:
        return {"success": False, "error": "Guest not found"}
    if guest_invited_by is not None and inviter_id is None:
        return {"success": False, "error": "Inviter not found"}

    is_invited = guest_invited_by is not None
    data = {"guest": {
            "id": guest_id,
            "first_name": guest_first_name,
            "last_name": guest_last_name,
            "user_role": FrontendUserRole.EXTERN if guest_user_role == "extern" else FrontendUserRole.INTERN,
            "is_invited": is_invited}
    }
    if is_invited:
        data["inviter"] = {
            "id": inviter_id,
            "first_name": inviter_first_name,
            "last_name": inviter_last_name,
            "user_role": FrontendUserRole.EXTERN if inviter_user_role == "extern" else FrontendUserRole.INTERN}

    data["stueble_id"] = result["data"][-1]

    # check if user is already present or absent
    result = db.read_table(
        cursor=cursor,
        table_name="events",
        keywords=["event_type"],
        conditions={"user_id": guest_id},
        expect_single_answer=True,
        select_max_of_key="submitted"
    )
    # TODO test, that no error is thrown when no data available
    if result["success"] is False:
        return result

    # if user has already been to the party, set last event
    if result["data"] is not None:
        last_event = EventType(result["data"])
    else:
        # if user hasn't been to the party yet, leave is not an option
        if event_type == EventType.LEAVE:
            return {"success": False, "error": "Guest hasn't arrived yet."}
        # if user hasn't been to the party yet, set last event to leave, so that the next check allows him to arrive
        else:
            last_event = EventType.LEAVE

    # make sure last_event isn't the same as the current event
    if last_event == event_type:
        return {"success": False, "error": f"Guest is already {'present' if event_type == EventType.ARRIVE else 'absent'}"}

    # add user to events
    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table="events",
        columns=["user_id", "event_type"],
        values=[guest_id, event_type.value],
        returning_column="id"
    )
    if result["success"] is False:
        return result

    data["event_id"] = result["data"]

    return {"success": True, "data": data}

def guest_list(cursor, stueble_id: int | None) -> dict:
    """
    returns list of all guests that are currently present
    Parameters:
        cursor: cursor from connection
        stueble_id (int | None): id for a specific stueble party, if None the current stueble party is used
    """

    parameters = {}

    if stueble_id is None:
        stueble_info = """(SELECT stueble_id FROM stueble WHERE date_of_time = CURRENT_DATE OR date_of_time = (CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time DESC LIMIT 1;)"""
    else:
        stueble_info = "%s"
        parameters["variables"] = [stueble_id]

    query = f"""
    SELECT  id, user_id, event_type, submitted FROM (
        SELECT 
            *, 
            ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY submitted DESC) as rn
        FROM events
            WHERE stueble_id = {stueble_info}) AS subquery
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

    if result["data"] is None:
        return result

    data = result["data"]
    groups = defaultdict(list)

    for sub in data:
        key = sub[1]   # group by user_id
        groups[key].append(sub)

    # data in clean dict format
    data_dict = {key: [{"status": item[2], "time": item[3]} for item in value] for key, value in groups.items()}

    return data_dict