from packages.backend.sql_connection import database as db
from packages.backend import hash_pwd

pwd_hes = input("Bitte gib ein Passwort für das Administratorenkonto ein: ")
# pwd_hirte = os.getenv("ADMIN_PASSWORD_HIRTE")

if not pwd_hes:
    raise Exception("Please set pwd_hes")
# if not pwd_hirte:
#     raise Exception("Please set pwd_hirte")

conn, cursor = db.connect()
password_hes = hash_pwd.hash_pwd(pwd_hes)
# password_hirte = hash_pwd.hash_pwd(pwd_hirte)
result = db.insert_table(
    cursor=cursor,
    table_name="users",
    arguments={"user_role":"admin",  "room": 0, "residence": "altbau", "first_name": "Super", "last_name": "Admin", "email": "tutorenheshirte@gmail.com", "user_name": "admin", "password_hash": password_hes},
    returning_column="id")
if result["success"] is False:
    raise result["error"]

"""
result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="users",
    arguments={"user_role":"admin",  "room": 0, "residence": "hirte", "first_name": "Hirte", "last_name": "Admin", "email": "tutorenhirte@gmail.com", "user_name": "admin hirte", "password_hash": password_hirte},
    returning_column="id")

if result["success"] is False:
    raise result["error"]
"""

print("Admin user added.")
