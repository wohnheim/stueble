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

def get_all_configurations(cursor) -> dict:
    """
    gets all configuration values from the table configurations
    Parameters:
        cursor: cursor for the connection
    Returns:
        dict: {"success": bool, "data": value}, {"success": False, "error": e} if error occurred
    """
    result = db.read_table(
        cursor=cursor,
        keywords=["key", "value"],
        table_name="configurations",
        expect_single_answer=False)
    return result

def change_configuration(connection, cursor, key: str, value) -> dict:
    """
    changes a configuration value from the table configurations
    Parameters:
        cursor: cursor for the connection
        key (str): key of the configuration
        value: new value of the configuration
    """
    result = db.update_table(
        connection=connection,
        cursor=cursor,
        table_name="configurations",
        arguments={"value": value}, 
        conditions={"key": key},
        returning_column="key"
    )

    if result["success"] and result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return result

def change_multiple_configurations(connection, cursor, configurations: dict) -> dict:
    """
    changes multiple configuration values from the table configurations
    Parameters:
        cursor: cursor for the connection
        configurations (dict): dictionary of key-value pairs to change
    """
    for key, value in configurations.items():
        result = change_configuration(connection, cursor, key, value)
        if not result["success"]:
            return result
    return {"success": True, "data": f"changed {len(configurations)} configurations"}
