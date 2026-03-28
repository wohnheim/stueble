from typing import Annotated
import uuid
from psycopg import sql

from backend.database import database as db
from backend.datatypes.funcres import FuncRes, Status, Message
from backend.datatypes.stueble_types import EventType, FrontendUserRole


def change_guest(event_type: EventType, user_uuid: Annotated[uuid.UUID | None, "Explicit with user_id"] = None,
                 user_id: Annotated[int | None, "Explicit with user_uuid"] = None) -> FuncRes:
    """
    add or remove a guest to the guest_list of present people in stueble.events for a stueble party \n
    used when a guest arrives / leaves
    
    Args:
        event_type (EventType): type of event
        user_uuid: uuid of guest
        user_id: id of guest
    Returns:
        FuncRes: Return object with success status and data containing the timestamp of the event if successful, error message if error occurred
    """

    if (user_uuid is not None and user_id is not None) or (user_uuid is None and user_id is None):
        return FuncRes(
            error="either user_uuid or user_id must be specified, but not both",
            status=Status.FULL_ERROR,
            message=Message(name="Change Guest Error",
                            type="error",
                            category="Change Guest",
                            code=400)
        )
    
    if user_id is None:
        # get user id from uuid
        result = db.select(
            columns=["id"],
            table="users",
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            conditions={"user_uuid": str(user_uuid)})

        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Change Guest Error",
                                type="error",
                                category="Change Guest",
                                code=500)
            )
        if result.data is None:
            return FuncRes(
            error="no user found",
            status=Status.FULL_ERROR,
            message=Message(name="Change Guest Error",
                            type="error",
                            category="Change Guest",
                            code=404)
        )
        user_id = result.data["id"]

    # get stueble_id
    result = db.select(
        columns=["id"],
        table="stueble.motto",
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        specific_where=sql.SQL("date_of_time = CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = (CURRENT_DATE - INTERVAL '1 day' ))"))

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Change Guest Error",
                            type="error",
                            category="Change Guest",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no stueble party found for today or yesterday",
            status=Status.FULL_ERROR,
            message=Message(name="Change Guest Error",
                            type="error",
                            category="Change Guest",
                            code=404)
        )

    stueble_id = result.data["id"]

    # add user to stueble.events
    result = db.insert(
        table="stueble.events",
        values={"user_id": user_id, "event_type": event_type.value, "stueble_id": stueble_id},
        returning_column="id")

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Change Guest Error",
                            type="error",
                            category="Change Guest",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="failed to add event",
            status=Status.FULL_ERROR,
            message=Message(name="Change Guest Error",
                            type="error",
                            category="Change Guest",
                            code=500)
        )

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Change Guest Success",
                        type="success",
                        category="Change Guest",
                        code=200)
    )

def guest_list_present(stueble_id: int | None = None) -> FuncRes:
    """
    returns list of all guests that are currently present

    Args:
        stueble_id (int | None): id for a specific stueble party, if None the current stueble party is used
    Returns:
        FuncRes: success: True if guest list was retrieved successfully, False otherwise, data: list of guests with first name, last name and user role
    """

    parameters = {}

    if stueble_id is None:
        stueble_info = """(SELECT id FROM stueble.motto WHERE date_of_time = CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = (CURRENT_DATE - INTERVAL '1 day')) ORDER BY date_of_time DESC LIMIT 1)"""
    else:
        stueble_info = "%s"
        parameters["variables"] = [stueble_id]

    query = f"""
    SELECT u.first_name, u.last_name, u.user_role, present_users.submitted
    FROM
    (SELECT user_id, submitted
    FROM (SELECT DISTINCT ON (user_id) id, user_id, event_type, submitted
          FROM stueble.events
            WHERE stueble_id = {stueble_info}
            ORDER BY user_id, submitted DESC) AS subquery
        WHERE event_type = 'arrive'
        ORDER BY user_id, submitted ASC) AS present_users
    JOIN users u ON present_users.user_id = u.id
    ORDER BY present_users.submitted ASC;
    """

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        **parameters)
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Guest List Present Error",
                            type="error",
                            category="Guest List Present",
                            code=500)
        )

    data = result.data

    return FuncRes(
        data=[{"first_name": i[0], "last_name": i[1], "user_role": FrontendUserRole.EXTERN if i[2] == "extern" else FrontendUserRole.INTERN} for i in data],
        status=Status.FULL_SUCCESS,
        message=Message(name="Guest List Present Success",
                        type="success",
                        category="Guest List Present",
                        code=200)

    )


def guest_list(stueble_id: int | None = None) -> FuncRes:
    """
    returns list of all guests that have been at the party

    Args:
        stueble_id (int | None): id for a specific stueble party, if None the current stueble party is used
    Returns:
        FuncRes: success: True if guest list was retrieved successfully, False otherwise, data: list of guests with first name, last name, user role, room number and residence for interns and invited by for externs
    """

    parameters = {}

    if stueble_id is None:
        stueble_info = """(SELECT id FROM stueble.motto WHERE date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1)"""
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
    COALESCE((SELECT event_type FROM stueble.events WHERE user_id = users_user_id AND event_type IN ('arrive', 'leave', 'remove') AND stueble_id = {stueble_info}ORDER BY submitted DESC LIMIT 1), 'leave') = 'arrive' AS present, 
    (SELECT user_uuid FROM users WHERE users.id = invited_by) AS invited_by
FROM (
    SELECT
        u.id AS users_user_id,
        u.first_name,
        u.last_name,
        u.user_role,
        u.user_uuid,
        u.verified,
        u.room,
        u.residence,
        e.event_type,
        e.submitted,
        e.invited_by,
        ROW_NUMBER() OVER (PARTITION BY e.user_id ORDER BY e.submitted DESC) as rn
    FROM stueble.events e
    LEFT JOIN users u ON e.user_id = u.id
    WHERE e.stueble_id = {stueble_info}
      AND e.event_type IN ('add', 'remove')
) AS all_events
WHERE rn = 1
  AND event_type = 'add';
    """

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        **parameters)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Guest List Error",
                            type="error",
                            category="Guest List",
                            code=500)
        )

    infos = []

    for guest in result.data:
        data_pack = {"firstName": guest[0],
                     "lastName": guest[1],
                     "extern": guest[2],
                     "id": guest[3],
                     "present": guest[7]}
        if data_pack["extern"] is False:
            data_pack["roomNumber"] = guest[5]
            data_pack["residence"] = guest[6]
            data_pack["verified"] = guest[4]
        else:
            data_pack["invitedBy"] = guest[8]
        infos.append(data_pack)

    return FuncRes(
        data=infos,
        status=Status.FULL_SUCCESS,
        message=Message(name="Guest List Success",
                        type="success",
                        category="Guest List",
                        code=200)
    )
