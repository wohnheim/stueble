"""
All sql-related functions for requests regarding stueble applications.
"""

import datetime as dt
from psycopg import sql
from backend.database import database as db
from backend.datatypes.funcres import FuncRes, Message, Status
from backend.datatypes.result import Result


def get_application_count(date: dt.date | None = None) -> FuncRes:
    """
    Receive the count of applications for a stueble date. If no date is specified, return information about all dates, that don't lie in the past.
    """

    query = sql.SQL("SELECT COUNT(id) FROM stueble.applications WHERE date {comparison} {date} {additional};").format(
        comparison=sql.SQL("<=" if date is None else "="),
        date=sql.SQL("NOW()") if date is None else sql.Placeholder(),
        additional=sql.SQL("GROUP BY date ORDER BY date ASC" if date is None else "")
    )

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER if date is None else db.ANSWER_TYPE.SINGLE_ANSWER,
        variables=(date.isoformat(),) if date is not None else None
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Get Application Count Error",
                            type="error",
                            category="Get Application Count",
                            code=500)
        )

    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Get Application Count Success",
                        type="success",
                        category="Get Application Count",
                        code=200)
    )


def get_applications(user_id: int) -> Result:
    """
    Get all current or future applications for a user.
    The result is ordered by date, application_priority and application group.

    Args:
        user_id (int): The id of the user for which the applications should be retrieved.
    Returns:
        Result: A Result object containing a list of applications or an error message.
    """
    columns = ["uuid", "date", "motto", "application_priority", "application_group"]
    query = sql.SQL("WITH a (application_group) AS (SELECT application_group FROM stueble.applicants WHERE user_id = {user_id}) \" \
                    \
                    SELECT {columns} \
                    FROM stueble.applications \
                    WHERE application_group IN (SELECT application_group FROM a) AND date >= CURRENT_DATE \
                    ORDER BY date, application_priority, application_group").format(
                        columns=sql.SQL(", ").join(sql.Identifier(col) for col in columns),
                        user_id=sql.Placeholder())
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[user_id]
    )
    if result.is_success:
        result.data = [{key if key != "uuid" else "id": value for key, value in zip(columns, entry)} for entry in result.data] # type: ignore

    return result


def send_application(motto: str, hosts: list[str], dates: list[tuple[str, int]]) -> FuncRes:
    """
    Send an application for the stueble. The application will be sent for all specified dates and priorities.

    Args:
        motto (str): The motto of the application.
        hosts (list[str | uuid.UUID]): A list of host ids or names for the application.
        dates (list[tuple[str, int]]): A list of tuples containing the date and application_priority for the application.

    Returns:
        FuncRes: A FuncRes object containing a success message or an error message.
    """

    query = sql.SQL("SELECT user_uuid \
                    FROM users \
                    WHERE user_uuid IN ({hosts}) AND user_role != 'extern'").format(
                        hosts=sql.SQL(", ").join(sql.Placeholder() * len(hosts))
                        )
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=hosts
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Error",
                            type="error",
                            category="Send Application",
                            code=500),
            user_warning=str(result.error)
        )
    
    found_users = result.data
    if len(found_users) != len(hosts):
        return FuncRes(
            error=ValueError("Not all specified hosts were found or some hosts are extern users."),
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Error",
                            type="error",
                            category="Send Application",
                            code=400),
            user_warning="Some hosts not found or are extern users"
        )
    
    current_group_hash = "-".join(sorted(hosts))
    query = sql.SQL("SELECT application_group FROM sql.applicants WHERE group_hash = {current_group}").format(current_group=sql.Placeholder())
    result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            variables=[current_group_hash]
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Error",
                            type="error",
                            category="Send Application",
                            code=500),
            user_warning=str(result.error)
        )
    
    group = result.data

    value = lambda : sql.SQL("((SELECT id \
                             FROM users \
                             WHERE user_uuid = {user_uuid}), {group}, {group_hash})").format(
                                 user_uuid = sql.Placeholder(),
                                 group=sql.Placeholder(),
                                 group_hash=sql.Placeholder())
    application = lambda : sql.SQL("({motto}, {date}, {application_priority}, a.application_group)").format(
        motto=sql.Placeholder(),
        date=sql.Placeholder(),
        application_priority=sql.Placeholder())

    query = sql.SQL("""
    WITH a (application_group) AS (
    INSERT INTO stueble.applicants (user_id, application_group, group_hash) VALUES {values}
    RETURNING application_group)

    INSERT INTO stueble.applications (motto, date, application_priority, application_group) VALUES {applications}
    RETURNING date, uuid;
    """).format(
        values=sql.SQL(", ").join(value() for _ in hosts),
        applications=sql.SQL(", ").join(application() for _ in dates)
    )
    result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
            variables=[ e for i in hosts for e in [i, group, current_group_hash]] + [e for i in dates for e in [motto, i[0], i[1]]]
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Get Hosts Error",
                            type="error",
                            category="Send Application",
                            code=500),
            user_warning=str(result.error)
        )
    
    return FuncRes(
        data=result.data,
        status=Status.FULL_SUCCESS,
        message=Message(name="Send Application Success",
                        type="success",
                        category="Send Application",
                        code=200)
    )


def delete_application(application_uuid: int, user_id: int) -> FuncRes:
    """
    Delete an application for the stueble.

    Args:
        application_uuid (int): The UUID of the application to delete.
        user_id (int): The id of the user deleting the application.
    Returns:
        FuncRes: A FuncRes object containing a success message or an error message.
    """

    result = db.select(
        table="stueble.applications",
        columns=["application_group"],
        conditions={"uuid": application_uuid},
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Get Application Error",
                            type="error",
                            category="Delete Application",
                            code=500),
            user_warning=str(result.error)
        )
    
    application_group = result.data

    if application_group is None:
        return FuncRes(
            error=ValueError("Application not found."),
            status=Status.FULL_ERROR,
            message=Message(name="Get Application Error",
                            type="error",
                            category="Delete Application",
                            code=404),
            user_warning="application not found"
        )
    
    result = db.select(
        table="stueble.applicants",
        columns=["id"],
        conditions={"application_group": application_group, "user_id": user_id},
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Get Applicant Error",
                            type="error",
                            category="Delete Application",
                            code=500),
            user_warning=str(result.error)
        )
    
    if result.data is None:
        return FuncRes(
            error=ValueError("User not entitled to delete this application."),
            status=Status.FULL_ERROR,
            message=Message(name="Get Applicant Error",
                            type="error",
                            category="Delete Application",
                            code=403),
            user_warning="Not entitled to delete this application"
        )

    result = db.delete(
        table="stueble.applications",
        conditions={"uuid": application_uuid}
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Delete Application Error",
                            type="error",
                            category="Delete Application",
                            code=500),
            user_warning=str(result.error)
        )
    
    return FuncRes(
        status=Status.FULL_SUCCESS,
        message=Message(name="Delete Application Success",
                        type="success",
                        category="Delete Application",
                        code=204)
    )