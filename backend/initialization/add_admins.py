from backend.sql_connection import database as db
from backend import hash_pwd

conn, cursor = db.connect()
password_hes = hash_pwd.hash_pwd("tutorenhes2025")
password_hirte = hash_pwd.hash_pwd("tutorenhirte2025")
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