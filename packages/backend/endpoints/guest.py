"""
Guest management routes for adding and removing guests to the guest list of the stueble, signing up for a stueble party and inviting extern guests via email with a qr-code.
"""

import asyncio
import datetime
import json

from flask import Blueprint, request, Response

from backend import hash_pwd as hp, websocket as ws, qr_code as qr
from backend.datatypes.stueble_types import *
from backend.google_functions import email as mail
from backend.sql_connection import (
    events,
    guest_events,
    motto,
    sessions,
    users,
)
from backend.database import database as db
from backend.mail_assets import templates
from backend.sql_connection.common_functions import check_permissions
from backend.basic_functions import *


guest = Blueprint("guests", __name__)

# NOTE: if no stueble is happening today or yesterday, an empty list is returned
@guest.route("/", methods=["GET"])
def guests():
    """
    returns list of all guests
    """

    session_id = request.cookies.get("SID", None)
    if session_id is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only hosts can add guests
    result = check_permissions(session_id=session_id, required_role=UserRole.HOST)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    if result.data["allowed"] is False:
        response = Response(
            response=json.dumps({"code": 401, "message": "invalid permissions, need role host or above"}),
            status=401,
            mimetype="application/json")
        return response

    # get guest list
    result = guest_events.guest_list()
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    response = Response(
        response=json.dumps(result.data),
        status=200,
        mimetype="application/json"
    )
    return response

@guest.route("/", methods=["POST"])
def guest_change():
    """
    add / remove a guest to the guest_list of present people
    """

    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    user_uuid = data.get("id", None)
    present = data.get("present", None)

    if session_id is None or user_uuid is None or present is None:
        response = Response(
            response=json.dumps({"code": 401, "message": "The session id, uuid, present must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only hosts can add guests
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

    event_type = EventType.ARRIVE if present else EventType.LEAVE

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified", "user_role", "id"]
    data = users.get_user(
        user_uuid=user_uuid,
        columns=keywords,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)

    if data.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(data.error)}),
            status=500,
            mimetype="application/json")
        return response

    guest_user_id = data.data["id"]
    user_info= {key: value for key, value in data.data.items() if key != "id"}

    if event_type == EventType.ARRIVE:
        # verify guest if not verified yet
        if user_info["verified"] is False:
            result = users.update_user(user_uuid_key=user_uuid, 
                                       verified=True)
            if result.is_error:
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result.error)}),
                    status=500,
                    mimetype="application/json")
                return response

    # change guest status to arrive / leave
    result = guest_events.change_guest(user_uuid=user_uuid, event_type=event_type)
    if result.is_error:
        error = {"code": 500, "message": str(result.error)}
        if all(i in error["message"] for i in ["Inviter of user", "is not registered for stueble"]):
            error = {"code": 400, "message": "Inviter not registered to stueble any more"}
        elif "is not registered for stueble" in error["message"]:
            error = {"code": 400, "message": "User not registered to stueble"}
        elif "; code: " in error["message"]:
            error_message, status_code = error["message"].split("; code: ")
            status_code = int(status_code.split("\n")[0])
            error = {"code": status_code, "message": error_message}
        response = Response(
            response=json.dumps(error),
            status=error["code"],
            mimetype="application/json")
        return response

    user_info["user_role"] = FrontendUserRole.EXTERN if user_info["user_role"] == "extern" else FrontendUserRole.INTERN

    user_data = {
            "id": user_uuid,
            "present": present,
            "firstName": user_info["first_name"],
            "lastName": user_info["last_name"],
            "extern": user_info["user_role"] == FrontendUserRole.EXTERN}

    if user_info["user_role"] == FrontendUserRole.INTERN:
        user_data["roomNumber"] = user_info["room"]
        user_data["residence"] = user_info["residence"]
        user_data["verified"] = True

    message = user_data

    result = sessions.get_session_ids(user_id=guest_user_id, uuid=True)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    guest_session_ids = result.data

    # send a websocket message to all hosts that the guest list changed
    asyncio.run(ws.broadcast(event="guestModified", data=message)) # don't skip_sid for guestModified

    # send a websocket message to the user
    for sess_id in guest_session_ids:
        asyncio.run(ws.stueble_status(session_id=sess_id, registered=True, present=present))

    # return 204
    response = Response(
        status=204)
    return response

# TODO broadcast add remove user
@guest.route("/", methods=["PUT", "DELETE"])
def attend_stueble():
    """
    sign up for a stueble party
    """

    # load data
    session_id = request.cookies.get("SID", None)
    try:
        data = request.get_json()
        date = data.get("date", None)
        user_uuid = data.get("id", None)
    except:
        date = None
        user_uuid = None

    required_role = UserRole.USER
    if user_uuid is not None:
        required_role = UserRole.HOST

    if date is None:
        result = motto.get_info()
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response
        if result.data is None:
            response = Response(
                response=json.dumps({"code": 400, "message": "No stueble is happening in the next time"}),
                status=400,
                mimetype="application/json")
            return response
        date = result.data["motto"]

    if session_id is None or date is None:
        response = Response(
            response=json.dumps({"code": 401, "message": f"The session id and date must be specified"}),
            status=401,
            mimetype="application/json")
        return response


    # check permissions, since only hosts can add guests
    result = check_permissions(session_id=session_id, required_role=required_role)

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

    if user_uuid is None:
        user_id = result.data["user_id"]
        user_uuid = result.data["user_uuid"]
    else:
        result = users.get_user(user_uuid=user_uuid, columns=["id", "user_uuid"], type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response
        user_id = result.data["id"]
        user_uuid = result.data["user_uuid"]

    # get all sessions of user
    result = sessions.get_session_ids(user_id=user_id, uuid=True)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    guest_session_ids = result.data

    result = motto.get_info(date=date)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    stueble_id = result.data["id"]

    if request.method == "PUT":
        result = events.add_guest(
            user_id=user_id,
            stueble_id=stueble_id)
    else:
        result = events.remove_guest(
            user_id=user_id,
            stueble_id=stueble_id)

    if result.is_error:
        status_code = 500
        error = str(result.error)
        if "; code: " in str(result.error):
            error, status_code = str(result.error).split("; code: ")
            status_code = status_code.split("\n")[0]
            status_code = int(status_code)
        response = Response(
            response=json.dumps({"code": status_code, "message": error}),
            status=status_code,
            mimetype="application/json")
        return response

    if request.method == "PUT":
        # TODO unneccessary
        timestamp = int(datetime.datetime.now().timestamp())

        information = {"id": user_uuid, "timestamp": timestamp, "extern": False}

        signature = hp.create_signature(message=information)

        data = {"data":
                    information,
                "signature": signature}
        response = Response(
            response=json.dumps(data),
            status=200,
            mimetype="application/json")

        # get user data
        keywords = ["first_name", "last_name", "room", "residence", "verified"]
        result = users.get_user(
            user_id=user_id,
            columns=keywords,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)

        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response

        user_info = {key: value for key, value in zip(keywords, result.data)}
        user_info["user_role"] = FrontendUserRole.INTERN

        user_data = {
            "id": user_uuid,
            "present": False,
            "firstName": user_info["first_name"],
            "lastName": user_info["last_name"],
            "extern": False,
            "roomNumber": user_info["room"],
            "residence": user_info["residence"],
            "verified": True if user_info["verified"] is not None else False}
    else:
        response = Response(
            status=204)
    action_type = Action_Type("guestAdded" if request.method == "PUT" else "guestRemoved")

    # send a websocket message to all hosts that the guest list changed
    asyncio.run(ws.broadcast(event=action_type.value, data=user_data if request.method == "PUT" else user_uuid, skip_sid=session_id)) # type: ignore # pylint: disable=E0606

    # send a websocket message to the user
    for sess_id in guest_session_ids:
        asyncio.run(ws.stueble_status(session_id=sess_id, date=date, registered=True if request.method == "PUT" else False, present=False))

    return response

# NOTE: extern guest can be multiple times in table users since only first_name, last_name are specified, which are not unique
@guest.route("//invitee", methods=["PUT", "DELETE"])
def invitee():
    """
    invite a friend and share a qr-code
    """
    # load data
    data = request.get_json()
    session_id = request.cookies.get("SID", None)
    date = data.get("date", None)
    invitee_first_name = data.get("firstName", None)
    invitee_last_name = data.get("lastName", None)
    invitee_email = data.get("email", None)
    if invitee_email is not None:
        try:
            invitee_email = Email(invitee_email)
        except ValueError:
            response = Response(
                response=json.dumps({"code": 400, "message": "Invalid email format"}),
                status=400,
                mimetype="application/json")
            return response

    if any(i is None for i in [session_id, invitee_first_name, invitee_last_name, invitee_email]):
        response = Response(
            response=json.dumps({"code": 401,
                "message": f"session_id, date, invitee_first_name, invitee_last_name, invitee_email must be specified"}),
            status=401,
            mimetype="application/json")
        return response

    # check permissions, since only users can add guests
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

    user_role = UserRole(result.data["user_role"])

    user_id = result.data["user_id"]
    first_name = result.data["first_name"]
    last_name = result.data["last_name"]

    if user_role < UserRole.HOST:
        result = users.check_user_guest_list(user_id=user_id)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response
        if result.data is False:
            response = Response(
                response=json.dumps({"code": 403, "message": "You need to be on the guest list to invite someone"}),
                status=403,
                mimetype="application/json")
            return response

        # check, whether user is present
        result = users.check_user_present(user_id=user_id)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                    status=500,
                    mimetype="application/json")
            return response
        present = result.data
    else:
        present = False

    # get all sessions for user
    result = sessions.get_session_ids(user_id=user_id, uuid=True)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    guest_session_ids = result.data

    result = motto.get_info(date=date)
    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    stueble_id = result.data["id"]
    motto_name = result.data["motto"]
    stueble_date = result.data["date"]
    stueble_date = stueble_date.strftime("%d.%m.%Y")

    if request.method == "PUT":
        # add user to table
        result = users.add_user(
            user_role=UserRole.EXTERN,
            first_name=invitee_first_name,
            last_name=invitee_last_name,
            returning_column="id, user_uuid") # id, user_uuid on purpose like that

    else:
        # get user to remove
        result = users.get_user(
            columns=["id", "user_uuid"],
            conditions={"first_name": invitee_first_name, "last_name": invitee_last_name, "user_role": UserRole.EXTERN.value},
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response
    if request.method == "PUT":
        created_invitee_id = result.data["id"]

    if request.method == "DELETE":
        possible_users = result.data
        if len(possible_users) == 0:
            response = Response(
                response=json.dumps({"code": 404, "message": "No such user found"}),
                status=404,
                mimetype="application/json")
            return response
        users_list = []
        for i in possible_users:
            query = """
            SELECT user_id FROM stueble.events
            WHERE user_id = %s AND stueble_id = %s AND event_type = 'add' AND invited_by = %s
            ORDER BY submitted DESC LIMIT 1"""
            result = db.custom_call(query=query,
                                    type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
                                    variables=[i[0], stueble_id, user_id])
            if result.is_error:
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result.error)}),
                    status=500,
                    mimetype="application/json")
                return response
            if result.data is None:
                continue
            possible_invitee_id = result.data[0][0]

            result = users.get_user(user_id=possible_invitee_id,
                                    columns=["user_uuid"],
                                    type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
            if result.is_error:
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result.error)}),
                    status=500,
                    mimetype="application/json")
                return response
            if result.data is None:
                response = Response(
                    response=json.dumps({"code": 500, "message": "Data integrity error, user not found"}),
                    status=500,
                    mimetype="application/json")
                return response
            possible_invitee_uuid = result.data["id"]
            users_list.append({"invitee_id": possible_invitee_id, "invitee_uuid": possible_invitee_uuid})
        if len(users_list) == 0:
            response = Response(
                response=json.dumps({"code": 401, "message": "No such user found"}),
                status=401,
                mimetype="application/json")
            return response
        if len(users_list) > 1:
            response = Response(
                response=json.dumps({"code": 409, "message": "Multiple users found, please contact an admin"}),
                status=409,
                mimetype="application/json")
            return response
        invitee_id = users_list[0]["invitee_id"]
        invitee_uuid = users_list[0]["invitee_uuid"]
    else:
        invitee_id = result.data["id"]
        invitee_uuid = result.data["user_uuid"]

    if request.method == "PUT":
        result = events.add_guest(
            user_id=invitee_id,
            stueble_id=stueble_id,
            invited_by=user_id)
    else:
        result = events.remove_guest(
            user_id=invitee_id,
            stueble_id=stueble_id)

    if result.is_error:
        status_code = 500
        error = str(result.error)
        if "; code: " in str(result.error):
            error, status_code = str(result.error).split("; code: ")
            status_code = status_code.split("\n")[0]
            status_code = int(status_code)
        if request.method == "PUT":
            result = db.delete(table="users", conditions={"id": created_invitee_id}) # type: ignore
            if result.is_error:
                response = Response(
                    response=json.dumps({"code": 500, "message": str(result.error)}),
                    status=500,
                    mimetype="application/json")
                return response
        response = Response(
            response=json.dumps({"code": status_code, "message": error}),
            status=status_code,
            mimetype="application/json")
        return response

    if request.method == "PUT":
        timestamp = int(datetime.datetime.now().timestamp())

        information = {"id": invitee_uuid, "timestamp": timestamp, "extern": True}

        result = hp.create_signature(message=information)
        if result.is_error:
            response = Response(
                response=json.dumps({"code": 500, "message": str(result.error)}),
                status=500,
                mimetype="application/json")
            return response

        signature = result.data

        data = {"data":information,
                "signature": signature}

    # get user data
    keywords = ["first_name", "last_name", "room", "residence", "verified"]
    result = users.get_user(
        user_id=invitee_id,
        columns=keywords,
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)

    if result.is_error:
        response = Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json")
        return response

    invitee_info = {key: value for key, value in zip(keywords, result.data)}
    invitee_info["user_role"] = FrontendUserRole.EXTERN

    invitee_data = {
        "id": invitee_uuid,
        "present": False,
        "firstName": invitee_info["first_name"],
        "lastName": invitee_info["last_name"],
        "extern": True}

    action_type = Action_Type("guestAdded") if request.method == "PUT" else Action_Type("guestRemoved")

    # send a websocket message to all hosts that the guest list changed
    asyncio.run(ws.broadcast(event=action_type.value, data=invitee_data)) # don't skip_sid for guestModified

    # send a websocket message to the user
    for sess_id in guest_session_ids:
        asyncio.run(ws.stueble_status(session_id=sess_id, date=date, registered=True, present=present))

    if request.method == "DELETE":
        response = Response(
            status=204)
        return response

    if invitee_email is not None:
        qr_code = qr.generate(json.dumps(data), size=400, rounded_edges=30)
        result = templates.stueble_guest(invitee_first_name=invitee_first_name,
                                invitee_last_name=invitee_last_name,
                                first_name=first_name,
                                last_name=last_name,
                                stueble_date=stueble_date,
                                motto_name=motto_name,
                                qr_code=qr_code)
        mail.send_mail(invitee_email, result["subject"], result["body"], html=True, images=result["images"])

    if request.method == "PUT":
        response = Response(
            status=204)
        return response

    response = Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json")
    return response