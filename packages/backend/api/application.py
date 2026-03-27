"""
Application related endpoints for the stueble party.
"""

import json

from flask import Blueprint, Response, request
from psycopg import sql

from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import applications
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions

applic = Blueprint("application", __name__)

@applic.route("/stueble/applications", methods=["GET"])
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


@applic.route("/stueble/application", methods=["POST"])
def send_applications():
    """
    Register for multiple dates using an application for throwing the stueble party.
    """

    data = request.form

    keys = ["motto", "hosts", "dates"]

    if data is None:
        return Response(
                response=json.dumps({"code": 400, "message": "The data must be specified"}),
                status=400,
                mimetype="application/json"
        )

    try:
        data = {key: data[key] for key in keys}
    except KeyError as e:
        return Response(
            response=json.dumps({"code": 400, "message": f"{e.args[0]} must be specified"}),
            status=400,
            mimetype="application/json"
        )

    if any(not isinstance(i, tuple) for i in data["dates"]):
        return Response(
                response=json.dumps({"code": 400, "message": "Dates must be a list of tuples containing date and priority"}),
                status=400,
                mimetype="application/json"
        )

    response = applications.send_application(motto=data["motto"], hosts=data["hosts"], dates=data["dates"])
    
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


@applic.route("/stueble/application", methods=["DELETE"])
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


@applic.route("/events", methods=["GET"])
def get_events():
    """
    Get the events in the dorm.
    """

    name = request.args.get("name", None)

    columns = [
        "name", 
        "category", 
        "location", 
        "start", 
        "end", 
        "full_days", 
        "description", 
        "image"
    ]

    query = sql.SQL("SELECT  \
                    FROM events.events \
                    WHERE end >= NOW() if end IS NOT NULL else start >= CURRENT_DATE() \
                    {name} \
                    ORDER BY start ASC").format(
        name=sql.SQL("AND name = {name}") if name else sql.SQL("")
                    )
    
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[name] if name else []
    )

    if result.is_error:
        return Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json"
        )

    data = [{key: value for key, value in zip(columns, i)} for i in result.data]
    # TODO: test time format conversion
    for i in data:
        if i["full_days"] is True:
            i["start"] = i["start"].strftime("%Y-%m-%d")
            i["end"] = i["end"].strftime("%Y-%m-%d") if i["end"] is not None else None
        else:
            i["start"] = i["start"].isoformat()
            i["end"] = i["end"].isoformat() if i["end"] is not None else None
        del i["full_days"]

    return Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json"
    )