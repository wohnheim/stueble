from backend.database import database as db
from backend.sql_connection.ultimate_functions import clean_single_data
from backend.datatypes.funcres import FuncRes, Message, Status


def add_guest(user_id: int, stueble_id: int, invited_by: int | None = None) -> FuncRes:
    """
    adds a guest to the table events with event_type "add"

    Args:
        user_id (int): id of the user
        stueble_id (int): id of the stueble party
        invited_by (int | None): id of the invited user
    Returns:
        FuncRes: Return object with success status and data containing the timestamp of the event if successful, error message if error occurred
    """

    values = {"user_id": user_id, "stueble_id": stueble_id, "event_type": "add"}
    if invited_by is not None:
        values["invited_by"] = invited_by

    result = db.insert(
        table="events",
        values=values,
        returning_column="NOW()")

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Add Guest Error",
                            type="error",
                            category="Add Guest",
                            code=500)
        )
    # maybe shouldn't be possible, but still left in
    if result.data is None:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Add Guest Error",
                            type="error",
                            category="Add Guest",
                            code=500)
        )
    return FuncRes(
        data=clean_single_data(result),
        status=Status.FULL_SUCCESS,
        message=Message(name="Add Guest Success",
                        type="success",
                        category="Add Guest",
                        code=200)
    )

def remove_guest(user_id: int, stueble_id: int) -> FuncRes:
    """
    adds a guest to the table events with event_type "remove" effectively removing them from the guest list

    Args:
        user_id (int): id of the user
        stueble_id (int): id of the stueble party, if -1 then removal from all added stueble parties
    Returns:
        FuncRes: Return object with success status and data containing the timestamp of the event if successful, error message if error occurred
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
            query=query,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
            variables=[user_id]
        )

        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Add Guest Error",
                                type="error",
                                category="Add Guest",
                                code=500)
            )
        return FuncRes(
            data=result.data,
            status=Status.FULL_SUCCESS,
            message=Message(name="Remove Guest Success",
                            type="success",
                            category="Remove Guest",
                            code=200)
        )
    else:
        result = db.insert(
            table="events",
            values={"user_id": user_id, "stueble_id": stueble_id, "event_type": "remove"},
            returning_column="NOW()")
        # maybe shouldn't be possible, but still left in
        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Remove Guest Error",
                                type="error",
                                category="Remove Guest",
                                code=500)
            )
        if result.is_success and result.data is None:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Remove Guest Error",
                                type="error",
                                category="Remove Guest",
                                code=500)
            )
        return FuncRes(
            data=clean_single_data(result),
            status=Status.FULL_SUCCESS,
            message=Message(name="Remove Guest Success",
                            type="success",
                            category="Remove Guest",
                            code=200)
        )

# use users.check_user_guest_list for automatic stueble_id handling
def check_guest(user_id: int, stueble_id: int | None = None) -> FuncRes:
    """
    checks if a user is currently a guest at a stueble party

    Args:
        user_id (int): id of the user
        stueble_id (int | None): id of the stueble party
    Returns:
        FuncRes: Return object with success status and data containing a boolean indicating if the user is a guest if successful, error message if error occurred
    """

    # TODO: add 6 o'clock handling
    if stueble_id is None:
        query = """SELECT id FROM stueble_motto WHERE date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time ASC LIMIT 1"""
        result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
        )
        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Check Guest Error",
                                type="error",
                                category="Check Guest",
                                code=500)
            )
        if result.data is None:
            return FuncRes(
                error="no stueble party_user found",
                status=Status.FULL_ERROR,
                message=Message(name="Check Guest Error",
                                type="error",
                                category="Check Guest",
                                code=500)
            )
        stueble_id = result.data[0]


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
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[user_id, stueble_id]
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Check Guest Error",
                            type="error",
                            category="Check Guest",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="user not on guest_list",
            status=Status.FULL_ERROR,
            message=Message(name="Check Guest Error",
                            type="error",
                            category="Check Guest",
                            code=500)
        )

    return FuncRes(
        data=clean_single_data(result),
        status=Status.FULL_SUCCESS,
        message=Message(name="Check Guest Success",
                        type="success",
                        category="Check Guest",
                        code=200)
    )
