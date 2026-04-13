from datetime import date
from typing import Annotated, Any, Literal

from psycopg import DatabaseError
from psycopg import Cursor, sql

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
            table="stueble.motto",
            columns=["motto", "date_of_time", "id"],
            conditions={"date_of_time": date},
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    else:
        result = db.select(
            table="stueble.motto",
            columns=["motto", "date_of_time", "id"],
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            specific_where=sql.SQL("date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"))

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
        arguments = {"conditions": {"date_of_time": date}, "order_by": ("date_of_time", db.ORDER.ASC)}
    else:
        arguments = {"specific_where": sql.SQL("date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1")}

    result = db.select(
        table="stueble.motto",
        columns=["id", "motto", "date_of_time", "description"],
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
    
    result._data["stueble_id"] = result._data.pop("id") # type: ignore
    result._data["date"] = result._data.pop("date_of_time") # type: ignore

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Info Success",
                        type="success",
                        category="Get Info",
                        code=200)
    )


@DeprecationWarning
def create_stueble(date: date  | None, motto: str,
                   applicants_uuids: list[str], description: str | None = None) -> FuncRes:
    """
    creates a new entry in the table stueble.motto

    Args:
        date (datetime.date | None): date for which the motto is valid
        motto (str): motto for the stueble party
        applicants_uuids (list[str]): list of applicant IDs for the stueble party
        description (str): description for the stueble party
    Returns:
        FuncRes: id for success, error else
    """

    current_group_hash = ":".join(sorted(applicants_uuids))

    query = sql.SQL("""SELECT a.id
            FROM stueble.applicants a
            JOIN stueble.application_groups g ON a.application_group = g.id
            WHERE g.group_hash = {group_hash}""").format(group_hash=sql.Placeholder())

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[current_group_hash]
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
        query = sql.SQL("INSERT INTO stueble.applicants (user_id, application_group) VALUES {rows} RETURNING id").format(
            rows=sql.SQL(", ").join([
                sql.SQL("(SELECT id FROM users WHERE user_uuid = {user_uuid}), (SELECT id FROM stueble.application_groups WHERE group_hash = {group_hash})").format(
                    user_uuid=sql.Placeholder(), group_hash=sql.Placeholder()) for i in applicants_uuids]))
        variables = [e for i in applicants_uuids for e in (i, current_group_hash)]
        result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
            variables=variables
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
        if result.data is None or len(result.data) != len(applicants_uuids):
            return FuncRes(
                error="one or more applicant UUIDs are invalid",
                status=Status.FULL_ERROR,
                message=Message(name="Create Stueble Error",
                                type="error",
                                category="Create Stueble",
                                code=400)
            )
        
    query = sql.SQL("SELECT DISTINCT application_group FROM stueble.application_groups WHERE group_hash = {group_hash} ORDER BY application_group DESC LIMIT 1").format(group_hash=sql.Placeholder())
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[current_group_hash]
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
            error="failed to retrieve application group",
            status=Status.FULL_ERROR,
            message=Message(name="Create Stueble Error",
                            type="error",
                            category="Create Stueble",
                            code=500)
        )
    
    application_group = result.data

    arguments: dict[str, Any] = {"date_of_time": date, "motto": motto}
    arguments["application_group"] = application_group
    if description is not None:
        arguments["description"] = description

    if arguments["date_of_time"] is None:
        del arguments["date_of_time"]
        query = f"""INSERT INTO stueble.applications (date_of_time, {', '.join(arguments.keys())})
        VALUES (CURRENT_DATE + (10 - EXTRACT(DOW FROM CURRENT_DATE)) %% 7 * INTERVAL '1 day', {', '.join('%s' for _ in range(len(arguments)))})
        RETURNING id"""
        result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            variables=list(arguments.values())
        )
    else:
        result = db.insert(
            table="stueble.motto",
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
    
    """result = db.insert(
        table="stueble.dates",

    )"""
    return FuncRes(
            data=clean_single_data(result.data),
            status=Status.FULL_SUCCESS,
            message=Message(name="Create Stueble Success",
                            type="success",
                            category="Create Stueble",
                            code=200)
    )

def update_stueble(date: date | None, **kwargs) -> FuncRes:
    """
    updates an entry in the table stueble.motto

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
    specific_where = sql.SQL("")

    if (date is None):
        specific_where = sql.SQL("id = (SELECT id FROM stueble.motto WHERE date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1) ORDER BY date_of_time ASC LIMIT 1)")
    else:
        conditions =  {"date_of_time": date}

    result = db.update(
        table="stueble.motto",
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
            data=clean_single_data(result.data),
            status=Status.FULL_SUCCESS,
            message=Message(name="Update Stueble Success",
                            type="success",
                            category="Update Stueble",
                            code=200)
    )


def update_hosts(stueble_id: str, method: Literal["add", "remove"], user_ids: Annotated[list[int] | tuple[int] | None, "Explicit with user_uuid"] = None,
                 user_uuids: Annotated[list[str] | tuple[str] | None, "Explicit with user_id"] = None) -> FuncRes:
    """
    adds a host to a stueble

    Args:
        stueble_id (int): id of the stueble
        user_ids (list[int | None]): ids of the users to be added as host, if None user_uuids must be provided
        user_uuids (list[str | None]): uuids of the users to be added as host, if None user_ids must be provided

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
        query = sql.SQL("SELECT id FROM users WHERE user_uuid IN ({user_uuids})").format(user_uuids=sql.SQL(', ').join(sql.Placeholder() * len(user_uuids)))
        result = db.custom_call(
                       query=query,
                       type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
                       variables=user_uuids)
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
        variables = [e for user_id in user_ids for e in (user_id, stueble_id)] # type: ignore
        query = sql.SQL("INSERT INTO stueble.hosts (user_id, stueble_id) VALUES {vars}").format(
            vars=sql.SQL(', ').join(sql.SQL("({user_id}, {stueble_id})").format(
                user_id=sql.Placeholder(),
                stueble_id=sql.Placeholder()
                ) * len(user_ids)) # type ignore
            )
    else:
        variables = [e for user_id in user_ids for e in (user_id, stueble_id)] # type: ignore
        query = sql.SQL("DELETE FROM stueble.hosts WHERE (user_id, stueble_id) IN ({vars})").format(
            vars=sql.SQL(', ').join(sql.SQL("({user_id}, {stueble_id})").format(
                user_id=sql.Placeholder(),
                stueble_id=sql.Placeholder()
                ) * len(user_ids)) # type ignore
            )
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
        variables=variables
    )
    if result.is_error:
        return FuncRes(
            error=str(result.error),
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

    query = f"""SELECT {', '.join(['u.' + i for i in params])} FROM stueble.hosts h JOIN users u ON u.id = h.user_id WHERE h.stueble_id = %s"""
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
    for i in hosts:
        i["user_uuid"] = str(i["user_uuid"])
    return FuncRes(
        data=hosts,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Hosts Success",
                        type="success",
                        category="Get Hosts",
                        code=200)
    )
