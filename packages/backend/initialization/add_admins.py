from backend.database import database as db
from backend import hash_pwd
import os

pwd_admin = os.getenv("ADMIN_PASSWORD")
interactive = False

if pwd_admin is None:
    pwd_admin = input("Please enter a password for the admin account: ")
    interactive = True

if pwd_admin is None:
    raise Exception("Invalid password")

bcrypt_hash = hash_pwd.hash_pwd(pwd_admin)
result = db.insert(
    table="users",
    values={"user_role":"admin",  "room": 0, "residence": "altbau", "first_name": "Super", "last_name": "Admin", "email": "tutorenhes@gmail.com", "user_name": "admin", "password_hash": bcrypt_hash, "password_algorithm": "bcrypt"},
    returning_column="id")
if result.is_error:
    raise result.error

if interactive:
    print("Admin user added.")

db.__close_pool()
