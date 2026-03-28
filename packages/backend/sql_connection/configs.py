from typing import Any

from backend.database import database as db
from backend.sql_connection.ultimate_functions import clean_single_data
from backend.datatypes.funcres import FuncRes, Status, Message


def get_configuration(key: str) -> FuncRes:
    """
    gets a configuration value from the table configurations
    Args:
        key (str): key of the configuration
    Returns:
        FuncRes: Return object with success status and data or error message
    """

    result = db.select(
        columns=["value"],
        table="configurations",
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        conditions={"key": key})

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Configuration Error",
                            type="error",
                            category="Get Configuration",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error=f"no configuration for {key} found",
            status=Status.FULL_ERROR,
            message=Message(name="Get Configuration Error",
                            type="error",
                            category="Get Configuration",
                            code=404)
        )
    return FuncRes(
            data=clean_single_data(result),
            status=Status.FULL_SUCCESS,
            message=Message(name="Get Configuration Success",
                            type="success",
                            category="Get Configuration",
                            code=200)
    )

def get_all_configurations() -> FuncRes:
    """
    gets all configuration values from the table configurations
    Returns:
        FuncRes: Return object with success status and data or error message
    """
    result = db.select(
        columns=["key", "value"],
        table="configurations",
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get All Configuration Error",
                            type="error",
                            category="Get All Configuration",
                            code=500)
        )
    return FuncRes(
            data={i["key"]: i["value"] for i in result.data},
            status=Status.FULL_SUCCESS,
            message=Message(name="Get Configuration Success",
                            type="success",
                            category="Get Configuration",
                            code=200)
    )

def change_configuration(key: str, value: Any) -> FuncRes:
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

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Change Configuration Error",
                            type="error",
                            category="Change Configuration",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error=f"no configuration for {key} found",
            status=Status.FULL_ERROR,
            message=Message(name="Change Configuration Error",
                            type="error",
                            category="Change Configuration",
                            code=404)
        )
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
            message=Message(name="Change Configuration Success",
                            type="success",
                            category="Change Configuration",
                            code=200)
    )

def change_multiple_configurations(configurations: dict[str, Any]) -> FuncRes:
    """
    changes multiple configuration values from the table configurations
    Args:
        configurations (dict): dictionary of key-value pairs to change
    """
    for key, value in configurations.items():
        result = change_configuration(key, value)
        if result.is_error:
            return result
    return FuncRes(
        data=f"changed {len(configurations)} values",
        status=Status.FULL_SUCCESS,
            message=Message(name="Change Multiple Configuration Success",
                            type="success",
                            category="Change Multiple Configuration",
                            code=200)
    )
