"""
Authentication routes for login, signup, logout, password reset and user deletion.
"""

from types import _ReturnT_co
from flask import Blueprint, request, Response
import json

from backend import hash_pwd as hp
from backend.google_functions import email as mail
from backend.sql_connection import (
    events,
    sessions,
    users,
)
from backend.datatypes.stueble_types import Residence, UserRole, Email, is_valid_residence
from backend.database import database as db
from backend.mail_assets import templates
from backend.sql_connection.common_functions import check_permissions
from backend.sql_connection.signup_validation import validate_user_data


auth = Blueprint("auth", __name__)

# TODO: test automatic deletion from all stueble parties
@auth.route("/delete", methods=["DELETE"])
def delete():
    """
    delete a user (set password to NULL)
    """

    if result.data["user_role"] == UserRole.ADMIN.value:
        return Response(
            response=json.dumps({"code": 403, "message": "Admins cannot be deleted"}),
            status=403,
            mimetype="application/json")

    # remove from guest_list
    result = events.remove_guest(user_id=user_id, stueble_id=-1)
    if result.is_error:
        return Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")

@auth.route("/reset_password", methods=["POST"])
def reset_password_mail():
    """
    reset password of a user
    """

    # load data
    data = request.get_json()
    name = data.get("user", None)
    if name is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "specify user"}),
            status=400,
            mimetype="application/json")
        return response

    user_email: Email | None = None
    user_name: str | None = None

    if "@" in name:
        try:
            name = Email(email=name)
        except ValueError:
            response = Response(
                response=json.dumps({"code": 400, "message": "Invalid email format"}),
                status=400,
                mimetype="application/json")
            return response
        user_email = name
    else:
        user_name = name

    # check whether user with email exists
    result = users.get_user(columns=["id", "first_name", "last_name", "email", "password_hash"], user_email=user_email, user_name=user_name)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500 if result.error != "No matching user found" else 404, "message": str(result.error)}),
            status=500 if result.error != "No matching user found" else 404,
            mimetype="application/json")
        return response
    user_id = result.data["id"]
    first_name = result.data["first_name"]
    last_name = result.data["last_name"]
    email = result.data["email"]
    password_hash = result.data["password_hash"]

    if password_hash is None or password_hash == "":
        response = Response(
            response=json.dumps({"code": 400, "message": "User was deleted, needs to signup again."}),
            status=400,
            mimetype="application/json")
        return response

    email = Email(email=email)

    result = users.create_verification_code(user_id=user_id)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    reset_token = result.data

    result = templates.reset_password(first_name=first_name, last_name=last_name, reset_token=reset_token)

    result = mail.send_mail(recipient=email, subject=result["subject"], body=result["body"], images=result["images"], html=True)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        status=204)
    return response

@auth.route("/reset_password_confirm", methods=["POST"])
def confirm_code():
    """
    confirm the reset code and set a new password
    """

    # load data
    data = request.get_json()
    reset_token = data.get("token", None)
    new_password = data.get("password", None)

    if reset_token is None or new_password is None:
        response = Response(
            response=json.dumps({"code": 400, "message": f"The {'token' if reset_token is None else 'password' if new_password is None else 'token and password'} must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    if new_password == "":
        response = Response(
            response=json.dumps({"code": 400, "message": "password cannot be empty"}),
            status=400,
            mimetype="application/json")
        return response

    # check whether reset token exists
    result = users.confirm_verification_code(reset_code=reset_token)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500 if str(result.error) != "Reset code doesn't exist" else 404, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    user_id = result.data

    # hash new password
    hashed_password = hp.hash_pwd(new_password)

    # set new password
    result = users.update_user(user_id=user_id, password_hash=hashed_password)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # remove all existing sessions of the user
    result = sessions.remove_user_sessions(user_id=user_id)
    if result.is_error:
        if result.error != "no sessions found":
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response

    # create a new session
    result = sessions.create_session(user_id=user_id)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    session_id = result.data["session_id"]
    expiration_date = result.data["expiration_date"]

    # return 204
    response = Response(
        status=204)

    response.set_cookie("SID",
                        session_id,
                        expires=expiration_date,
                        httponly=True,
                        secure=True,
                        samesite='Lax')
    return response

# NOTE: no websocket update, since neither password nor username are needed
@auth.route("/change_password", methods=["POST"])
@auth.route("/change_username", methods=["POST"])
def change_user_data():
    """
    changes user data when logged in \n
    different from password reset, since user is logged in here
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions
    result = check_permissions(session_id=session_id, required_role=UserRole.USER)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result.data["user_id"]

    data = {}
    if request.path == "/user/change_password":
        new_pwd = data.get("newPassword", None)
        if new_pwd is None:
            response = Response(
                response=json.dumps({"code": 400, "message": "The new_password must be specified"}),
                status=400,
                mimetype="application/json")
            return response
        if new_pwd == "":
            response = Response(
                response=json.dumps({"code": 400, "message": "Password cannot be empty"}),
                status=400,
                mimetype="application/json")
            return response
        data["password_hash"] = hp.hash_pwd(new_pwd)
    elif request.path == "/user/change_username":
        username = data.get("username", None)
        if username is None:
            response = Response(
                response=json.dumps({"code": 400, "message": "Username must be specified"}),
                status=400,
                mimetype="application/json")
            return response
        if username == "":
            response = Response(
                response=json.dumps({"code": 400, "message": "Username cannot be empty"}),
                status=400,
                mimetype="application/json")
            return response
        data["user_name"] = username.lower()

    # get user id from session id
    result = users.update_user(session_id=session_id,
                               user_id=user_id, **data)
    if result.is_error and ("user_name" in data.keys()):
        error = result.error
        if f"Key (user_name)=({data['user_name']}) already exists." in error:
            response = Response(
                response=json.dumps({"code": 400, "message": "Username already exists"}),
                status=400,
                mimetype="application/json")
            return response
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response

    response = Response(
        status=204
    )
    return response
