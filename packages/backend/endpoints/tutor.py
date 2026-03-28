
import asyncio
import json

from flask import Blueprint, Response, request

from backend import websocket as ws
from backend.sql_connection import hosts_tutors as hosts
from backend.sql_connection import users
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions
from backend.datatypes.stueble_types import UserRole


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


@tutor.route("/", methods=["PUT", "DELETE"])
def update_tutors():
    """
    Update tutors.
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    data = request.get_json()
    user_uuids = data.get("tutors", None)

    if not user_uuids:
        response = Response(
            response=json.dumps({"code": 403, "message": "tutors must be specified"}),
            status=403,
            mimetype="application/json")
        return response

    # check permissions, since only admins can change user role
    result = check_permissions(session_id=session_id, required_role=UserRole.ADMIN)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role admin"}),
            status=403,
            mimetype="application/json")
        return response

    # get information about users
    result = users.get_users(user_uuids=user_uuids, keywords=["user_uuid", "first_name", "last_name", "residence", "user_role", "user_uuid"])
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # clean result data
    tutors_data = result.data
    tutors_data = [{"id": i["user_uuid"], "firstName": i["first_name"], "lastName": i["last_name"], "residence": i["residence"], "user_role": UserRole(i["user_role"]), "user_uuid": i["user_uuid"]} for i in tutors_data]

    # check, whether all users were found
    if len(tutors_data) != len(user_uuids):
        response = Response(
            response=json.dumps({"code": 404, "message": "Not all users found"}),
            status=404,
            mimetype="application/json")
        return response

    # if any user is admin, raise error
    if any(i["user_role"] >= UserRole.ADMIN for i in tutors_data):
        response = Response(
            response=json.dumps({"code": 403, "message": "Can only remove tutors or make admins to tutors"}),
            status=403,
            mimetype="application/json")
        return response

    hosts_removed = []

    # changing tutors back to users
    if request.method == "DELETE":
        # set new role
        new_role = UserRole.USER

        # remove wrong users from tutor list
        tutors_data = [{key: value for key, value in i.items() if key != "user_role"} for i in tutors_data if i["user_role"] == UserRole.TUTOR]
    else:
        if any(i["user_role"] == UserRole.EXTERN for i in tutors_data):
            response = Response(
                response=json.dumps({"code": 403, "message": "Can't promote extern users to tutors"}),
                status=403,
                mimetype="application/json")
            return response
        hosts_removed = [i["user_uuid"] for i in tutors_data if i["user_role"] == UserRole.HOST]
        # set new role
        new_role = UserRole.TUTOR
        # remove wrong users from tutor list
        tutors_data = [{key: value for key, value in i.items() if key != "user_role"} for i in tutors_data if i["user_role"] == UserRole.USER or i["user_role"] == UserRole.HOST]
    if len(tutors_data) != len(user_uuids):
        response = Response(
            response=json.dumps({"code": 400, "message": "Some users can't be promoted to tutors"}),
            status=403,
            mimetype="application/json")
        return response

    query = """
        UPDATE users
        SET user_role = %s
        WHERE user_uuid IN %s
        RETURNING id
    """
    result = db.custom_call(query=query,
                            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
                            variables=[new_role.value, tuple(i["id"] for i in tutors_data)])

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # NOTE: unneccessary due to trigger
    user_ids = result.data
    query = """DELETE FROM hosts WHERE user_id IN %s"""
    result = db.custom_call(query=query, type_of_answer=db.ANSWER_TYPE.NO_ANSWER, variables=(tuple(user_ids),))
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    query = f"SELECT id FROM sessions WHERE user_id IN ({', '.join(['%s' for _ in range(len(user_ids))])})"
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=tuple(user_ids))

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    session_ids = [i[0] for i in result.data]

    result = ws.update_hosts_tutors(session_ids, "add" if request.method == "PUT" else "remove")

    if request.method == "PUT":
        for user in tutors_data:
            asyncio.run(ws.broadcast(event="tutorAdded", data=user, skip_sid=session_id))
            asyncio.run(ws.status(user_uuid=user["id"]))
        for host in hosts_removed:
            asyncio.run(ws.broadcast(event="hostRemoved", data=host))
    else:
        for user in user_uuids:
            asyncio.run(ws.broadcast(event="tutorRemoved", data=user, skip_sid=session_id))
            asyncio.run(ws.status(user_uuid=user))

    if request.method == "DELETE":
        response = Response(
            status=204)
        return response

    response = Response(
        response=json.dumps(tutors_data),
        status=201,
        mimetype="application/json")
    return response