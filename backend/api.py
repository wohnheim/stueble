from flask import Flask
import json
import sql_connection.database as db

# Initialize connections to database
pool = db.create_pool()

# initialize flask app
app = Flask(__name__)
app.pool = pool

app.route("/auth/login")
def login():
    """
    """
    

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
