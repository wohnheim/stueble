from flask import request_tearing_down

from backend.sql_connection import users, database as db
from backend.data_types import *

def validate_user_data(cursor,
                       user_role: UserRole,
                       room: str | int,
                       residence: Residence,
                       first_name: str,
                       last_name: str,
                       email: Email,
                       user_name: str) -> dict:
    """
    Validate user data for signup.

    Parameters:
        cursor: database cursor
        user_role (UserRole): Role of the user, must be one of UserRole except 'admin'.
        room (str | int): Room number, must be convertible to an integer.
        residence (Residence): Residence of the user, must be one of Residence.
        first_name (str): First name of the user, cannot be empty or None.
        last_name (str): Last name of the user, cannot be empty or None.
        email (Email): Email of the user, must be of type Email.
        user_name (str): Username of the user, cannot be empty or None.

    Returns:
        dict: A dictionary with keys 'success' (bool), 'error' (str, optional), and 'status' (int).
              'success' is True if all validations pass, otherwise False with an appropriate error message.
              'status' is 200 for success, 400 for client errors, and 500 for server errors.
    """
    if not is_valid_role(user_role) or (user_role.value == "admin"):
        return {"success": False, "error": "Invalid user role, admin not allowed"}
    try:
        room = int(room)
    except ValueError:
        return {"success": False, "error": "Room must be a number"}

    if not is_valid_residence(residence):
        return {"success": False, "error": "Invalid residence"}

    if not first_name or not last_name:
        return {"success": False, "error": "First name and last name cannot be or None"}

    if not isinstance(email, Email):
        return {"success": False, "error": "Invalid email format, must be of type Email"}

    query = """SELECT email, user_name FROM users WHERE email = %s OR user_name = %s;"""
    result = db.custom_call(
        connection=None,
        cursor=cursor,
        query=query,
        variables=[email.email, user_name],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result["success"] is False:
        result["status"] = 500
        return result

    email_list = [row[0] for row in result["data"]]
    user_name_list = [row[1] for row in result["data"]]
    if len(result["data"]) != 0:
        if email.email in email_list and user_name in user_name_list:
            return {"success": False, "error": "Email and username already exist", "status": 400}
        if email.email in email_list:
            return {"success": False, "error": "Email already exists", "status": 400}
        if user_name in user_name_list:
            return {"success": False, "error": "Username already exists", "status": 400}

    return {"success": True, "status": 200}