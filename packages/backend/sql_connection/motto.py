from datetime import date
from typing import Annotated, Any, Literal, TypedDict, cast

from psycopg2 import DatabaseError
from psycopg2.extensions import cursor
from psycopg2.extras import execute_values

from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import (
    GenericFailure,
    GenericSuccess,
    SingleSuccessCleaned,
    error_to_failure,
)
from packages.backend.sql_connection.ultimate_functions import clean_single_data

class GetMottoSuccess(TypedDict):
    success: Literal[True]
    data: tuple[str, date, int]

class GetInfoSuccess(TypedDict):
    success: Literal[True]
    data: tuple[int, str]

class GetHostsData(TypedDict):
    user_uuid: str
    first_name: str
    last_name: str
    user_name: str

class GetHostsSuccess(TypedDict):
    success: Literal[True]
    data: list[GetHostsData]

# replace get_motto with get_info
# TODO: Deprecated
def get_motto(cursor: cursor, date: date | None = None) -> GetMottoSuccess | GenericFailure:
    """
    gets the motto from the table motto
    Parameters:
        cursor: cursor for the connection
        date (datetime.date | None): date for which the motto is requested, if None the motto for the next stueble will be returned
    Returns:
        dict: {"success": bool, "data": (motto, author)}, {"success": False, "error": e} if error occurred
    """

    if date is not None:
        result = db.read_table(
            cursor=cursor,
            table_name="stueble_motto",
            keywords=["motto", "date_of_time", "id"],
            conditions={"date_of_time": date},
            expect_single_answer=True)
    else:
        result = db.read_table(
            cursor=cursor,
            table_name="stueble_motto",
            keywords=["motto", "date_of_time", "id"],
            expect_single_answer=True,
            specific_where="date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1")

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no motto found"}

    return cast(GetMottoSuccess, cast(object, result))

def get_info(cursor: cursor, date: date | None=None) -> GetInfoSuccess | GenericFailure:
    """
    gets the info from the table motto for a party at a specific date
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the info is requested
    Returns:
        dict: {"success": bool, "data": (info, author)}, {"success": False, "error": e} if error occurred
    """
    conditions = None
    specific_where = ""

    arguments = {}
    if date is not None:
        arguments = {"conditions": {"date_of_time": date}, "order_by": ("date_of_time", 1)}
    else:
        arguments = {"specific_where": "date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"}

    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=["id", "motto", "date_of_time"],
        expect_single_answer=True,
        **arguments
    )

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no stueble party found"}
    
    return cast(GetInfoSuccess, cast(object, result))

def create_stueble(cursor: cursor, date: date, motto: str,
                   shared_apartment: str | None = None, description: str | None = None) -> SingleSuccessCleaned | GenericFailure:
    """
    creates a new entry in the table stueble_motto
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the motto is valid
        motto (str): motto for the stueble party
        shared_apartment (str): shared apartment for the stueble party, can be None
        description (str): description for the stueble party
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occurred
    """

    arguments: dict[str, Any] = {"date_of_time": date, "motto": motto}
    if shared_apartment is not None:
        arguments["shared_apartment"] = shared_apartment
    if description is not None:
        arguments["description"] = description

    result = db.insert_table(
        cursor=cursor,
        table_name="stueble_motto",
        arguments=arguments,
        returning_column="id"
    )

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return clean_single_data(result)

def update_stueble(cursor: cursor, date: date | None, **kwargs) -> SingleSuccessCleaned | GenericFailure:
    """
    updates an entry in the table stueble_motto
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the motto is valid
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occurred
    """

    allowed_keys = ["motto", "shared_apartment", "description"]
    if any(key not in allowed_keys for key in kwargs.keys()):
        return {"success": False, "error": "invalid field to update"}

    arguments = {key: value for key, value in kwargs.items() if value is not None}
    if len(arguments) == 0:
        return {"success": False, "error": "no fields to update"}

    conditions = None
    specific_where = ""

    if (date is None):
        specific_where = """id = (SELECT id FROM stueble_motto WHERE date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1) ORDER BY date_of_time ASC LIMIT 1)"""
    else:
        conditions =  {"date_of_time": date}

    result = db.update_table(
        cursor=cursor,
        table_name="stueble_motto",
        arguments=arguments,
        conditions=conditions,
        specific_where=specific_where,
        returning_column="id"
    )
    
    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "no stueble found"}

    return clean_single_data(result)

def update_hosts(cursor: cursor, stueble_id: str, method: Literal["add", "remove"], user_ids: Annotated[list[int] | tuple[int] | None, "Explicit with user_uuid"] = None,
                 user_uuids: Annotated[list[str] | tuple[str] | None, "Explicit with user_id"] = None) -> GenericSuccess | GenericFailure:
    """
    adds a host to a stueble

    Parameters:
        cursor: cursor for the connection
        stueble_id (int): id of the stueble
        user_ids (list[int | None]): ids of the users to be added as host, if None user_uuids must be provided
        user_uuids (list[str | None]): uuids of the users to be added as host, if None user_ids must be provided
    """

    if user_ids is None and user_uuids is None or (user_ids is not None and user_uuids is not None):
        return {"success": False, "error": "either user_ids or user_uuids must be provided"}

    if method not in ["add", "remove"]:
        return {"success": False, "error": "invalid method"}

    if user_uuids is not None:
        query = f"""SELECT id FROM users WHERE user_uuid IN ({', '.join(['%s' for _ in range(len(user_uuids))])})"""
        result = db.custom_call(cursor=cursor, 
                       query=query, 
                       type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                       variables=tuple(user_uuids))
        if result["success"] is False:
            return error_to_failure(result)
        if len(result["data"]) != len(user_uuids):
            return {"success": False, "error": "one or more user_uuids are invalid"}
        user_ids = [i[0] for i in result["data"]]

    if method == "add":
        rows = [(user_id, stueble_id) for user_id in user_ids]
        query = """INSERT INTO hosts (user_id, stueble_id) VALUES %s"""
    else:
        rows = [tuple((user_id, stueble_id) for user_id in user_ids)]
        query = """DELETE FROM hosts WHERE (user_id, stueble_id) IN %s"""
    try:
        execute_values(cursor, query, rows)
        cursor.connection.commit()
    except DatabaseError as e:
        cursor.connection.rollback()
        return {"success": False, "error": str(e)}
    return {"success": True, "data": user_ids}

def get_hosts(cursor: cursor, stueble_id: int) -> GetHostsSuccess | GenericFailure:
    """
    gets the hosts for a stueble

    Parameters:
        cursor: cursor for the connection
        stueble_id (int): id of the stueble
    """

    params = ["user_uuid", "first_name", "last_name", "residence"]

    query = f"""SELECT {', '.join(['u.' + i for i in params])} FROM hosts h JOIN users u ON u.id = h.user_id WHERE h.stueble_id = %s"""
    result = db.custom_call(cursor=cursor, 
                   query=query, 
                   type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                   variables=[stueble_id])
    if result["success"] is False:
        return error_to_failure(result)
    hosts = [dict(zip(params, host)) for host in result["data"]]
    return cast(GetHostsSuccess, cast(object, {"success": True, "data": hosts}))