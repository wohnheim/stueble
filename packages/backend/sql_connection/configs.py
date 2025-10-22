from psycopg2.extensions import cursor

from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.ultimate_functions import clean_single_data

def get_configuration(cursor: cursor, key: str) -> dict:
    """
    gets a configuration value from the table configurations
    Parameters:
        cursor: cursor for the connection
        key (str): key of the configuration
    Returns:
        dict: {"success": bool, "data": value}, {"success": False, "error": e} if error occurred
    """

    # get a specific configuration value
    result = db.read_table(
        cursor=cursor,
        keywords=["value"],
        table_name="configurations",
        expect_single_answer=True,
        conditions={"key": key})

    # return the result
    if result["success"] and result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return clean_single_data(result)

def get_all_configurations(cursor: cursor) -> dict:
    """
    gets all configuration values from the table configurations
    Parameters:
        cursor: cursor for the connection
    Returns:
        dict: {"success": bool, "data": value}, {"success": False, "error": e} if error occurred
    """

    # set keywords
    keywords = ["key", "value"]

    # get all configuration values
    result = db.read_table(
        cursor=cursor,
        keywords=keywords,
        table_name="configurations",
        expect_single_answer=False)

    # map the keys to the values
    if result["success"]:
        result["data"] = [{key: value for key, value in zip(keywords, item)} for item in result["data"]]

    # return the result
    return result

def change_configuration(cursor: cursor, key: str, value) -> dict:
    """
    changes a configuration value from the table configurations
    Parameters:
        cursor: cursor for the connection
        key (str): key of the configuration
        value: new value of the configuration
    """

    # change a specific configuration value
    result = db.update_table(
        cursor=cursor,
        table_name="configurations",
        arguments={"value": value}, 
        conditions={"key": key},
        returning_column="key")

    # catch error
    if result["success"] and result["data"] is None:
        return {"success": False, "error": f"no configuration for {key} found"}
    return result

def change_multiple_configurations(cursor: cursor, configurations: dict) -> dict:
    """
    changes multiple configuration values from the table configurations
    Parameters:
        cursor: cursor for the connection
        configurations (dict): dictionary of key-value pairs to change
    """

    # split information for placeholders
    case_statements = '\n'.join(["WHEN %s THEN %s" for i in range(len(configurations))])
    keys = configurations.keys()
    values = configurations.values()

    params = [i for i in zip(keys, values)] + [tuple(keys)]

    # create query
    query = f"""UPDATE configurations
            SET value = CASE key
            {case_statements}
            END
            WHERE key IN %s"""

    # execute query
    result = db.custom_call(cursor=cursor,
                            query=query,
                            type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
                            variables=params)

    # return result
    if result["success"] is False:
        return result
    return {"success": True, "data": f"changed {len(configurations)} values"}
