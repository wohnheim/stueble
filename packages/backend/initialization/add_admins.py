from backend.database import database as db
from backend import hash_pwd

pwd_hes = input("Bitte gib ein Passwort für das Administratorenkonto ein: ")

if not pwd_hes:
    raise Exception("Please set pwd_hes")

password_hes = hash_pwd.hash_pwd(pwd_hes)
result = db.insert(
    table="users",
    values={"user_role":"admin",  "room": 0, "residence": "altbau", "first_name": "Super", "last_name": "Admin", "email": "tutorenhes@gmail.com", "user_name": "admin", "password_hash": password_hes},
    returning_column="id")
if result.is_error:
    raise result.error

print("Admin user added.")

db.__close_pool()