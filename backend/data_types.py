from enum import Enum
import re

class UserRole(Enum):
    ADMIN = "admin"
    USER = "host"
    GUEST = "guest"
    EXTERN = "extern"

def is_valid_role(value):
    return value in UserRole._value2member_map_


class Residence(Enum):
    ALTBAU = "altbau"
    NEUBAU = "neubau"
    ANBAU = "anbau"
    HIRTE = "hirte"

def is_valid_residence(value):
    return value in Residence._value2member_map_


class Email:
    pattern = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
    
    def __init__(self, email: str):
        if not isinstance(email, str) or not self.pattern.match(email):
            raise ValueError("Invalid email format")
        self.email = email