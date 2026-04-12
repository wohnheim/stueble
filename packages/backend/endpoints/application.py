"""
Application related endpoints for the stueble party.
"""

import json

from flask import Blueprint, Response, request

from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import applications
from backend.sql_connection.common_functions import check_permissions

applic = Blueprint("application", __name__)

@applic.route("", methods=["GET"])
def get_applications():
    """
    Get all applications for throwing the stueble party.
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions
    result = check_permissions(session_id=session_id, required_role=UserRole.USER)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response

    user_id = result.data["user_id"]
    
    result = applications.get_applications(user_id=user_id)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    response = Response(
        response=json.dumps(result.data),
        status=200,
        mimetype="application/json")
    return response


@applic.route("", methods=["POST"])
def send_applications():
    """
    Register for multiple dates using an application for throwing the stueble party.
    """

    data = request.get_json()

    keys = ["motto", "hosts", "dates", "description", "image"]

    if data is None:
        return Response(
                response=json.dumps({"code": 400, "message": "The data must be specified"}),
                status=400,
                mimetype="application/json"
        )

    if any(key not in keys for key in data):
        return Response(
                response=json.dumps({"code": 400, "message": f"Only the following keys are allowed: {keys}"}),
                status=400,
                mimetype="application/json"
        )
    if any(key not in data for key in ["motto", "hosts", "dates"]):
        return Response(
                response=json.dumps({"code": 400, "message": "The keys motto, hosts and dates must be specified"}),
                status=400,
                mimetype="application/json"
        )

    if any(not isinstance(i, tuple) and not isinstance(i, list) for i in data["dates"]):
        return Response(
                response=json.dumps({"code": 400, "message": "Dates must be a list of tuples / list containing date, application_priority"}),
                status=400,
                mimetype="application/json"
        )
    data["dates"] = [tuple(i) for i in data["dates"]]
    
    description = data.get("description", None)
    image = data.get("image", None)

    response = applications.send_application(motto=data["motto"], hosts=data["hosts"], dates=data["dates"], description=description, image=image) # type: ignore
    
    if response.is_error:
        return Response(
            response=json.dumps({"code": response.message.code, "message": str(response.user_warning)}),
            status=response.message.code,
            mimetype="application/json"
        )

    return Response(
        response=json.dumps(response.data),
        status=200,
        mimetype="application/json"
    )


@applic.route("", methods=["DELETE"])
def delete_application():
    """
    Delete an application.
    """
    
    data = request.get_json()
    application_uuid = data.get("id", None)

    if application_uuid is None:
        return Response(
            response=json.dumps({"code": 400, "message": "The id must be specified"}),
            status=400,
            mimetype="application/json"
        )
    
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions
    result = check_permissions(session_id=session_id, required_role=UserRole.USER)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role user or above"}),
            status=403,
            mimetype="application/json")
        return response
    
    user_id = result.data["user_id"]

    response = applications.delete_application(application_uuid=application_uuid, user_id=user_id)

    if response.is_error:
        return Response(
            response=json.dumps({"code": response.message.code, "message": str(response.user_warning)}),
            status=response.message.code,
            mimetype="application/json"
        )
    
    return Response(
        status=204
    )