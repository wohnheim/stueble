import json
from flask import Response
from psycopg import sql
from backend.datatypes.stueble_types import Residence, UserRole, Email
from backend.database import database as db
from backend.sql_connection import users
from backend.mail_assets import templates
from backend.google_functions import email as mail

def verified_signup(room: int, residence: Residence, first_name: str, last_name: str, email: Email, user_name: str, password_hash: str, user_role: UserRole) -> Response:
    """
    This is a temporary function to bypass the signup validation for testing purposes. It should be removed after the signup validation is implemented.

    Args:
        user_info (dict | None): Optional user information to create a user with. If None, a default user will be created.
    Returns:
        Response: A Flask Response object containing the result of the signup process.
    """

    # validate input
    if not isinstance(user_role, UserRole) or (user_role.value == "admin"):
        return Response(
            response=json.dumps({"code": 400, "message": "Invalid user role, admin not allowed"}),
            status=400,
            mimetype="application/json")
    try:
        room = int(room)
    except ValueError:
        return Response(
                response=json.dumps({"code": 400, "message": "Room must be a number"}),
                status=400,
                mimetype="application/json")

    if not isinstance(residence, Residence):
        return Response(
            response=json.dumps({"code": 400, "message": "Invalid residence"}),
            status=400,
            mimetype="application/json")

    if not first_name or not last_name:
        return Response(
                response=json.dumps({"code": 400, "message": "First name and last name cannot be empty or None"}),
                status=400,
                mimetype="application/json")

    if not isinstance(email, Email):
        return Response(
            response=json.dumps({"code": 400, "message": "Invalid email format, must be of type Email"}),
            status=400,
            mimetype="application/json")

    query = sql.SQL("""SELECT email, user_name, room, residence FROM users WHERE email = {email} OR user_name = {user_name}""").format(email=sql.Placeholder(), user_name=sql.Placeholder()) # ignore room and residence
    result = db.custom_call(
        query=query,
        variables=[email.email, user_name],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result.is_error:
        return Response(response=json.dumps({"code": 500, "message": "Validate User Data Error"}),
                        status=500,
                        mimetype="application/json")

    email_list = [row[0] for row in result.data]
    user_name_list = [row[1] for row in result.data]
    
    if len(email_list) > 0:
        return Response(
            response=json.dumps({"code": 400, "message": "Email already exists"}),
            status=400,
            mimetype="application/json")
    
    if len(user_name_list) > 0:
        return Response(
            response=json.dumps({"code": 400, "message": "Username already exists"}),
            status=400,
            mimetype="application/json")

    query = sql.SQL("""
    UPDATE users SET room = room * 23149871324712347 WHERE room = {room} AND residence = {residence} RETURNING first_name, last_name, email""").format(
        room = sql.Placeholder(), residence = sql.Placeholder()
    )
    result = db.custom_call(
        query=query,
        variables=[room, residence.value],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)
    if result.is_error:
        return Response(response=json.dumps({"code": 500, "message": "Error creating account"}),
                        status=500,
                        mimetype="application/json")
    if result.data is not None and len(result.data) > 0:
        overwritten_users = [{"first_name": row[0], "last_name": row[1], "email": row[2]} for row in result.data]
        # send email to overwritten users
        for user in overwritten_users:
            result = templates.inform_overwritten_user(first_name=user["first_name"], last_name=user["last_name"])
            mail.send_mail(recipient=user["email"], subject=result["subject"], body=result["body"], images=result["images"], html=True)
    
    additional_data = {
        "room": room,
        "residence": residence.value,
        "first_name": first_name,
        "last_name": last_name,
        "email": email.email,
        "user_name": user_name,
        "user_role": user_role.value,
        "password_hash": password_hash
    }

    result = users.create_verification_code(user_id=None, additional_data=additional_data)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    verification_token = result.data

    result = templates.confirm_email(first_name=first_name,
                            last_name=last_name,
                            verification_token=verification_token)

    result = mail.send_mail(recipient=email, subject=result["subject"], body=result["body"], images=result["images"], html=True)

    if result.is_error: # NOTE: until now not possible, since no event, that returns result.error, exists
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        status=204)
    return response