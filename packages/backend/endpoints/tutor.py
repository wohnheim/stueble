
import asyncio
import json

from flask import Blueprint, Response, request
from psycopg import sql

from backend import websocket as ws
from backend.sql_connection import hosts_tutors as hosts
from backend.sql_connection import users
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions
from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import applications as applics

tutor = Blueprint("tutor", __name__)

@tutor.route("", methods=["GET"])
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


@tutor.route("", methods=["PUT", "DELETE"])
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

    # user_uuids to be added or removed
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

    # get information about users, that should be updated
    result = users.get_users(user_uuids=user_uuids, keywords=["id", "first_name", "last_name", "residence", "user_role", "user_uuid"])
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    # clean result data
    tutors_data = result.data
    tutors_data = [{"id": i["id"], "firstName": i["first_name"], "lastName": i["last_name"], "residence": i["residence"], "user_role": UserRole(i["user_role"]), "user_uuid": str(i["user_uuid"])} for i in tutors_data]
    user_ids = [i["id"] for i in tutors_data] # ids of users, that should be changed

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
        tutors_data = [{key: value for key, value in i.items() if key != "user_role"} for i in tutors_data if i["user_role"] == UserRole.TUTOR] # filter all users, that should be removed from tutor and are actually tutor
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
        tutors_data = [{key: value for key, value in i.items() if key not in  ["user_role", "id"]} for i in tutors_data if i["user_role"] == UserRole.USER or i["user_role"] == UserRole.HOST]
    if len(tutors_data) != len(user_uuids):
        response = Response(
            response=json.dumps({"code": 400, "message": "Some users can't be promoted to tutors"}),
            status=403,
            mimetype="application/json")
        return response

    query = sql.SQL("""
        UPDATE users
        SET user_role = {new_role}
        WHERE user_uuid IN ({user_uuids})
        RETURNING id
    """).format(new_role=sql.Placeholder(), user_uuids=sql.SQL(', ').join(sql.Placeholder() * len(user_uuids)))
    result = db.custom_call(query=query,
                            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
                            variables=[new_role.value] + [i["user_uuid"] for i in tutors_data])

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    query = sql.SQL("SELECT id FROM sessions WHERE user_id IN ({uids})").format(uids=sql.SQL(', ').join(sql.Placeholder() * len(user_ids)))
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=user_ids)

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
            asyncio.run(ws.status(user_uuid=user["user_uuid"]))
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


@tutor.route("/stueble/dates", methods=["GET"])
def get_stueble_applications():
    """
    Get stueble applications for a date.
    """
    
    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only admins can change user role
    result = check_permissions(session_id=session_id, required_role=UserRole.TUTOR)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor"}),
            status=403,
            mimetype="application/json")
        return response

    data = request.get_json()
    date = data.get("date", None)

    query = sql.SQL("""
        SELECT uuid, motto, date_of_time, application_priority, (SELECT group_hash FROM stueble.application_groups WHERE id = application_group LIMIT 1) AS members
        FROM stueble.applications applications
        {where_date}
        """).format(where_date=sql.SQL("WHERE date_of_time = {date}").format(date=sql.Placeholder()) if date is not None else sql.SQL(""))
    
    result = db.custom_call(query=query, type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, variables=[date] if date is not None else [])

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    
    if result.data is None:
        response = Response(
            response=json.dumps({"code": 404, "message": "No applications found"}),
            status=404,
            mimetype="application/json")
        return response

    cols = ["application_id", "motto", "date", "application_priority", "members"]
    data = [dict(zip(cols, i)) for i in result.data]
    for i in data:
        i["members"] = i["members"].split(":") if i["members"] is not None else []

    response = Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")
    return response


@tutor.route("/stueble/dates", methods=["POST"])
def submit_application_selection():
    """
    Saves the selection of stueble applications and makes it public
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only admins can change user role
    result = check_permissions(session_id=session_id, required_role=UserRole.TUTOR)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 401, "message": str(result.error)}),
            status=401,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 403, "message": "invalid permissions, need role tutor"}),
            status=403,
            mimetype="application/json")
        return response
    user_uuid = result.data["user_uuid"]

    data = request.get_json()
    application_uuids = data.get("application_ids", None)

    if not application_uuids:
        response = Response(
            response=json.dumps({"code": 403, "message": "application_ids must be specified"}),
            status=403,
            mimetype="application/json")
        return response
    
    query = sql.SQL("SELECT id, date_of_time FROM stueble.applications WHERE uuid IN ({application_uuids})").format(application_uuids=sql.SQL(', ').join(sql.Placeholder() * len(application_uuids)))
    result = db.custom_call(query=query, type_of_answer=db.ANSWER_TYPE.LIST_ANSWER, variables=application_uuids)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    
    if result.data is None:
        result._data = []

    data = [{"new_application_id": i[0], "date": i[1].strftime("%Y-%m-%d")} for i in result.data]

    if len(data) != len(set(i["date"] for i in data)):
        response = Response(
            response=json.dumps({"code": 400, "message": "Some applications have the same date"}),
            status=400,
            mimetype="application/json")
        return response

    result = db.select(
        table="stueble.dates",
        columns=["application_id"],
        specific_where=sql.SQL("application_id IN ({application_ids})").format(application_ids=sql.SQL(', ').join(sql.Placeholder() * len(application_uuids))),
        variables=[i["new_application_id"] for i in data]
    )

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    
    no_informing = set(i["application_id"] for i in result.data)  # application ids that are already in the database, so no informing is needed
    informing = [i["new_application_id"] for i in data if i["new_application_id"] not in no_informing]  # application ids that are not in the database, so informing is needed

    query = sql.SQL("INSERT INTO stueble.dates (application_id) VALUES {values} ON CONFLICT (application_id) DO UPDATE SET application_id = EXCLUDED.application_id").format(values=sql.SQL(', ').join(sql.SQL("(%s)") * len(data)))

    result = db.custom_call(query=query, type_of_answer=db.ANSWER_TYPE.NO_ANSWER, variables=[i["new_application_id"] for i in data])

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    

    response = applics.send_application_confirmation(application_ids=informing)
    if response.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(response.error)}),
            status=500,
            mimetype="application/json")
        return response
    
    result = db.select(
        table="stueble.applications",
        columns=["uuid"],
        conditions={"id": informing},
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER
    )

    if result.is_success:
        application_uuids = [str(i[0]) for i in result.data]
        asyncio.run(ws.broadcast(event="stuebleSelection", data=application_uuids, room=ws.Room.TUTOR_UPWARDS, skip_sid=session_id))

    return Response(
        response=json.dumps({"code": 200, "message": "Application selection submitted successfully", "data": data}),
        status=200,
        mimetype="application/json")