"""
Authentication routes for login, signup, logout, password reset and user deletion.
"""

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

@auth.route("/login", methods=["POST"])
def login():
    """
    checks, whether a user exists and whether user is logged in (if exists and not logged in, session is created)
    """

    # load data
    data = request.get_json()

    name = data.get("user", None)
    password = data.get("password", None)

    # password can't be empty
    if password == "":
        response = Response(
            response=json.dumps({"code": 400, "message": "password cannot be empty"}),
            status=401,
            mimetype="application/json")
        return response

    if name is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "specify user"}),
            status=400,
            mimetype="application/json")
        return response
    else:
      name = name.lower()

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

    # if data is not valid return error
    if password is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "specify password"}),
            status=400,
            mimetype="application/json")
        return response

    # get user data from table
    result = users.get_user(columns=["id", "password_hash", "user_role"], user_email=user_email, user_name=user_name)

    # return error
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    if result.data is None:
        response = Response(
            response=json.dumps({"code": 500, "message": "Failed to find user"}),
            status=500,
            mimetype="application/json")
        return response

    # check password
    user = result.data

    if user["password_hash"] is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "account was deleted, can be reactivated by signup"}),
            status=401,
            mimetype="application/json")
        return response

    # if passwords don't match return error
    if not hp.match_pwd(password, user["password_hash"]):
        response = Response(
            response=json.dumps({"code": 401, "message": "invalid password"}),
            status=401,
            mimetype="application/json")
        return response

    # create a new session
    result = sessions.create_session(user_id=user["id"])

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    session_id, expiration_date = result.data

    # return 204
    response = Response(
        status=204)

    response.set_cookie("SID",
                        str(session_id),
                        expires=expiration_date,
                        httponly=True,
                        secure=True,
                        samesite='Lax')
    return response

@auth.route("/signup", methods=["POST"])
def signup_data():
    """
    create a new user
    """

    # load data
    data = request.get_json()

    privacy_policy = data.get("privacyPolicy", None)
    if privacy_policy is None or privacy_policy is False:
        response = Response(
            response=json.dumps({"code": 400, "message": "Privacy policy needs to be accepted"}),
            status=400,
            mimetype="application/json")
        return response

    # initialize user_info
    user_info = {}
    user_info["room"] = data.get("roomNumber", None)
    user_info["residence"] = data.get("residence", None)
    user_info["first_name"] = data.get("firstName", None)
    user_info["last_name"] = data.get("lastName", None)
    user_info["email"] = data.get("email", None)
    user_info["user_name"] = data.get("username", None)
    user_info["password"] = data.get("password", None)

    # if a value wasn't set, return error
    if any(e is None for e in user_info.values()):
        response = Response(
            response=json.dumps({"code": 400, "message": f"The following fields must be specified: {', '.join([key for key, value in user_info.items() if value is None])}"}),
            status=400,
            mimetype="application/json")
        return response
    else:
      user_info["email"] = user_info["email"].lower()
      user_info["user_name"] = user_info["user_name"].lower()

    # check, whether user data is valid
    try:
        user_info["room"] = int(user_info["room"])
    except ValueError:
        response = Response(
            response=json.dumps({"code": 400, "message": "Room must be a number"}),
            status=400,
            mimetype="application/json")
        return response

    # check, whether residence is valid
    if not is_valid_residence(user_info["residence"]):
        response = Response(
            response=json.dumps({"code": 400, "message": "Invalid residence"}),
            status=400,
            mimetype="application/json")
        return response

    # check, whether email is valid
    try:
        user_info["email"] = Email(email=user_info["email"])
    except ValueError:
        response = Response(
            response=json.dumps({"code": 400, "message": "Invalid email format"}),
            status=400,
            mimetype="application/json")
        return response

    user_role = UserRole.USER
    user_info["user_role"] = user_role
    user_info["residence"] = Residence(user_info["residence"])
    check_info = user_info.copy()
    del check_info["password"]
    # check whether user data is unique
    result = validate_user_data(**check_info)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": result.message.code, "message": str(result.error)}),
            status=result.message.code,
            mimetype="application/json")
        return response

    # hash password
    hashed_password = hp.hash_pwd(user_info["password"])
    user_info["password_hash"] = hashed_password
    del user_info["password"]

    additional_data = user_info

    if result.user_warning is not None:
        additional_data["method"] = "update"
    else:
        additional_data["method"] = "create"

    result = users.create_verification_code(user_id=None, additional_data=additional_data)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    verification_token = result.data

    result = templates.confirm_email(first_name=user_info["first_name"],
                            last_name=user_info["last_name"],
                            verification_token=verification_token)

    result = mail.send_mail(recipient=user_info["email"], subject=result["subject"], body=result["body"], images=result["images"], html=True)

    if result.is_error: # NOTE: until now not possible, since no event, that returns result.error, exists
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        status=204)
    return response

@auth.route("/verify_signup", methods=["POST"])
def verify_signup():
    """
    verifies the signup
    """

    # load data
    data = request.get_json()
    token = data.get("token", None)

    if token is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "The token must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # verify token
    result = users.confirm_verification_code(reset_code=token, additional_data=True, expiration_minutes=30)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": (code := result.message.code) if result.message is not None else 500, "message": str(result.error)}),
            status=code if result.message is not None else 500,
            mimetype="application/json")
        return response
    
    additional_data = result.data["additional_data"]
    method = additional_data["method"]
    user_info = additional_data.copy()
    del user_info["method"]

    user_info = {k: Residence(v) if k == "residence" else UserRole(v) if k == "user_role" else Email(v) if k == "email" else v for k, v in user_info.items()}

    # add user to table
    # TODO maybe check, whether correct user is updated and whether it is really allowed
    if method == "update":
        user_data = {}
        user_data["user_role"] = user_info["user_role"]
        user_data["password_hash"] = user_info["password_hash"]
        user_data["user_name"] = user_info["user_name"]
        result = users.update_user(
            user_email=user_info["email"], # type: ignore
            **user_data)
    else:
        result = users.add_user(
            returning_column="id",
            **user_info) # type: ignore
    # if server error occurred, return error
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    user_id = result.data

    # create a new session
    result = sessions.create_session(user_id=user_id)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    session_id, expiration_date = result.data

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

@auth.route("/logout", methods=["POST"])
def logout():
    """
    removes the session id
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # remove session from table
    result = sessions.remove_session(session_id=session_id)

    # if nothing could be removed, return error
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response

    # return 204
    response = Response(
        status=204)
    return response

# TODO: remove test function
# @auth.route("/delete", methods=["DELETE"])
def TEST_DELETE_PLEASE_REMOVE():
    """
    TEST FUNCTION - PLEASE REMOVE
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get user id from session id
    result = sessions.get_user(session_id=session_id, keywords=["id", "user_role"])

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response

    # set user_id
    user_id = result.data["id"]

    result = db.delete(table="users", conditions={"id": user_id})
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(status=204)
    return response

# TODO: test automatic deletion from all stueble parties
@auth.route("/delete", methods=["DELETE"])
def delete():
    """
    delete a user (set password to NULL)
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get user id from session id
    result = sessions.get_user(session_id=session_id, keywords=["id", "user_role"])

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response

    if result.data["user_role"] == UserRole.ADMIN.value:
        response = Response(
            response=json.dumps({"code": 403, "message": "Admins cannot be deleted"}),
            status=403,
            mimetype="application/json")
        return response

    # set user_id
    user_id = result.data["id"]

    # remove user from table
    result = users.remove_user(user_id=user_id)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # remove session from table
    result = sessions.remove_session(session_id=session_id)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # remove from guest_list
    result = events.remove_guest(user_id=user_id, stueble_id=-1)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # return 204
    response = Response(
        status=204)
    return response

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
    session_id, expiration_date = result.data

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
