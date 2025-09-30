import enum
import json
from typing import Annotated, Any, Literal, TypedDict, cast, overload

from psycopg2.extensions import cursor

from packages.backend.data_types import Email, Residence, UserRole, VerificationMethod
from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.common_types import (
    GenericFailure,
    GenericSuccess,
    MultipleSuccess,
    MultipleTupleSuccess,
    SingleSuccess,
    SingleSuccessCleaned,
    error_to_failure,
    is_single_success,
)
from packages.backend.sql_connection.ultimate_functions import clean_single_data

class AddRemoveUserSuccess(TypedDict):
    success: Literal[True]
    data: int

def add_user(cursor: cursor,
             user_role: UserRole,
             first_name: str,
             last_name: str,
             returning_column: str | None = None,
             room: str | int | None = None,
             residence: Residence | None = None,
             email: Email | None = None,
             password_hash: str | None = None,
             user_name: str | None = None) -> AddRemoveUserSuccess | GenericSuccess | GenericFailure:
    """
    adds a user to the table users

    Parameters:
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
            return {"success": False, "error": "For user_role other than extern, room, residence, email, password_hash and user_name must be set. For user_role extern, these values must not be specified."}

    arguments = {"user_role": user_role.value, "first_name": first_name, "last_name": last_name}
    if user_role != UserRole.EXTERN:
        if room is not None and str(room).isdigit() is False:
            return {"success": False, "error": "Room must be an integer, provided as str | int."}

        if room is not None: arguments["room"] = str(room)
        if residence is not None: arguments["residence"] = residence.value
        if email is not None: arguments["email"] = email.email
        if password_hash is not None: arguments["password_hash"] = password_hash
        if user_name is not None: arguments["user_name"] = user_name

    result = db.insert_table(
        cursor=cursor,
        table_name="users",
        arguments=arguments,
        returning_column=returning_column)

    if result["success"] is False:
        return error_to_failure(result)
    if is_single_success(result):
        result = clean_single_data(result)

        if result["data"] is None:
            return {"success": False, "error": "Insert of user failed"}
        return cast(AddRemoveUserSuccess, result)
    return result


def remove_user(cursor: cursor, user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name"] = None,
                user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name"] = None,
                user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name"] = None) -> AddRemoveUserSuccess | GenericFailure:
    """
    removes a user from the table users \n
    actually not the whole user but just their password will be set to NULL

    Parameters:
        cursor: cursor for the connection
        user_id (int | None): id of the user to be removed
        user_email (Email | None): email of the user to be removed
        user_name (str | None): username of the user to be removed
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": id} otherwise
    """
    if user_id is None and user_email is None and user_name is None:
        return {"success": False, "error": "Either user_id or user_email or user_name must be set."}

    conditions: dict[str, str | int] = {}
    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    elif user_name is not None:
        conditions["user_name"] = user_name

    result = db.update_table(cursor=cursor, table_name="users",
                             arguments={"password_hash": None}, conditions=conditions, returning_column="id, user_role")

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "User doesn't exist."}
    if result["data"][1] == UserRole.EXTERN.value:
        return {"success": False, "error": "User role is extern."}

    return {"success": True, "data": int(result["data"][0])}

def update_user(
        cursor: cursor,
        user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_uuid: Annotated[str | None, "Explicit with user_id, user_email OR user_name OR user_uuid"] = None,
        **kwargs) -> AddRemoveUserSuccess | GenericFailure:
    """
    updates a user in the table users

    Parameters:
        cursor: cursor for the connection
        user_id (int | None): id of the user to be updated
        user_email (Email | None): email of the user to be updated
        user_name (str | None): username of the user to be updated
        user_uuid (str | None): uuid of the user to be updated
        **kwargs: fields to update
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": True, "data": id} otherwise
    """

    allowed_fields = ["user_role", "first_name", "last_name", "email", "password_hash", "user_name"]
    for k in kwargs.keys():
        if k not in allowed_fields:
            return {"success": False, "error": f"Field {k} is not allowed to be updated."}

    if all(i is None for i in [user_id, user_email, user_name, user_uuid]):
        return {"success": False, "error": "Either user_id or user_email or user_name or user_uuid must be set."}

    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    elif user_uuid is not None:
        conditions["user_uuid"] = user_uuid
    else:
        conditions["user_name"] = user_name

    result = db.update_table(cursor=cursor, table_name="users", arguments=kwargs,
                             conditions=conditions, returning_column="id")

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "User doesn't exist."}

    return cast(AddRemoveUserSuccess, clean_single_data(result))

@overload
def get_user(
        cursor: cursor,
        expect_single_answer: Literal[True] = True,
        user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_uuid: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        keywords: tuple[str] | list[str] = ("*",),
        conditions: Annotated[dict[str, Any] | None, "Explicit with user_id, user_email, select_max_of_key, specific_where"] = None,
        select_max_of_key: Annotated[str, "Explicit with user_id, user_email, conditions, specific_where"] = "",
        specific_where: Annotated[str, "Explicit with user_id, user_email, select_max_of_key, conditions"] = "",
        order_by: Annotated[tuple[str, Literal[0, 1]] | None, "Explicit with expect_single_answer=True"] = None
    ) -> SingleSuccess | GenericFailure: ...

@overload
def get_user(
        cursor: cursor,
        expect_single_answer: Literal[False],
        user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_uuid: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        keywords: tuple[str] | list[str] = ("*",),
        conditions: Annotated[dict[str, Any] | None, "Explicit with user_id, user_email, select_max_of_key, specific_where"] = None,
        select_max_of_key: Annotated[str, "Explicit with user_id, user_email, conditions, specific_where"] = "",
        specific_where: Annotated[str, "Explicit with user_id, user_email, select_max_of_key, conditions"] = "",
        order_by: Annotated[tuple[str, Literal[0, 1]] | None, "Explicit with expect_single_answer=True"] = None
    ) -> MultipleSuccess | GenericFailure: ...

def get_user(
        cursor: cursor,
        expect_single_answer: bool = True,
        user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_uuid: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        keywords: tuple[str] | list[str] = ("*",),
        conditions: Annotated[dict[str, Any] | None, "Explicit with user_id, user_email, select_max_of_key, specific_where"] = None,
        select_max_of_key: Annotated[str, "Explicit with user_id, user_email, conditions, specific_where"] = "",
        specific_where: Annotated[str, "Explicit with user_id, user_email, select_max_of_key, conditions"] = "",
        order_by: Annotated[tuple[str, Literal[0, 1]] | None, "Explicit with expect_single_answer=True"] = None
    ) -> SingleSuccess | MultipleSuccess | GenericFailure:
    """
    retrieves a user from the table users

    Parameters:
        cursor: cursor for the connection
        user_id (int | None): id of the user to be retrieved
        user_email (Email | None): email of the user to be retrieved
        user_name (str | None): username of the user to be retrieved
        user_uuid (str | None): uuid of the user to be retrieved
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
        return {"success": False, "error": "Either expect_single_answer=True or order_by can be set."}

    # check, whether a where statement is set for sql query
    if user_id is None and user_email is None and user_name is None and conditions == {} and specific_where == "":
        return {"success": False, "error": "Either user_id, user_email, user_name, conditions or specific_where must be set."}
    conditions_counter = 0
    if user_id is not None: conditions_counter += 1
    if user_email is not None: conditions_counter += 1
    if user_name is not None: conditions_counter += 1
    if user_uuid is not None: conditions_counter += 1
    if select_max_of_key != "": conditions_counter += 1
    if specific_where != "": conditions_counter += 1
    if conditions != {}: conditions_counter += 1
    if conditions_counter > 1:
        return {
            "success": False,
            "error": "user_id, user_email, user_uuid, user_name, select_max_of_key, specific_where and conditions are explicit. Therefore just one of them can be set."
        }

    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    elif user_name is not None:
        conditions["user_name"] = user_name
    elif user_uuid is not None:
        conditions["user_uuid"] = user_uuid
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

    if result["success"] is False:
        return error_to_failure(result)

    if result["data"] is None or (isinstance(result["data"], list) and len(result["data"]) == 0):
        return {"success": False, "error": "No matching user found"}
        
    return result

def get_invited_friends(cursor: cursor, user_id: int, stueble_id: int) -> MultipleTupleSuccess | GenericFailure:
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
          ORDER BY user_id) AS invitees
    JOIN users u ON invitees.user_id = u.id;
    """

    # check how many friends were invited by the user to a specific stueble party
    result = db.custom_call(
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[user_id, stueble_id]
    )

    if result["success"] is False:
        return error_to_failure(result)

    if result["success"] is True and len(result["data"]) == 0:
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
            cursor=cursor,
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            variables=[user_id, stueble_id]
        )
        if result["success"] is False:
            return error_to_failure(result)
        if result["success"] is True and result["data"] is None:
            return {"success": False, "error": "User has to be in stueble in order to invite friends."}
        return {"success": True, "data": []}

    return result

def create_verification_code(cursor: cursor, user_id: int | None, additional_data: dict[str, Any] | None = None) -> SingleSuccessCleaned | GenericFailure:
    """
    creates a password reset code for a specific user

    Parameters:
        cursor: cursor for the connection
        user_id (int | None): id of the user; if None, then code is a verification code for email
        additional_data (dict | None): additional data to be stored in the table; can be None
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occurred
    """

    arguments = {}
    if user_id is not None:
        arguments["user_id"] = user_id
    if additional_data is not None:
        additional_data = {k: v.value if isinstance(v, enum.Enum) else v.email if isinstance(v, Email) else v for k, v in additional_data.items()}
        arguments["additional_data"] = json.dumps(additional_data)
    if arguments == {}:
        arguments = None

    result = db.insert_table(
        cursor=cursor,
        table_name="verification_codes",
        arguments=arguments,
        returning_column="reset_code")

    if result["success"] is False:
        return error_to_failure(result)
    # maybe shouldn't be possible, but still left in
    if result["success"] and result["data"] is None:
        return {"success": False, "error": "error occurred"}
    return clean_single_data(result)

@overload
def confirm_verification_code(cursor: cursor, reset_code: str, additional_data: Literal[False] = False) -> SingleSuccessCleaned | GenericFailure: ...

@overload
def confirm_verification_code(cursor: cursor, reset_code: str, additional_data: Literal[True]) -> MultipleSuccess | GenericFailure: ...

def confirm_verification_code(cursor: cursor, reset_code: str, additional_data: bool = False) -> SingleSuccessCleaned | MultipleSuccess | GenericFailure:
    """
    confirms a password reset code for a specific user

    Parameters:
        cursor: cursor for the connection
        reset_code (str): reset code of the user
        additional_data (bool): whether to return additional data
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occured
    """

    keywords = ["user_id"]
    if additional_data:
        keywords.append("additional_data")

    result = db.read_table(
        cursor=cursor,
        table_name="verification_codes",
        keywords=keywords,
        conditions={"reset_code": reset_code},
        expect_single_answer=True
    )

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "Reset code doesn't exist."}

    return result

def add_verification_method(cursor: cursor, method: VerificationMethod,
                            user_id: Annotated[str | None, "Explicit with user_uuid"]=None,
                            user_uuid: Annotated[str | None, "Explicit with user_id"]=None) -> GenericSuccess | GenericFailure:
    """
    adds a verification method for a specific user

    Parameters:
        cursor: cursor for the connection
        method (VerificationMethod): verification method to be added
        user_id (int | None): id of the user
        user_uuid (str | None): uuid of the user
    Returns:
        dict: {"success": bool} by default, {"success": False, "error": e} if error occurred
    """

    if (user_id is None and user_uuid is None) or (user_id is not None and user_uuid is not None):
        return {"success": False, "error": "Either user_id or user_uuid must be set."}

    arguments = {"method": method.value}
    if user_id is not None:
        arguments["id"] = user_id
    else:
        arguments["user_uuid"] = user_uuid

    result = db.insert_table(
        cursor=cursor,
        table_name="user_verification_methods",
        arguments=arguments,
        returning_column="id")

    if result["success"] is False:
        return error_to_failure(result)

    if result["data"] is None:
        return {"success": False, "error": "error occurred"}

    return {"success": True}

def get_users(cursor: cursor,
              user_uuids: list[str],
              keywords: list[str] | tuple[str] = ("id",)) -> MultipleSuccess | GenericFailure:
    """
    retrieves users from the table users

    Parameters:
        cursor: cursor for the connection
        user_uuids (list[str | int]): list of user uuids
        keywords (tuple[str] | list[str]): list of fields to be retrieved, defaults to ["*"]
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": users} otherwise
    """
    keywords = list(keywords)
    # users_list = [(i, "email") if isinstance(i, str) and "@" in i else (i, "user_name") for i in information]

    specific_where = f"user_uuid IN ({', '.join(['%s' for _ in range(len(user_uuids))])})"
    result = db.read_table(
        cursor=cursor,
        table_name="users",
        keywords=keywords,
        expect_single_answer=False,
        specific_where=specific_where,
        variables=tuple(user_uuids))

    if result["success"] is False:
        return error_to_failure(result)
    if len(result["data"]) != len(user_uuids):
        return {"success": False, "error": "Not all users found."}
    return result

def check_user_guest_list(cursor: cursor, user_id: int) -> SingleSuccess | GenericFailure:
    """
    checks, whether the user is on the guest list for the latest stueble

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
    """

    query = """SELECT (COALESCE(
  (SELECT event_type
   FROM events
   WHERE user_id = %s
     AND stueble_id = (
       SELECT id
       FROM stueble_motto
       WHERE date_of_time >= CURRENT_DATE
          OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1)
       ORDER BY date_of_time ASC
       LIMIT 1
     )
   ORDER BY submitted DESC
   LIMIT 1
  ),
  'remove'
) AS event_type) != 'remove' AS is_registered"""

    result = db.custom_call(
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[user_id])

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "User or stueble doesn't exist."}
    return clean_single_data(result)

def check_user_present(cursor: cursor, user_id: int) -> SingleSuccessCleaned | GenericFailure:
    """
    checks, whether the user is currently present at the latest stueble

    Parameters:
        cursor: cursor for the connection
        user_id (int): id of the user
    """

    query = """SELECT (COALESCE(
            (SELECT event_type
             FROM events
             WHERE user_id = %s
               AND stueble_id = (SELECT id 
                                 FROM stueble_motto 
                                 WHERE date_of_time >= CURRENT_DATE 
                                    OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1) 
                                 ORDER BY date_of_time ASC 
                                 LIMIT 1)
             ORDER BY submitted DESC
             LIMIT 1),
            'remove'
                       ) AS event_type) == 'arrive' AS is_registered"""

    result = db.custom_call(
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[user_id])

    if result["success"] is False:
        return error_to_failure(result)
    if result["data"] is None:
        return {"success": False, "error": "User or stueble doesn't exist."}
    return clean_single_data(result)