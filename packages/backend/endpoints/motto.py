"""
Motto endpoint
"""

import json

from flask import Blueprint, Response, request

from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import motto
from backend.sql_connection.common_functions import check_permissions


mo = Blueprint("motto", __name__)

# TODO allow date changes
@mo.route("", methods=["POST"])
def create_stueble():
    """
    creates or modifies a stueble event
    """

    # load data
    data = request.get_json()
    date = data.get("date", None)
    stueble_motto = data.get("motto", None)
    description = data.get("description", None)
    shared_apartment = data.get("shared_apartment", None)

    if stueble_motto is None and shared_apartment is None and description is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "motto or shared_apartment or description must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    user_role = UserRole.TUTOR
    # date can't be changed but rather acts as an identifier
    if date is None and shared_apartment is None and stueble_motto is None:
        user_role = UserRole.HOST

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only hosts or above can change the motto
    result = check_permissions(session_id=session_id, required_role=user_role)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": f"invalid permissions, need role {user_role.value} or above"}),
            status=403,
            mimetype="application/json")
        return response
    actual_user_role = result.data["user_role"]
    actual_user_role = UserRole(actual_user_role)

    result = motto.update_stueble(date=date,
                                motto=stueble_motto,
                                description=description,
                                shared_apartment=shared_apartment)

    if result.is_error:
        if result.error == "no stueble found":
            if actual_user_role == UserRole.HOST:
                response = Response(
                    response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor or above to create a new stueble"}),
                    status=403,
                    mimetype="application/json")
                return response
            result = motto.create_stueble(date=date,
                                    motto=stueble_motto,
                                    description=description,
                                    shared_apartment=shared_apartment)

            if result.is_error:
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result.error)}),
                    status=500,
                    mimetype="application/json")
                return response
        else:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response

    response = Response(status=204)
    return response