import bcrypt

def hash_pwd(password: str) -> str:
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode()

def match_pwd(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password, hashed.encode())