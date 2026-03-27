

import json

from flask import Blueprint, Response, request

from backend.sql_connection import hosts_tutors as hosts

tutor = Blueprint("tutor", __name__)

@tutor.route("/", methods=["GET"])
def get_tutors():
    """
    Get tutors.
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