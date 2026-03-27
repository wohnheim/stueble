# TODO: check, whether user is kicked from stueble_guest_list when promoted to host
# TODO: forbid to remove host capabilities during stueble since: user -> present -> host -> host_removed, now not on guest list any more

import asyncio
import json

from flask import Flask, Response, request

from backend.endpoints import (
    auth,
    guest,
    tutor,
    host,
    user,
    application,
    event,
)

from backend import websocket as ws
from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import (
    applications,
    configs,
    motto,
    users,
)
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions
from backend.basic_functions import camel_to_snake_case, snake_to_camel_case


# NOTE frontend barely ever gets the real user role, rather just gets intern / extern

# initialize flask app
app = Flask(__name__)
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/users")
app.register_blueprint(tutor, url_prefix="/tutors")

app.register_blueprint(event, url_prefix="/events")

app.register_blueprint(host, url_prefix="/stueble/hosts")
app.register_blueprint(guest, url_prefix="/stueble/guests")
app.register_blueprint(application, url_prefix="/stueble/applications")


"""
Motto management (GET via WebSocket)
"""

# TODO allow date changes
@app.route("/motto", methods=["POST"])
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

"""
Hosts management (Changes via WebSocket)
"""

@app.route("/tutors", methods=["PUT", "DELETE"])
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
    tutors_data = [{"id": i[0], "firstName": i[1], "lastName": i[2], "residence": i[3], "user_role": UserRole(i[4]), "user_uuid": i[5]} for i in tutors_data]

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

@app.route("/hosts", methods=["PUT", "DELETE"])
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
    stueble_id = result.data[2]

    # stueble_id is the id of the current stueble, therefore also delete the host priviledges from users

    result = users.get_users(user_uuids=user_uuids, keywords=["user_uuid", "first_name", "last_name", "residence", "user_role"])
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    hosts_data = result.data
    hosts_data = [{"id": i[0], "firstName": i[1], "lastName": i[2], "residence": i[3]} for i in hosts_data if i[4] == ('user' if request.method == "PUT" else 'host')]
    if len(hosts_data) != len(user_uuids):
        response = Response(
            response=json.dumps({"code": 404, "message": "Tutoren und Admins können nicht zu Hosts gemacht werden"}), # "Not all users found"}),
            status=404,
            mimetype="application/json")
        return response

    result = motto.update_hosts(stueble_id=stueble_id, method="add" if request.method == "PUT" else "remove", user_uuids=user_uuids)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    user_ids = result.data

    # stueble_id is the id of the current stueble, therefore also delete the host priviledges from users
    if request.method == "DELETE":
        result = db.custom_call(query="UPDATE users SET user_role = 'user' WHERE id IN %s AND user_role = 'host'", type_of_answer=db.ANSWER_TYPE.NO_ANSWER, variables=(tuple(user_ids),))
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response
    else:
        result = db.custom_call(query="UPDATE users SET user_role = 'host' WHERE id IN %s AND user_role = 'user'", type_of_answer=db.ANSWER_TYPE.NO_ANSWER, variables=(tuple(user_ids),))
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
        variables=tuple(user_ids)
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



"""
Config management
"""

@app.route("/config", methods=["GET", "POST"])
def config():
    """
    get or update config values
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only admins can change config values
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

    if request.method == "POST":
        data = request.get_json()

        case_statements = '\n'.join(["WHEN %s THEN %s" for _ in range (len(data))])
        keys = tuple(camel_to_snake_case(key) for key in data.keys())
        values = tuple(value for value in data.values())

        params = [elem for i in zip(keys, values) for elem in i] + [tuple(keys)]

        query = f"""UPDATE configurations
        SET value = CASE key
        {case_statements}
        END
        WHERE key IN %s"""
        result = db.custom_call(query=query,
                                type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
                                variables=params)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response

        # send websocket message to all admins
        # asyncio.run(ws.broadcast(event="configUpdate", data=data, room=ws.Room.ADMINS, skip_sid=session_id))
    # Method GET & POST
    result = configs.get_all_configurations()

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    response = Response(
        response=json.dumps({snake_to_camel_case(key): value for key, value in result.data.items()}),
        status=200,
        mimetype="application/json")
    return response


"""
Stueble dates
"""

@app.route("/stueble/stueble_dates", methods=["GET"])
def stueble_dates():
    """
    Get the dates and the number of applications for that date of stueble
    """

    date = request.args.get("date", None)

    return applications.get_application_count(date=date)



"""
Internal
"""

@app.route("/websocket_local", methods=["POST"])
def websocket_change():
    """
    receive data from websocket_runner and send it to all connected clients
    """
    if request.remote_addr != "127.0.0.1":
        response = Response(
            response=json.dumps({"code": 401, "message": "Unauthorized, only local requests are allowed"}),
            status=401,
            mimetype="application/json")
        return response

    # load data
    data = request.get_json()
    first_name = data.get("first_name", None)
    last_name = data.get("last_name", None)
    user_uuid = data.get("user_uuid", None)
    stueble_id = data.get("stuebleId", None)
    # event = data.get("event", None)
    if first_name is None or last_name is None or user_uuid is None: # or event is None:
        response = Response(
            response=json.dumps({"code": 400, "message": f"first_name, last_name and user_uuid must be specified"}),
            status=400,
            mimetype="application/json")
        return response

    asyncio.run(ws.broadcast(event="guestRemoved", data=user_uuid))

    response = Response(
        status=200)
    return response