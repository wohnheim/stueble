import backend.sql_connection.database as db
from datetime import datetime, date

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
        parameters["specific_where"] = "(SELECT date_of_time FROM stueble_motto WHERE date_of_time >= (CURRENT_DATE - INTERVAL '1 day') ORDER BY date_of_time ASC LIMIT 1)"
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