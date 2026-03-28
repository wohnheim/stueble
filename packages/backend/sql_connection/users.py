import enum
import json
from typing import Annotated, Any, Literal
from psycopg import sql
from psycopg.sql import Composed

from backend.datatypes.stueble_types import Email, Residence, UserRole, VerificationMethod
from backend.database import database as db
from backend.datatypes.funcres import FuncRes, Status, Message
from backend.sql_connection.ultimate_functions import clean_single_data


def add_user(user_role: UserRole,
             first_name: str,
             last_name: str,
             returning_column: str | None = None,
             room: str | int | None = None,
             residence: Residence | None = None,
             email: Email | None = None,
             password_hash: str | None = None,
             user_name: str | None = None) -> FuncRes:
    """
    adds a user to the table users

    Args:
        user_role (UserRole): available roles for the user
        first_name (str): first name of the user
        last_name (str): last name of the user
        returning_column (str | None): which column to return
        room (str | int | None): room of the user
        residence (Residence | None): residence of the user
        email (Email | None): email of the user
        password_hash (str | None): password hash of the user
        user_name (str | None): username of the user
    Returns:
        FuncRes: id if returning is True and successful, error otherwise
    """
    values_set = any(i is None for i in [room, residence, email, password_hash, user_name, first_name, last_name])
    values_not_set = any(i is not None for i in [room, residence, email, password_hash, user_name])

    if (values_set and user_role != UserRole.EXTERN) or (user_role == UserRole.EXTERN and values_not_set):
        if user_role != UserRole.EXTERN:
            return FuncRes(error="For user_role other than extern, room, residence, email, password_hash and user_name must be set. For user_role extern, these values must not be specified.",
                            status=Status.FULL_ERROR,
                            message=Message(name="Add User Error",
                                            type="error",
                                            category="Add User",
                                            code=400)
            )

    arguments = {"user_role": user_role.value, "first_name": first_name, "last_name": last_name}
    if user_role != UserRole.EXTERN:
        if room is not None and str(room).isdigit() is False:
            return FuncRes(error="Room must be an integer, provided as str | int.",
                            status=Status.FULL_ERROR,
                            message=Message(name="Add User Error",
                                            type="error",
                                            category="Add User",
                                            code=400)
            )

        if room is not None: arguments["room"] = str(room)
        if residence is not None: arguments["residence"] = residence.value
        if email is not None: arguments["email"] = email.email
        if password_hash is not None: arguments["password_hash"] = password_hash
        if user_name is not None: arguments["user_name"] = user_name

    result = db.insert(
        table="users",
        values=arguments,
        returning_column=returning_column)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Add User Error",
                            type="error",
                            category="Add User",
                            code=500)
        )
    if result.data is None:
            return FuncRes(error="Insert of user failed",
                            status=Status.FULL_ERROR,
                            message=Message(name="Add User Error",
                                            type="error",
                                            category="Add User",
                                            code=500)
            )
    if returning_column is not None and ", " not in returning_column:
            result = FuncRes(
                data=clean_single_data(result.data),
                status=Status.FULL_SUCCESS,
                message=Message(name="Add User Success",
                                type="success",
                                category="Add User",
                                code=200)
            )

        
    return FuncRes(
        data=result,
        status=Status.FULL_SUCCESS,
        message=Message(name="Add User Success",
                        type="success",
                        category="Add User",
                        code=200)
    )


def remove_user(user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name"] = None,
                user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name"] = None,
                user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name"] = None) -> FuncRes:
    """
    removes a user from the table users \n
    actually not the whole user but just their password will be set to NULL

    Args:
        user_id (int | None): id of the user to be removed
        user_email (Email | None): email of the user to be removed
        user_name (str | None): username of the user to be removed
    Returns:
        FuncRes: id if successful, error otherwise
    """
    if user_id is None and user_email is None and user_name is None:
        return FuncRes(error="Either user_id or user_email or user_name must be set.",
                        status=Status.FULL_ERROR,
                        message=Message(name="Remove User Error",
                                        type="error",
                                        category="Remove User",
                                        code=400)
        )

    conditions: dict[str, str | int] = {}
    if user_id is not None:
        conditions["id"] = str(user_id)
    elif user_email is not None:
        conditions["email"] = user_email.email
    elif user_name is not None:
        conditions["user_name"] = user_name


    query = sql.SQL("UPDATE users SET password_hash = NULL WHERE {conditions} RETURNING {id}, {user_role}").format(
        conditions=sql.SQL(" AND ").join([sql.SQL("{key} = {value}").format(key=sql.Identifier(key), value=sql.Placeholder()) for key in conditions.keys()]),
        id=sql.Identifier("id"),
        user_role=sql.Identifier("user_role")
    )

    result = db.custom_call(query=query,
                            variables=list(conditions.values()),
                            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Remove User Error",
                            type="error",
                            category="Remove User",
                            code=500)
        )
    if result.data is None:
        return FuncRes(error="User doesn't exist.",
                        status=Status.FULL_ERROR,
                        message=Message(name="Remove User Error",
                                        type="error",
                                        category="Remove User",
                                        code=404)
        )
    
    result._data = {key: value for key, value in zip(["id", "user_role"], result.data)}

    if result.data["user_role"] == UserRole.EXTERN.value:
        return FuncRes(error="User role is extern.",
                        status=Status.FULL_ERROR,
                        message=Message(name="Remove User Error",
                                        type="error",
                                        category="Remove User",
                                        code=400)
        )

    return FuncRes(
        data=int(result.data["id"]),
        status=Status.FULL_SUCCESS,
        message=Message(name="Remove User Success",
                        type="success",
                        category="Remove User",
                        code=200)
    )

def update_user(
        user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_name_key: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_uuid_key: Annotated[str | None, "Explicit with user_id, user_email OR user_name OR user_uuid"] = None,
        **kwargs) -> FuncRes:
    """
    updates a user in the table users

    Args:
        user_id (int | None): id of the user to be updated
        user_email (Email | None): email of the user to be updated
        user_name (str | None): username of the user to be updated
        user_uuid (str | None): uuid of the user to be updated
        **kwargs: fields to update
    Returns:
        FuncRes: id if successful, error otherwise
    """

    # TODO: disallow unallowed fields in db
    allowed_fields = ["user_role", "first_name", "last_name", "email", "password_hash", "user_name", "verified"]
    for k in kwargs.keys():
        if k not in allowed_fields:
            return FuncRes(error=f"Field {k} is not allowed to be updated.",
                            status=Status.FULL_ERROR,
                            message=Message(name="Update User Error",
                                            type="error",
                                            category="Update User",
                                            code=400)
            )

    if all(i is None for i in [user_id, user_email, user_name_key, user_uuid_key]):
        return FuncRes(error="Either user_id or user_email or user_name or user_uuid must be set.",
                        status=Status.FULL_ERROR,
                        message=Message(name="Update User Error",
                                        type="error",
                                        category="Update User",
                                        code=400)
        )

    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    elif user_uuid_key is not None:
        conditions["user_uuid"] = user_uuid_key
    else:
        conditions["user_name"] = user_name_key

    result = db.update(table="users", columns=kwargs,
                             conditions=conditions, returning_column="id")

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Update User Error",
                            type="error",
                            category="Update User",
                            code=500)
        )
    if result.data is None:
        return FuncRes(error="User doesn't exist.",
                        status=Status.FULL_ERROR,
                        message=Message(name="Update User Error",
                                        type="error",
                                        category="Update User",
                                        code=404)
        )

    return FuncRes(
        data=clean_single_data(result.data),
        status=Status.FULL_SUCCESS,
        message=Message(name="Update User Success",
                        type="success",
                        category="Update User",
                        code=200)
        )


def get_user(
        type_of_answer: db.ANSWER_TYPE = db.ANSWER_TYPE.SINGLE_ANSWER,
        user_id: Annotated[int | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_email: Annotated[Email | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_name: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        user_uuid: Annotated[str | None, "set EITHER user_id OR user_email OR user_name OR user_uuid"] = None,
        columns: tuple[str] | list[str] = ("*",),
        conditions: Annotated[dict[str, Any] | None, "Explicit with user_id, user_email, select_max_of_key, specific_where"] = None,
        select_max_of_key: Annotated[str, "Explicit with user_id, user_email, conditions, specific_where"] = "",
        specific_where: Annotated[sql.SQL | Composed, "Explicit with user_id, user_email, select_max_of_key, conditions"] = sql.SQL(""),
        order_by: Annotated[tuple[str, Literal[0, 1]] | None, "Explicit with type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER"] = None
    ) -> FuncRes:
    """
    retrieves a user from the table users

    Args:
        type_of_answer (db.ANSWER_TYPE): whether to expect a single user or multiple users; defaults to db.ANSWER_TYPE.SINGLE_ANSWER
        user_id (int | None): id of the user to be retrieved
        user_email (Email | None): email of the user to be retrieved
        user_name (str | None): username of the user to be retrieved
        user_uuid (str | None): uuid of the user to be retrieved
        columns (tuple[str] | list[str]): list of fields to be retrieved, defaults to ["*"]
        conditions (dict | None): additional conditions for the query
        type_of_answer (bool): whether to expect a single user or multiple users
        select_max_of_key (str): if set, will select the max of this key
        specific_where (sql.SQL | Composed): if set, will add this specific where clause
        order_by (tuple): if set, will order the results by this tuple
    Returns:
        FuncRes: user data if successful, error otherwise
    """
    columns = list(columns)
    if conditions is None:
        conditions = {}
    # check, whether explicitly of type_of_answer and order_by is met
    if type_of_answer and order_by is not None:
        return FuncRes(error="Either type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER or order_by can be set.",
                        status=Status.FULL_ERROR,
                        message=Message(name="Get User Error",
                                        type="error",
                                        category="Get User",
                                        code=400)
        )

    # check, whether a where statement is set for sql query
    if user_id is None and user_email is None and user_name is None and user_uuid is None and conditions == {} and specific_where.as_string() == "":
        return FuncRes(
            error="At least one of user_id, user_email, user_name, user_uuid, conditions or specific_where must be set.",
            status=Status.FULL_ERROR,
            message=Message(name="Get User Error",
                            type="error",
                            category="Get User",
                            code=400)
        )           
    conditions_counter = 0
    if user_id is not None: conditions_counter += 1
    if user_email is not None: conditions_counter += 1
    if user_name is not None: conditions_counter += 1
    if user_uuid is not None: conditions_counter += 1
    if select_max_of_key != "": conditions_counter += 1
    if specific_where.as_string() != "": conditions_counter += 1
    if conditions != {}: conditions_counter += 1
    if conditions_counter > 1:
        return FuncRes(
            error="Only one of user_id, user_email, user_name, user_uuid, conditions, select_max_of_key or specific_where can be set.",
            status=Status.FULL_ERROR,
            message=Message(name="Get User Error",
                            type="error",
                            category="Get User",
                            code=400)
        )

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

    result = db.select(
        table="users",
        columns=columns,
        type_of_answer=type_of_answer,
        conditions=conditions,
        select_max_of_key=select_max_of_key,
        specific_where=specific_where,
        **value)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get User Error",
                            type="error",
                            category="Get User",
                            code=500)
        )

    if result.data is None or (isinstance(result.data, list) and len(result.data) == 0):
        return FuncRes(
            error="No matching user found",
            status=Status.FULL_ERROR,
            message=Message(name="Get User Error",
                            type="error",
                            category="Get User",
                            code=404)
        )
        
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get User Success",
                        type="success",
                        category="Get User",
                        code=200)
    )

def get_invited_friends(user_id: int, stueble_id: int) -> FuncRes:
    """
    retrieves all friends that were invited by a specific user to a specific stueble party

    Args:
        user_id (int): id of the user who invited friends
        stueble_id (int): id of the specific stueble party
    Returns:
        FuncRes: friends if successful, error otherwise
    """
    
    arguments = ["first_name", "last_name", "user_uuid"]
    query = f"""
    SELECT {', '.join(['u.' + i for i in arguments])}
    FROM (SELECT user_id
          FROM (SELECT DISTINCT ON (user_id) *
                FROM stueble.events
                WHERE invited_by = %s
                  AND stueble_id = %s
                  AND event_type IN ('add', 'remove')
                ORDER BY user_id, submitted DESC) as latest_event
          WHERE latest_event.event_type = 'add'
          ORDER BY user_id) AS invitees
    JOIN users u ON invitees.user_id = u.id;
    """

    # check how many friends were invited by the user to a specific stueble party
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[user_id, stueble_id]
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Invited Friends Error",
                            type="error",
                            category="Get Invited Friends",
                            code=500)
        )

    if result.is_success and len(result.data) == 0:
        # if no friends were invited, check if user is registered for the specific stueble
        query = """
        SELECT 'add' =
        COALESCE((SELECT event_type
        FROM stueble.events
        WHERE user_id = %s
          AND stueble_id = %s
          AND event_type IN ('add', 'remove')
        ORDER BY submitted DESC
        LIMIT 1), 'remove')
        """
        result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            variables=[user_id, stueble_id]
        )
        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Get Invited Friends Error",
                                type="error",
                                category="Get Invited Friends",
                                code=500)
            )
        if result.is_success and result.data is None:
            return FuncRes(
                error="User has to be in stueble in order to invite friends.",
                status=Status.FULL_ERROR,
                message=Message(name="Get Invited Friends Error",
                                type="error",
                                category="Get Invited Friends",
                                code=404)
            )
        return FuncRes(
            data=[],
            status=Status.FULL_SUCCESS,
            message=Message(name="Get Invited Friends Success",
                            type="success",
                            category="Get Invited Friends",
                            code=200)
        )

    return FuncRes(
        data=[{key: value for key, value in zip(arguments, guest)} for guest in result.data],
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Invited Friends Success",
                        type="success",
                        category="Get Invited Friends",
                        code=200)
    )

def create_verification_code(user_id: int | None, additional_data: dict[str, Any] | None = None) -> FuncRes:
    """
    creates a password reset code for a specific user

    Args:
        user_id (int | None): id of the user; if None, then code is a verification code for email
        additional_data (dict | None): additional data to be stored in the table; can be None
    Returns:
        FuncRes: id if successful, error otherwise
    """

    values = {}
    if user_id is not None:
        values["user_id"] = user_id
    if additional_data is not None:
        additional_data = {k: v.value if isinstance(v, enum.Enum) else v.email if isinstance(v, Email) else v for k, v in additional_data.items()}
        values["additional_data"] = json.dumps(additional_data)
    if values == {}:
        values = None

    result = db.insert(
        table="verification_codes",
        values=values,
        returning_column="reset_code")

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Create Verification Code Error",
                            type="error",
                            category="Create Verification Code",
                            code=500)
        )
    # maybe shouldn't be possible, but still left in
    if result.data is None:
        return FuncRes(
            error="error occured",
            status=Status.FULL_ERROR,
            message=Message(name="Create Verification Code Error",
                            type="error",
                            category="Create Verification Code",
                            code=500)
        )
    return FuncRes(
        data=clean_single_data(result.data),
        status=Status.FULL_SUCCESS,
        message=Message(name="Create Verification Code Success",
                        type="success",
                        category="Create Verification Code",
                        code=200)
    )

def confirm_verification_code(reset_code: str, additional_data: bool = False, expiration_minutes: int | None=None) -> FuncRes:
    """
    confirms a password reset code for a specific user

    Args:
        reset_code (str): reset code of the user
        additional_data (bool): whether to return additional data
        expiration_minutes (int | None): if set, the code is only valid for this many minutes
    Returns:
        FuncRes: id if successful, error otherwise
    """

    columns = ["user_id"]
    if additional_data:
        columns.append("additional_data")

    arguments = {}
    if expiration_minutes is not None:
        arguments["specific_where"] = sql.SQL("reset_code = {reset_code} AND used = FALSE AND created_at >= NOW() - ({expiration_minutes} * INTERVAL '1 minute')").format(
            reset_code=sql.Placeholder(),
            expiration_minutes=sql.Placeholder()
        )
        arguments["variables"] = (reset_code, expiration_minutes,)
    else:
        arguments["specific_where"] = sql.SQL("reset_code = {reset_code} AND created_at >= NOW() - ((SELECT value::int FROM configurations WHERE key = 'reset_code_expiration_minutes') * INTERVAL '1 minute') AND used = FALSE").format(
            reset_code=sql.Placeholder()
        )
        arguments["variables"] = (reset_code,)
    result = db.select(
        table="verification_codes",
        columns=columns,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        **arguments
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Confirm Verification Code Error",
                            type="error",
                            category="Confirm Verification Code",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="Reset code doesn't exist anymore.",
            status=Status.FULL_ERROR,
            message=Message(name="Confirm Verification Code Error",
                            type="error",
                            category="Confirm Verification Code",
                            code=404)
        )

    if result.is_success:
        result_insert = db.update(table="verification_codes",
                                 columns={"used": True}, conditions={"reset_code": reset_code})
        if result_insert.is_error:
            return FuncRes(
                error=str(result_insert.error),
                status=Status.FULL_ERROR,
                message=Message(name="Confirm Verification Code Error",
                                type="error",
                                category="Confirm Verification Code",
                                code=500)
            )

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Confirm Verification Code Success",
                        type="success",
                        category="Confirm Verification Code",
                        code=200)
    )

def add_verification_method(method: VerificationMethod,
                            user_id: Annotated[str | None, "Explicit with user_uuid"]=None,
                            user_uuid: Annotated[str | None, "Explicit with user_id"]=None) -> FuncRes:
    """
    adds a verification method for a specific user

    Args:
        method (VerificationMethod): verification method to be added
        user_id (int | None): id of the user
        user_uuid (str | None): uuid of the user
    Returns:
        FuncRes: id if successful, error otherwise
    """

    if (user_id is None and user_uuid is None) or (user_id is not None and user_uuid is not None):
        return FuncRes(
            error="Either user_id or user_uuid must be set, but not both.",
            status=Status.FULL_ERROR,
            message=Message(name="Add Verification Method Error",
                            type="error",
                            category="Add Verification Method",
                            code=400)
        )

    values = {"method": method.value}
    if user_id is not None:
        values["id"] = user_id
    else:
        values["user_uuid"] = user_uuid

    result = db.insert(
        table="user_verification_methods",
        values=values,
        returning_column="id")

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Add Verification Method Error",
                            type="error",
                            category="Add Verification Method",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="Error occurred while adding verification method.",
            status=Status.FULL_ERROR,
            message=Message(name="Add Verification Method Error",
                            type="error",
                            category="Add Verification Method",
                            code=500)
        )

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Add Verification Method Success",
                        type="success",
                        category="Add Verification Method",
                        code=200)
    )

def get_users(user_uuids: list[str],
              keywords: list[str] | tuple[str] = ("id",)) -> FuncRes:
    """
    retrieves users from the table users

    Args:
        user_uuids (list[str | int]): list of user uuids
        keywords (tuple[str] | list[str]): list of fields to be retrieved, defaults to ["*"]
    Returns:
        FuncRes: users if successful, error otherwise
    """
    keywords = list(keywords)
    # users_list = [(i, "email") if isinstance(i, str) and "@" in i else (i, "user_name") for i in information]

    query = f"SELECT {', '.join(keywords)} FROM users WHERE user_uuid IN ({', '.join(['%s' for _ in range(len(user_uuids))])})"
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=tuple(user_uuids))

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Users Error",
                            type="error",
                            category="Get Users",
                            code=500)
        )
    if len(result.data) != len(user_uuids):
        return FuncRes(
            error="Not all users found.",
            status=Status.FULL_ERROR,
            message=Message(name="Get Users Error",
                            type="error",
                            category="Get Users",
                            code=404)
        )
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Users Success",
                        type="success",
                        category="Get Users",
                        code=200)
    )

def check_user_guest_list(user_id: int) -> FuncRes:
    """
    checks, whether the user is on the guest list for the latest stueble

    Args:
        user_id (int): id of the user
    Returns:
        FuncRes: whether the user is on the guest list if successful, error otherwise
    """

    query = """SELECT (COALESCE(
  (SELECT event_type
   FROM stueble.events
   WHERE user_id = %s
     AND stueble_id = (
       SELECT id
       FROM stueble.motto
       WHERE date_of_time >= CURRENT_DATE
          OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1)
       ORDER BY date_of_time ASC
       LIMIT 1
     )
   ORDER BY submitted DESC
   LIMIT 1
  ),
  'remove'
)) != 'remove'"""

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[user_id])

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Check User Guest List Error",
                            type="error",
                            category="Check User Guest List",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error="User or stueble doesn't exist.",
            status=Status.FULL_ERROR,
            message=Message(name="Check User Guest List Error",
                            type="error",
                            category="Check User Guest List",
                            code=404)
        )
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Check User Guest List Success",
                        type="success",
                        category="Check User Guest List",
                        code=200)
    )

def check_user_present(user_id: int) -> FuncRes:
    """
    checks, whether the user is currently present at the latest stueble

    Args:
        user_id (int): id of the user
    Returns:
        FuncRes: whether the user is currently present if successful, error otherwise
    """

    query = """SELECT COALESCE(
            (SELECT event_type
             FROM stueble.events
             WHERE user_id = 1
               AND stueble_id = (SELECT id
                                 FROM stueble.motto
                                 WHERE date_of_time >= CURRENT_DATE
                                    OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - 1)
                                 ORDER BY date_of_time ASC
                                 LIMIT 1)
             ORDER BY submitted DESC
             LIMIT 1),
            'remove') = 'arrive' AS is_registered"""

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=[user_id])

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Check User Present Error",
                            type="error",
                            category="Check User Present",
                            code=500)
        )
    if result.data is None:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Check User Present Error",
                            type="error",
                            category="Check User Present",
                            code=404)
        )
    return FuncRes(
        data=clean_single_data(result.data),
        status=Status.FULL_SUCCESS,
        message=Message(name="Check User Present Success",
                        type="success",
                        category="Check User Present",
                        code=200)
    )
