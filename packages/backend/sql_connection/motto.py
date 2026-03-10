from datetime import date
from typing import Annotated, Any

from psycopg2 import DatabaseError
from psycopg import Cursor
from psycopg2.extras import execute_values

from backend.database import database as db
from backend.sql_connection.ultimate_functions import clean_single_data
from backend.datatypes.funcres import FuncRes, Status, Message


# replace get_motto with get_info
# TODO: Deprecated
@DeprecationWarning
def get_motto(date: date | None = None) -> FuncRes:
    """
    gets the motto from the table motto
    Args:
        date (datetime.date | None): date for which the motto is requested, if None the motto for the next stueble will be returned
    Returns:
        FuncRes: Return object with (motto, author) at success and error else
    """

    if date is not None:
        result = db.select(
            table="stueble_motto",
            columns=["motto", "date_of_time", "id"],
            conditions={"date_of_time": date},
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    else:
        result = db.select(
            table="stueble_motto",
            columns=["motto", "date_of_time", "id"],
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            specific_where="date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1")

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Motto Error",
                            type="error",
                            category="Get Motto",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no motto found",
            status=Status.FULL_ERROR,
            message=Message(name="Get Motto Error",
                            type="error",
                            category="Get Motto",
                            code=404)
        )

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Motto Success",
                        type="success",
                        category="Get Motto",
                        code=200)
    )

def get_info(date: date | None=None) -> FuncRes:
    """
    gets the info from the table motto for a party at a specific date

    Args:
        date (datetime.date): date for which the info is requested
    Returns:
        FuncRes: Return object with (info, author) at success, error else
    """
    arguments = {}
    if date is not None:
        arguments = {"conditions": {"date_of_time": date}, "order_by": ("date_of_time", 1)}
    else:
        arguments = {"specific_where": "date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"}

    result = db.select(
        table="stueble_motto",
        columns=["id", "motto", "date_of_time"],
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        **arguments # type: ignore
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Info Error",
                            type="error",
                            category="Get Info",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no stueble party found",
            status=Status.FULL_ERROR,
            message=Message(name="Get Info Error",
                            type="error",
                            category="Get Info",
                            code=404)
        )
    
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Info Success",
                        type="success",
                        category="Get Info",
                        code=200)
    )

def create_stueble(date: date  | None, motto: str,
                   shared_apartment: str | None = None, description: str | None = None) -> FuncRes:
    """
    creates a new entry in the table stueble_motto

    Args:
        date (datetime.date | None): date for which the motto is valid
        motto (str): motto for the stueble party
        shared_apartment (str): shared apartment for the stueble party, can be None
        description (str): description for the stueble party
    Returns:
        FuncRes: id for success, error else
    """

    arguments: dict[str, Any] = {"date_of_time": date, "motto": motto}
    if shared_apartment is not None:
        arguments["shared_apartment"] = shared_apartment
    if description is not None:
        arguments["description"] = description

    if arguments["date_of_time"] is None:
        del arguments["date_of_time"]
        query = f"""INSERT INTO stueble_motto (date_of_time, {', '.join(arguments.keys())})
        VALUES (CURRENT_DATE + (10 - EXTRACT(DOW FROM CURRENT_DATE)) %% 7 * INTERVAL '1 day', {', '.join('%s' for _ in range(len(arguments)))})
        RETURNING id"""
        result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            variables=list(arguments.values())
        )
    else:
        result = db.insert(
            table="stueble_motto",
            values=arguments,
            returning_column="id"
        )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Create Stueble Error",
                            type="error",
                            category="Create Stueble",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="failed to create stueble",
            status=Status.FULL_ERROR,
            message=Message(name="Create Stueble Error",
                            type="error",
                            category="Create Stueble",
                            code=500)
        )
    return FuncRes(
            data=clean_single_data(result),
            status=Status.FULL_SUCCESS,
            message=Message(name="Create Stueble Success",
                            type="success",
                            category="Create Stueble",
                            code=200)
    )

def update_stueble(date: date | None, **kwargs) -> FuncRes:
    """
    updates an entry in the table stueble_motto

    Args:
        date (datetime.date): date for which the motto is valid
    Returns:
        FuncRes: id for success, error else
    """

    allowed_keys = ["motto", "shared_apartment", "description"]
    if any(key not in allowed_keys for key in kwargs.keys()):
        return FuncRes(
            error="invalid field to update",
            status=Status.FULL_ERROR,
            message=Message(name="Update Stueble Error",
                            type="error",
                            category="Update Stueble",
                            code=400)
        )

    arguments = {key: value for key, value in kwargs.items() if value is not None}
    if len(arguments) == 0:
        return FuncRes(
            error="no fields to update",
            status=Status.FULL_ERROR,
            message=Message(name="Update Stueble Error",
                            type="error",
                            category="Update Stueble",
                            code=400)
        )

    conditions = None
    specific_where = ""

    if (date is None):
        specific_where = """id = (SELECT id FROM stueble_motto WHERE date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1) ORDER BY date_of_time ASC LIMIT 1)"""
    else:
        conditions =  {"date_of_time": date}

    result = db.update(
        table="stueble_motto",
        columns=arguments,
        conditions=conditions,
        specific_where=specific_where,
        returning_column="id"
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Update Stueble Error",
                            type="error",
                            category="Update Stueble",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="no stueble found",
            status=Status.FULL_ERROR,
            message=Message(name="Update Stueble Error",
                            type="error",
                            category="Update Stueble",
                            code=404)
        )
    return FuncRes(
            data=clean_single_data(result),
            status=Status.FULL_SUCCESS,
            message=Message(name="Update Stueble Success",
                            type="success",
                            category="Update Stueble",
                            code=200)
    )


@db.cursor_handling(manually_supply_cursor=False)
def update_hosts(stueble_id: str, method: Literal["add", "remove"], user_ids: Annotated[list[int] | tuple[int] | None, "Explicit with user_uuid"] = None,
                 user_uuids: Annotated[list[str] | tuple[str] | None, "Explicit with user_id"] = None, cursor: Cursor | None = None) -> FuncRes:
    """
    adds a host to a stueble

    Args:
        stueble_id (int): id of the stueble
        user_ids (list[int | None]): ids of the users to be added as host, if None user_uuids must be provided
        user_uuids (list[str | None]): uuids of the users to be added as host, if None user_ids must be provided
        cursor (Cursor | None): Cursor object for database connection. DO NOT SUPPLY MANUALLY, AS THE DECORATOR HANDLES IT

    Returns:
        FuncRes: Return object containing user ids or error
    """

    if user_ids is None and user_uuids is None or (user_ids is not None and user_uuids is not None):
        return FuncRes(
            error="either user_ids or user_uuids must be provided",
            status=Status.FULL_ERROR,
            message=Message(name="Update Hosts Error",
                            type="error",
                            category="Update Hosts",
                            code=400)
        )

    if method not in ["add", "remove"]:
        return FuncRes(
            error="invalid method",
            status=Status.FULL_ERROR,
            message=Message(name="Update Hosts Error",
                            type="error",
                            category="Update Hosts",
                            code=400)
        )

    if user_uuids is not None:
        query = f"""SELECT id FROM users WHERE user_uuid IN ({', '.join(['%s' for _ in range(len(user_uuids))])})"""
        result = db.custom_call(
                       query=query,
                       type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
                       variables=tuple(user_uuids))
        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Update Hosts Error",
                                type="error",
                                category="Update Hosts",
                                code=500)
            )
        if len(result.data) != len(user_uuids):
            return FuncRes(
                error="one or more user_uuids are invalid",
                status=Status.FULL_ERROR,
                message=Message(name="Update Hosts Error",
                                type="error",
                                category="Update Hosts Error",
                                code=400)
            )
        user_ids = [i[0] for i in result.data]

    if method == "add":
        rows = [(user_id, stueble_id) for user_id in user_ids]
        query = """INSERT INTO hosts (user_id, stueble_id) VALUES %s"""
    else:
        rows = [tuple((user_id, stueble_id) for user_id in user_ids)]
        query = """DELETE FROM hosts WHERE (user_id, stueble_id) IN %s"""
    try:
        execute_values(cursor, query, rows)
        cursor.connection.commit() # type: ignore
    except DatabaseError as e:
        cursor.connection.rollback() # type: ignore

        return FuncRes(
            error=str(e),
            status=Status.FULL_ERROR,
            message=Message(name="Update Hosts Error",
                            type="error",
                            code=500)
            )
    return FuncRes(
        data=user_ids,
        status=Status.FULL_SUCCESS,
        message=Message(
            name="Update Hosts Success",
            type="success",
            code=200)
    )

def get_hosts(stueble_id: int) -> FuncRes:
    """
    gets the hosts for a stueble

    Args:
        stueble_id (int): id of the stueble

    Returns:
        FuncRes: Return object containing hosts data with user uuid, first name, last name and residence, or error
    """

    params = ["user_uuid", "first_name", "last_name", "residence"]

    query = f"""SELECT {', '.join(['u.' + i for i in params])} FROM hosts h JOIN users u ON u.id = h.user_id WHERE h.stueble_id = %s"""
    result = db.custom_call(
                   query=query,
                   type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
                   variables=[stueble_id])
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Error",
                            type="error",
                            category="Get Hosts",
                            code=500)
        )
    hosts = [dict(zip(params, host)) for host in result.data]
    return FuncRes(
        data=hosts,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Hosts Success",
                        type="success",
                        category="Get Hosts",
                        code=200)
    )
