from packages.backend.sql_connection import database as db
from packages.backend import hash_pwd

# set the password for the admin account
pwd_hes = input("Bitte gib ein Passwort für das Administratorenkonto ein: ")
if not pwd_hes:
    raise Exception("Please set pwd_hes")

# create the admin account
conn, cursor = db.connect()
password_hes = hash_pwd.hash_pwd(pwd_hes)
result = db.insert_table(
    cursor=cursor,
    table_name="users",
    arguments={"user_role":"admin",  "room": 0, "residence": "altbau", "first_name": "Super", "last_name": "Admin", "email": "tutorenheshirte@gmail.com", "user_name": "admin", "password_hash": password_hes},
    returning_column="id")
if result["success"] is False:
    raise result["error"]

# print success message
print("Admin user added.")