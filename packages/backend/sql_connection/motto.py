from collections.abc import Sequence
from datetime import date
from typing import Annotated, Any, Literal, TypedDict, cast, overload

from psycopg2 import DatabaseError
from psycopg2.extensions import cursor
from psycopg2.extras import execute_values

from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import (
    GenericFailure,
    GenericSuccess,
    SingleSuccessCleaned,
    is_generic_failure,
    is_multiple_tuple_success,
    is_single_success,
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

    if is_single_success(result) and result["data"] is None:
        return {"success": False, "error": "no motto found"}
    return cast(GetMottoSuccess | GenericFailure, result)

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

    if date is not None:
        conditions = {"date_of_time": date}
    else:
        specific_where = "date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"

    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=["id", "motto", "date_of_time"],
        expect_single_answer=True,
        order_by=("date_of_time", 1),
        conditions=conditions,
        specific_where=specific_where
    )

    if is_single_success(result) and result["data"] is None:
        return {"success": False, "error": "no stueble party found"}

    return cast(GetInfoSuccess | GenericFailure, result)

def create_stueble(cursor: cursor, date: date, motto: str, hosts: list[int] | None = None, 
                   shared_apartment: str | None = None) -> SingleSuccessCleaned | GenericFailure:
    """
    creates a new entry in the table stueble_motto
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the motto is valid
        motto (str): motto for the stueble party
        hosts (list[int]): list of user ids who are the hosts for the stueble party
        shared_apartment (str): shared apartment for the stueble party, can be None
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occurred
    """

    arguments: dict[str, Any] = {"date_of_time": date, "motto": motto}
    if shared_apartment is not None:
        arguments["shared_apartment"] = shared_apartment
    if hosts is not None:
        arguments["hosts"] = hosts

    result = db.insert_table(
        cursor=cursor,
        table_name="stueble_motto",
        arguments=arguments,
        returning_column="id"
    )

    if is_single_success(result):
        if result["data"] is None:
            return {"success": False, "error": "error occurred"}
        return clean_single_data(result)
    return result

def update_stueble(cursor: cursor, date: date, **kwargs) -> SingleSuccessCleaned | GenericFailure:
    """
    updates an entry in the table stueble_motto
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the motto is valid
        kwargs: arguments to be updated, can be "motto", "hosts", "shared_apartment"
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occurred
    """

    allowed_keys = ["motto", "hosts", "shared_apartment"]
    if any(key not in allowed_keys for key in kwargs.keys()):
        return {"success": False, "error": "invalid field to update"}

    arguments = {key: value for key, value in kwargs.items() if value is not None}
    if len(arguments) == 0:
        return {"success": False, "error": "no fields to update"}

    result = db.update_table(
        cursor=cursor,
        table_name="stueble_motto",
        arguments=arguments,
        conditions={"date_of_time": date},
        returning_column="id"
    )

    if is_single_success(result):
        if result["data"] is None:
            return {"success": False, "error": "no stueble found"}
        return clean_single_data(result)
    return result

@overload
def update_hosts(cursor: cursor, stueble_id: str, method: Literal["add", "remove"], user_ids: None = None, user_uuids: None = None) -> GenericFailure: ...

@overload
def update_hosts(cursor: cursor, stueble_id: str, method: Literal["add", "remove"], user_ids: Annotated[Sequence[int], "Explicit with user_uuid"],
                 user_uuids: None = None) -> GenericSuccess | GenericFailure: ...

@overload
def update_hosts(cursor: cursor, stueble_id: str, method: Literal["add", "remove"], user_ids: None = None,
                 user_uuids: Annotated[Sequence[str], "Explicit with user_id"] = ()) -> GenericSuccess | GenericFailure: ...

def update_hosts(cursor: cursor, stueble_id: str, method: Literal["add", "remove"], user_ids: Annotated[Sequence[int] | None, "Explicit with user_uuid"] = None,
                 user_uuids: Annotated[Sequence[str] | None, "Explicit with user_id"] = None) -> GenericSuccess | GenericFailure:
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
        query = """SELECT id FROM users WHERE id IN %s"""
        result = db.custom_call(cursor=cursor, 
                       query=query, 
                       type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                       variables=user_uuids)
        if is_generic_failure(result):
            return result
        if is_multiple_tuple_success(result):
            if len(result["data"]) != len(user_uuids):
                return {"success": False, "error": "one or more user_uuids are invalid"}
            user_ids = list(map(lambda d: int(d[0]), result["data"]))
    
    rows = [(user_id, stueble_id) for user_id in cast(list[int], user_ids)]

    if method == "add":
        query = """INSERT INTO hosts (user_id, stueble_id) VALUES %s"""
    else:
        query = """DELETE FROM hosts WHERE (user_id, stueble_id) IN %s"""
    try:
        execute_values(cursor, query, rows)
        cursor.connection.commit()
    except DatabaseError as e:
        cursor.connection.rollback()
        return {"success": False, "error": str(e)}
    return {"success": True}

def get_hosts(cursor: cursor, stueble_id: int) -> GetHostsSuccess | GenericFailure:
    """
    gets the hosts for a stueble

    Parameters:
        cursor: cursor for the connection
        stueble_id (int): id of the stueble
    """

    params = ["user_uuid", "first_name", "last_name", "user_name"]

    query = f"""SELECT {', '.join(['u.' + i for i in params])} FROM hosts h JOIN users u ON u.id = h.user_id WHERE h.stueble_id = %s"""
    result = db.custom_call(cursor=cursor, 
                   query=query, 
                   type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                   variables=[stueble_id])
    if result["success"] is False:
        return result
    hosts = [dict(zip(params, host)) for host in result["data"]]
    return cast(GetHostsSuccess, cast(object, {"success": True, "data": hosts}))