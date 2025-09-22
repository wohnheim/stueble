import datetime
from zoneinfo import ZoneInfo

from flask import Flask, request, Response
import json

from packages.backend.data_types import *
from packages.backend.sql_connection.common_functions import *
from packages.backend.sql_connection.ultimate_functions import *
from packages.backend.sql_connection import (
    users,
    sessions,
    motto,
    guest_events,
    configs,
    events,
    database as db, signup_validation as signup_val)
from packages.backend import hash_pwd as hp, websocket as ws
from packages.backend.google_functions import gmail
import re
import asyncio
from packages.backend.sql_connection.conn_cursor_functions import *

# NOTE frontend barely ever gets the real user role, rather just gets intern / extern
# Initialize connections to database

# initialize flask app
app = Flask(__name__)

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
            response=json.dumps({"code": 401, "message": "password cannot be empty"}),
            status=401,
            mimetype="application/json")
        return response

    if name is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "specify user"}),
            status=400,
            mimetype="application/json")
        return response

    value = {}
    if "@" in name:
        try:
            name = Email(email=name)
        except ValueError:
            response = Response(
                response=json.dumps({"code": 400, "message": "Invalid email format"}),
                status=400,
                mimetype="application/json")
            return response
        value = {"user_email": name}
    else:
        value = {"user_name": name}

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
    result = users.get_user(cursor=cursor, keywords=["id", "password_hash", "user_role"], expect_single_answer=True, **value)

    # return error
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
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
    result = sessions.create_session(connection=conn, cursor=cursor, user_id=user[0])

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
    result = signup_val.validate_user_data(cursor=cursor, **check_info)
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

    result = users.create_verification_code(connection=conn, cursor=cursor, user_id=None, additional_data=additional_data)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    verification_token = result["data"]

    subject = "Neuer Benutzeraccount für das Stüble"
    body = f"""Hallo {user_info["first_name"]} {user_info["last_name"]},\n\nklicke diesen Link, um deinen Account zu bestätigen:\n\nhttps://stueble.pages.dev/verify?token={verification_token}\n\nFalls du keinen neuen Account erstellt hast, wende dich bitte umgehend an das Tutoren-Team.\n\nViele Grüße,\nDein Stüble-Team"""

    result = gmail.send_mail(recipient=user_info["email"], subject=subject, body=body)

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
    close_conn_cursor(conn, cursor)
    # if server error occurred, return error
    if result["success"] is False:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    user_id = result["data"]

    # create a new session
    result = sessions.create_session(connection=conn, cursor=cursor, user_id=user_id)

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
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
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
            response=json.dumps({"code": 401, "message": str(result["error"])}),
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
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
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
    result = users.remove_user(connection=conn, cursor=cursor, user_id=user_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # remove session from table
    result = sessions.remove_session(connection=conn, cursor=cursor, session_id=session_id)
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

# NOTE: if no stueble is happening today or yesterday, an empty list is returned
@app.route("/guests", methods=["GET"])
def guests():
    """
    returns list of all guests
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
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

@app.route("/user", methods=["GET"])
def user():
    """
    return data to user
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "The session_id must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user id from session id
    result = sessions.get_user(cursor=cursor, session_id=session_id, keywords=["first_name", "last_name", "room", "residence", "email", "user_uuid", "user_name", "id"])
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    data = result["data"]
    # extract and remove user_id
    user_id = data[-1]
    del data[-1] # deletion is unnecessary

    # check, whether user is guest for the next stueble
    result = users.check_user_guest_list(cursor=cursor, user_id=user_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    is_guest = result["data"]

    # initialize user
    user = {"firstName": data[0],
            "lastName": data[1],
            "roomNumber": data[2],
            "residence": data[3],
            "email": data[4],
            "id": data[5], 
            "username": data[6], 
            "registered": is_guest}

    response = Response(
        response=json.dumps(user),
        status=200,
        mimetype="application/json")
    return response

@app.route("/user/search", methods=["GET"])
def search_intern():
    """
    search for a guest \n
    allowed keys for searching are first_name, last_name, email, (room, residence), user_uuid
    """

    # load data
    data = request.get_json()

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "The session_id must be specified"}),
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
    allowed_keys = ["first_name", "last_name", "room_number", "residence", "email", "id", "username"]

    # if no key was specified return error
    if any(key not in allowed_keys for key in data.keys()):
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 400, "message": f"Only the following keys are allowed: {', '.join(allowed_keys)}"}),
            status=400,
            mimetype="application/json")
        return response
    
    keywords = ["first_name", "last_name", "id"]
    if "username" in data:
        conditions = {"user_name": f"{data["username"]} AND user_role != USER_ROLE.EXTERN"}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            expect_single_answer=True)

    # search room and / or residence
    elif "room" in data or "residence" in data:
        conditions = [(key, value) for key, value in data.items() if key in ["room", "residence"]]
        conditions[-1] = conditions[-1] + " AND user_role != USER_ROLE.EXTERN"
        conditions = dict(conditions)
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            expect_single_answer=True)
    
    # search user_uuid
    elif "id" in data:
        conditions = {"user_uuid": f"{data["id"]} AND user_role != USER_ROLE.EXTERN"}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            expect_single_answer=True)

    # search email
    elif "email" in data:
        conditions = {"email": f"{data["email"]} AND user_role != USER_ROLE.EXTERN"}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            keywords=keywords,
            conditions=conditions,
            expect_single_answer=True)
        
    # search first_name and/or last_name
    else:
        conditions = {key: value if index != (len(data.keys())-1) else f"{value} AND user_role != USER_ROLE.EXTERN" for index, (key, value) in enumerate(data.items()) if value is not None}
        result = db.read_table(
            cursor=cursor,
            table_name="users",
            conditions=conditions,
            keywords=keywords,
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

    response = Response(
        response=json.dumps({"users": users}),
        status=200,
        mimetype="application/json")

    return response

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
            response=json.dumps({"code": 401, "message": f"The session_id, uuid, present must be specified"}),
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
            result = users.update_user(connection=conn, 
                                       cursor=cursor, 
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
    result = guest_events.change_guest(connection=conn, cursor=cursor, user_uuid=user_uuid, event_type=event_type)
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

    # return 204
    response = Response(
        status=204)
    return response

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
            response=json.dumps({"code": 401, "message": f"The session_id and date must be specified"}),
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
            connection=conn,
            cursor=cursor,
            user_id=user_id,
            stueble_id=stueble_id)
    else:
        result = events.remove_guest(
            connection=conn,
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

        signature = hp.create_signature(message={"id": user_uuid, "timestamp": timestamp})

        data = {"data":
                    {"id": user_uuid,
                    "timestamp": timestamp},
                "signature": signature}

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
    asyncio.run(ws.send(event=action_type.value, data=user_data, skip_sid=session_id))

    response = Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")
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

    # TODO: make date optional

    if any(i is None for i in [session_id,  date,  invitee_first_name,  invitee_last_name,  invitee_email]):
        response = Response(
            response=json.dumps({"code": 401,
                "message": f"session_id, date, invitee_first_name, invitee_last_name, invitee_email must be specified"}),
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
        # add user to table
        result = users.add_user(
            connection=conn,
            cursor=cursor,
            user_role=UserRole.EXTERN,
            first_name=invitee_first_name,
            last_name=invitee_last_name,
            returning="id, user_uuid") # id, user_uuid on purpose like that

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
            result = db.custom_call(connection=None,
                                    cursor=cursor,
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

        signature = hp.create_signature(message={"id": invitee_uuid, "timestamp": timestamp})

        data = {"data":
                    {"id": invitee_uuid,
                     "timestamp": timestamp},
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
    asyncio.run(ws.send(event=action_type.value, data=invitee_data, skip_sid=session_id))

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
            response=json.dumps({"code": 400, "message": "specify user"}),
            status=400,
            mimetype="application/json")
        return response

    value = {}
    if "@" in name:
        try:
            name = Email(email=name)
        except ValueError:
            response = Response(
                response=json.dumps({"code": 403, "message": "Invalid email format"}),
                status=403,
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

    result = users.create_verification_code(connection=conn, cursor=cursor, user_id=user_id)
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

    result = gmail.send_mail(recipient=email, subject=subject, body=body)
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
    result = users.update_user(connection=conn, cursor=cursor, user_id=user_id, password_hash=hashed_password)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 500, "message": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # remove all existing sessions of the user
    result = sessions.remove_user_sessions(connection=conn, cursor=cursor, user_id=user_id)
    if result["success"] is False:
        if result["error"] != "no sessions found":
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response

    # create a new session
    result = sessions.create_session(connection=conn, cursor=cursor, user_id=user_id)
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
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
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
    result = users.update_user(connection=conn, cursor=cursor, session_id=session_id,
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
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response
    user_uuid = data.get("id", None)
    new_role = data.get("role", None)
    if new_role is None or is_valid_role(new_role) is False or new_role == "admin":
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 400, "message": "The new_role must be specified and needs to be valid and can't be admin"}),
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

    data = {}
    data["user_role"] = UserRole(new_role)

    result = users.update_user(
        connection=conn,
        cursor=cursor,
        user_uuid=user_uuid,
        **data)

    close_conn_cursor(conn, cursor)
    if user["success"] is False:
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

    response = Response(
        status=204)
    return response

@app.route("/motto", methods=["POST"])
def create_stueble():
    """
    creates a new stueble event
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
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

    # load data
    data = request.get_json()
    date = data.get("date", None)
    stueble_motto = data.get("motto", None)
    hosts = data.get("hosts", None)
    shared_apartment = data.get("shared_apartment", None)

    if stueble_motto is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 400, "message": "motto must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    if date is None:
        date = datetime.date.today()
        days_ahead = (2 - date.weekday() + 7) % 7
        date = date + datetime.timedelta(days=days_ahead)

    if hosts is not None and hosts != []:
        user_ids = users.get_users(cursor=cursor, information=hosts)
        if result["success"] is False:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
        if len(user_ids["data"]) != len(hosts):
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 400, "message": "One or more hosts not found"}),
                status=400,
                mimetype="application/json")
            return response
    result = motto.update_stueble(connection=conn,
                                cursor=cursor,
                                date=date,
                                motto=stueble_motto,
                                hosts=hosts,
                                shared_apartment=shared_apartment)
    if result["success"] is False:
        if result["error"] == "no stueble found":
            result = motto.create_stueble(connection=conn,
                                    cursor=cursor,
                                    date=date,
                                    motto=stueble_motto,
                                    hosts=hosts,
                                    shared_apartment=shared_apartment)
            if result["success"] is False:
                result = motto.create_stueble(connection=conn,
                                    cursor=cursor,
                                    date=date,
                                    motto=stueble_motto,
                                    hosts=hosts,
                                    shared_apartment=shared_apartment)
        else:
            close_conn_cursor(conn, cursor)
            response = Response(
                response=json.dumps({"code": 500, "message": str(result["error"])}),
                status=500,
                mimetype="application/json")
            return response
    close_conn_cursor(conn, cursor)
    response = Response(
        status=204)
    return response

@app.route("/hosts", methods=["PUT", "DELETE"])
def update_hosts():
    """
    Update hosts for a stueble.
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
    user_uuids = data.get("hosts", None)

    if not user_uuids:
        response = Response(
            response=json.dumps({"code": 403, "message": "hosts must be specified"}),
            status=403,
            mimetype="application/json")
        return response
    
    # get conn, cursor
    conn, cursor = db.get_conn_cursor()

    # check permissions, since only tutors or above can change user role
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.TUTOR)
    if result["success"] is False:
        db.close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 401, "message": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        db.close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor or above"}),
            status=403,
            mimetype="application/json")
        return response
    
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
                response=json.dumps({"code": 404, "message": "no stueble party found"}),
                status=404,
                mimetype="application/json")
            return response
        stueble_id = result["data"][2]

    result = motto.update_hosts(connection=conn,
                                cursor=cursor,
                                stueble_id=stueble_id,
                                user_uuids=user_uuids, 
                                method="add" if request.method == "PUT" else "remove")

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
# TODO update host room and send websocket message

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