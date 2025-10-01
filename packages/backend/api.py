import asyncio
import base64
import datetime
import json
import os

from flask import Flask, Response, request

from packages.backend import hash_pwd as hp, websocket as ws, qr_code as qr
from packages.backend.data_types import *
from packages.backend.google_functions import email as mail
from packages.backend.sql_connection import (
    configs,
    database as db,
    events,
    guest_events,
    motto,
    sessions,
    users,
)
from packages.backend.sql_connection.common_functions import check_permissions
from packages.backend.sql_connection.conn_cursor_functions import *
from packages.backend.sql_connection.signup_validation import validate_user_data

# NOTE frontend barely ever gets the real user role, rather just gets intern / extern
# Initialize connections to database

# initialize flask app
app = Flask(__name__)

"""
Session and account management
"""

@app.route("/auth/login", methods=["POST"])
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
    
    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user data from table
    result = users.get_user(cursor=cursor, keywords=["id", "password_hash", "user_role"], user_email=user_email, user_name=user_name)

    # return error
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": "Failed to find user"}),
            status=500,
            mimetype="application/json")
        return response

    # check password
    user = result["data"]

    if user[1] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": "account was deleted, can be reactivated by signup"}),
            status=401,
            mimetype="application/json")
        return response

    # if passwords don't match return error
    if not hp.match_pwd(password, user[1]):
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": "invalid password"}),
            status=401,
            mimetype="application/json")
        return response

    # create a new session
    result = sessions.create_session(cursor=cursor, user_id=user[0])

    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    session_id, expiration_date = result["data"]

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

@app.route("/auth/signup", methods=["POST"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    user_role = UserRole.USER
    user_info["user_role"] = user_role
    user_info["residence"] = Residence(user_info["residence"])
    check_info = user_info.copy()
    del check_info["password"]
    # check whether user data is unique
    result = validate_user_data(cursor=cursor, **check_info)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": result["status"], "message": str(result["error"])}),
            status=result["status"],
            mimetype="application/json")
        return response

    # hash password
    hashed_password = hp.hash_pwd(user_info["password"])
    user_info["password_hash"] = hashed_password
    del user_info["password"]

    additional_data = user_info
    
    if result["warning"] is not None:
        additional_data["method"] = "update"
    else:
        additional_data["method"] = "create"

    result = users.create_verification_code(cursor=cursor, user_id=None, additional_data=additional_data)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    verification_token = result["data"]
    wohnheime_logo = os.path.expanduser("~/stueble/packages/backend/google_functions/images/wohnheime_small.png")
    with open(wohnheime_logo, "rb") as image_file:
        wohnheime_logo = base64.b64encode(image_file.read()).decode("utf-8")
    subject = "Neuer Benutzeraccount für das Stüble"
    body = f"""<html lang="de">
<body style="background-color: #430101; text-align: center; font-family: Arial, sans-serif; padding: 20px; color: #ffffff;">
    <div>
            <img src="data:image/png;base64,{wohnheime_logo}" alt="Stüble Logo" width="150">
    </div>
    <h2>Hallo {user_info["first_name"]} {user_info["last_name"]},</h2>
    <p>Du hast einen Account für das Stüble erstellt.</p>
    <p>Um die Registrierung abzuschließen, musst du noch deine Email bestätigen.</p>
    </br>
    <div style="text-align:center; margin: 20px 0;">
  <a href="https://stueble.pages.dev/verify?token={verification_token}"
     style="
       background-color: #0b9a79;
       color: #ffffff;
       padding: 12px 24px;
       text-decoration: none;
       border-radius: 5px;
       display: inline-block;
       font-weight: bold;
       box-shadow: 0 0 10px #da6cff;
       font-family: Arial, sans-serif;
     ">
    Email bestätigen
  </a>
</div>

    </br>
    <p>Wir freuen uns auf dich!</p>
    <p>Dein Stüble-Team</p>
</body>
</html>"""
    # body = f"""Hallo {user_info["first_name"]} {user_info["last_name"]},\n\nklicke diesen Link, um deinen Account zu bestätigen:\n\nhttps://stueble.pages.dev/verify?token={verification_token}\n\nFalls du keinen neuen Account erstellt hast, wende dich bitte umgehend an das Tutoren-Team.\n\nViele Grüße,\nDein Stüble-Team"""

    result = mail.send_mail(recipient=user_info["email"], subject=subject, body=body, html=True)

    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        status=204)
    return response

@app.route("/auth/verify_signup", methods=["POST"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # verify token
    result = users.confirm_verification_code(cursor=cursor, reset_code=token, additional_data=True)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    additional_data = result["data"][1]
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
            cursor=cursor,
            user_email=user_info["email"],
            **user_data)
    else:
        result = users.add_user(
            cursor=cursor,
            returning_column="id",
            **user_info)
    # if server error occurred, return error
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_id = result["data"]

    # create a new session
    result = sessions.create_session(cursor=cursor, user_id=user_id)

    close_conn_cursor(conn, cursor)  # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    session_id, expiration_date = result["data"]

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

@app.route("/auth/logout", methods=["POST"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # remove session from table
    result = sessions.remove_session(cursor=cursor, session_id=session_id)

    close_conn_cursor(conn, cursor)

    # if nothing could be removed, return error
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response

    # return 204
    response = Response(
        status=204)
    return response

@app.route("/auth/delete", methods=["DELETE"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user id from session id
    result = sessions.get_user(cursor=cursor, session_id=session_id, keywords=["id", "user_role"])

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response

    # set user_id
    user_id = result["data"][0]

    result = db.remove_table(cursor=cursor, table_name="users", conditions={"id": user_id})
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(status=204)
    return response

# TODO: test automatic deletion from all stueble parties
# TODO: uncomment route
# app.route("/auth/delete", methods=["DELETE"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user id from session id
    result = sessions.get_user(cursor=cursor, session_id=session_id, keywords=["id", "user_role"])

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response

    if result["data"][1] == UserRole.ADMIN.value:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "Admins cannot be deleted"}),
            status=403,
            mimetype="application/json")
        return response

    # set user_id
    user_id = result["data"][0]

    # remove user from table
    result = users.remove_user(cursor=cursor, user_id=user_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # remove session from table
    result = sessions.remove_session(cursor=cursor, session_id=session_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # remove from guest_list
    result = events.remove_guest(cursor=cursor, user_id=user_id, stueble_id=-1)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # return 204
    response = Response(
        status=204)
    return response

@app.route("/auth/reset_password", methods=["POST"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check whether user with email exists
    result = users.get_user(cursor=cursor, keywords=["id", "first_name", "last_name", "email", "password_hash"], user_email=user_email, user_name=user_name)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 404, "message": "No user with the given email exists"}),
            status=404,
            mimetype="application/json")
        return response
    user_id = result["data"][0]
    first_name = result["data"][1]
    last_name = result["data"][2]
    email = result["data"][3]
    password_hash = result["data"][4]

    if password_hash is None or password_hash == "":
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 400, "message": "User was deleted, needs to signup again."}),
            status=400,
            mimetype="application/json")
        return response

    email = Email(email=email)

    result = users.create_verification_code(cursor=cursor, user_id=user_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    reset_token = result["data"]

    subject = "Passwort zurücksetzen"
    body = f"""Hallo {first_name} {last_name},\n\nmit diesem Code kannst du dein Passwort zurücksetzen: {reset_token}\nFalls du keine Passwort-Zurücksetzung angefordert hast, wende dich bitte umgehend an das Tutoren-Team.\n\nViele Grüße,\nDein Stüble-Team"""

    result = mail.send_mail(recipient=email, subject=subject, body=body)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        status=204)
    return response

@app.route("/auth/reset_password_confirm", methods=["POST"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check whether reset token exists
    result = users.confirm_verification_code(cursor=cursor, reset_code=reset_token)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_id = result["data"]

    # hash new password
    hashed_password = hp.hash_pwd(new_password)

    # set new password
    result = users.update_user(cursor=cursor, user_id=user_id, password_hash=hashed_password)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # remove all existing sessions of the user
    result = sessions.remove_user_sessions(cursor=cursor, user_id=user_id)
    if result["success"] is False:
        if result["error"] != "no sessions found":
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response

    # create a new session
    result = sessions.create_session(cursor=cursor, user_id=user_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    session_id, expiration_date = result["data"]

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
@app.route("/auth/change_password", methods=["POST"])
@app.route("/auth/change_username", methods=["POST"])
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

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.USER)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result["data"]["user_id"]

    data = {}
    if request.path == "/user/change_password":
        new_pwd = data.get("newPassword", None)
        if new_pwd is None:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 400, "message": "The new_password must be specified"}),
                status=400,
                mimetype="application/json")
            return response
        if new_pwd == "":
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 400, "message": "Password cannot be empty"}),
                status=400,
                mimetype="application/json")
            return response
        data["password_hash"] = hp.hash_pwd(new_pwd)
    elif request.path == "/user/change_username":
        username = data.get("username", None)
        if username is None:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 400, "message": f"Username must be specified"}),
                status=400,
                mimetype="application/json")
            return response
        if username == "":
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 400, "message": "Username cannot be empty"}),
                status=400,
                mimetype="application/json")
            return response
        data["user_name"] = username

    # get user id from session id
    result = users.update_user(cursor=cursor, session_id=session_id,
                               user_id=user_id, **data)
    close_conn_cursor(conn, cursor)
    if result["success"] is False and ("user_name" in data.keys()):
        error = result["error"]
        if f"Key (user_name)=({data['user_name']}) already exists." in error:
            response = Response(
                response=json.dumps({"code": 400, "message": "Username already exists"}),
                status=400,
                mimetype="application/json")
            return response
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response

    response = Response(
        status=204
    )
    return response

"""
Guest list management
"""

# NOTE: if no stueble is happening today or yesterday, an empty list is returned
@app.route("/guests", methods=["GET"])
def guests():
    """
    returns list of all guests
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only hosts can add guests
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": "invalid permissions, need role host or above"}),
            status=401,
            mimetype="application/json")
        return response

    # get guest list
    result = guest_events.guest_list(cursor=cursor)
    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    response = Response(
        response=json.dumps(result["data"]),
        status=200,
        mimetype="application/json"
    )
    return response

@app.route("/guest", methods=["POST"])
def guest_change():
    """
    add / remove a guest to the guest_list of present people
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    user_uuid = data.get("id", None)
    present = data.get("present", None)

    if session_id is None or user_uuid is None or present is None:
        response = Response(
            response=json.dumps({"code": 401, "message": f"The session id, uuid, present must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only hosts can add guests
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role host or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result["data"]["user_id"]
    event_type = EventType.ARRIVE if present else EventType.LEAVE

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified", "user_role"]
    data = users.get_user(
        cursor=cursor,
        user_id=user_id,
        keywords=keywords,
        expect_single_answer=True)

    if data["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    if event_type == EventType.ARRIVE:
        # verify guest if not verified yet
        if data["data"][4] is False:
            result = users.update_user(cursor=cursor, 
                                       user_id=user_id, 
                                       verified=True)
            if result["success"] is False:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result["error"])}),
                    status=500,
                    mimetype="application/json")
                return response


    # change guest status to arrive / leave
    result = guest_events.change_guest(cursor=cursor, user_uuid=user_uuid, event_type=event_type)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_info = {key: value for key, value in zip(keywords, data["data"])}
    user_info["user_role"] = FrontendUserRole.EXTERN if user_info["user_role"] == "extern" else FrontendUserRole.INTERN

    user_data = {
            "id": user_uuid,
            "present": present,
            "firstName": user_info["first_name"],
            "lastName": user_info["last_name"],
            "extern": user_info["user_role"] == FrontendUserRole.EXTERN}

    if user_info["user_role"] == FrontendUserRole.INTERN:
        user_data["roomNumber"] = user_info["room"]
        user_data["residence"] = user_info["residence"]
        user_data["verified"] = True

    message = {
        "event": "guestModified",
        "data": user_data}

    # send a websocket message to all hosts that the guest list changed
    asyncio.run(ws.broadcast(event="guestModified", data=message, skip_sid=session_id))

    # send a websocket message to the user
    asyncio.run(ws.stueble_status(session_id=session_id, registered=True, present=present))

    # return 204
    response = Response(
        status=204)
    return response

# TODO broadcast add remove user
@app.route("/guests", methods=["PUT", "DELETE"])
def attend_stueble():
    """
    sign up for a stueble party
    """

    # load data
    session_id = request.cookies.get("SID", None)
    try:
        data = request.get_json()
        date = data.get("date", None)
        user_uuid = data.get("id", None)
    except:
        date = None
        user_uuid = None
    
    required_role = UserRole.USER
    if user_uuid is not None:
        required_role = UserRole.HOST

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    if date is None:
        result = motto.get_motto(cursor=cursor)
        if result["success"] is False:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
        if result["data"] is None:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 400, "message": "No stueble is happening in the next time"}),
                status=400,
                mimetype="application/json")
            return response
        date = result["data"][1]

    if session_id is None or date is None:
        response = Response(
            response=json.dumps({"code": 401, "message": f"The session id and date must be specified"}),
            status=401,
            mimetype="application/json")
        return response


    # check permissions, since only hosts can add guests
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=required_role)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    if user_uuid is None:
        user_id = result["data"]["user_id"]
        user_uuid = result["data"]["user_uuid"]
    else:
        result = users.get_user(cursor=cursor, user_uuid=user_uuid, keywords=["id", "user_uuid"], expect_single_answer=True)
        if result["success"] is False:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
        user_id = result["data"][0]
        user_uuid = result["data"][1]

    result = motto.get_info(cursor=cursor, date=date)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    stueble_id = result["data"][0]

    if request.method == "PUT":
        result = events.add_guest(
            cursor=cursor,
            user_id=user_id,
            stueble_id=stueble_id)
    else:
        result = events.remove_guest(
            cursor=cursor,
            user_id=user_id,
            stueble_id=stueble_id)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        status_code = 500
        error = str(result["error"])
        if "; code: " in str(result["error"]):
            error, status_code = str(result["error"]).split("; code: ")
            status_code = status_code.split("\n")[0]
            status_code = int(status_code)
        response = Response(
            response=json.dumps({"code": status_code, "message": error}),
            status=status_code,
            mimetype="application/json")
        return response

    if request.method == "PUT":
        timestamp = int(datetime.datetime.now().timestamp())
        
        information = {"id": user_uuid, "timestamp": timestamp, "extern": False}

        signature = hp.create_signature(message=information)

        data = {"data":
                    information,
                "signature": signature}
        response = Response(
            response=json.dumps(data),
            status=200,
            mimetype="application/json")
    else:
        response = Response(
            status=204)

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified"]
    result = users.get_user(
        cursor=cursor,
        user_id=user_id,
        keywords=keywords,
        expect_single_answer=True)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_info = {key: value for key, value in zip(keywords, result["data"])}
    user_info["user_role"] = FrontendUserRole.INTERN

    user_data = {
        "id": user_uuid,
        "present": False,
        "firstName": user_info["first_name"],
        "lastName": user_info["last_name"],
        "extern": False,
        "roomNumber": user_info["room"],
        "residence": user_info["residence"],
        "verified": True if user_info["verified"] is not None else False}

    if request.method == "PUT":
        action_type = Action_Type("guestAdded")
    else:
        action_type = Action_Type("guestRemoved")

    # send a websocket message to all hosts that the guest list changed
    asyncio.run(ws.broadcast(event=action_type.value, data=user_data, skip_sid=session_id))

    # send a websocket message to the user
    asyncio.run(ws.stueble_status(session_id=session_id, date=date, registered=True if request.method == "PUT" else False, present=False))

    return response

# NOTE: extern guest can be multiple times in table users since only first_name, last_name are specified, which are not unique
@app.route("/guests/invitee", methods=["PUT", "DELETE"])
def invitee():
    """
    invite a friend and share a qr-code
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    date = data.get("date", None)
    invitee_first_name = data.get("firstName", None)
    invitee_last_name = data.get("lastName", None)
    invitee_email = data.get("email", None)

    if any(i is None for i in [session_id, invitee_first_name, invitee_last_name, invitee_email]):
        response = Response(
            response=json.dumps({"code": 401,
                "message": f"session_id, date, invitee_first_name, invitee_last_name, invitee_email must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only users can add guests
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.USER)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_role = UserRole(result["data"]["user_role"])

    user_id = result["data"]["user_id"]
    first_name = result["data"]["first_name"]
    last_name = result["data"]["last_name"]

    if user_role < UserRole.HOST:
        result = users.check_user_guest_list(cursor=cursor, user_id=user_id)
        if result["success"] is False:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
        if result["data"] is False:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 403, "message": "You need to be on the guest list to invite someone"}),
                status=403,
                mimetype="application/json")
            return response

    result = motto.get_info(cursor=cursor, date=date)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    stueble_id = result["data"][0]
    motto_name = result["data"][1]
    stueble_date = result["data"][2]
    stueble_date = stueble_date.strftime("%d.%m.%Y")

    if request.method == "PUT":
        # add user to table
        result = users.add_user(
            cursor=cursor,
            user_role=UserRole.EXTERN,
            first_name=invitee_first_name,
            last_name=invitee_last_name,
            returning_column="id, user_uuid") # id, user_uuid on purpose like that

    else:
        # get user to remove
        result = users.get_user(
            cursor=cursor,
            keywords=["id", "user_uuid"],
            conditions={"first_name": invitee_first_name, "last_name": invitee_last_name, "user_role": UserRole.EXTERN.value},
            expect_single_answer=False)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    if request.method == "DELETE":
        possible_users = result["data"]
        if len(possible_users) == 0:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 404, "message": "No such user found"}),
                status=404,
                mimetype="application/json")
            return response
        users_list = []
        for i in possible_users:
            query = """
            SELECT user_id FROM events
            WHERE user_id = %s AND stueble_id = %s AND event_type = 'add' AND invited_by = %s
            ORDER BY submitted DESC LIMIT 1"""
            result = db.custom_call(cursor=cursor,
                                    query=query,
                                    type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
                                    variables=[i[0], stueble_id, user_id])
            if result["success"] is False:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result["error"])}),
                    status=500,
                    mimetype="application/json")
                return response
            if result["data"] is None:
                continue
            possible_invitee_id = result["data"][0][0]

            result = users.get_user(cursor=cursor,
                                    user_id=possible_invitee_id,
                                    keywords=["user_uuid"],
                                    expect_single_answer=True)
            if result["success"] is False:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result["error"])}),
                    status=500,
                    mimetype="application/json")
                return response
            if result["data"] is None:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"code": 500, "message": "Data integrity error, user not found"}),
                    status=500,
                    mimetype="application/json")
                return response
            possible_invitee_uuid = result["data"][0]
            users_list.append({"invitee_id": possible_invitee_id, "invitee_uuid": possible_invitee_uuid})
        if len(users_list) == 0:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 401, "message": "No such user found"}),
                status=401,
                mimetype="application/json")
            return response
        if len(users_list) > 1:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 409, "message": "Multiple users found, please contact an admin"}),
                status=409,
                mimetype="application/json")
            return response
        invitee_id = users_list[0]["invitee_id"]
        invitee_uuid = users_list[0]["invitee_uuid"]
    else:
        invitee_id = result["data"][0]
        invitee_uuid = result["data"][1]

    if request.method == "PUT":
        result = events.add_guest(
            cursor=cursor,
            user_id=invitee_id,
            stueble_id=stueble_id,
            invited_by=user_id)
    else:
        result = events.remove_guest(
            cursor=cursor,
            user_id=invitee_id,
            stueble_id=stueble_id)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        status_code = 500
        error = str(result["error"])
        if "; code: " in str(result["error"]):
            error, status_code = str(result["error"]).split("; code: ")
            status_code = status_code.split("\n")[0]
            status_code = int(status_code)
        response = Response(
            response=json.dumps({"code": status_code, "message": error}),
            status=status_code,
            mimetype="application/json")
        return response

    if request.method == "PUT":
        timestamp = int(datetime.datetime.now().timestamp())

        information = {"id": invitee_uuid, "timestamp": timestamp, "extern": True}

        signature = hp.create_signature(message=information)

        data = {"data":information,
                "signature": signature}

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified"]
    result = users.get_user(
        cursor=cursor,
        user_id=invitee_id,
        keywords=keywords,
        expect_single_answer=True)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    invitee_info = {key: value for key, value in zip(keywords, result["data"])}
    invitee_info["user_role"] = FrontendUserRole.EXTERN

    invitee_data = {
        "id": invitee_uuid,
        "present": False,
        "firstName": invitee_info["first_name"],
        "lastName": invitee_info["last_name"],
        "extern": True}

    action_type = Action_Type("guestModified")

    # send a websocket message to all hosts that the guest list changed
    asyncio.run(ws.broadcast(event=action_type.value, data=invitee_data, skip_sid=session_id))
    asyncio.run(ws.broadcast(event=action_type.value, data=invitee_data, skip_sid=session_id))

    if request.method == "DELETE":
        response = Response(
            status=204)
        return response

    if invitee_email is not None:
        stueble_logo = os.path.expanduser("~/stueble/packages/backend/google_functions/images/favicon_150.png")
        qr_code = qr.generate(json.dumps(data), size=300)
        subject = "Einladung zum Stüble"
        image_data = ({"name": "stueble_logo", "value": stueble_logo}, {"name": "qr_code", "value": qr_code})
        name = "wohnheime_small"
        body = f"""<html lang="de">
        <head>
    <meta charset="UTF-8">
 </head>
<body style="background-color: #430101; text-align: center; font-family: Arial, sans-serif; padding: 20px; color: #ffffff;">
    <div>
            <img src="cid:{image_data[0]["name"]}" alt="Stüble Logo" width="150">
    </div>
    <h2>Hallo {invitee_first_name} {invitee_last_name},</h2>
    <p>Du wurdest von {first_name} {last_name} zu unserem nächsten Stüble am {stueble_date} eingeladen 🥳.</p>
    <p>Das Motto lautet {motto_name}.</p>
    </br>
    <p>Zeige bitte diesen QR-Code beim Einlass vor:</p>
    <img src="cid:{image_data[1]["name"]}" alt="QR-Code" width="300">
    </br>
    <p>Wir freuen uns auf dich!</p>
    <p>Dein Stüble-Team</p>
</body>
</html>"""
        # body = f"""Hallo {invitee_first_name} {invitee_last_name},\n\ndu wurdest von {first_name} {last_name} zu unserem nächsten Stüble am {stueble_date} eingeladen. \nDas Motto lautet {motto_name}. Wir freuen uns, wenn du kommst.\n\nViele Grüße,\nDein Stüble-Team"""
        mail.send_mail(Email(invitee_email), subject, body, html=True, images=image_data)

    response = Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")
    return response

"""
User management
"""

@app.route("/user", methods=["GET"])
def user():
    """
    return data to user
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user id from session id
    result = sessions.get_user(cursor=cursor, session_id=session_id, keywords=("id", "user_role", "user_uuid", "room", "residence", "first_name", "last_name", "email", "user_name"))
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    data = result["data"]

    # initialize user
    user = {"firstName": data[5],
            "lastName": data[6],
            "roomNumber": data[3],
            "residence": data[4],
            "email": data[7],
            "id": data[0], 
            "username": data[8]}

    close_conn_cursor(conn, cursor)
    response = Response(
        response=json.dumps(user),
        status=200,
        mimetype="application/json")
    return response

# TODO websocket change update user
@app.route("/user/change_role", methods=["POST"])
def change_user_role():
    """
    change the user role of a user (only admin can change user to tutor)
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response
    user_uuid = data.get("id", None)
    new_role = data.get("role", None)
    if new_role is None or is_valid_role(new_role) is False or new_role == "admin":
            response = Response(
                response=json.dumps({"code": 400, "message": "The new_role must be specified, needs to be valid and can't be admin"}),
                status=400,
                mimetype="application/json")
            return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only tutors or above can change user role
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.ADMIN if new_role == UserRole.TUTOR else UserRole.TUTOR)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor or above"}),
            status=403,
            mimetype="application/json")
        return response
    user_id = result["data"]["user_id"]

    result = users.update_user(
        cursor=cursor,
        user_uuid=user_uuid,
        user_role=UserRole(new_role))

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    if result["data"] is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "No user found with the given user_id / email"}),
            status=400,
            mimetype="application/json")
        return response

    capabilities = [i.value for i in get_leq_roles(result["data"]["user_role"]) if i.value in ["user", "host", "tutor", "admin"]]

    data = {"code": "200",
            "capabilities": capabilities,
            "authorized": True}

    asyncio.run(ws.send(websocket=ws.get_websocket_by_sid(sid=session_id), event="status", data=data))

    # check if user is on guest list

    result = users.check_user_guest_list(cursor=cursor, user_id=user_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    if result["data"] is True:
        keywords = ["user_uuid", "first_name", "last_name", "user_role"]
        result = users.get_user(cursor=cursor, user_id=user_id, keywords=keywords)
        if result["success"] is False:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
        user_info = {key: value for key, value in zip(keywords, result["data"])}

        result = users.check_user_present(cursor=cursor, user_id=user_id)
        close_conn_cursor(conn, cursor)
        if result["success"] is False:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
        present = result["data"]

        user_data = {
            "id": user_info["user_uuid"],
            "present": present,
            "firstName": user_info["first_name"],
            "lastName": user_info["last_name"],
            "extern": user_info["user_role"] == FrontendUserRole.EXTERN}

        if user_info["user_role"] == FrontendUserRole.INTERN:
            user_data["roomNumber"] = user_info["room"]
            user_data["residence"] = user_info["residence"]
            user_data["verified"] = True

        asyncio.run(ws.broadcast(event="guestModified", data=user_data, skip_sid=session_id))

    response = Response(
        status=204)
    return response

@app.route("/user/search", methods=["GET"])
def search_intern():
    """
    search for a guest \n
    allowed keys for searching are first_name, last_name, email, (room, residence), user_uuid
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # check permissions, since only hosts can see guests

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": "invalid permissions, need at least role host"}),
            status=401,
            mimetype="application/json")
        return response

    # load data
    data = request.args.to_dict()

    if data is None or not isinstance(data, dict):
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 400, "message": "The data must be a valid json object"}),
            status=400,
            mimetype="application/json")
        return response

    # json format data: {"session_id": str, data: {"first_name": str or None, "last_name": str or None, "room": str or None, "residence": str or None, "email": str or None}}

    # allowed keys to search for a user
    allowed_keys = ["first_name", "last_name", "room", "residence", "email", "id", "username"]

    # if no key was specified return error
    if any(key not in allowed_keys for key in data.keys()):
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 400, "message": f"Only the following keys are allowed: {', '.join(allowed_keys)}"}),
            status=400,
            mimetype="application/json")
        return response

    keywords = ["first_name", "last_name", "user_uuid"]
    negated_conditions = {"user_role": "extern"}
    if "username" in data:
        conditions = {"user_name": data["username"]}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            expect_single_answer=True)

    # search room and / or residence
    elif "room" in data or "residence" in data:
        conditions = [[key, value] for key, value in data.items() if key in ["room", "residence"]]
        conditions = dict(conditions)
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            expect_single_answer=True)
    
    # search user_uuid
    elif "id" in data:
        conditions = {"user_uuid":data["id"]}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            expect_single_answer=True)

    # search email
    elif "email" in data:
        conditions = {"email": data["email"]}
        negated_conditions = {"user_role": "extern"}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            expect_single_answer=True)
        
    # search first_name and/or last_name
    else:
        conditions = {key: value for key, value in data.items() if value is not None}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            conditions=conditions,
            keywords=keywords,
            negated_conditions=negated_conditions,
            expect_single_answer=False)

    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # if data is None, set it to empty list
    if result["data"] is None:
        result["data"] = []

    users = []
    for entry in result["data"]:

        users.append({"first_name": entry[0], 
                      "last_name": entry[1], 
                      "id": entry[2]})
    users = [{snake_to_camel_case(key): value for key, value in i.items()} for i in users]

    response = Response(
        response=json.dumps(users),
        status=200,
        mimetype="application/json")

    return response

"""
Motto management (GET via WebSocket)
"""

# TODO allow date changes
@app.route("/motto", methods=["POST"])
def create_stueble():
    """
    creates a new stueble event
    """

    # load data
    data = request.get_json()
    date = data.get("date", None)
    stueble_motto = data.get("motto", None)
    description = data.get("description", None)
    shared_apartment = data.get("shared_apartment", None)

    if stueble_motto is None and shared_apartment is None and description is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "motto or shared_apartment or description must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    user_role = UserRole.TUTOR
    # date can't be changed but rather acts as an identifier
    if shared_apartment is not None:
        user_role = UserRole.HOST

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only hosts or above can change the motto
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=user_role)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": f"invalid permissions, need role {user_role.value} or above"}),
            status=403,
            mimetype="application/json")
        return response
    actual_user_role = result["data"]["user_role"]
    actual_user_role = UserRole(actual_user_role)

    if date is None:
        date = datetime.date.today()
        days_ahead = (2 - date.weekday() + 7) % 7
        date = date + datetime.timedelta(days=days_ahead)

    result = motto.update_stueble(cursor=cursor,
                                date=date,
                                motto=stueble_motto,
                                description=description,
                                shared_apartment=shared_apartment)

    if result["success"] is False:
        if result["error"] == "no stueble found":
            if actual_user_role == UserRole.HOST:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor or above to create a new stueble"}),
                    status=403,
                    mimetype="application/json")
                return response

            result = motto.create_stueble(cursor=cursor,
                                    date=date,
                                    motto=stueble_motto,
                                    description=description,
                                    shared_apartment=shared_apartment)

            if result["success"] is False:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result["error"])}),
                    status=500,
                    mimetype="application/json")
                return response
        else:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response

    close_conn_cursor(conn, cursor)
    response = Response(status=204)
    return response

"""
Hosts management (Changes via WebSocket)
"""

@app.route("/hosts", methods=["PUT", "DELETE"])
def update_hosts():
    """
    Update hosts for a stueble.
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response
    
    data = request.get_json()
    date = data.get("date", None)
    user_uuids = data.get("hosts", None)

    if not user_uuids:
        response = Response(
            response=json.dumps({"code": 403, "message": "hosts must be specified"}),
            status=403,
            mimetype="application/json")
        return response
    
    # get conn, cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only tutors or above can change user role
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.TUTOR)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor or above"}),
            status=403,
            mimetype="application/json")
        return response
    
    result = motto.get_motto(cursor=cursor, date=date)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 404, "message": "no stueble party found"}),
            status=404,
            mimetype="application/json")
        return response
    stueble_id = result["data"][2]

    result = users.get_users(cursor=cursor, user_uuids=user_uuids, keywords=["user_uuid", "first_name", "last_name"])
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    hosts_data = result["data"]
    hosts_data = [{"id": i[0], "firstName": i[1], "lastName": i[2]} for i in hosts_data]

    result = motto.update_hosts(cursor=cursor, stueble_id=stueble_id, method="add" if request.method == "PUT" else "remove", user_uuids=user_uuids)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_ids = result["data"]

    query = f"SELECT id FROM sessions WHERE user_id IN ({', '.join(['%s' for _ in range(len(user_ids))])})"
    result = db.custom_call(
        cursor=cursor,
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=tuple(user_ids)
    )

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    session_ids = [i[0] for i in result["data"]]

    result = ws.update_hosts(session_ids, "add" if request.method == "PUT" else "remove")

    for host in hosts_data:
        asyncio.run(ws.broadcast(event="hostAdded" if request.method == "PUT" else "hostRemoved", data=host, skip_sid=session_id))

    response = Response(
        status=204)
    return response

@app.route("/hosts", methods=["GET"])
def get_hosts():
    """
    Get hosts for a stueble.
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response
    
    data = request.get_json()
    date = data.get("date", None)
    
    # get conn, cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only hosts or above can change user role
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role host or above"}),
            status=403,
            mimetype="application/json")
        return response

    result = motto.get_motto(cursor=cursor, date=date)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 404, "message": "no stueble party found"}),
            status=404,
            mimetype="application/json")
        return response
    stueble_id = result["data"][2]
    result = motto.get_hosts(cursor=cursor, stueble_id=stueble_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        response=json.dumps(result["data"]),
        status=200,
        mimetype="application/json")
    return response

@app.route("/hosts/force_add_guest", methods=["POST"])
def force_add_guest():
    """
    force add guest to current stueble
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response
    user_uuid = data.get("id", None)
    if user_uuid is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "The user_uuid must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only hosts and above can add guests
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role host or above"}),
            status=403,
            mimetype="application/json")
        return response

    # get user_id from user_uuid
    result = users.get_user(cursor=cursor, user_uuid=user_uuid, keywords=["id"])
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    user_id = result["data"][0]
    query = """SET additional.skip_triggers = 'on';
INSERT INTO events (user_id, stueble_id, event_type) VALUES (%s, %s, %s), (%s, %s, %s);  -- Triggers will be skipped
RESET additional.skip_triggers;"""
    result = db.custom_call(cursor=cursor,
                            query=query,
                            type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
                            variables=[user_id, 1, 'add', user_id, 1, 'arrive'])
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        status=204)
    return response

"""
Config management
"""

def snake_to_camel_case(snake_case: str):
    """
    turns snake_case into camelCase
    Parameters:
        snake_case (str): the snake_case string
    Returns:
        str: the camelCase string
    """
    camel_case = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), snake_case)
    if "Qr" in camel_case:
        camel_case = camel_case.replace("Qr", "QR")
    return camel_case



def camel_to_snake_case(camel_case: str):
    """
    turns camelCase into snake_case
    Parameters:
        camel_case (str): the camelCase string
    Returns:
        snake_case (str): the snake_case string
    """
    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_case).lower()
    if "_q_r_" in snake_case:
        snake_case = snake_case.replace("_q_r_", "_qr_")
        return snake_case

@app.route("/config", methods=["GET", "POST"])
def config():
    """
    get or update config values
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response        

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only admins can change config values
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.ADMIN)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role admin"}),
            status=403,
            mimetype="application/json")
        return response

    if request.method == "POST":
        data = request.get_json()

        case_statements = '\n'.join(["WHEN %s THEN %s" for i in range (len(data))])
        keys = tuple(camel_to_snake_case(key) for key in data.keys())
        values = tuple(value for value in data.values())

        params = [i for i in zip(keys, values)] + [tuple(keys)]

        query = f"""UPDATE configurations
        SET value = CASE key
        {case_statements}
        END
        WHERE key IN %s"""
        result = db.custom_call(cursor=cursor,
                                query=query,
                                type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
                                variables=params)
        if result["success"] is False:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response

        # send websocket message to all admins
        asyncio.run(ws.broadcast(event="config_update", data=data, room=ws.Room.ADMINS))

    # Method GET & POST
    result = configs.get_all_configurations(cursor=cursor)
    close_conn_cursor(conn, cursor)

    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    response = Response(
        response=json.dumps({snake_to_camel_case(key): value for key, value in result.get("data")}),
        status=200,
        mimetype="application/json")
    return response


"""
Internal
"""

@app.route("/websocket_local", methods=["POST"])
def websocket_change():
    """
    receive data from websocket_runner and send it to all connected clients
    """

    if request.remote_addr != "127.0.0.1":
        response = Response(
            response=json.dumps({"code": 401, "message": "Unauthorized, only local requests are allowed"}),
            status=401,
            mimetype="application/json")
        return response

    # load data
    data = request.get_json()
    first_name = data.get("firstName", None)
    last_name = data.get("lastName", None)
    user_uuid = data.get("user_uuid", None)
    stueble_id = data.get("stuebleId", None)
    event = data.get("event", None)
    if first_name is None or last_name is None or event is None:
        response = Response(
            response=json.dumps({"code": 400, "message": f"first_name, last_name and event must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    asyncio.run(ws.broadcast(event="guest_list_update", data={"first_name": first_name, "last_name": last_name}))

    response = Response(
        status=200)
    return response
