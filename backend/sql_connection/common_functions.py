from data_types import *
import database as db

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

def remove_user(connection, cursor, user_id: int | None=None, user_email: Email | None=None):
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
        conditions["email"] = user_email.value
    result = db.update_table(connection=connection, cursor=cursor, table_name="users", arguments={"password_hash": None}, conditions=conditions, returning_column="user_role")
    if result["success"] is False:
        return result
    if result["data"] == UserRole.GUEST.value:
        return {"success": False, "error": "User role is guest."}
    return result

def update_user(connection, cursor, user_id: int | None=None, user_email: Email | None=None, **kwargs) -> dict:
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
    for k, v in **kwargs:
        if k not in allowed_fields:
            raise ValueError(f"Field {k} is not allowed to be updated.")

    if user_id is None and user_email is None:
        return ValueError("Either user_id or user_email must be set.")
    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    else:
        conditions["email"] = user_email.value
    result = db.update_table(connection=connection, cursor=cursor, table_name="users", arguments=kwargs, conditions=conditions)
    return result

def get_user(cursor, user_id: int | None=None, user_email: Email | None=None, keywords: list[str]=["*"], expect_single_answer=False, ) -> dict:
    """
    retrieves a user from the table users

    Parameters:
        cursor: cursor for the connection
        user_id (int | None): id of the user to be retrieved
        user_email (Email | None): email of the user to be retrieved

    Returns:
        dict: {"success": False, "error": e} if unsuccessful, {"success": bool, "data": user} otherwise
    """
    if user_id is None and user_email is None:
        return ValueError("Either user_id or user_email must be set.")
    conditions = {}
    if user_id is not None:
        conditions["id"] = user_id
    else:
        conditions["email"] = user_email.value
    result = db.read_table(cursor=cursor, table_name="users", conditions=conditions)
    return result