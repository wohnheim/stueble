from typing import Any, Literal, TypedDict


from backend.database import database as db
from backend.sql_connection.common_types import (
    GenericFailure,
    MultipleSuccess,
    SingleSuccess,
    SingleSuccessCleaned,
    error_to_failure,
    is_single_success,
)
from backend.sql_connection.ultimate_functions import clean_single_data

class ChangeConfigurationMultipleSuccess(TypedDict):
    success: Literal[True]
    data: str

def get_configuration(key: str) -> SingleSuccessCleaned | GenericFailure:
    """
    gets a configuration value from the table configurations
    Args:
        key (str): key of the configuration
    Returns:
        dict: {"success": bool, "data": value}, {"success": False, "error": e} if error occurred
    """

    result = db.select(
        columns=["value"],
        table="configurations",
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        conditions={"key": key})

    if result["success"] is False:
        return error_to_failure(result)
    if is_single_success(result) and result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return clean_single_data(result)

def get_all_configurations() -> MultipleSuccess | GenericFailure:
    """
    gets all configuration values from the table configurations
    Returns:
        dict: {"success": bool, "data": value}, {"success": False, "error": e} if error occurred
    """
    result = db.select(
        columns=["key", "value"],
        table="configurations",
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result["success"] is False:
        return error_to_failure(result)
    return {"success": True, "data": {i[0]: i[1] for i in result["data"]}}

def change_configuration(key: str, value: Any) -> SingleSuccess | GenericFailure:
    """
    changes a configuration value from the table configurations
    Args:
        key (str): key of the configuration
        value: new value of the configuration
    """
    result = db.update(
        table="configurations",
        columns={"value": value}, 
        conditions={"key": key},
        returning_column="key"
    )

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return result

def change_multiple_configurations(configurations: dict[str, Any]) -> ChangeConfigurationMultipleSuccess | GenericFailure:
    """
    changes multiple configuration values from the table configurations
    Args:
        configurations (dict): dictionary of key-value pairs to change
    """
    for key, value in configurations.items():
        result = change_configuration(key, value)
        if result["success"] is False:
            return result
    return {"success": True, "data": f"changed {len(configurations)} values"}
