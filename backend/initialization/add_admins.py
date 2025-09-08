from backend.sql_connection import database as db

conn, cursor = db.connect()

result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="users",
    arguments=["user_role", "room", "residence", "first_name", "last_name", "email", "user_name", "password_hash"],
    variables=["admin", 0, "altbau", "Altbau", "Admin", "tutorenhes@gmail.com", "admin altbau", "tutorenhes2025"],
    returning_column="id")
if result["success"] is False:
    raise result["error"]

result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="users",
    arguments=["user_role", "room", "residence", "first_name", "last_name", "email", "user_name", "password_hash"],
    variables=["admin", 0, "hirte", "Hirte", "Admin", "tutorenhirte@gmail.com", "admin hirte", "tutorenhirte2025"],
    returning_column="id")

if result["success"] is False:
    raise result["error"]