import datetime
from zoneinfo import ZoneInfo

from flask import Flask, request, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
import json

from jwcrypto import jwk

from packages.backend.http_to_websocket import *

from packages.backend.data_types import *
from packages.backend.sql_connection import (
    users,
    sessions,
    motto,
    guest_events,
    websocket,
    configs,
    events,
    database as db)
from packages.backend.sql_connection import signup_validation as signup_val
from packages.backend import hash_pwd as hp
from packages.backend.google_functions import gmail
import re
from datetime import timedelta
import msgpack

# TODO code isn't written nicely, e.g. in logout and delete there are big code overlaps
# TODO always close connection after last request
# NOTE frontend barely ever gets the real user role, rather just gets intern / extern
# Initialize connections to database
pool = db.create_pool()

# initialize flask app
app = Flask(__name__)
app.pool = pool

socketio = SocketIO(app, async_mode="eventlet")

host_upwards_room = "host_upwards"

def valid_session_id(func):
    def wrapper(*args, **kwargs):
        pass


def check_permissions(cursor, session_id: str, required_role: UserRole) -> dict:
    """
    checks whether the user with the given session_id has the required role
    Parameters:
        cursor: cursor for the connection
        session_id (str): session id of the user
        required_role (UserRole): required role of the user
    Returns:
        dict: {"success": bool, "data": {"allowed": bool, "user_id": int, "user_role": UserRole}, {"success": False, "error": e} if error occurred
    """

    # get the user_id, user_role by session_id
    result = sessions.get_user(cursor=cursor, session_id=session_id)

    # if error occurred, return error
    if result["success"] is False:
        return result
    user_id = result["data"][0]
    user_role = result["data"][1]
    user_role = UserRole(user_role)
    user_uuid = result["data"][2]
    if user_role >= required_role:
        return {"success": True, "data": {"allowed": True, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid}}
    return {"success": True, "data": {"allowed": False, "user_id": user_id, "user_role": user_role, "user_uuid": user_uuid}}

def get_conn_cursor():
    """
    gets a connection and a cursor from the connection pool
    """
    conn = app.pool.getconn()
    cursor = conn.cursor()
    return conn, cursor

def close_conn_cursor(connection, cursor):
    """
    closes the cursor and returns the connection to the pool
    """
    cursor.close()
    app.pool.putconn(connection)

# TODO: decide, whether to handle deleted accounts with password reset or signup
@app.route("/auth/login", methods=["POST"])
def login():
    """
    checks, whether a user exists and whether user is logged in (if exists and not logged in, session is created)
    """

    # load data
    data = request.get_json()
    # TODO: make user_name and email one parameter user
    name = data.get("user", None)
    password = data.get("password", None)

    # password can't be empty
    if password == "":
        response = Response(
            response=json.dumps({"error": "password cannot be empty"}),
            status=401,
            mimetype="application/json")
        return response

    if name is None:
        response = Response(
            response=json.dumps({"error": "specify user"}),
            status=400,
            mimetype="application/json")
        return response

    value = {}
    if "@" in name:
        try:
            name = Email(email=name)
        except ValueError:
            response = Response(
                response=json.dumps({"error": "Invalid email format"}),
                status=400,
                mimetype="application/json")
            return response
        value = {"user_email": name}
    else:
        value = {"user_name": name}

    # if data is not valid return error
    if password is None:
        response = Response(
            response=json.dumps({"error": "specify password"}),
            status=400,
            mimetype="application/json")
        return response
    
    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user data from table
    result = users.get_user(cursor=cursor, keywords=["id", "password_hash", "user_role"], expect_single_answer=True, **value)

    # return error
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # check password
    user = result["data"]

    if user[1] is None:
        response = Response(
            response=json.dumps({"error": "account was deleted, can be reactivated by signup"}),
            status=401,
            mimetype="application/json")
        return response

    # if passwords don't match return error
    if not hp.match_pwd(password, user[1]):
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid password"}),
            status=401,
            mimetype="application/json")
        return response

    # create a new session
    result = sessions.create_session(connection=conn, cursor=cursor, user_id=user[0])

    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    session_id = result["data"]

    # return 204
    response = Response(
        status=204)

    response.set_cookie("SID",
                        session_id,
                        httponly=True,
                        secure=True,
                        samesite='Lax')
    return response

# TODO: handle deleted accounts like signup
# TODO: add email verification
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
            response=json.dumps({"error": "Privacy policy needs to be accepted"}),
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
    user_info["user_name"] = data.get("userName", None)
    user_info["password"] = data.get("password", None)

    # if a value wasn't set, return error
    if any(e is None for e in user_info.values()):
        response = Response(
            response=json.dumps({"error": f"The following fields must be specified: {', '.join([key for key, value in user_info.items() if value is None])}"}),
            status=400,
            mimetype="application/json")
        return response

    # check, whether user data is valid
    try:
        user_info["room"] = int(user_info["room"])
    except ValueError:
        response = Response(
            response=json.dumps({"error": "Room must be a number"}),
            status=400,
            mimetype="application/json")
        return response

    # check, whether residence is valid
    if not is_valid_residence(user_info["residence"]):
        response = Response(
            response=json.dumps({"error": "Invalid residence"}),
            status=400,
            mimetype="application/json")
        return response

    # check, whether email is valid
    try:
        user_info["email"] = Email(email=user_info["email"])
    except ValueError:
        response = Response(
            response=json.dumps({"error": "Invalid email format"}),
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
    result = signup_val.validate_user_data(cursor=cursor, **check_info)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
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

    result = users.create_verification_code(connection=conn, cursor=cursor, user_id=None, additional_data=additional_data)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    verification_token = result["data"]

    subject = "Neuer Benutzeraccount für das Stüble"
    body = f"""Hallo {user_info["first_name"]} {user_info["last_name"]},\n\nmit diesem Code kannst du deinen Account bestätigen: {verification_token}\nFalls du keinen neuen Account erstellt hast, wende dich bitte umgehend an das Tutoren-Team.\n\nViele Grüße,\nDein Stüble-Team"""

    result = gmail.send_mail(recipient=user_info["email"], subject=subject, body=body)

    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
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
            response=json.dumps({"error": "The token must be specified"}),
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
            response=json.dumps({"error": str(result["error"])}),
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
            connection=conn,
            cursor=cursor,
            user_email=user_info["email"],
            **user_data)
    else:
        result = users.add_user(
            connection=conn,
            cursor=cursor,
            returning="id",
            **user_info)

    # if server error occurred, return error
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_id = result["data"]

    # create a new session
    result = sessions.create_session(connection=conn, cursor=cursor, user_id=user_id)

    close_conn_cursor(conn, cursor)  # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    session_id = result["data"]

    # return 204
    response = Response(
        status=204)

    response.set_cookie("SID",
                        session_id,
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
            response=json.dumps({"error": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # remove session from table
    result = sessions.remove_session(connection=conn, cursor=cursor, session_id=session_id)

    close_conn_cursor(conn, cursor)

    # if nothing could be removed, return error
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response

    # return 204
    response = Response(
        status=204)
    return response

@app.route("/auth/delete", methods=["DELETE"])
def delete():
    """
    delete a user (set password to NULL)
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
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
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response

    if result["data"][1] == UserRole.ADMIN.value:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "Admins cannot be deleted"}),
            status=403,
            mimetype="application/json")
        return response

    # set user_id
    user_id = result["data"][0]

    # remove user from table
    result = users.remove_user(connection=conn, cursor=cursor, user_id=user_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # remove session from table
    result = sessions.remove_session(connection=conn, cursor=cursor, session_id=session_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # TODO remove user and invited users from stueble_table

    # return 204
    response = Response(
        status=204)
    return response

# NOTE: this endpoint is public, since the motto is also shown on the website without logging in
@app.route("/motto", methods=["GET"])
def get_motto(date: str | None = None):
    """
    returns the motto for the next stueble party

    Parameters:
        date (str | None): the date of the motto
    """

    if date is None:
        data = request.get_json()
        date = data.get("date", None)
        # load data
    elif date == "":
        date = None

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # if date is None, return all stuebles
    if date is None:
        result = db.read_table(
            cursor=cursor,
            table_name="stueble_motto",
            keywords=["motto", "date_of_time"],
            order_by=("date_of_time", 0), # descending
            expect_single_answer=False)
        close_conn_cursor(conn, cursor) # close conn, cursor
        if result["success"] is False:
            response = Response(
                response=json.dumps({"error": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
        data = [{"motto": entry[0], "date": entry[1].isoformat()} for entry in result["data"]]
        response = Response(
            response=json.dumps(data),
            status=200,
            mimetype="application/json")
        return response

    # get motto from table
    result = motto.get_motto(cursor=cursor, date=date)
    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    data = {"motto": result["data"][0], "date": result["data"][1].isoformat()} if result["data"] is not None else {}
    response = Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")
    return response

@socketio.on("requestMotto")
def request_motto(msg):
    try:
        data = msgpack.unpack(msg, raw=False)
    except Exception as e:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "500",
             "message": f"Invalid msgpack format: {str(e)}"}}, use_bin_type=True))
        return
    req_id = data.get("reqId", None)
    date = data.get("date", "")

    if req_id is None:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "401",
             "message": "req_id must be specified"}}, use_bin_type=True))

    result = get_motto(date=date)
    emit("motto", http_to_websocket_response(response=result, event="motto"), to=request.sid)
    return


#TODO: work on guest dictionary
# NOTE: if no stueble is happening today or yesterday, an empty list is returned
@app.route("/guests", methods=["GET"])
def guests():
    """
    returns list of all guests
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
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
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role host or above"}),
            status=401,
            mimetype="application/json")
        return response

    # get guest list
    result = guest_events.guest_list(cursor=cursor)
    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    response = Response(
        response=json.dumps(result["data"]),
        status=200,
        mimetype="application/json"
    )
    return response

@app.route("/user", methods=["GET"])
def user():
    """
    return data to user
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user id from session id
    result = sessions.get_user(cursor=cursor, session_id=session_id, keywords=["first_name", "last_name", "room", "residence", "email", "user_role"])
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response

    data = result["data"]

    # initialize user
    user = {"firstName": data[0],
            "lastName": data[1],
            "roomNumber": data[2],
            "residence": data[3],
            "email": data[4],
            "capabilities": [""] if UserRole(data[5]) <= UserRole.USER else ["host"] if UserRole(
                data[5]) < UserRole.ADMIN else ["host", "admin"]}

    response = Response(
        response=json.dumps(user),
        status=200,
        mimetype="application/json")
    return response

# DEPRECATED: this function isn't used
# TODO: add stueble_code search
@DeprecationWarning
@app.route("/host/search_guest", methods=["POST"])
def search():
    """
    search for a guest \n
    allowed keys for searching are first_name, last_name, email, (room, residence)
    """

    # load data
    data = request.get_json()

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
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
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need at least role host"}),
            status=401,
            mimetype="application/json")
        return response

    # load data
    data = data.get("data", None)

    if data is None or not isinstance(data, dict):
        response = Response(
            response=json.dumps({"error": "The data must be a valid json object"}),
            status=400,
            mimetype="application/json")
        return response

    # json format data: {"session_id": str, data: {"first_name": str or None, "last_name": str or None, "room": str or None, "residence": str or None, "email": str or None}}

    # allowed keys to search for a user
    allowed_keys = ["first_name", "last_name", "room", "residence", "email"]

    # if no key was specified return error
    if any(key not in allowed_keys for key in data.keys()):
        response = Response(
            response=json.dumps({"error": f"Only the following keys are allowed: {', '.join(allowed_keys)}"}),
            status=400,
            mimetype="application/json")
        return response
    keywords = ["first_name", "last_name", "email", "user_role"]

    # if only either room or residence but not both were specified, return error
    if any(key in data.keys() for key in ["room", "residence"]) and not all(key in data.keys() for key in ["room", "residence"]):
        response = Response(
            response=json.dumps({"error": "If room or residence is specified, both must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # search email
    if "email" in data:
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions={"email": data["email"]},
            expect_single_answer=True)

    # search room and residence
    elif "room" in data:
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions={"room": data["room"], "residence": data["residence"]},
            expect_single_answer=True)

    # search first_name and/or last_name
    else:
        conditions = {key: value for key, value in data.items() if value is not None}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            conditions=conditions,
            keywords=keywords,
            expect_single_answer=False)

    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # if data is None, set it to empty list
    if result["data"] is None:
        result["data"] = []

    users = []
    if "email" in data or "room" in data:

        email_key = "email" in data
        data = result["data"]

        if not email_key:
            # showing only a part of the email
            email = data[2]
            email = email[:2] + "*" * (re.search("@", email).start() - 2) + email[re.search("@", email).start():]
        else:
            email = data[2]

        user = {"first_name": data[0],
                "last_name": data[1],
                "email": email,
                "user_role": FrontendUserRole.EXTERN if data[3] == "extern" else FrontendUserRole.INTERN}
        users.append(user)
    else:
        for entry in result["data"]:
            # showing only a part of the email
            email = entry[2]
            email = email[:2] + "*" * (re.search("@", email).start() - 2) + email[re.search("@", email).start():]

            users.append({"first_name": entry[0],
                          "last_name": entry[1],
                          "email": email,
                          "user_role": FrontendUserRole.EXTERN if entry[3] == "extern" else FrontendUserRole.INTERN})

    response = Response(
        response=json.dumps({"users": users}),
        status=200,
        mimetype="application/json")

    return response

# TODO: change other /guests endpoint
@app.route("/guests", methods=["POST"])
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
            response=json.dumps({"error": f"The session_id, uuid, present must be specified"}),
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
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role host or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result["data"]["user_id"]
    event_type = EventType.ARRIVE if present else EventType.LEAVE

    # change guest status to arrive / leave
    result = guest_events.change_guest(connection=conn, cursor=cursor, user_uuid=user_uuid, event_type=event_type)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # find sid to skip
    result = websocket.get_sid_by_session_id(cursor=cursor, session_id=session_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    req_id = result["data"]

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified", "user_role"]
    result = users.get_user(
        cursor=cursor,
        user_id=user_id,
        keywords=keywords,
        expect_single_answer=True)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_info = {key: value for key, value in zip(keywords, result["data"])}
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
        user_data["verified"] = True if user_info["verified"] is not None else False

    message = {
        "event": "guestModified",
        "req_id": req_id,
        "data": user_data}

    action_type = Action_Type("guestArrived") if present else Action_Type("guestLeft")
    # insert into websocket_log
    result = websocket.add_websocket_event(
        connection=conn,
        cursor=cursor,
        action_type=action_type,
        user_id=user_id,
        message_content=message,
        required_role=UserRole.HOST)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # send a websocket message to all hosts that the guest list changed
    emit("guestModified", msgpack.packb(message), to=host_upwards_room, skip_sid=result["data"])

    # return 204
    response = Response(
        status=204)
    return response

@app.route("/user/stueble_signup", methods=["POST"])
def attend_stueble():
    """
    sign up for a stueble party
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    date = data.get("date", None)

    if session_id is None or date is None:
        response = Response(
            response=json.dumps({"error": f"The session_id and date must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only hosts can add guests
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.USER)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result["data"]["user_id"]
    user_uuid = result["data"]["user_uuid"]

    result = motto.get_info(cursor=cursor, date=date)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    stueble_id = result["data"][0]

    result = events.add_guest(
        connection=conn,
        cursor=cursor,
        user_id=user_id,
        stueble_id=stueble_id)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        status_code = 500
        error = str(result["error"])
        if "; code: " in str(result["error"]):
            error, status_code = str(result["error"]).split("; code: ")
            status_code = int(status_code)
        response = Response(
            response=json.dumps({"error": error}),
            status=status_code,
            mimetype="application/json")
        return response

    timestamp = int(datetime.datetime.now().timestamp())

    signature = hp.create_signature(cursor=cursor, message=json.dumps({"id": user_uuid,
                                                                       "timestamp": timestamp}))

    data = {"data":
                {"id": user_uuid,
                 "timestamp": timestamp},
            "signature": signature}

    # find sid to skip
    result = websocket.get_sid_by_session_id(cursor=cursor, session_id=session_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    req_id = result["data"]

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified"]
    result = users.get_user(
        cursor=cursor,
        user_id=user_id,
        keywords=keywords,
        expect_single_answer=True)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
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

    message = {
        "event": "guestModified",
        "req_id": req_id,
        "data": user_data}

    action_type = Action_Type("guestAdded")
    # insert into websocket_log
    result = websocket.add_websocket_event(
        connection=conn,
        cursor=cursor,
        action_type=action_type,
        user_id=user_id,
        message_content=user_data,
        required_role=UserRole.HOST)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # send a websocket message to all hosts that the guest list changed
    emit(action_type.value, msgpack.packb(message), to=host_upwards_room, skip_sid=result["data"])

    response = Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")
    return response

# NOTE: extern guest can be multiple times in table users since only first_name, last_name are specified, which are not unique
@app.route("/user/invite_friend", methods=["POST"])
@app.route("/user/invite_friend", methods=["DELETE"])
def invite_friend():
    """
    invite a friend and share a qr-code
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    date = data.get("date", None)
    invitee_first_name = data.get("inviteeFirstName", None)
    invitee_last_name = data.get("inviteeLastName", None)
    invitee_email = data.get("inviteeEmail", None)

    if any(i is None for i in [session_id,  date,  invitee_first_name,  invitee_last_name]):
        response = Response(
            response=json.dumps({
                "error": f"session_id, date, invitee_first_name, invitee_last_name, invitee_email must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only hosts can add guests
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.USER)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result["data"]["user_id"]

    result = motto.get_info(cursor=cursor, date=date)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    stueble_id = result["data"][0]

    if request.method == "POST":
        # add user to table
        result = users.add_user(
            connection=conn,
            cursor=cursor,
            user_role=UserRole.EXTERN,
            first_name=invitee_first_name,
            last_name=invitee_last_name,
            returning="id, user_uuid")

    else:
        # get user to remove
        result = user.get_user(
            cursor=cursor,
            keywords=["id", "user_uuid"],
            conditions={"first_name": invitee_first_name, "last_name": invitee_last_name, "user_role": UserRole.EXTERN.value},
            expect_single_answer=False)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    if request.method == "DELETE":
        possible_users = result["data"]
        if len(possible_users) == 0:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"error": "No such user found"}),
                status=404,
                mimetype="application/json")
            return response
        users_list = []
        for i in possible_users:
            query = """
            SELECT user_id FROM events
            WHERE user_id = %s AND stueble_id = %s AND event_type = 'add' AND invited_by = %s
            ORDER BY submitted DESC LIMIT 1"""
            result = db.custom_call(connection=None,
                                    cursor=cursor,
                                    query=query,
                                    type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
                                    variables=[i[0], stueble_id, user_id])
            if result["success"] is False:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"error": str(result["error"])}),
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
                    response=json.dumps({"error": str(result["error"])}),
                    status=500,
                    mimetype="application/json")
                return response
            if result["data"] is None:
                close_conn_cursor(conn, cursor)
                response = Response(
                    response=json.dumps({"error": "Data integrity error, user not found"}),
                    status=500,
                    mimetype="application/json")
                return response
            possible_invitee_uuid = result["data"][0]
            users_list.append({"invitee_id": possible_invitee_id, "invitee_uuid": possible_invitee_uuid})
        if len(users_list) == 0:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"error": "No such user found"}),
                status=401,
                mimetype="application/json")
            return response
        if len(users_list) > 1:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"error": "Multiple users found, please contact an admin"}),
                status=409,
                mimetype="application/json")
            return response
        invitee_id = users_list[0]["invitee_id"]
        invitee_uuid = users_list[0]["invitee_uuid"]
    else:
        invitee_id = result["data"][0]
        invitee_uuid = result["data"][1]

    if request.method == "POST":
        result = events.add_guest(
            connection=conn,
            cursor=cursor,
            user_id=invitee_id,
            stueble_id=stueble_id,
            invited_by=user_id)
    else:
        result = events.remove_guest(
            connection=conn,
            cursor=cursor,
            user_id=invitee_id,
            stueble_id=stueble_id)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        status_code = 500
        error = str(result["error"])
        if "; code: " in str(result["error"]):
            error, status_code = str(result["error"]).split("; code: ")
            status_code = int(status_code)
        response = Response(
            response=json.dumps({"error": error}),
            status=status_code,
            mimetype="application/json")
        return response

    if request.method == "POST":
        timestamp = int(datetime.datetime.now().timestamp())

        signature = hp.create_signature(cursor=cursor, message=json.dumps({"id": invitee_uuid,
                                                                "timestamp": timestamp}))

        data = {"data":
                    {"id": invitee_uuid,
                     "timestamp": timestamp},
                "signature": signature}

    # find sid to skip
    result = websocket.get_sid_by_session_id(cursor=cursor, session_id=session_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    req_id = result["data"]

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified"]
    result = users.get_user(
        cursor=cursor,
        user_id=invitee_id,
        keywords=keywords,
        expect_single_answer=True)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
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

    message = {
        "event": "guestModified",
        "req_id": req_id,
        "data": invitee_data}

    action_type = Action_Type("guestAdded") if request.method == "POST" else Action_Type("guestRemoved")

    # insert into websocket_log
    result = websocket.add_websocket_event(
        connection=conn,
        cursor=cursor,
        action_type=action_type,
        user_id=user_id,
        message_content=message,
        required_role=UserRole.HOST)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # send a websocket message to all hosts that the guest list changed
    emit(action_type.value, msgpack.packb(message), to=host_upwards_room, skip_sid=result["data"])

    if request.method == "DELETE":
        response = Response(
            status=204)
        return response

    response = Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")
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
            response=json.dumps({"error": "specify user"}),
            status=400,
            mimetype="application/json")
        return response

    value = {}
    if "@" in name:
        try:
            name = Email(email=name)
        except ValueError:
            response = Response(
                response=json.dumps({"error": "Invalid email format"}),
                status=400,
                mimetype="application/json")
            return response
        value = {"user_email": name}
    else:
        value = {"user_name": name}

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check whether user with email exists
    result = users.get_user(cursor=cursor, keywords=["id", "first_name", "last_name", "email", "password_hash"], expect_single_answer=True, **value)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "No user with the given email exists"}),
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
            response=json.dumps({"error": "User was deleted, needs to signup again."}),
            status=400,
            mimetype="application/json")
        return response

    email = Email(email=email)

    result = users.create_verification_code(connection=conn, cursor=cursor, user_id=user_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    reset_token = result["data"]

    subject = "Passwort zurücksetzen"
    body = f"""Hallo {first_name} {last_name},\n\nmit diesem Code kannst du dein Passwort zurücksetzen: {reset_token}\nFalls du keine Passwort-Zurücksetzung angefordert hast, wende dich bitte umgehend an das Tutoren-Team.\n\nViele Grüße,\nDein Stüble-Team"""

    result = gmail.send_mail(recipient=email, subject=subject, body=body)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
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
    reset_token = data.get("resetToken", None)
    new_password = data.get("newPassword", None)

    if reset_token is None or new_password is None:
        response = Response(
            response=json.dumps({"error": f"The {'reset_token' if reset_token is None else 'new_password' if new_password is None else 'reset_token and new_password'} must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    if new_password == "":
        response = Response(
            response=json.dumps({"error": "password cannot be empty"}),
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
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_id = result["data"]

    # hash new password
    hashed_password = hp.hash_pwd(new_password)

    # set new password
    result = users.update_user(connection=conn, cursor=cursor, user_id=user_id, password_hash=hashed_password)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # remove all existing sessions of the user
    result = sessions.remove_user_sessions(connection=conn, cursor=cursor, user_id=user_id)
    if result["success"] is False:
        if result["error"] != "no sessions found":
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"error": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response

    # create a new session
    result = sessions.create_session(connection=conn, cursor=cursor, user_id=user_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    session_id = result["data"]

    # return 204
    response = Response(
        status=204)

    response.set_cookie("SID",
                        session_id,
                        httponly=True,
                        secure=True,
                        samesite='Lax')
    return response

@app.route("/user/change_password", methods=["POST"])
@app.route("/user/change_username", methods=["POST"])
def change_user_data():
    """
    changes user data when logged in \n
    different from password reset, since user is logged in here
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
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
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result["data"]["user_id"]

    data = {}
    if request.path == "/user/change_password":
        new_pwd = data.get("newPassword", None)
        if new_pwd is None:
            response = Response(
                response=json.dumps({"error": "The new_password must be specified"}),
                status=400,
                mimetype="application/json")
            return response
        if new_pwd == "":
            response = Response(
                response=json.dumps({"error": "Password cannot be empty"}),
                status=400,
                mimetype="application/json")
            return response
        data["password_hash"] = hp.hash_pwd(new_pwd)
    elif request.path == "/user/change_username":
        username = data.get("userName", None)
        if username is None:
            response = Response(
                response=json.dumps({"error": f"Username must be specified"}),
                status=400,
                mimetype="application/json")
            return response
        if username == "":
            response = Response(
                response=json.dumps({"error": "Username cannot be empty"}),
                status=400,
                mimetype="application/json")
            return response
        data["user_name"] = username

    # get user id from session id
    result = users.update_user(connection=conn, cursor=cursor, session_id=session_id,
                               user_id=user_id, **data)
    close_conn_cursor(conn, cursor)
    if result["success"] is False and ("user_name" in data.keys()):
        error = result["error"]
        if f"Key (user_name)=({data['user_name']}) already exists." in error:
            response = Response(
                response=json.dumps({"error": "Username already exists"}),
                status=400,
                mimetype="application/json")
            return response
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    response = Response(
        status=204
    )
    return response

@app.route("/tutor/change_user_role", methods=["POST"])
def change_user_role():
    """
    change the user role of a user (only admin)
    """

    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only tutors or above can change user role
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.TUTOR)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role tutor or above"}),
            status=403,
            mimetype="application/json")
        return response

    # load data, part 2
    name = data.get("user", None)
    if name is None:
        response = Response(
            response=json.dumps({"error": "specify user"}),
            status=400,
            mimetype="application/json")
        return response

    value = {}
    if "@" in name:
        try:
            name = Email(email=name)
        except ValueError:
            response = Response(
                response=json.dumps({"error": "Invalid email format"}),
                status=400,
                mimetype="application/json")
            return response
        value = {"user_email": name}
    else:
        value = {"user_name": name}

    new_role = data.get("newRole", None)

    if new_role is None:
        response = Response(
            response=json.dumps({"error": "The new_role must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    if is_valid_role(new_role) is False or new_role == "admin":
        response = Response(
            response=json.dumps({"error": "The new_role must be a valid role (extern, user, host, tutor) and can't be admin"}),
            status=400,
            mimetype="application/json")
        return response

    data = value
    data["user_role"] = UserRole(new_role)

    result = users.update_user(
        connection=conn,
        cursor=cursor,
        **data)

    close_conn_cursor(conn, cursor)
    if user["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    if result["data"] is None:
        response = Response(
            response=json.dumps({"error": "No user found with the given user_id / email"}),
            status=400,
            mimetype="application/json")
        return response

    response = Response(
        status=204)
    return response

@app.route("/tutor/create_stueble", methods=["POST"])
def create_stueble():
    """
    creates a new stueble event
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only tutors or above can change user role
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.TUTOR)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role tutor or above"}),
            status=403,
            mimetype="application/json")
        return response

    # load data
    data = request.get_json()
    date = data.get("timestamp", None)
    motto = data.get("motto", None)
    hosts = data.get("hosts", None)
    shared_apartment = data.get("shared_apartment", None)

    if date is None or motto is None or hosts is None or hosts == [] or motto == "":
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "date, motto and hosts must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    try:
        date = datetime.datetime.fromtimestamp(date, tz=ZoneInfo("Europe/Berlin"))
    except ValueError:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "Invalid timestamp"}),
            status=400,
            mimetype="application/json")
        return response

    user_ids = users.get_users(cursor=cursor, information=hosts)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    if len(user_ids["data"]) != len(hosts):
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "One or more hosts not found"}),
            status=400,
            mimetype="application/json")
        return response

    result = motto.create_stueble(connection=conn,
                                  cursor=cursor,
                                  date=date,
                                  motto=motto,
                                  hosts=hosts,
                                  shared_apartment=shared_apartment)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    response = Response(
        status=204)
    return response

@socketio.on("guestVerification")
def verify_guest(msg):
    """
    sets guest verified to True
    """

    # load data
    try:
        data = msgpack.unpack(msg, raw=False)
    except Exception as e:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "500",
             "message": f"Invalid msgpack format: {str(e)}"}}, use_bin_type=True))
        return
    req_id = data.get("reqId", None)
    if req_id is None:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "401",
             "message": "req_id must be specified"}}, use_bin_type=True))
        return
    user_data = data.get("data", None)
    if user_data is None:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "400",
             "message": "data must be specified"}}, use_bin_type=True))
        return
    user_uuid = data.get("id", None)
    verification_method = data.get("method", None)
    session_id = request.cookies.get("SID", None)

    if session_id is None:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "400",
             "message": "missing cookie"}}, use_bin_type=True))
        return

    if user_uuid is None or verification_method is None:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "400",
             "message": "id and method must be specified"}}, use_bin_type=True))
        return

    if not valid_verification_method(verification_method) or verification_method == "kolping":
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "400",
             "message": "invalid verification method"}}, use_bin_type=True))
        return

    verification_method = VerificationMethod(verification_method)

    # get connection, cursor
    conn, cursor = get_conn_cursor()

    # check permissions
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "401",
             "message": str(result["error"])}}, use_bin_type=True))
        return
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "403",
             "message": "invalid permissions, need role host or above"}}, use_bin_type=True))
        return

    result = users.add_verification_method(connection=conn, cursor=cursor, user_uuid=user_uuid, method=verification_method)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "500",
             "message": str(result["error"])}}, use_bin_type=True))
        return

    emit("guestVerification", msgpack.packb({"event": "guestVerification"}, use_bin_type=True))

    emit("guestVerified", msgpack.packb({
        "event": "guestVerified",
        "req_id": req_id,
        "data": user_data
    }, use_bin_type=True), to=host_upwards_room, skip_sid=request.sid)
    return

@socketio.on("connect")
def handle_connect():
    """
    handle a new websocket connection
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        emit("error",
             msgpack.packb({
                 "event": "error",
                 "data": {
                     "code": "401",
                     "message": "missing SID cookie"}
             }, use_bin_type=True))
        return

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)

    close_conn_cursor(conn, cursor)
    if result["success"] is False and result["error"] == "no matching session and user found":
        emit("status",
             msgpack.packb({
                 "event": "status",
                 "data": {"code": "200",
                          "capabilities": [],
                          "authorized": False}}, use_bin_type=True))

    if result["success"] is False:
        emit("error",
             msgpack.packb({
                 "event": "error",
                 "data": {
                     "code": "500",
                     "message": str(result["error"])}
             }, use_bin_type=True))
        return

    capabilities = [i.value for i in get_leq_roles(result["data"]["role"]) if i.value in ["host", "tutor", "admin"]]

    if result["data"]["allowed"] is False:
        emit("status",
             msgpack.packb({
                 "event": "error",
                 "data": {
                     "code": "200",
                     "capabilities": capabilities,
                     "authorized": True}
             }, use_bin_type=True))
        return

    if result["data"]["allowed"] is True:
        user_role = result["data"]["user_role"]
        user_role = UserRole(user_role)

        # get connection, cursor
        conn, cursor = get_conn_cursor()

        result = websocket.add_websocket_sid(
            connection=conn,
            cursor=cursor,
            session_id=session_id,
            sid=request.sid)

        close_conn_cursor(conn, cursor)
        if result["success"] is False:
            emit("status",
                 msgpack.packb({
                     "event": "status",
                     "data": {
                         "authorized": False,
                         "capabilities": [],
                         "status_code": "500",
                         "error": str(result["error"])}
                 }, use_bin_type=True))
            return

        join_room(room=host_upwards_room)

        # can only be "authorized": True but still checking
        emit("status", msgpack.packb({
            "event": "status",
            "data": {
                "authorized": True if user_role >= UserRole.HOST else False,
                "capabilities": capabilities,
                "status_code": "200"
            }}, use_bin_type=True))
        return

@socketio.on("disconnect")
def handle_disconnect():
    """
    handle a websocket disconnection
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        return

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        return
    if result["data"]["allowed"] is False:
        return

    # get connection, cursor
    conn, cursor = get_conn_cursor()

    result = websocket.remove_websocket_sid(
        connection=conn,
        cursor=cursor,
        sid=request.sid)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        return

    leave_room(room=host_upwards_room)
    return

@socketio.on("ping")
def handle_ping(msg):
    """
    handle a ping from the client
    """
    try:
        data = msgpack.unpack(msg, raw=False)
    except Exception as e:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "500",
             "message": f"Invalid msgpack format: {str(e)}"}}, use_bin_type=True))
        return

    req_id = data.get("reqId", None)

    if req_id is None:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "401",
             "message": f"The req_id must be specified"}}, use_bin_type=True))
        return

    emit("pong", msgpack.packb({"event": "pong", "req_id": req_id}, use_bin_type=True))
    return

@socketio.on("heartbeat")
def handle_heartbeat():
    """
    handle a heartbeat from the client
    """

    # get connection, cursor
    conn, cursor = get_conn_cursor()

    emit("heartbeat", msgpack.packb({"event": "heartbeat"}, use_bin_type=True))
    return

@socketio.on("requestQRCode")
def get_qrcode(msg):
    """
    get a new qr-code for a guest

    Parameters:
        msg (bytes): msgpack packed data containing:
            - reqId (str): request id to identify the request
            - data (dict): data containing:
                - id (uuid): user_uuid
    """
    try:
        data = msgpack.unpack(msg, raw=False)
    except Exception as e:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "500",
             "message": f"Invalid msgpack format: {str(e)}"}}, use_bin_type=True))
        return
    user_uuid = data.get("id", None)
    req_id = data.get("reqId", None)
    if req_id is None or user_uuid is None:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "401",
             "message": "reqId and id must be specified"}}, use_bin_type=True))
        return

    stueble_id = data.get("stuebleId", None)

    # get connection, cursor
    conn, cursor = get_conn_cursor()

    result = events.check_guest(cursor=cursor,
                                user_uuid=user_uuid,
                                stueble_id=stueble_id)
    if result["success"] is False:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "500",
             "message": str(result["error"])}}, use_bin_type=True))
        return

    if result["data"] is False:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "401",
             "message": "Guest not on guest_list"}}, use_bin_type=True))
        return

    timestamp = int(datetime.datetime.now().timestamp())

    signature = hp.create_signature(cursor=cursor, message=json.dumps({"id": user_uuid,
                                                                       "timestamp": timestamp}))

    data = {"data":
                {"id": user_uuid,
                 "timestamp": timestamp},
            "signature": signature}

    emit("requestQRCode", msgpack.packb({"event": "requestQRCode",
                                        "req_id": req_id,
                                        "data": data}, use_bin_type=True))
    return

@socketio.on("requestPublicKey")
def get_public_key(msg):
    """
    sends the public key
    """

    # get connection, cursor
    conn, cursor = get_conn_cursor()

    result = configs.get_configuration(cursor=cursor, key="public_key")
    if result["success"] is False:
        emit("error", msgpack.packb({"event": "error", "data":
            {"code": "500",
             "message": str(result["error"])}}, use_bin_type=True))
        return

    pem_public = result["data"]
    jwk_public = jwk.JWK(kty='OKP', crv='Ed25519', x=pem_public.hex())
    jwk_public_json = jwk_public.export(private_key=False)

    emit("publicKey", msgpack.packb({"event": "requestPublicKey", "data": {
        "publicKey": jwk_public_json
    }}, use_bin_type=True))
    return

@app.route("/websocket_local", methods=["POST"])
def websocket_change():
    """
    receive data from websocket_runner and send it to all connected clients
    """

    if request.remote_addr != "127.0.0.1":
        response = Response(
            response=json.dumps({"error": "Unauthorized, only local requests are allowed"}),
            status=401,
            mimetype="application/json")
        return response

    # load data
    data = request.get_json()
    first_name = data.get("firstName", None)
    last_name = data.get("lastName", None)
    personal_hash = data.get("personalHash", None)
    stueble_id = data.get("stuebleId", None)
    event = data.get("event", None)
    if first_name is None or last_name is None or event is None:
        response = Response(
            response=json.dumps({"error": f"first_name, last_name and event must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    emit("guest_list_update", msgpack.packb({"payload": {"first_name": first_name, "last_name": last_name, "event": event}}, use_bin_type=True))

    response = Response(
        status=200)
    return response

# TODO: remove this after debugging
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000)
