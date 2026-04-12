# TODO: check, whether user is kicked from stueble_guest_list when promoted to host
# TODO: forbid to remove host capabilities during stueble since: user -> present -> host -> host_removed, now not on guest list any more

import asyncio
import json
from datetime import datetime as dt

from flask import Flask, Response, request
from psycopg import sql

from backend.endpoints import (
    auth,
    guest,
    tutor,
    host,
    user,
    application,
    event,
    motto
)

from backend import websocket as ws
from backend.datatypes.stueble_types import UserRole
from backend.sql_connection import applications, configs
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions
from backend.basic_functions import camel_to_snake_case, snake_to_camel_case


# NOTE frontend barely ever gets the real user role, rather just gets intern / extern

# initialize flask app
app = Flask(__name__)
app.register_blueprint(auth.auth, url_prefix="/auth")
app.register_blueprint(user.user, url_prefix="/user")
app.register_blueprint(tutor.tutor, url_prefix="/tutors")

app.register_blueprint(event.event, url_prefix="/events")

app.register_blueprint(host.host, url_prefix="/stueble/hosts")
app.register_blueprint(guest.guest, url_prefix="/stueble/guests")
app.register_blueprint(application.applic, url_prefix="/stueble/applications")
app.register_blueprint(motto.mo, url_prefix="/stueble/motto")


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

        case_statements = sql.SQL('\n').join([sql.SQL("WHEN %s THEN %s") for _ in range (len(data))])
        keys = tuple(camel_to_snake_case(key) for key in data.keys())
        values = tuple(value for value in data.values())

        params = [elem for i in zip(keys, values) for elem in i] + list(keys)

        query = sql.SQL("""UPDATE configurations
        SET value = CASE key
        {case_statements}
        END
        WHERE key IN ({keys})""").format(case_statements=case_statements, keys=sql.SQL(', ').join(sql.Placeholder() * len(keys)))
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

@app.route("/stueble/dates", methods=["GET"])
def get_available_dates():
    """
    Get the available dates for stueble
    """

    result = db.select(
        table="stueble.available_dates",
        columns=["date_of_time"],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER
    )

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    
    data = sorted([entry["date_of_time"].isoformat() for entry in result.data])
    return Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")


@app.route("/stueble/stueble_dates", methods=["GET"])
def stueble_dates():
    """
    Get the dates and the number of applications for that date of stueble
    """

    date = request.args.get("date", None)

    result = applications.get_application_count(date=dt.strptime(date, "%Y-%m-%d").date() if date is not None else None)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    return Response(
        response=json.dumps(result.data),
        status=200,
        mimetype="application/json")



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
    user_uuid = str(user_uuid) if user_uuid is not None else None
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