import backend.sql_connection.database as db
from backend.data_types import EventType

def change_guest(connection, cursor, stueble_code: str, event_type: EventType) -> dict:
    """
    add a guest to the guest_list of present people in events
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
        inviter.user_role as inviter_user_role
        
        FROM (SELECT * 
              FROM users 
              WHERE id = (SELECT user_id 
                          FROM stueble_codes 
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
            "user_role": guest_user_role,
            "is_invited": is_invited}
    }
    if is_invited:
        data["inviter"] = {
            "id": inviter_id,
            "first_name": inviter_first_name,
            "last_name": inviter_last_name,
            "user_role": inviter_user_role}

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