"""
Motto endpoint
"""

import json
from datetime import date, datetime as dt, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, request
from psycopg import sql

from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import applications
from backend.sql_connection.common_functions import check_permissions
from backend.database import database as db


mo = Blueprint("motto", __name__)

# TODO allow date changes
@mo.route("", methods=["POST"])
def create_stueble():
    """
    creates or modifies a stueble event
    """

    # load data
    data = request.get_json()
    stueble_motto = data.get("motto", None)
    description = data.get("description", None)
    hosts = data.get("hosts", None)

    if stueble_motto is None and hosts is None and description is None:
        response = Response(
            response=json.dumps({"code": 400, "message": "motto or hosts or description must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    user_role = UserRole.TUTOR
    # date can't be changed
    if hosts is None:
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
    user_id = result.data["user_id"]
    user_uuid = result.data["user_uuid"]

    date_of_time = dt.now(ZoneInfo("Europe/Berlin"))
    additional_days = (2 - dt.now(ZoneInfo("Europe/Berlin")).weekday()) % 7
    if additional_days == 1 and dt.now(ZoneInfo("Europe/Berlin")).time() < dt.strptime("06:00:00", "%H:%M:%S").time():
        additional_days = -1
    date_of_time = date_of_time + timedelta(days=additional_days)
    date_of_time = date_of_time.date().isoformat()

    query = sql.SQL("SELECT a.id, ag.group_hash, a.uuid \
                    FROM stueble.dates d \
                    JOIN stueble.applications a ON d.application_id = a.id \
                    JOIN stueble.application_groups ag ON a.application_group = ag.id \
                    WHERE date_of_time = {date_of_time}").format(date_of_time=sql.Placeholder())
    
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=(date_of_time,)
    )

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    
    if result.data is not None:
        application_id = result.data[0]
        application_uuid = result.data[2]
        group = result.data[1].split(":") if result.data[1] is not None else []
        
        if actual_user_role < UserRole.TUTOR and user_uuid not in group:
            response = Response(
                response=json.dumps({"code": 403, "message": "invalid permissions, user is not part of the stueble group and not tutor or above"}),
                status=403,
                mimetype="application/json")
            return response

        result = applications.update_application(
        application_uuid=application_uuid,
        user_id=user_id,
        motto=data.get("motto", None),
        hosts=data.get("hosts", None),
        description=data.get("description", None),
        image=data.get("image", None)
        )

        if result.is_error:
            return Response(
                response=json.dumps({"code": result.message.code if result.message is not None else 500, "message": str(result.user_warning)}),
                status=result.message.code if result.message is not None else 500,
                mimetype="application/json"
            )

        return Response(
            status=204
        )

    response = applications.send_application(
        motto=stueble_motto,
        hosts=hosts,
        description=data.get("description", None),
        image=data.get("image", None),
        dates=[(date_of_time, -1)],
        automatic_priorities=True
    )

    if response.is_error:
        return Response(
            response=json.dumps({"code": response.message.code if response.message is not None else 500, "message": str(response.user_warning)}),
            status=response.message.code if response.message is not None else 500,
            mimetype="application/json"
        )
    
    application_id = response.data[0]["application_id"]

    result = db.insert(
        table="stueble.dates",
        values={
            "application_id": application_id
        }
    )

    if result.is_error:
        return Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json"
        )

    return Response(
        status=204
    )