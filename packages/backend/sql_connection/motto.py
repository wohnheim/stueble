from packages.backend.sql_connection import database as db, users
from datetime import date
from typing import Annotated, Literal
import psycopg2

from packages.backend.sql_connection.ultimate_functions import clean_single_data


def get_motto(cursor, date: date | None=None) -> dict:
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
            keywords=["motto", "date_of_time", "id"],
            table_name="stueble_motto",
            conditions={"date_of_time": date},
            expect_single_answer=True)
    else:
        result = db.read_table(
            cursor=cursor,
            keywords=["motto", "date_of_time", "id"],
            table_name="stueble_motto",
            expect_single_answer=True,
            specific_where="date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1")

    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no motto found"}
    return result

def get_info(cursor, date: date | None=None) -> dict:
    """
    gets the info from the table motto for a party at a specific date
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the info is requested
    Returns:
        dict: {"success": bool, "data": (info, author)}, {"success": False, "error": e} if error occurred
    """
    parameters = {}
    if date is not None:
        parameters["conditions"] = {"date_of_time": date}
    else:
        parameters["specific_where"] = "date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE -1) ORDER BY date_of_time ASC LIMIT 1"
    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=["id", "motto"],
        expect_single_answer=True,
        order_by=("date_of_time", "ASC"),
        **parameters
    )

    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no stueble party found"}
    return result

def create_stueble(connection, cursor, date: date, motto: str, hosts: list[int]=None, shared_apartment: str | None=None) -> dict:
    """
    creates a new entry in the table stueble_motto
    Parameters:
        connection: connection to the database
        cursor: cursor for the connection
        date (datetime.date): date for which the motto is valid
        motto (str): motto for the stueble party
        hosts (list[int]): list of user ids who are the hosts for the stueble party
        shared_apartment (str): shared apartment for the stueble party, can be None
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occurred
    """

    arguments = {"date_of_time": date, "motto": motto}
    if shared_apartment is not None:
        arguments["shared_apartment"] = shared_apartment
    if hosts is not None:
        arguments["hosts"] = hosts

    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="stueble_motto",
        arguments=arguments,
        returning_column="id"
    )
    if result["success"] is True and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    if result["success"] is True:
        return clean_single_data(result)
    return result

def update_stueble(connection, cursor, date: date, **kwargs) -> dict:
    """
    updates an entry in the table stueble_motto
    Parameters:
        connection: connection to the database
        cursor: cursor for the connection
        date (datetime.date): date for which the motto is valid
        kwargs: arguments to be updated, can be "motto", "hosts", "shared_apartment"
    Returns:
        dict: {"success": bool, "data": id}, {"success": False, "error": e} if error occurred
    """

    allowed_keys = ["motto", "hosts", "shared_apartment"]
    if any(key not in allowed_keys for key in kwargs.keys()):
        return {"success": False, "error": "invalid field to update"}

    result = db.update_table(
        connection=connection,
        cursor=cursor,
        table_name="stueble_motto",
        arguments=kwargs, 
        conditions={"date_of_time": date},
        returning_column="id"
    )
    if result["success"] is True and result["data"] is None:
        return {"success": False, "error": "no stueble found"}
    if result["success"] is True:
        return clean_single_data(result)
    return result

def update_hosts(connection, cursor, stueble_id: str, method: Literal["add", "remove"], user_ids: Annotated[list[int | None], "Explicit with user_uuid"]=None, user_uuids: Annotated[list[str | None], "Explicit with user_id"]=None)->dict:
    """
    adds a host to a stueble

    Parameters:
        connection: connection to the database
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
        result = db.custom_call(connection=None, 
                       cursor=cursor, 
                       query=query, 
                       type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                       variables=user_uuids)
        if result["success"] is False:
            return result
        if len(result["data"]) != len(user_uuids):
            return {"success": False, "error": "one or more user_uuids are invalid"}
        user_ids = result["data"]
    
    rows = [(user_id, stueble_id) for user_id in user_ids]

    if method == "add":
        query = """INSERT INTO hosts (user_id, stueble_id) VALUES %s"""
    else:
        query = """DELETE FROM hosts WHERE (user_id, stueble_id) IN %s"""
    try:
        psycopg2.extras.execute_values(cursor, query, rows)
        connection.commit()
    except psycopg2.DatabaseError as e:
        connection.rollback()
        return {"success": False, "error": str(e)}
    return {"success": True}

def get_hosts(cursor, stueble_id: int) -> dict:
    """
    gets the hosts for a stueble

    Parameters:
        cursor: cursor for the connection
        stueble_id (int): id of the stueble
    """

    query = """SELECT u.user_uuid, u.first_name, u.last_name, u.user_name FROM hosts h JOIN users u ON u.id = h.user_id WHERE h.stueble_id = %s"""
    result = db.custom_call(connection=None, 
                   cursor=cursor, 
                   query=query, 
                   type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, 
                   variables=[stueble_id])
    return result