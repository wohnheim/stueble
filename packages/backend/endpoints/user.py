"""
User management
"""

import asyncio
import json

from flask import Blueprint, request, Response

from backend import websocket as ws
from backend.datatypes.stueble_types import FrontendUserRole, UserRole, get_leq_roles, is_valid_role
from backend.sql_connection import (
    sessions,
    users,
)
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions
from backend.basic_functions import snake_to_camel_case

user = Blueprint("users", __name__)

@user.route("/user", methods=["GET"])
def get_user():
    """
    return data to user
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # get user id from session id
    result = sessions.get_user(session_id=session_id, keywords=("id", "user_role", "user_uuid", "room", "residence", "first_name", "last_name", "email", "user_name"))
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    data = result.data

    # initialize user
    user_data = {"firstName": data["first_name"],
            "lastName": data["last_name"],
            "roomNumber": data["room"],
            "residence": data["residence"],
            "email": data["email"],
            "id": data["user_uuid"],
            "username": data["user_name"]}

    response = Response(
        response=json.dumps(user_data),
        status=200,
        mimetype="application/json")
    return response

@user.route("/user", methods=["POST"])
def verify_user():
    """
    verify a user (only hosts and above can verify users)
    """
    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only tutors or above can change user role
    result = check_permissions(session_id=session_id,
                               required_role=UserRole.USER)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor or above"}),
            status=403,
            mimetype="application/json")
        return response
    user_id = result.data["user_id"]

    result = users.update_user(user_id=user_id,
                               verified=True)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    keywords = ["user_uuid", "first_name", "last_name", "user_role"]
    result = users.get_user(user_id=user_id, columns=keywords)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    user_info = {key: value for key, value in zip(keywords, result.data)}

    result = users.check_user_present(user_id=user_id)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    present = result.data

    user_data = {
        "id": user_info["user_uuid"],
        "present": present,
        "firstName": user_info["first_name"],
        "lastName": user_info["last_name"],
        "extern": user_info["user_role"] == FrontendUserRole.EXTERN.value}

    if user_info["user_role"] == FrontendUserRole.INTERN.value:
        user_data["roomNumber"] = user_info["room"]
        user_data["residence"] = user_info["residence"]
        user_data["verified"] = True

    asyncio.run(ws.broadcast(event="guestModified", data=user_data)) # don't skip_sid for guestModified

    response = Response(
        response=json.dumps(user_data),
        status=200,
        mimetype="application/json")
    return response

# TODO websocket change update user
@user.route("/user/change_role", methods=["POST"])
def change_user_role():
    """
    change the user role of a user (only admin can change user to tutor)
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response
    user_uuid = data.get("id", None)
    new_role = data.get("role", None)
    if new_role is None or is_valid_role(new_role) is False or new_role == "admin":
            response = Response(
                response=json.dumps({"code": 400, "message": "The new_role must be specified, needs to be valid and can't be admin"}),
                status=400,
                mimetype="application/json")
            return response

    # check permissions, since only tutors or above can change user role
    result = check_permissions(session_id=session_id, required_role=UserRole.ADMIN if new_role == UserRole.TUTOR else UserRole.TUTOR)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor or above"}),
            status=403,
            mimetype="application/json")
        return response

    result = users.update_user(
        user_uuid_key=user_uuid,
        user_role=UserRole(new_role))

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    user_id = result.data

    capabilities = [i.value for i in get_leq_roles(result.data["user_role"]) if i.value in ["user", "host", "tutor", "admin"]]

    data = {"code": "200",
            "capabilities": capabilities,
            "authorized": True}

    result = sessions.get_session_ids(user_id=user_id)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    session_ids = result.data
    for sid in session_ids:
        websocket = ws.get_websocket_by_sid(sid=sid)
        if websocket is not None:
            asyncio.run(ws.send(websocket=websocket, event="status", data=data))

    # check if user is on guest list

    result = users.check_user_guest_list(user_id=user_id)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    if result.data is True:
        keywords = ["user_uuid", "first_name", "last_name", "user_role"]
        result = users.get_user(user_id=user_id, columns=keywords)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response
        user_info = {key: value for key, value in zip(keywords, result.data)}

        result = users.check_user_present(user_id=user_id)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response
        present = result.data

        user_data = {
            "id": user_info["user_uuid"],
            "present": present,
            "firstName": user_info["first_name"],
            "lastName": user_info["last_name"],
            "extern": user_info["user_role"] == FrontendUserRole.EXTERN.value}

        if user_info["user_role"] == FrontendUserRole.INTERN.value:
            user_data["roomNumber"] = user_info["room"]
            user_data["residence"] = user_info["residence"]
            user_data["verified"] = True

        asyncio.run(ws.broadcast(event="guestModified", data=user_data)) # don't skip_sid for guestModified

    response = Response(
        status=204)
    return response

@user.route("/user/search", methods=["GET"])
def search_intern():
    """
    search for a guest \n
    allowed keys for searching are first_name, last_name, email, (room, residence), user_uuid
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # check permissions, since only hosts can see guests

    result = check_permissions(session_id=session_id, required_role=UserRole.HOST)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 401, "message": "invalid permissions, need at least role host"}),
            status=401,
            mimetype="application/json")
        return response

    # load data
    data = request.args.to_dict()

    if data is None or not isinstance(data, dict):
        response = Response(
            response=json.dumps({"code": 400, "message": "The data must be a valid json object"}),
            status=400,
            mimetype="application/json")
        return response

    # json format data: {"session_id": str, data: {"first_name": str or None, "last_name": str or None, "room": str or None, "residence": str or None, "email": str or None}}

    # allowed keys to search for a user
    allowed_keys = ["first_name", "last_name", "room", "residence", "email", "id", "username"]

    # if no key was specified return error
    if any(key not in allowed_keys for key in data.keys()):
        response = Response(
            response=json.dumps({"code": 400, "message": f"Only the following keys are allowed: {', '.join(allowed_keys)}"}),
            status=400,
            mimetype="application/json")
        return response

    keywords = ["first_name", "last_name", "user_uuid", "residence"]
    negated_conditions = {"user_role": "extern"}
    # search user_name
    if "username" in data:
        conditions = {"user_name": data["username"]}
        result = db.select(
            table="users",
            columns=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER) # originally True but since it is handled as list, False is specified

    # search user_uuid
    elif "id" in data:
        conditions = {"user_uuid":data["id"]}
        result = db.select(
            table="users",
            columns=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER) # originally True but since it is handled as list, False is specified

    # search email
    elif "email" in data:
        conditions = {"email": data["email"]}
        negated_conditions = {"user_role": "extern"}
        result = db.select(
            table="users",
            columns=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER) # originally True but since it is handled as list, False is specified

    # search room AND residence
    elif "room" in data and "residence" in data:
        conditions = {key: value for key, value in data.items() if key in ["room", "residence"]}
        result = db.select(
            table="users",
            columns=keywords,
            conditions=conditions,
            negated_conditions=negated_conditions,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER) # originally True but since it is handled as list, False is specified

    # search first_name and / or last_name as well as room or residence
    else:
        search_dict = {
            "first_name": "first_name ILIKE %s", 
            "last_name": "last_name ILIKE %s", 
            "room": "room = %s", 
            "residence": "residence = %s"}
        query = f"""
        SELECT {', '.join(keywords)} FROM users
        WHERE {" AND ".join([search_dict[key] for key in data.keys()])}
        AND user_role != 'extern'
        """
        variables = [f"{value}%" if key in ["first_name", "last_name"] else value for key, value in data.items()]
        result = db.custom_call(query=query,
                                type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
                                variables=variables)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # if data is None, set it to empty list
    if result.data is None:
        result._data = list()

    users_data = []
    for entry in result.data:
        users_data.append({"first_name": entry["first_name"],
                      "last_name": entry["last_name"],
                      "id": entry["user_uuid"],
                      "residence": entry["residence"]})
    users_data = [{snake_to_camel_case(key): value for key, value in i.items()} for i in users_data]

    response = Response(
        response=json.dumps(users_data),
        status=200,
        mimetype="application/json")

    return response