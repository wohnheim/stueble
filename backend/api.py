from flask import Flask
import json
import sql_connection.database as db
import sql_connection.common_functions as cf

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

    # if data is not valid return error
    if email is None or password is None:
        return jsonify("error": "specify email and password"), 401
    
    # get connection and cursor
    conn, cursor = get_conn_cursor()

    cf.get_user()


    # close cursor and return connection
    close_conn_cursor(conn, cursor)


app.route("/auth/signup")
def signup():
    """
    """

app.route("/auth/logout")
def logout():
    """
    """

app.route("/auth/delete")
def delete():
    """
    """

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
