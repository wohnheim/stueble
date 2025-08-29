import bcrypt

def hash_pwd(password: str) -> str:
    password = password.encode()
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode()

def match_pwd(password: str, hashed: str) -> bool:
    password = password.encode()
    return bcrypt.checkpw(password, hashed.encode())