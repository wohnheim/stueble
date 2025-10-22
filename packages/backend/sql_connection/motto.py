from datetime import date
from typing import Annotated, Literal

from psycopg2 import DatabaseError
from psycopg2.extensions import cursor
from psycopg2.extras import execute_values

from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.ultimate_functions import clean_single_data

# replace get_motto with get_info
# TODO: Deprecated
def get_motto(cursor: cursor, date: date | None = None) -> dict:
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

    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no motto found"}

    return result

def get_info(cursor: cursor, date: date | None=None) -> dict:
    """
    gets the info from the table motto for a party at a specific date
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the info is requested
    Returns:
        dict: {"success": bool, "data": (info, author)}, {"success": False, "error": e} if error occurred
    """

    # set arguments based on whether date is provided
    if date is not None:
        arguments = {"conditions": {"date_of_time": date}, "order_by": ("date_of_time", 1)}
    else:
        arguments = {"specific_where": "date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"}

    # set keywords
    keywords = ["id", "motto", "date_of_time"]

    # fetch data
    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=keywords,
        expect_single_answer=True,
        **arguments)

    # handle error
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no stueble party found"}

    # map data to keywords
    if result["success"] is True:
        result["data"] = dict(zip(keywords, result["data"]))

    # return data
    return result

def create_stueble(cursor: cursor, date: date, motto: str,
                   shared_apartment: str | None = None, description: str | None = None) -> dict:
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

    # specify arguments
    arguments = {"date_of_time": date, "motto": motto}

    # add optional arguments
    if shared_apartment is not None:
        arguments["shared_apartment"] = shared_apartment
    if description is not None:
        arguments["description"] = description

    # execute insert
    result = db.insert_table(
        cursor=cursor,
        table_name="stueble_motto",
        arguments=arguments,
        returning_column="id")

    # handle error
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}

    # return result
    return clean_single_data(result)

def update_stueble(cursor: cursor, date: date, **kwargs) -> dict:
    """
    updates an entry in the table stueble_motto
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the motto is valid
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occurred
    """

    # check for valid keys
    allowed_keys = ["motto", "shared_apartment", "description"]
    if any(key not in allowed_keys for key in kwargs.keys()):
        return {"success": False, "error": "invalid field to update"}

    # set arguments and return error if no arguments were specified
    arguments = {key: value for key, value in kwargs.items() if value is not None}
    if len(arguments) == 0:
        return {"success": False, "error": "no fields to update"}

    # execute update
    result = db.update_table(
        cursor=cursor,
        table_name="stueble_motto",
        arguments=arguments,
        conditions={"date_of_time": date},
        returning_column="id")

    # handle error
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no stueble found"}

    # return result
    return clean_single_data(result)

def update_hosts(cursor: cursor, stueble_id: str, method: Literal["add", "remove"], user_ids: Annotated[list[int] | tuple[int] | None, "Explicit with user_uuid"] = None,
                 user_uuids: Annotated[list[str] | tuple[str] | None, "Explicit with user_id"] = None) -> dict:
    """
    adds a host to a stueble

    Parameters:
        cursor: cursor for the connection
        stueble_id (int): id of the stueble
        method (Literal["add", "remove"]): whether to add or remove the host
        user_ids (list[int] | tuple[int] | None): ids of the users to be added as host, if None user_uuids must be provided
        user_uuids (list[str] | tuple[int] | None): uuids of the users to be added as host, if None user_ids must be provided
    """

    # if neither user_ids nor user_uuids or both are provided, return error
    if (user_ids is None and user_uuids is None) or (user_ids is not None and user_uuids is not None):
        return {"success": False, "error": "either user_ids or user_uuids must be provided"}

    # if method is invalid, return error
    if method not in ["add", "remove"]:
        return {"success": False, "error": "invalid method"}

    # if user_uuids are provided, get user_ids from user_uuids
    if user_uuids is not None:
        # create query
        query = f"""SELECT id FROM users WHERE user_uuid IN ({', '.join(['%s' for _ in range(len(user_uuids))])})"""

        # execute query
        result = db.custom_call(cursor=cursor, 
                       query=query, 
                       type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                       variables=tuple(user_uuids))

        # handle errors
        if result["success"] is False:
            return result
        # if not all user_uuids are valid, return error
        if len(result["data"]) != len(user_uuids):
            return {"success": False, "error": "one or more user_uuids are invalid"}

        # set user_ids
        user_ids = [i[0] for i in result["data"]]

    # set rows for insert / delete
    rows = [(user_id, stueble_id) for user_id in user_ids]

    # create query
    if method == "add":
        query = """INSERT INTO hosts (user_id, stueble_id) VALUES %s"""
    else:
        query = """DELETE FROM hosts WHERE (user_id, stueble_id) IN %s"""

    # try executing query
    try:
        execute_values(cursor, query, rows)
        cursor.connection.commit()
    # if not all could be executed, rollback and return error
    except DatabaseError as e:
        cursor.connection.rollback()
        return {"success": False, "error": str(e)}

    # return result
    return {"success": True, "data": user_ids}

def get_hosts(cursor: cursor, stueble_id: int) -> dict:
    """
    gets the hosts for a stueble

    Parameters:
        cursor: cursor for the connection
        stueble_id (int): id of the stueble
    """

    # set parameters
    params = ["user_uuid", "first_name", "last_name", "user_name"]

    # create query
    query = f"""SELECT {', '.join(['u.' + i for i in params])} FROM hosts h JOIN users u ON u.id = h.user_id WHERE h.stueble_id = %s"""

    # execute query
    result = db.custom_call(cursor=cursor, 
                   query=query, 
                   type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                   variables=[stueble_id])

    # handle error
    if result["success"] is False:
        return result

    # combine data and keys
    hosts = [dict(zip(params, host)) for host in result["data"]]

    # return data
    return {"success": True, "data": hosts}