from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.ultimate_functions import clean_single_data


def get_configuration(cursor, key: str) -> dict:
    """
    gets a configuration value from the table configurations
    Parameters:
        cursor: cursor for the connection
        key (str): key of the configuration
    Returns:
        dict: {"success": bool, "data": value}, {"success": False, "error": e} if error occurred
    """

    result = db.read_table(
        cursor=cursor,
        keywords=["value"],
        table_name="configurations",
        expect_single_answer=True,
        conditions={"key": key})
    if result["success"] and result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return clean_single_data(result)