
import json

from flask import Blueprint, Response, request

from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import (
    users,
    hosts_tutors as hosts
)
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions

host = Blueprint("host", __name__)

@host.route("/hosts", methods=["GET"])
def get_hosts():
    """
    Get hosts for a stueble.
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session_id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    date = None
    try:
        data = request.get_json()
        date = data.get("date", None)
    except:
        pass

    path = request.path

    response = hosts.get_hosts_tutors(session_id=session_id, path=path, date=date)

    if response.is_error:
        return Response(
            response=json.dumps({"code": response.message.code, "message": response.user_warning}),
            status=response.message.code,
            mimetype="application/json")
    
    return Response(
        response=json.dumps(response.data),
        status=response.message.code,
        mimetype="application/json")
    

@host.route("/hosts/force_add_guest", methods=["POST"])
def force_add_guest():
    """
    force add guest to current stueble
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response
    user_uuid = data.get("id", None)
    if user_uuid is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "The user_uuid must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    # check permissions, since only hosts and above can add guests
    result = check_permissions(session_id=session_id, required_role=UserRole.HOST)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role host or above"}),
            status=403,
            mimetype="application/json")
        return response

    # get user_id from user_uuid
    result = users.get_user(user_uuid=user_uuid, columns=["id"])
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    user_id = result.data[0]
    query = """SET additional.skip_triggers = 'on';
INSERT INTO stueble.events (user_id, stueble_id, event_type) VALUES (%s, %s, %s), (%s, %s, %s);  -- Triggers will be skipped
RESET additional.skip_triggers;"""
    result = db.custom_call(query=query,
                            type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
                            variables=[user_id, 1, 'add', user_id, 1, 'arrive'])
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    response = Response(
        status=204)
    return response