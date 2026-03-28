
import json
from datetime import date

from backend.datatypes.stueble_types import UserRole
from backend.datatypes.funcres import FuncRes, Message, Status
from backend.sql_connection import motto
from backend.database import database as db
from backend.sql_connection.common_functions import check_permissions 


def get_hosts_tutors(session_id: str, path: str, date: date | None = None) -> FuncRes:
    """
    Get the hosts for a given date or tutors.

    Args:
        session_id (str): The session id of the user.
        path (str): The path of the request, either "/hosts" or "/tutors".
        date (date | None): The date for which to get the hosts, if path is "/hosts". If path is "/tutors", this parameter is ignored.
    Returns:
        FuncRes: The result of the operation, containing the list of hosts or tutors, or an error message.
    """

    # check permissions, since only hosts or above can change user role
    result = check_permissions(session_id=session_id, required_role=UserRole.HOST)
    if result.is_error:
        response = FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Tutors Error",
                            type="error",
                            category="Get Hosts Tutors",
                            code=401),
            user_warning=str(result.error)
        )
        return response
    if result.data["allowed"] is False:
        response = FuncRes(
            error="invalid permissions, need role host or above",
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Tutors Error",
                            type="error",
                            category="Get Hosts Tutors",
                            code=403),
            user_warning="invalid permissions, need role host or above"
        )
        return response

    if path == "/tutors":
        query = """SELECT user_uuid, first_name, last_name, residence FROM users WHERE user_role = 'tutor'"""
        result = db.custom_call(query=query,
                                type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)
        if result.is_error:
            response = FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Get Tutors Error",
                                type="error",
                                category="Get Tutors",
                                code=500),
                user_warning=str(result.error)
            )
            return response
        tutors = [{"id": i[0], "firstName": i[1], "lastName": i[2], "residence": i[3]} for i in result.data]
        response = FuncRes(
            data=tutors,
            status=Status.FULL_SUCCESS,
            message=Message(name="Get Tutors Success",
                            type="success",
                            category="Get Tutors",
                            code=200),
            user_warning=None
        )
        return response

    result = motto.get_info(date=date)
    if result.is_error:
        response = FuncRes(
            message=Message(name="Get Hosts Tutors Error",
                            type="error",
                            category="Get Hosts Tutors",
                            code=result.message.code),
        )

        # through marking as full_success an empty list will be returned in backend/api/host.py - get_hosts_tutors
        if result.message.code == 404:
            response._data = []
            response._status = Status.FULL_SUCCESS
        else:
            response._status = Status.FULL_ERROR
            response._error = str(result.error)
            response._user_warning = str(result.error)
        return response

    # NOTE: can't occurr, but still added in case of redesign of get_info function
    if result.data is None:
        response = FuncRes(
            error="no stueble party found",
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Tutors Error",
                            type="error",
                            category="Get Hosts Tutors",
                            code=404),
            user_warning="no stueble party found"
        )
        return response
    stueble_id = result.data["id"]

    result = motto.get_hosts(stueble_id=stueble_id)
    if result.is_error:
        response = FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Tutors Error",
                            type="error",
                            category="Get Hosts Tutors",
                            code=500),
            user_warning=str(result.error)
        )
        return response

    result._data = [{"id": str(i["user_uuid"]), "firstName": i["first_name"], "lastName": i["last_name"], "residence": i["residence"]} for i in result.data]

    response = FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Hosts Tutors Success",
                        type="success",
                        category="Get Hosts Tutors",
                        code=200),
        user_warning=None
    )
    return response