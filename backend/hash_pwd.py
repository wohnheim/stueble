import bcrypt

def hash_pwd(password: str) -> str:
    password = password.encode()
    hashed_pwd = bcrypt.hashpw(password, bcrypt.gensalt())
    return hashed_pwd.decode()

def match_pwd(password: str, hashed: str) -> bool:
    password = password.encode()
    hashed = hashed.encode()
    return bcrypt.checkpw(password, hashed)