import backend.sql_connection.database as db
from datetime import datetime

def get_motto(cursor, date: datetime.date | None=None) -> dict:
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
            table_name="motto",
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

def get_info(cursor, date: datetime.date | None) -> dict:
    """
    gets the info from the table motto for a party at a specific date
    Parameters:
        cursor: cursor for the connection
        date (datetime.date): date for which the info is requested
    Returns:
        dict: {"success": bool, "data": (info, author)}, {"success": False, "error": e} if error occurred
    """

    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=["id", "motto"],
        conditions={"date_of_time": date},
        expect_single_answer=True
    )

    if result["success"] and result["data"] is None:
        return {"success": False, "error": "no stueble party found"}
    return result