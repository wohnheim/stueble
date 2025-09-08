from flask import Flask, request, Response, send_file
from flask_socketio import SocketIO, emit
import json
from backend.sql_connection import (
    users,
    sessions,
    motto,
    guest_events as guests,
    configs,
    websocket,
    signup_validation as signup_val,
    stueble_codes as codes,
    database as db)
import backend.hash_pwd as hp
from backend.data_types import *
import backend.qr_code as qr
from backend.google_functions import gmail
import re

# TODO code isn't written nicely, e.g. in logout and delete there are big code overlaps
# TODO always close connection after last request
# NOTE frontend barely ever gets the real user role, rather just gets intern / extern
# Initialize connections to database
pool = db.create_pool()

# initialize flask app
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.pool = pool

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
    if user_role >= required_role:
        return {"success": True, "data": {"allowed": True, "user_id": user_id, "user_role": user_role}}
    return {"success": True, "data": {"allowed": False, "user_id": user_id, "user_role": user_role}}

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

@app.route("/auth/login", methods=["POST"])
def login():
    """
    checks, whether a user exists and whether user is logged in (if exists and not logged in, session is created)
    """
    
    # load data
    data = request.get_json()
    email = data.get("email", None)
    user_name = data.get("user_name", None)
    password = data.get("password", None)

    # password can't be empty
    if password == "":
        response = Response(
            response=json.dumps({"error": "password cannot be empty"}),
            status=401,
            mimetype="application/json")
        return response

    if (user_name is None and email is None) or (user_name is not None and email is not None):
        response = Response(
            response=json.dumps({"error": "specify either email or user_name, but not both"}),
            status=400,
            mimetype="application/json")
        return response

    value = {}

    # if the email is in wrong format, return error
    if email is not None:
        try:
            email = Email(email)
            value = {"email": email}
        except ValueError:
            response = Response(
                response=json.dumps({"error": "invalid email format"}),
                status=401,
                mimetype="application/json")
            return response
    else:
        value = {"user_name": user_name}
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

    # return 200
    response = Response(
        response=json.dumps({"session_id": session_id}),
        status=200,
        mimetype="application/json")
    return response

@app.route("/auth/signup", methods=["POST"])
def signup():
    """
    create a new user
    """
    # load data
    data = request.get_json()

    # initialize user_info
    user_info = {}
    user_info["room"] = data.get("room", None)
    user_info["residence"] = data.get("residence", None)
    user_info["first_name"] = data.get("first_name", None)
    user_info["last_name"] = data.get("last_name", None)
    user_info["email"] = data.get("email", None)
    user_info["user_name"] = data.get("user_name", None)
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

    # add user to table
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

    close_conn_cursor(conn, cursor) # close conn, cursor
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    session_id = result["data"]

    # return 200
    response = Response(
        response=json.dumps({"session_id": session_id}),
        status=200,
        mimetype="application/json")
    return response

@app.route("/auth/logout", methods=["POST"])
def logout():
    """
    removes the session id
    """

    # load data
    data = request.get_json()
    session_id = data.get("session_id", None)
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

    # load data
    data = request.get_json()
    session_id = data.get("session_id", None)
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

    # return 204
    response = Response(
        status=204)
    return response

# NOTE: this endpoint is public, since the motto is also shown on the website without logging in
@app.route("/motto", methods=["GET"])
def get_motto():
    """
    returns the motto for the next stueble party
    """

    # load data
    data = request.get_json()
    date = data.get("date", None)

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

@app.route("/guests", methods=["POST"])
def guests():
    """
    returns list of all guests
    """

    # load data
    data = request.get_json()
    session_id = data.get("session_id", None)
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
    result = guests.guest_list(cursor=cursor)
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

@app.route("/user")
def user():
    """
    return data to user
    """

    # load data
    data = request.get_json()
    session_id = data.get("session_id", None)
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
    user = {"first_name": data[0],
            "last_name": data[1],
            "room": data[2],
            "residence": data[3],
            "email": data[4],
            "user_role": UserRole(data[5])}

    response = Response(
        response=json.dumps(user),
        status=200,
        mimetype="application/json")
    return response

@app.route("/host/search_guest")
def search():
    """
    search for a guest \n
    allowed keys for searching are first_name, last_name, email, (room, residence)
    """
    # load data
    data = request.get_json()

    session_id = data.get("session_id", None)
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
            keywords=keywords,
            conditions={"email": data["email"]},
            expect_single_answer=True)

    # search room and residence
    elif "room" in data:
        result = db.read_table(
            cursor=cursor,
            keywords=keywords,
            conditions={"room": data["room"], "residence": data["residence"]},
            expect_single_answer=True)

    # search first_name and/or last_name
    else:
        conditions = {key: value for key, value in data.items() if value is not None}
        result = db.read_table(
            cursor=cursor,
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
    if "email" in result["data"]:
        # showing only a part of the email
        email = data[2]
        email = email[:2] + "*" * (re.search("@", email).start() - 2) + email[re.search("@", email).start():]

        data = result["data"]
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

@app.route("/host/add_guest", methods=["POST"])
@app.route("/host/remove_guest", methods=["POST"])
def guest_change():
    """
    add / remove a guest to the guest_list of present people
    """

    # load data
    data = request.get_json()
    session_id = data.get("session_id", None)
    guest_stueble_code = data.get("guest_stueble_code", None)

    if session_id is None or guest_stueble_code is None:
        response = Response(
            response=json.dumps({"error": f"The {'session_id' if session_id is None else 'guest_stueble_code' if guest_stueble_code is None else 'session_id and guest_stueble_id'} must be specified"}),
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

    event_type = EventType.ARRIVE if request.path == "/host/add_guest" else EventType.LEAVE if request.path == "/host/remove_guest" else None

    # can't occur, for security reasons still checked
    if event_type is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "invalid path"}),
            status=500,
            mimetype="application/json")
        return response

    # change guest status to arrive / leave
    result = guests.change_guest(connection=conn, cursor=cursor, stueble_code=guest_stueble_code, event_type=event_type)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    # return 204
    response = Response(
        status=204)
    return response

@app.route("/user/invite_friend", methods=["POST"])
def invite_friend():
    """
    invite a friend and share a qr-code
    """

    # load data
    data = request.get_json()
    session_id = data.get("session_id", None)
    guest_stueble_code = data.get("guest_stueble_code", None)

    if session_id is None or guest_stueble_code is None:
        response = Response(
            response=json.dumps({
                "error": f"The {'session_id' if session_id is None else 'guest_stueble_code' if guest_stueble_code is None else 'session_id and guest_stueble_id'} must be specified"}),
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

    result = motto.get_info(cursor=cursor)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    stueble_id = result["data"][0]

    result = users.get_invited_friends(cursor=cursor, user_id=user_id, stueble_id=stueble_id)

    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    friends = result["data"]

    result = configs.get_configuration(cursor=cursor, key="maximum_invites_per_user")
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json"
        )
        return response

    max_invites = int(result["data"])

    if len(friends) >= max_invites:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "maximum number of invites already reached"}),
            status=403,
            mimetype="application/json"
        )
        return response

    result = codes.add_guest(
        connection=conn,
        cursor=cursor,
        user_id=user_id,
        stueble_id=stueble_id)

    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    code = result["data"]

    try:
        qr_code = qr.generate(code=code)
    except Exception as e:
        response = Response(
            response=json.dumps({"error": e}),
            status=500,
            mimetype="application/json"
        )
        return  response

    return send_file(qr_code, mimetype="image/png")

@app.route("/auth/reset_password", methods=["POST"])
def reset_password_mail():
    """
    reset password of a user
    """

    # load data
    data = request.get_json()
    email = data.get("email", None)
    user_name = data.get("user_name", None)

    if email is None and user_name is None:
        response = Response(
            response=json.dumps({"error": "Either email or username must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    if email is not None:
        try:
            email = Email(email=email)
        except ValueError:
            response = Response(
                response=json.dumps({"error": "Invalid email format"}),
                status=400,
                mimetype="application/json")
            return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    value = {"user_email": email} if email is not None else {"user_name": user_name}

    # check whether user with email exists
    result = users.get_user(cursor=cursor, keywords=["id", "first_name", "last_name", "email"], expect_single_answer=True, **value)
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

    email = Email(email=email)

    result = users.create_password_reset_code(connection=conn, cursor=cursor, user_id=user_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response
    reset_token = result["data"]

    subject = "Passwort zurücksetzen"
    body = f"""Hallo {first_name} {last_name},\nMit diesem Code kannst du dein Passwort zurücksetzen: {reset_token}.\nFalls du keine Passwort-Zurücksetzung angefordert hast, wende dich bitte umgehend an das Tutoren-Team.\n\nViele Grüße,\nDein Stüble-Team"""

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
    reset_token = data.get("reset_token", None)
    new_password = data.get("new_password", None)

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
    result = users.confirm_reset_code(cursor=cursor, reset_code=reset_token)
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

    # return 200
    response = Response(
        response=json.dumps({"session_id": session_id}),
        status=200,
        mimetype="application/json")
    return response

@app.route("/user/change_password", methods=["POST"])
@app.route("/user/change_username", methods=["POST"])
def change_user_data():
    """
    changes user data when logged in \n
    different from password reset, since user is logged in here
    """

    # load data
    data = request.get_json()
    session_id = data.get("session_id", None)
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
        new_pwd = data.get("new_password", None)
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
        username = data.get("user_name", None)
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

@app.route("/admin/change_user_role", methods=["POST"])
def change_user_role():
    """
    change the user role of a user (only admin)
    """

    # load data, part 1
    data = request.get_json()
    session_id = data.get("session_id", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions, since only admins can change user role
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.ADMIN)
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
            response=json.dumps({"error": "invalid permissions, need role admin"}),
            status=403,
            mimetype="application/json")
        return response

    # load data, part 2
    user_id = data.get("user_id", None)
    user_email = data.get("user_email", None)
    new_role = data.get("new_role", None)
    if user_id is None and user_email is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "Either user_id or user_email must be specified, do not specify both."}),
            status=400,
            mimetype="application/json")
        return response

    if user_id is None and user_email is not None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "Specify either user_id or email, but not both."}),
            status=400,
            mimetype="application/json")
        return response

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

    if user_email is not None:
        try:
            user_email = Email(user_email)
        except ValueError:
            response = Response(
                response=json.dumps({"error": "The email is not valid"}),
                status=400,
                mimetype="application/json")
            return response

    data = {"id": user_id} if user_id is not None else {"email": user_email}
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

@socketio.on("connect")
def handle_connect():
    """
    handle a new websocket connection
    """

    data = request.get_json()
    session_id = data.get("session_id", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"error": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=401,
            mimetype="application/json")
        return response
    if result["data"]["allowed"] is False:
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role host or above"}),
            status=403,
            mimetype="application/json")
        return response

    if result["data"]["allowed"] is False:
        response = Response(
            response=json.dumps({"error": "invalid permissions, need role host or above"}),
            status=403,
            mimetype="application/json")
        return response

    result = websocket.get_websocket_sids(cursor)
    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    result = websocket.add_websocket_sid(
        cursor=cursor,
        connection=conn,
        sid=request.sid,
        user_id=result["data"]["user_id"],
        session_id=session_id)

    if result["success"] is False:
        response = Response(
            response=json.dumps({"error": str(result["error"])}),
            status=500,
            mimetype="application/json")
        return response

    emit("connected", {"message": "connected to websocket", "sid": request.sid})

    response = Response(
        status=200)
    return response

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
    first_name = data.get("first_name", None)
    last_name = data.get("last_name", None)
    personal_hash = data.get("personal_hash", None)
    stueble_id = data.get("stueble_id", None)
    event = data.get("event", None)
    if first_name is None or last_name is None or event is None:
        response = Response(
            response=json.dumps({"error": f"first_name, last_name and event must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    emit("guest_list_update", {"payload": {"first_name": first_name, "last_name": last_name, "event": event}})

    response = Response(
        status=200)
    return response

if __name__ == "__main__":
    socketio.run(app)