from collections.abc import Callable, Sequence
from enum import Enum
import os
from typing import Any, Literal, overload

from dotenv import load_dotenv
import psycopg2 as pg
from psycopg2.extensions import connection, cursor

from packages.backend.sql_connection.common_types import (
    GenericFailure,
    GenericSuccess,
    MultipleSuccess,
    MultipleTupleSuccess,
    SingleSuccess,
)

_ = load_dotenv()

USER = os.getenv("USERDB") # stueble (like the linux user name!)
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST") # localhost
PORT = os.getenv("PORT") # 5432
DBNAME = os.getenv("DBNAME") # stueble_data

class ANSWER_TYPE(Enum):
    NO_ANSWER = -1
    SINGLE_ANSWER = 0
    LIST_ANSWER = 1

def is_valid_answer_type(value):
    return value in ANSWER_TYPE._value2member_map_

def full_pack(func: Callable[..., Any]):
    """
    full_pack \n
    wrapper function to make just one function call for initializing, closing and the actual function

    Parameters:
        func (func): function
    Returns:
        function: wrapped function
    """
    def wrapped(*args, **kwargs):
        conn, cursor = connect()
        result = func(cursor, *args, **kwargs)
        close(connection=conn, cursor=cursor)
        return result
    return wrapped

# TODO right now for development and testing enabled, for website rather use failsafes (SAME AS IN often_used_db_calls.py)
'''def catch_exception(func):
    """
    catches errors
    connect, pool, update, remove functions DON'T use this wrapper

    Parameters:
        func (func): function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise Exception(f"An error occurred in database: {e}")
    return wrapper'''

def connect(**kwargs):
    """
    connect \n
    kwargs format: user, password, host, port, database \n
    kwargs format if lazy: database (takes longer, so if called often use first option)

    Parameters:
        kwargs (dict):
    Returns:
        connection, cursor
    """
    if len(kwargs) > 0:
        conn: connection = pg.connect(**kwargs)
        return conn, conn.cursor()
    conn = pg.connect(user=USER, password=PASSWORD, host=HOST,
                                 port=PORT, database=DBNAME)
    return conn, conn.cursor()

@overload
def read_table(cursor: cursor, table_name: str, expect_single_answer: Literal[True], keywords: tuple[str] | list[str] = ("*",),
               conditions: dict[str, Any] | None = None, select_max_of_key: str = "", specific_where: str = "", variables: list[str] | None = None, 
               order_by: tuple[str, Literal[0, 1]] | None = None) -> SingleSuccess | GenericFailure: ...

@overload
def read_table(cursor: cursor, table_name: str, expect_single_answer: Literal[False] = False, keywords: tuple[str] | list[str] = ("*",),
               conditions: dict[str, Any] | None = None, select_max_of_key: str = "", specific_where: str = "", variables: list[str] | None = None, 
               order_by: tuple[str, Literal[0, 1]] | None = None) -> MultipleSuccess | GenericFailure: ...

# TODO can't return success: False right now
# TODO for arguments as list might not be completely implemented
# @catch_exception
def read_table(cursor: cursor, table_name: str, expect_single_answer: bool = False, keywords: tuple[str] | list[str] = ("*",), 
               conditions: dict[str, Any] | None = None, negated_conditions: dict[str, Any] | None = None, select_max_of_key: str = "", specific_where: str = "", variables: list[str] | None = None,
               order_by: tuple[str, Literal[0, 1]] | None = None) -> SingleSuccess | MultipleSuccess | GenericFailure:
    """
    read_table \n
    read data from a table
    
    Parameters:
        cursor (from): conn to db
        keywords (tuple[str] | list[str]): columns, that should be selected, if empty, get all
        conditions (dict): under which conditions (key: column, value: value) values should be selected, if empty, no conditions
        negated_conditions (dict): under which conditions (key: column, value: value) values should NOT be selected, if empty, no negated conditions
        expect_single_answer (bool): specify whether one or more answers are to be received, therefore it changes, whether list or single object will be returned
        select_max_of_key (bool): conditions must be empty, otherwise it won't be used
        specific_where (str): select_max_of_key must be empty as well as conditions must be empty, else specific_where is ignored, allows to pass in a unique where statement (WHERE is already in the string),
        variables (list | None): list of variables that should be passed into the specific_where statement
        order_by (tuple | None): (key to order by, 0: descending / 1: ascending) by default no ordering, if specified and second value is invalid, then set to DESC
    Returns:
        dict: {"success": bool, data: value}
    """

    if specific_where == "" and variables is not None:
        return GenericFailure(success=False, error="if specific_where is empty, variables must be None as well")

    keywords = list(keywords)
    conditions = {} if conditions is None else conditions
    negated_conditions = {} if negated_conditions is None else negated_conditions
    all_conditions = {key: {"value": value, "negated": False} for key, value in conditions.items()} | {key: {"value": value, "negated": True} for key, value in negated_conditions.items()}
    query = f"""SELECT {', '.join(keywords)} FROM {table_name}"""

    if len(all_conditions) > 0:
        query += f" WHERE {' AND '.join([f'{key} {'!' if value_data['negated'] is True else ''}= %s' for key, value_data in all_conditions.items()])}"
        if order_by is not None:
            query += f" ORDER BY {order_by[0]} {'ASC' if order_by[1] == 1 else 'DESC'}"
        cursor.execute(query, tuple([i["value"] for i in all_conditions.values()]))
        if expect_single_answer:
            data = cursor.fetchone()
            return {"success": True, "data": data}

        return {"success": True, "data": [list(i) for i in cursor.fetchall()]}

    if select_max_of_key != "":
        query += f" WHERE {select_max_of_key} = (SELECT MAX({select_max_of_key}) FROM {table_name}) LIMIT 1"
        if order_by is not None:
            query += f" ORDER BY {order_by[0]} {'ASC' if order_by[1] == 1 else 'DESC'}"
    elif specific_where != "":
        query += f" WHERE {specific_where}"
        if order_by is not None:
            query += f" ORDER BY {order_by[0]} {'ASC' if order_by[1] == 1 else 'DESC'}"

    if variables is None:
        cursor.execute(query)
    else:
        cursor.execute(query, variables)

    if expect_single_answer:
        data = cursor.fetchone()
        return {"success": True, "data": data}

    return {"success": True, "data": [list(i) for i in cursor.fetchall()]}

@overload
def insert_table(cursor: cursor, table_name: str, returning_column: None = None,
                 arguments: dict[str, Any] | list[str] | None = None) -> GenericSuccess | GenericFailure: ...

@overload
def insert_table(cursor: cursor, table_name: str, returning_column: str,
                 arguments: dict[str, Any] | list[str] | None = None) -> SingleSuccess | GenericFailure: ...

# NOTE arguments is either of type dict or of type list
# @catch_exception
def insert_table(cursor: cursor, table_name: str, returning_column: str | None = None, 
                 arguments: dict[str, Any] | list[str] | None = None) -> GenericSuccess | SingleSuccess | GenericFailure:
    """
    insert data into table

    Parameters:
        cursor (cursor): cursor for interaction with db
        table_name (str): table to insert into, if empty set all
        arguments (dict | None): values that should be entered (key: column, value: value), if empty, no conditions, if arguments is of type list, then list has to contain all values that have to be entered
        returning_column (int): returns the column
    Returns:
        dict: {"success": bool, "data": id} by default, {"success": bool} if returning is False, {"success": False, "error": e} if error occurred
    """
    if arguments is None:
        arguments = {}

    # Overloads can't distinguish between empty and non-empty strings
    if (returning_column is not None and len(returning_column) == 0):
        returning_column = None

    try:
        query = ""
        vals = []

        if type(arguments) == list:
            query = f"""INSERT INTO {table_name}
                        VALUES ({', '.join('%s' for _ in range(len(arguments)))})"""
            vals = arguments
        elif type(arguments) == dict:
            query = f"""INSERT INTO {table_name} ({', '.join(arguments.keys())})
                    VALUES ({', '.join('%s' for _, _ in enumerate(arguments.keys()))})"""
            vals = list(arguments.values())

        if returning_column != None:
            query += f" RETURNING {returning_column}"

        cursor.execute(query, vals)
        cursor.connection.commit()

        if returning_column != None:
            data = cursor.fetchone()
            return {"success": True, "data": data}
        return {"success": True}
    except Exception as e:
        cursor.connection.rollback()
        return {"success": False, "error": str(e)}

@overload
def update_table(cursor: cursor, table_name: str, returning_column: None = None, arguments: dict[str, Any] | None = None,
                 conditions: dict[str, Any] | None = None, specific_where: str = "", specific_set: str = "") -> GenericSuccess | GenericFailure: ...

@overload
def update_table(cursor: cursor, table_name: str, returning_column: str, arguments: dict[str, Any] | None = None,
                 conditions: dict[str, Any] | None = None, specific_where: str = "", specific_set: str = "") -> SingleSuccess | GenericFailure: ...

# for specific_where conditions must be empty, otherwise conditions will be ignored IMPORTANT what is being ignored differs from the other functions
def update_table(cursor: cursor, table_name: str, returning_column: str | None = None, arguments: dict[str, Any] | None = None,
                 conditions: dict[str, Any] | None = None, specific_where: str = "", specific_set: str = "") -> GenericSuccess | SingleSuccess | GenericFailure:
    """
    updates values in a table \n
    already has try catch

    Parameters:
        cursor (cursor): cursor to interact with db
        table_name (str): table to insert into, if empty set all
        arguments (dict | None): values that should be entered (key: column, value: value)
        conditions (dict | None): specify to insert into the correct row
        specific_where (str): conditions must be empty, otherwise conditions will be ignored, specifies where should be set, IMPORTANT what is being ignored differs from the other functions
        specific_set (str): arguments must be empty, otherwise arguments will be ignored, specifies what should be set
        returning_column (str): returns the specified column, returns just a single column
    Returns:
        dict: {"success": bool} by default, {"success": bool, data: value} if returning_column is filled, {"success": False, "error": e} if error occurred
    """

    if arguments is None:
        arguments = {}
    if conditions is None:
        conditions = {}

    # Overloads can't distinguish between empty and non-empty strings
    if (returning_column is not None and len(returning_column) == 0):
        returning_column = None

    try:
        query = f"""UPDATE {table_name}"""
        if specific_set != "":
            query += f""" SET {specific_set}"""
        else:
             query += f""" SET  {', '.join(key + ' = %s' for _, key in enumerate(arguments.keys()))}"""
        if specific_where != "":
            query += " WHERE " + specific_where
        else:
            query += f""" WHERE {' AND '.join(key + " = %s" for _, key in enumerate(conditions))}"""
        if returning_column != None:
            query += f" RETURNING {returning_column}"
        cursor.execute(query, list(arguments.values()) + list(conditions.values()))
        cursor.connection.commit()
        if returning_column != None:
            data = cursor.fetchone()
            return {"success": True, "data": data}
        return {"success": True}
    except Exception as e:
        cursor.connection.rollback()
        return {"success": False, "error": str(e)}

@overload
def remove_table(cursor: cursor, table_name: str, conditions: dict[str, Any],
                 returning_column: None = None) -> GenericSuccess | GenericFailure: ...

@overload
def remove_table(cursor: cursor, table_name: str, conditions: dict[str, Any],
                 returning_column: str) -> SingleSuccess | GenericFailure: ...

def remove_table(cursor: cursor, table_name: str, conditions: dict[str, Any],
                 returning_column: str | None = None) -> GenericSuccess | SingleSuccess | GenericFailure:
    """
    removes data from table \n
    already has try catch

    Parameters:
        cursor (cursor): cursor to interact with db
        table_name (str): table to insert into, if empty set all
        conditions (dict): specify from which row to remove the data
        returning_column (str): returns the specified column, returns just a single value
    Returns:
        dict: {"success": True} if successful, {"success": False, "error": e} else
    """

    # Overloads can't distinguish between empty and non-empty strings
    if (returning_column is not None and len(returning_column) == 0):
        returning_column = None

    try:
        query = f"""DELETE FROM {table_name}
                    WHERE {' AND '.join(key + " = %s" for _, key in enumerate(conditions))}"""
        if returning_column != None:
            query += f" RETURNING {returning_column}"
        cursor.execute(query, list(conditions.values()))
        cursor.connection.commit()
        if returning_column != None:
            data = cursor.fetchone()
            return {"success": True, "data": data}
        return {"success": True}
    except Exception as e:
        cursor.connection.rollback()
        return {"success": False, "error": str(e)}

@overload
def custom_call(cursor: cursor, query: str, type_of_answer: Literal[ANSWER_TYPE.NO_ANSWER],
                variables: Sequence[Any] | None = None) -> GenericSuccess | GenericFailure: ...

@overload
def custom_call(cursor: cursor, query: str, type_of_answer: Literal[ANSWER_TYPE.SINGLE_ANSWER],
                variables: Sequence[Any] | None = None) -> SingleSuccess | GenericFailure: ...

@overload
def custom_call(cursor: cursor, query: str, type_of_answer: Literal[ANSWER_TYPE.LIST_ANSWER],
                variables: Sequence[Any] | None = None) -> MultipleTupleSuccess | GenericFailure: ...

def custom_call(cursor: cursor, query: str, type_of_answer: ANSWER_TYPE, 
                variables: Sequence[Any] | None = None) -> GenericSuccess | SingleSuccess | MultipleTupleSuccess | GenericFailure:
    """
    send a custom query to the database

    Parameters:
        cursor (cursor): cursor to interact with db
        query (str):
        type_of_answer (ANSWER_TYPE): what answer to expect
        variables (list | None): list of variables that should be passed into the query
    Returns:
        dict
    """
    try:
        cursor.execute(query, variables)

        # Always commit (TODO: Filter SELECT statements)
        if query.startswith("SELECT") is False:
            cursor.connection.commit()

        if type_of_answer == ANSWER_TYPE.NO_ANSWER:
            return {"success": True}
        elif type_of_answer == ANSWER_TYPE.SINGLE_ANSWER:
            return {"success": True, "data": cursor.fetchone()}
        elif type_of_answer == ANSWER_TYPE.LIST_ANSWER:
            return {"success": True, "data": cursor.fetchall()}
        else:
            # would usually be better to check at the beginning, but since code is used backend, function is mostly used correctly. Therefore, it is more effective to check at the end if no other case matches
            return {"success": False, "error": "parameter type_of_answer of the function must be of enum type ANSWER_TYPE"}
    except Exception as e:
        cursor.connection.rollback()
        return {"success": False, "error": str(e)}

# TODO can only return success True right now
# @catch_exception
def get_time(cursor: cursor) -> SingleSuccess:
    """
    returns the current berlin time

    Parameters:
        cursor (cursor): cursor to interact with db
        connection (connection): is added to make using the wrapper full_pack easier
    Returns:
        dict: {"success": True, "data": data}
    """
    query = """SELECT NOW() AT TIME ZONE 'Europe/Berlin' AS current_time"""
    cursor.execute(query)
    data = cursor.fetchone()
    return {"success": True, "data": data[0] if data is not None else None}

def close(connection: connection | None, cursor: cursor | None = None):
    """
    closes the current cursor and/or connection
    
    Parameters:
        connection (closed): connection that should be closed
        cursor: cursor that should be closed
    """

    if connection is not None:
        connection.close()
    elif cursor is not None:
        cursor.close()

if __name__ == "__main__":
    connect()
