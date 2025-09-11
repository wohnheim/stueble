from enum import Enum
import re

class UserRole(str, Enum):
    ADMIN = "admin"
    TUTOR = "tutor"
    HOST = "host"
    USER = "user"
    EXTERN = "extern"

    def __lt__(self, other):
        if isinstance(other, UserRole):
            members = list(self.__class__)
            return members.index(other) < members.index(self)
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, UserRole):
            members = list(self.__class__)
            return members.index(other) > members.index(self)
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, UserRole):
            members = list(self.__class__)
            return members.index(other) <= members.index(self)
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, UserRole):
            members = list(self.__class__)
            return members.index(other) >= members.index(self)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, UserRole):
            return self.value == other.value
        return NotImplemented

def get_leq_roles(role: UserRole):
    return [r for r in UserRole if r <= role]

def is_valid_role(value):
    return value in UserRole._value2member_map_

class FrontendUserRole(str, Enum):
    INTERN = "intern"
    EXTERN = "extern"

def is_valid_frontend_role(value):
    return value in FrontendUserRole._value2member_map_

class Residence(Enum):
    ALTBAU = "altbau"
    NEUBAU = "neubau"
    ANBAU = "anbau"
    HIRTE = "hirte"

def is_valid_residence(value):
    return value in Residence._value2member_map_

class EventType(Enum):
    ARRIVE = "arrive"
    LEAVE = "leave"

def valid_event_type(value):
    return value in EventType._value2member_map_

class Email:
    pattern = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
    
    def __init__(self, email: str):
        if not isinstance(email, str) or not self.pattern.match(email):
            raise ValueError("Invalid email format")
        self.email = email

class Event_Notify(str, Enum):
    ARRIVE = "ARRIVE"
    LEAVE = "LEAVE"