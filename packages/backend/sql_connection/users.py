from packages.backend.sql_connection import database as db
from typing import Annotated

from packages.backend.data_types import *
from packages.backend.sql_connection.common_functions import clean_single_data


def add_user(connection,
             cursor,
             user_role: UserRole,
             first_name: str,
             last_name: str,
             returning: str="",
             room: str | int | None=None,
             residence: Residence | None=None,
             email: Email | None=None,
             password_hash: str | None=None,
             user_name: str | None=None) -> dict:
    """
    adds a user to the table users

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_role (UserRole): available roles for the user
        first_name (str): first name of the user
        last_name (str): last name of the user
        returning (str): which column to return
        room (str | int | None): room of the user
        residence (Residence | None): residence of the user
        email (Email | None): email of the user
        password_hash (str | None): password hash of the user
        user_name (str | None): username of the user
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occurred
    """
    values_set = any(i is None for i in [room, residence, email, password_hash, user_name, first_name, last_name])
    values_not_set = any(i is not None for i in [room, residence, email, password_hash, user_name])

    if (values_set and user_role != UserRole.EXTERN) or (user_role == UserRole.EXTERN and values_not_set):
        if user_role != UserRole.EXTERN:
            return {"success": False, "error": ValueError("For user_role other than extern, room, residence, email, password_hash and user_name must be set. For user_role extern, these values must not be specified.")}

    arguments = {"user_role": user_role.value, "first_name": first_name, "last_name": last_name}
    if user_role != UserRole.EXTERN:
        try:
            room = int(room)
        except ValueError:
            return {"success": False, "error": "Room must be an integer, provided as str | int."}
        arguments["room"] = room
        arguments["residence"] = residence.value
        arguments["email"] = email.email
        arguments["password_hash"] = password_hash
        arguments["user_name"] = user_name

    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="users",
        arguments=arguments,
        returning_column=returning)
    if returning != "" and result["success"]:
        return clean_single_data(result)
    return result


def remove_user(connection, cursor, user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name"] = None,
                user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name"] = None,
                user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name"] = None) -> dict:
    """
    removes a user from the table users \n
    actually not the whole user but just their password will be set to NULL

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int | None): id of the user to be removed
        user_email (Email | None): email of the user to be removed
        user_name (str | None): username of the user to be removed
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": id} otherwise
    """
    if user_id is None and user_email is None and user_name is None:
        return {"success": False, "error": ValueError("Either user_id or user_email or user_name must be set.")}
    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    elif user_name is not None:
        conditions["user_name"] = user_name
    result = db.update_table(connection=connection, cursor=cursor, table_name="users",
                             arguments={"password_hash": None}, conditions=conditions, returning_column="user_role")
    if result["success"] is False:
        return result
    if result["data"] is None:
        return {"success": False, "error": "User doesn't exist."}
    result = clean_single_data(result)
    if result["data"] == UserRole.EXTERN.value:
        return {"success": False, "error": "User role is extern."}
    return {"success": True, "data": user_id}

def update_user(
        connection,
        cursor,
        user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name"] = None,
        user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name"] = None,
        **kwargs) -> dict:
    """
    updates a user in the table users

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int | None): id of the user to be updated
        user_email (Email | None): email of the user to be updated
        user_name (str | None): username of the user to be updated
        **kwargs: fields to update
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": id} otherwise
    """

    allowed_fields = ["user_role", "first_name", "last_name", "email", "password_hash", "user_name"]
    for k, v in kwargs.items():
        if k not in allowed_fields:
            return {"success": False, "error": ValueError(f"Field {k} is not allowed to be updated.")}

    if user_id is None and user_email is None and user_name is None:
        return {"success": False, "error": ValueError("Either user_id or user_email or user_name must be set.")}
    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    else:
        conditions["user_name"] = user_name
    result = db.update_table(connection=connection, cursor=cursor, table_name="users", arguments=kwargs,
                             conditions=conditions, returning_column="id")
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "User doesn't exist."}
    return clean_single_data(result)

def get_user(
        cursor,
        user_id: Annotated[int | None, "set EITHER user_id OR user_email or user_name"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email or user_name"] = None,
        user_name: Annotated[str | None, "set EITHER user_id OR user_email or user_name"] = None,
        keywords: tuple[str] | list[str] = ("*",),
        conditions: Annotated[dict | None, "Explicit with user_id, user_email, select_max_of_key, specific_where"] = None,
        expect_single_answer=True,
        select_max_of_key: Annotated[str, "Explicit with user_id, user_email, conditions, specific_where"] = "",
        specific_where: Annotated[str, "Explicit with user_id, user_email, select_max_of_key, conditions"] = "",
        order_by: Annotated[tuple, "Explicit with expect_single_answer=True"] = None) -> dict:
    """
    retrieves a user from the table users

    Parameters:
        cursor: cursor for the connection
        user_id (int | None): id of the user to be retrieved
        user_email (Email | None): email of the user to be retrieved
        user_name (str | None): username of the user to be retrieved
        keywords (tuple[str] | list[str]): list of fields to be retrieved, defaults to ["*"]
        conditions (dict | None): additional conditions for the query
        expect_single_answer (bool): whether to expect a single user or multiple users
        select_max_of_key (str): if set, will select the max of this key
        specific_where (str): if set, will add this specific where clause
        order_by (tuple): if set, will order the results by this tuple
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": user} otherwise
    """
    keywords = list(keywords)
    if conditions is None:
        conditions = {}
    # check, whether explicitly of expect_single_answer and order_by is met
    if expect_single_answer and order_by is not None:
        return {"success": False, "error": ValueError("Either expect_single_answer=True or order_by can be set.")}

    # check, whether a where statement is set for sql query
    if user_id is None and user_email is None and user_name is None and conditions == {} and specific_where == "":
        return {"success": False, "error": ValueError("Either user_id, user_email, user_name, conditions or specific_where must be set.")}
    conditions_counter = 0
    if user_id is not None: conditions_counter += 1
    if user_email is not None: conditions_counter += 1
    if user_name is not None: conditions_counter += 1
    if select_max_of_key != "": conditions_counter += 1
    if specific_where != "": conditions_counter += 1
    if conditions != {}: conditions_counter += 1
    if conditions_counter > 1:
        return {"success": False, "error": ValueError(
            "user_id, user_email, select_max_of_key, specific_where and conditions are explicit. Therefore just one of them can be set.")}

    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    elif user_name is not None:
        conditions["user_name"] = user_name
    value = {}
    if order_by is not None:
        value["order_by"] = order_by

    result = db.read_table(
        cursor=cursor,
        table_name="users",
        keywords=keywords,
        expect_single_answer=expect_single_answer,
        conditions=conditions,
        select_max_of_key=select_max_of_key,
        specific_where=specific_where,
        **value)

    if result["success"] and result["data"] is None:
        return {"success": False, "error": "User doesn't exist."}
    return result

def get_invited_friends(cursor, user_id: int, stueble_id: int) -> dict:
    """
    retrieves all friends that were invited by a specific user to a specific stueble party

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user who invited friends
        stueble_id (int): id of the specific stueble party
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": friends} otherwise
    """

    query = """
    SELECT u.first_name, u.last_name, u.user_role, u.user_uuid
    FROM (SELECT user_id
          FROM (SELECT DISTINCT ON (user_id) *
                FROM events
                WHERE invited_by = %s
                  AND stueble_id = %s
                  AND event_type IN ('add', 'remove')
                ORDER BY user_id, submitted DESC) as latest_event
          WHERE latest_event = 'add'
          ORDER BY user_id) as invitees
    JOIN users AS u ON invitees.user_id = u.id;
    """

    # check how many friends were invited by the user to a specific stueble party
    result = db.custom_call(
        connection=None,
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[user_id, stueble_id]
    )

    if result["success"] is True and result["data"] is None:
        # if no friends were invited, check if user is registered for the specific stueble
        query = """
        SELECT 'add' =
        COALESCE((SELECT event_type
        FROM events
        WHERE user_id = %s
          AND stueble_id = %s
          AND event_type IN ('add', 'remove')
        ORDER BY submitted DESC
        LIMIT 1), 'remove')
        """
        result = db.custom_call(
            connection=None,
            cursor=cursor,
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            variables=[user_id, stueble_id]
        )
        if result["success"] is True and (result["data"] is None or result["data"] is False):
            return {"success": False, "error": "User has to be in stueble in order to invite friends."}
        elif result["success"] is False:
            return result
        return {"success": True, "data": []}

    return result

def create_password_reset_code(connection, cursor, user_id: int | None) -> dict:
    """
    creates a password reset code for a specific user

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int | None): id of the user; if None, then code is a verification code for email
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occured
    """

    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="password_resets",
        arguments={"user_id": user_id} if user_id is not None else None,
        returning_column="reset_code")

    # maybe shouldn't be possible, but still left in
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return clean_single_data(result)

def confirm_reset_code(cursor, reset_code: str):
    """
    confirms a password reset code for a specific user

    Parameters:
        cursor: cursor for the connection
        reset_code (str): reset code of the user
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occured
    """

    result = db.read_table(
        cursor=cursor,
        table_name="password_resets",
        keywords=["user_id"],
        conditions={"reset_code": reset_code},
        expect_single_answer=True
    )

    if result["success"] is False:
        return result
    if result["data"] is None:
        return {"success": False, "error": "Reset code doesn't exist."}
    return clean_single_data(result)

def add_verification_method(connection, cursor, method: VerificationMethod,
                            user_id: Annotated[str | None, "Explicit with user_uuid"]=None,
                            user_uuid: Annotated[str | None, "Explicit with user_id"]=None) -> dict:
    """
    adds a verification method for a specific user

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        method (VerificationMethod): verification method to be added
        user_id (int | None): id of the user
        user_uuid (str | None): uuid of the user
    Returns:
        dict: {"success": bool} by default, {"success": False, "error": e} if error occurred
    """

    if (user_id is None and user_uuid is None) or (user_id is not None and user_uuid is not None):
        return {"success": False, "error": ValueError("Either user_id or user_uuid must be set.")}

    arguments = {"method": method.value}
    if user_id is not None:
        arguments["id"] = user_id
    else:
        arguments["user_uuid"] = user_uuid

    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name="user_verification_methods",
        arguments=arguments,
        returning_column="id")

    if result["success"] is False:
        return result

    if result["data"] is None:
        return {"success": False, "error": "error occurred"}

    return {"success": True}

def get_users(cursor,
              information: list[str | int],
              keywords: tuple[str] | list[str] = ("id",)) -> dict:
    """
    retrieves users from the table users

    Parameters:
        cursor: cursor for the connection
        information (list[str | int]): list of user emails / usernames
        keywords (tuple[str] | list[str]): list of fields to be retrieved, defaults to ["*"]
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": users} otherwise
    """
    keywords = list(keywords)
    users_list = [(i, "email") if "@" in i else (i, "user_name") for i in information]

    specific_where = f' OR '.join([f"{i[1]} = {i[0]}"  for i in users_list])
    result = db.read_table(
        cursor=cursor,
        table_name="users",
        keywords=keywords,
        expect_single_answer=False,
        specific_where=specific_where)

    if result["success"] and result["data"] is None:
        return {"success": False, "error": "No users found."}
    return result