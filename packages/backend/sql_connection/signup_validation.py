from backend.datatypes.stueble_types import Email, Residence, UserRole
from backend.datatypes.funcres import FuncRes, Status, Message
from backend.database import database as db


def validate_user_data(user_role: UserRole,
                       room: str | int,
                       residence: Residence,
                       first_name: str,
                       last_name: str,
                       email: Email,
                       user_name: str) -> FuncRes:
    """
    Validate user data for signup.

    Args:
        user_role (UserRole): Role of the user, must be one of UserRole except 'admin'.
        room (str | int): Room number, must be convertible to an integer.
        residence (Residence): Residence of the user, must be one of Residence.
        first_name (str): First name of the user, cannot be empty or None.
        last_name (str): Last name of the user, cannot be empty or None.
        email (Email): Email of the user, must be of type Email.
        user_name (str): Username of the user, cannot be empty or None.

    Returns:
        FuncRes: Return object containing status (True if validation passes, False otherwise), error message if any, and status code (200 for success, 400 for client errors, 500 for server errors).
    """
    if not isinstance(user_role, UserRole) or (user_role.value == "admin"):
        return FuncRes(
            error="Invalid user role, admin not allowed",
            status=Status.FULL_ERROR,
            message=Message(name="Validate User Data Error",
                            type="error",
                            category="Validate User Data",
                            code=400)
        )
    try:
        room = int(room)
    except ValueError:
        return FuncRes(
            error="Room must be a number",
            status=Status.FULL_ERROR,
            message=Message(name="Validate User Data Error",
                            type="error",
                            category="Validate User Data",
                            code=400)
        )

    if not isinstance(residence, Residence):
        return FuncRes(
            error="Invalid residence",
            status=Status.FULL_ERROR,
            message=Message(name="Validate User Data Error",
                            type="error",
                            category="Validate User Data",
                            code=400)
        )

    if not first_name or not last_name:
        return FuncRes(
            error="First name and last name cannot be empty or None",
            status=Status.FULL_ERROR,
            message=Message(name="Validate User Data Error",
                            type="error",
                            category="Validate User Data",
                            code=400)
        )

    if not isinstance(email, Email):
        return FuncRes(
            error="Invalid email format, must be of type Email",
            status=Status.FULL_ERROR,
            message=Message(name="Validate User Data Error",
                            type="error",
                            category="Validate User Data",
                            code=400)
        )

    query = """SELECT email, user_name, room, residence FROM users WHERE email = %s OR user_name = %s OR (room = %s AND residence = %s);"""
    result = db.custom_call(
        query=query,
        variables=[email.email, user_name, room, residence.value],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Validate User Data Error",
                            type="error",
                            category="Validate User Data",
                            code=500)
        )

    email_list = [row[0] for row in result.data]
    user_name_list = [row[1] for row in result.data]
    room_residence_list = [(row[2], row[3]) for row in result.data]

    if len(result.data) != 0:
        query = """SELECT email, user_name, room, residence FROM users WHERE (email = %s OR user_name = %s OR (room = %s AND residence = %s)) AND password_hash IS NOT NULL"""
        result = db.custom_call(
            query=query,
            variables=[email.email, user_name, room, residence.value],
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)
        
        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Validate User Data Error",
                                type="error",
                                category="Validate User Data",
                                code=500)
            )
 
        if len(result.data) == 0:
            return FuncRes(
                error="An account was already created, but deleted.",
                status=Status.FULL_ERROR,
                message=Message(name="Validate User Data Error",
                                type="error",
                                category="Validate User Data",
                                code=200),
                user_warning="An account was already created, but deleted."
            )

        if (room, residence.value) in room_residence_list:
            return FuncRes(
                error="For this apartment an account already exists.",
                status=Status.FULL_ERROR,
                message=Message(name="Validate User Data Error",
                                type="error",
                                category="Validate User Data",
                                code=400)
            )
        if email.email in email_list:
            return FuncRes(
                error="For this email an account already exists.",
                status=Status.FULL_ERROR,
                message=Message(name="Validate User Data Error",
                                type="error",
                                category="Validate User Data",
                                code=400)
            )
        if user_name in user_name_list:
            return FuncRes(
                error="Username already exists.",
                status=Status.FULL_ERROR,
                message=Message(name="Validate User Data Error",
                                type="error",
                                category="Validate User Data",
                                code=400)
            )

    return FuncRes(
        error=None,
        status=Status.FULL_SUCCESS,
        message=Message(name="Validate User Data Error",
                        type="success",
                        category="Validate User Data",
                        code=200,
                        details={"status": 200, "warning": None})
    )
