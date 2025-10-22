from psycopg2.extensions import cursor

from packages.backend.data_types import Email, Residence, UserRole
from packages.backend.sql_connection import database as db

def validate_user_data(cursor: cursor,
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

    # check, whether user_role is admin
    if not isinstance(user_role, UserRole) or (user_role.value == "admin"):
        return {"success": False, "error": "Invalid user role, admin not allowed", "status": 400}

    # check, whether room is actually a valid number
    try:
        room = int(room)
    except ValueError:
        return {"success": False, "error": "Room must be a number", "status": 400}

    # check, whether residence is of the correct instance
    if not isinstance(residence, Residence):
        return {"success": False, "error": "Invalid residence", "status": 400}

    # first_name and last_name have to be specified and can't be empty
    if not first_name or not last_name:
        return {"success": False, "error": "First name and last name cannot be or None", "status": 400}

    # check whether email if of correct instance
    if not isinstance(email, Email):
        return {"success": False, "error": "Invalid email format, must be of type Email", "status": 400}

    # create query
    query = """SELECT email, user_name, room, residence FROM users WHERE email = %s OR user_name = %s OR (room = %s AND residence = %s);"""

    # fetch data
    result = db.custom_call(
        cursor=cursor,
        query=query,
        variables=[email.email, user_name, room, residence.value],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result["success"] is False:
        return {**error_to_failure(result), "status": 500}

    email_list = [row[0] for row in result["data"]]
    user_name_list = [row[1] for row in result["data"]]
    room_residence_list = [(row[2], row[3]) for row in result["data"]]

    if len(result["data"]) != 0:
        query = """SELECT email, user_name, room, residence FROM users WHERE (email = %s OR user_name = %s OR (room = %s AND residence = %s)) AND password_hash IS NOT NULL"""
        result = db.custom_call(
            cursor=cursor,
            query=query,
            variables=[email.email, user_name, room, residence.value],
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)
        
        if result["success"] is False:
            return {**error_to_failure(result), "status": 500}
        
        if len(result["data"]) == 0:
            return {"success": True, "status": 200, "warning": "An account was already created, but deleted."}

        if (room, residence.value) in room_residence_list:
            return {"success": False, "error": "For this apartment an account already exists.", "status": 400}
        if email.email in email_list:
            return {"success": False, "error": "For this email an account already exists.", "status": 400}
        if user_name in user_name_list:
            return {"success": False, "error": "Username already exists.", "status": 400}

    return {"success": True, "status": 200, "warning": None}