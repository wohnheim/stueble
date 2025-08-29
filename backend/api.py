from flask import Flask, request, jsonify, Response
import json
from backend.sql_connection import users, sessions, database as db
import backend.hash_pwd as hp

# TODO make sure that change password doesn't allow an empty password, since that would delete the user

# Initialize connections to database
pool = db.create_pool()

# initialize flask app
app = Flask(__name__)
app.pool = pool

def get_conn_cursor():
    conn = app.pool.getconn()
    cursor = conn.cursor()
    return conn, cursor

def close_conn_cursor(connection, cursor):
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
    password = data.get("password", None)
    if password == "":
        response = Response(
            response=json.dumps({"error": "password cannot be empty"}),
            status=401,
            mimetype="application/json")
        return response

    # if data is not valid return error
    if email is None or password is None:
        response = Response(
            response=json.dumps({"error": "specify email and password"}),
            status=401,
            mimetype="application/json")
        return response
    
    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # get user data from table
    result = users.get_user(cursor=cursor, user_email=email, keywords=["id", "password_hash", "user_role"], expect_single_answer=True)

    # return error
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": result["error"]}),
            status=401,
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
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": result["error"]}), 
            status=500, 
            mimetype="application/json")
        return response
    
    session_id = result["data"]

    # close cursor and return connection
    close_conn_cursor(conn, cursor)

    # return 200
    response = Response(
        response=json.dumps({"session_id": session_id}),
        status=200,
        mimetype="application/json")
    return response

app.route("/auth/signup")
def signup():
    """
    """

app.route("/auth/logout")
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

    # if nothing could be removed, return error
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": result["error"]}),
            status=401,
            mimetype="application/json")
        return response
    
    # return 204
    response = Response(
        status=204)
    return response



app.route("/auth/delete")
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
    result = sessions.get_session(cursor=cursor, session_id=session_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": result["error"]}),
            status=401,
            mimetype="application/json")
        return response

    # if no session found return error
    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "no session found"}),
            status=401,
            mimetype="application/json")
        return response

    # set user_id
    user_id = result["data"]

    # remove user from table
    result = users.remove_user(connection=conn, cursor=cursor, user_id=user_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": result["error"]}),
            status=500,
            mimetype="application/json")
        return response

    # if no user found return error
    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "no user found"}),
            status=500,
            mimetype="application/json")
        return response

    # remove session from table
    result = sessions.remove_session(connection=conn, cursor=cursor, session_id=session_id)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": result["error"]}),
            status=500,
            mimetype="application/json")
        return response

    # if no session found return error
    if result["data"] is None:
        close_conn_cursor(conn, cursor)
        response = Response(
            response=json.dumps({"error": "no session found"}),
            status=500,
            mimetype="application/json")
        return response

    # close cursor and return connection
    close_conn_cursor(conn, cursor)

    # return 204
    response = Response(
        status=204)
    return response
    

app.route("/guests")
def guests():
    """
    """

app.route("/websocket")
def websocket():
    """
    """

app.route("/user")
def user():
    """
    """

app.route("/user/search")
def search():
    """
    """
