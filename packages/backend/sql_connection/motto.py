from packages.backend.sql_connection import database as db
from datetime import date

from packages.backend.sql_connection.common_functions import clean_single_data


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
            keywords=["motto", "date_of_time"],
            table_name="stueble_motto",
            conditions={"date_of_time": date},
            expect_single_answer=True)
    else:
        result = db.read_table(
            cursor=cursor,
            keywords=["motto", "date_of_time"],
            table_name="motto",
            expect_single_answer=True,
            specific_where="date_of_time >= CURRENT_DATE ORDER BY date_of_time ASC LIMIT 1")

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
        parameters["specific_where"] = "date_of_time = (SELECT date_of_time FROM stueble_motto WHERE date_of_time >= (CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time ASC LIMIT 1)"
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

def create_stueble(connection, cursor, date: date, motto: str, hosts: list[int], shared_apartment: str | None) -> dict:
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
    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="stueble_motto",
        data={"date_of_time": date, "motto": motto, "shared_apartment": shared_apartment, "hosts": hosts},
        returning="id"
    )
    if result["success"] is True and result["data"] is not None:
        return {"success": False, "error": "error occurred"}
    if result["success"] is True:
        return clean_single_data(result)
    return result