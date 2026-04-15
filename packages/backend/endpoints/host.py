
import asyncio
import json

from flask import Blueprint, Response, request
from psycopg import sql

from backend import websocket as ws
from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import (
    users,
    hosts_tutors as hosts,
    motto
)
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions

host = Blueprint("host", __name__)

@host.route("", methods=["GET"])
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
    

@host.route("/force_add_guest", methods=["POST"])
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
    user_id = result.data["id"]
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

@host.route("", methods=["PUT", "DELETE"])
def update_hosts():
    """
    Update hosts for a stueble.
    """
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    data = request.get_json()
    date = data.get("date", None)
    user_uuids = data.get("hosts", None)

    if not user_uuids:
        response = Response(
            response=json.dumps({"code": 403, "message": "hosts must be specified"}),
            status=403,
            mimetype="application/json")
        return response

    # check permissions, since only tutors or above can change user role
    result = check_permissions(session_id=session_id, required_role=UserRole.TUTOR)
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

    result = motto.get_info(date=date)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    if result.data is None:
        response = Response(
            response=json.dumps({"code": 404, "message": "no stueble party found"}),
            status=404,
            mimetype="application/json")
        return response
    application_id = result.data["stueble_id"]

    # application_id is the id of the current stueble, therefore also delete the host priviledges from users
    result = users.get_users(user_uuids=user_uuids, keywords=["user_uuid", "first_name", "last_name", "residence", "user_role", "id"])
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    user_ids = [i["id"] for i in result.data]
    hosts_data = [{"id": i["user_uuid"], "firstName": i["first_name"], "lastName": i["last_name"], "residence": i["residence"]} for i in result.data if i["user_role"] == ('user' if request.method == "PUT" else 'host')]
    if len(hosts_data) != len(user_uuids):
        response = Response(
            response=json.dumps({"code": 404, "message": "Tutoren, Admins und Hosts können nicht zu Hosts gemacht werden"}),
            status=404,
            mimetype="application/json")
        return response

    if request.method == "PUT":
        query = sql.SQL("INSERT INTO stueble.applicants (user_id, application_group) \
                        SELECT id, {application_group} \
                        FROM users \
                        WHERE user_uuid IN ({user_uuids})").format(
                            application_group=sql.Placeholder(),
                            user_uuids=sql.SQL(', ').join(sql.Placeholder() * len(user_uuids))
                        )
        variables = [application_id] + user_uuids
    else:
        query = sql.SQL("WITH selected_users AS (SELECT id FROM users WHERE user_uuid IN ({user_uuids})) \
                        DELETE FROM stueble.applicants \
                        WHERE user_id IN (SELECT id FROM selected_users) AND application_group = {application_group}").format(
                            application_group=sql.Placeholder(),
                            user_uuids=sql.SQL(', ').join(sql.Placeholder() * len(user_uuids))
                        )
        variables = user_uuids + [application_id]

    result = db.custom_call(query=query, type_of_answer=db.ANSWER_TYPE.NO_ANSWER, variables=variables)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # stueble_id is the id of the current stueble, therefore also delete the host priviledges from users
    if request.method == "DELETE":
        query = sql.SQL("UPDATE users SET user_role = 'user' WHERE id IN ({user_ids}) AND user_role = 'host'").format(
            user_ids=sql.SQL(', ').join(sql.Placeholder() * len(user_ids))
        )
        result = db.custom_call(query=query, type_of_answer=db.ANSWER_TYPE.NO_ANSWER, variables=user_ids)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response
    else:
        query = sql.SQL("UPDATE users SET user_role = 'host' WHERE id IN ({user_ids}) AND user_role = 'user'").format(
            user_ids=sql.SQL(', ').join(sql.Placeholder() * len(user_ids))
        )
        result = db.custom_call(query=query, type_of_answer=db.ANSWER_TYPE.NO_ANSWER, variables=user_ids)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response

    query = sql.SQL("SELECT id FROM sessions WHERE user_id IN ({user_ids})").format(user_ids=sql.SQL(', ').join(sql.Placeholder() * len(user_ids)))
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=user_ids
    )

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    session_ids = [i[0] for i in result.data]

    result = ws.update_hosts_tutors(session_ids, "add" if request.method == "PUT" else "remove")

    if request.method == "PUT":
        for user in hosts_data:
            asyncio.run(ws.broadcast(event="hostAdded", data=user, skip_sid=session_id))
            asyncio.run(ws.status(user_uuid=user["id"]))
    else:
        for user in user_uuids:
            asyncio.run(ws.broadcast(event="hostRemoved", data=user, skip_sid=session_id))

            asyncio.run(ws.status(user_uuid=user))

    if request.method == "DELETE":
        response = Response(
            status=204)
        return response

    response = Response(
        response=json.dumps(hosts_data),
        status=201,
        mimetype="application/json")
    return response