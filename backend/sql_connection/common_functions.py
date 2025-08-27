from backend.data_types import *
import database as db
from typing import Annotated

def add_user(connection, cursor, user_role: UserRole, room: str, residence: Residence, first_name: str, last_name: str, email: Email, password_hash: str, invited_by: int, returning=False) -> dict:
    """
    adds a user to the table users

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_role (UserRole): available roles for the user
        room (str): room of the user
        residence (Residence): residence of the user
        first_name (str): first name of the user
        last_name (str): last name of the user
        email (Email): email of the user
        password_hash (str): password hash of the user
        invited_by (int): id of the user who invited this user
        returning (bool): whether to return the id of the new user
    Returns:
        dict: {"success": bool} by default, {"success": bool, "data": id} if returning is True, {"success": False, "error": e} if error occured
    """
    result = db.insert_table(
        connection=connection, 
        cursor=cursor, 
        table_name="users", 
        arguments={"user_role": user_role.value, "room": room, "residence": residence.value, "first_name": first_name, "last_name": last_name, "email": email.value, "password_hash": password_hash, "invited_by": invited_by}, 
        returning=returning)
    return result

def remove_user(connection, cursor, user_id: Annotated[int | None, "set EITHER user_id OR user_email"]=None, user_email: Annotated[Email | None, "set EITHER user_id OR user_email"]=None):
    """
    removes a user from the table users \n
    actually not the whole user but just their password will be set to NULL

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int | None): id of the user to be removed
        user_email (Email | None): email of the user to be removed
    Returns: 
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": id} otherwise
    """
    if user_id is None and user_email is None:
        return ValueError("Either user_id or user_email must be set.")
    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    else:
        conditions["email"] = user_email.email
    result = db.update_table(connection=connection, cursor=cursor, table_name="users", arguments={"password_hash": None}, conditions=conditions, returning_column="user_role")
    if result["success"] is False:
        return result
    if result["data"] == UserRole.GUEST.value:
        return {"success": False, "error": "User role is guest."}
    return result

def update_user(
    connection, 
    cursor, 
    user_id: Annotated[int | None, "set EITHER user_id OR user_email"]=None, 
    user_email: Annotated[Email | None, "set EITHER user_id OR user_email"]=None, 
    **kwargs) -> dict:
    """
    updates a user in the table users

    Parameters:
        connection: connection to the db
        cursor: cursor for the connection
        user_id (int | None): id of the user to be updated
        user_email (Email | None): email of the user to be updated
        **kwargs: fields to update
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": id} otherwise
    """

    allowed_fields = ["user_role", "room", "residence", "first_name", "last_name", "email", "password_hash", "invited_by"]
    for k, v in kwargs:
        if k not in allowed_fields:
            raise ValueError(f"Field {k} is not allowed to be updated.")

    if user_id is None and user_email is None:
        raise ValueError("Either user_id or user_email must be set.")
    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    else:
        conditions["email"] = user_email.email
    result = db.update_table(connection=connection, cursor=cursor, table_name="users", arguments=kwargs, conditions=conditions)
    return result

def get_user(
    cursor, 
    user_id: Annotated[int | None, "set EITHER user_id OR user_email"]=None, 
    user_email: Annotated[Email | None, "set EITHER user_id OR user_email"]=None, 
    keywords: list[str]=["*"], 
    conditions: Annotated[dict, "Explicit with user_id, user_email, select_max_of_key, specific_where"]={}, 
    expect_single_answer=True, 
    select_max_of_key: Annotated[str, "Explicit with user_id, user_email, conditions, specific_where"]="", 
    specific_where: Annotated[str, "Explicit with user_id, user_email, select_max_of_key, conditions"]="", 
    order_by: Annotated[tuple, "Explicit with expect_single_answer=True"]=()) -> dict:
    """
    retrieves a user from the table users

    Parameters:
        cursor: cursor for the connection
        user_id (int | None): id of the user to be retrieved
        user_email (Email | None): email of the user to be retrieved
        keywords (list[str]): list of fields to be retrieved, defaults to ["*"]
        conditions (dict): additional conditions for the query
        expect_single_answer (bool): whether to expect a single user or multiple users
        select_max_of_key (str): if set, will select the max of this key
        specific_where (str): if set, will add this specific where clause
        order_by (tuple): if set, will order the results by this tuple
    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": user} otherwise
    """
    
    # check, whether explicity of expect_single_answer and order_by is met
    if expect_single_answer and order_by != {}:
        raise ValueError("Either expect_single_answer=True or order_by can be set.")
    
    # check, whether an where statement is set for sql query
    if user_id is None and user_email is None and conditions == {} and specific_where == "":
        raise ValueError("Either user_id, user_email, conditions or specific_where must be set.")
    conditions_counter = 0
    if user_id is not None: conditions_counter += 1
    if user_email is not None: conditions_counter += 1
    if select_max_of_key != "": conditions_counter += 1
    if specific_where != "": conditions_counter += 1
    if conditions != {}: conditions_counter += 1
    if conditions_counter > 1:
        raise ValueError("user_id, user_email, select_max_of_key, specific_where and conditions are explicit. Therefore just one of them can be set.")
    
    if user_id is not None:
        conditions["id"] = user_id
    elif user_email is not None:
        conditions["email"] = user_email.email
    result = db.read_table(
        cursor=cursor, 
        table_name="users", 
        keywords=keywords, 
        expect_single_answer=expect_single_answer, 
        conditions=conditions, 
        select_max_of_key=select_max_of_key, 
        specific_where=specific_where, 
        order_by=order_by)
    
    return result