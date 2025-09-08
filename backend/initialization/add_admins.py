from backend.sql_connection import database as db

conn, cursor = db.connect()

result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="users",
    arguments={"user_role":"admin",  "room": 0, "residence": "altbau", "first_name": "Altbau", "last_name": "Admin", "email": "tutorenhes@gmail.com", "user_name": "admin altbau", "password_hash": "tutorenhes2025"},
    returning_column="id")
if result["success"] is False:
    raise result["error"]

result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="users",
    arguments={"user_role":"admin",  "room": 0, "residence": "hirte", "first_name": "Hirte", "last_name": "Admin", "email": "tutorenhirte@gmail.com", "user_name": "admin hirte", "password_hash": "tutorenhirte2025"},
    returning_column="id")

if result["success"] is False:
    raise result["error"]