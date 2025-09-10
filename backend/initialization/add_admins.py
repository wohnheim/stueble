from backend.sql_connection import database as db
from backend import hash_pwd
import os

pwd_hes = os.getenv("ADMIN_PASSWORD_HES")
pwd_hirte = os.getenv("ADMIN_PASSWORD_HIRTE")

if not pwd_hes:
    raise Exception("Please set pwd_hes")
if not pwd_hirte:
    raise Exception("Please set pwd_hirte")

conn, cursor = db.connect()
password_hes = hash_pwd.hash_pwd(pwd_hes)
password_hirte = hash_pwd.hash_pwd(pwd_hirte)
result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="users",
    arguments={"user_role":"admin",  "room": 0, "residence": "altbau", "first_name": "Altbau", "last_name": "Admin", "email": "tutorenhes@gmail.com", "user_name": "admin altbau", "password_hash": password_hes},
    returning_column="id")
if result["success"] is False:
    raise result["error"]

result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="users",
    arguments={"user_role":"admin",  "room": 0, "residence": "hirte", "first_name": "Hirte", "last_name": "Admin", "email": "tutorenhirte@gmail.com", "user_name": "admin hirte", "password_hash": password_hirte},
    returning_column="id")

if result["success"] is False:
    raise result["error"]

print("Admin users added.")