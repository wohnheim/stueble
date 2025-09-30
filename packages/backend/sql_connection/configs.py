from typing import Any, Literal, TypedDict

from psycopg2.extensions import cursor

from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import (
    GenericFailure,
    MultipleSuccess,
    SingleSuccess,
    SingleSuccessCleaned,
    error_to_failure,
    is_single_success,
)
from packages.backend.sql_connection.ultimate_functions import clean_single_data

class ChangeConfigurationMultipleSuccess(TypedDict):
    success: Literal[True]
    data: str

def get_configuration(cursor: cursor, key: str) -> SingleSuccessCleaned | GenericFailure:
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

    if result["success"] is False:
        return error_to_failure(result)
    if is_single_success(result) and result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return clean_single_data(result)

def get_all_configurations(cursor: cursor) -> MultipleSuccess | GenericFailure:
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

    if result["success"] is False:
        return error_to_failure(result)
    return result

def change_configuration(cursor: cursor, key: str, value: Any) -> SingleSuccess | GenericFailure:
    """
    changes a configuration value from the table configurations
    Parameters:
        cursor: cursor for the connection
        key (str): key of the configuration
        value: new value of the configuration
    """
    result = db.update_table(
        cursor=cursor,
        table_name="configurations",
        arguments={"value": value}, 
        conditions={"key": key},
        returning_column="key"
    )

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return result

def change_multiple_configurations(cursor: cursor, configurations: dict[str, Any]) -> ChangeConfigurationMultipleSuccess | GenericFailure:
    """
    changes multiple configuration values from the table configurations
    Parameters:
        cursor: cursor for the connection
        configurations (dict): dictionary of key-value pairs to change
    """
    for key, value in configurations.items():
        result = change_configuration(cursor, key, value)
        if result["success"] is False:
            return result
    return {"success": True, "data": f"changed {len(configurations)} values"}
