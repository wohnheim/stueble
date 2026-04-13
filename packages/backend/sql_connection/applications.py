"""
All sql-related functions for requests regarding stueble applications.
"""

import datetime as dt
from typing import Annotated
from psycopg import sql
from backend.database import database as db
from backend.datatypes.funcres import FuncRes, Message, Status
from backend.datatypes.result import Result
from backend.sql_connection import users
from backend.mail_assets import templates
from backend.google_functions import email as mail
from backend.datatypes.stueble_types import UserRole


def get_application_count(date: dt.date | None = None) -> FuncRes:
    """
    Receive the count of applications for a stueble date. If no date is specified, return information about all dates, that don't lie in the past.
    """

    query = sql.SQL("SELECT COUNT(id){date_identifier} FROM stueble.applications WHERE date_of_time {comparison} {date} {additional};").format(
        date_identifier=sql.SQL(", date_of_time") if date is None else sql.SQL(""),
        comparison=sql.SQL("<=" if date is None else "="),
        date=sql.SQL("NOW()") if date is None else sql.Placeholder(),
        additional=sql.SQL("GROUP BY date_of_time ORDER BY date_of_time ASC" if date is None else "")
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

    data = [{"date": entry[1].isoformat(), "count": entry[0]} for entry in result.data] if date is None else result.data[0]
    return FuncRes(
        data=result.data[0] if date is not None else data,
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
    columns = ["uuid", "date_of_time", "motto", "application_priority", "application_group", "description", "image"]
    query = sql.SQL("WITH a (application_group) AS (SELECT application_group FROM stueble.applicants WHERE user_id = {user_id}) \
                    \
                    SELECT {columns} \
                    FROM stueble.applications \
                    WHERE application_group IN (SELECT application_group FROM a) AND date_of_time >= CURRENT_DATE \
                    ORDER BY date_of_time, application_priority, application_group").format(
                        columns=sql.SQL(", ").join(sql.Identifier(col) for col in columns),
                        user_id=sql.Placeholder())
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[user_id]
    )
    if result.is_success:
        result._data = [{key if key != "uuid" else "id": value for key, value in zip(columns, entry)} for entry in result.data]

    return result


def send_application(motto: str, hosts: list[str] | None, dates: list[tuple[str, int]], description: str | None = None, image: str | None = None, automatic_priorities: bool = False) -> FuncRes:
    """
    Send an application for the stueble. The application will be sent for all specified dates and priorities.

    Args:
        motto (str): The motto of the application.
        hosts (list[str]): A list of host ids or names for the application.
        dates (list[tuple[str, int]]): A list of tuples containing the date and application_priority for the application.
        description (str | None): The description of the application.
        image (str | None): The image of the application.
        automatic_priorities (bool): Whether to automatically set priorities for the application. If True, all priorities have to be set to -1

    Returns:
        FuncRes: A FuncRes object containing a success message or an error message.
    """
    if hosts is not None:
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
        
        found_users = [str(i[0]) for i in result.data]
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
        
        current_group_hash = ":".join(sorted(hosts))
        query = sql.SQL("WITH ins AS ( \
                            INSERT INTO stueble.application_groups (group_hash) \
                            VALUES ({group_hash}) \
                            ON CONFLICT (group_hash) DO NOTHING \
                            RETURNING id) \
                        SELECT id FROM ins \
                        UNION ALL \
                        SELECT id FROM stueble.application_groups \
                        WHERE group_hash = {group_hash} AND NOT EXISTS (SELECT 1 FROM ins)").format(
            group_hash=sql.Placeholder()
        )
        result = db.custom_call(
                query=query,
                type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
                variables=[current_group_hash, current_group_hash]
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
        
        group = result.data[0]
    else:
        query = sql.SQL("INSERT INTO stueble.application_groups (group_hash) VALUES (NULL) RETURNING id").format()
        result = db.custom_call(
                query=query,
                type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
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
        group = result.data[0]

    if automatic_priorities is True:
        query = sql.SQL("SELECT COALESCE(MAX(application_priority), 0) FROM stueble.applications WHERE application_group = {group}").format(
            group=sql.Placeholder()
        )
        result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
            variables=[group]
        )
        if result.is_error:
            return FuncRes(
                error=result.error,
                status=Status.FULL_ERROR,
                message=Message(name="Get Priorities Error",
                                type="error",
                                category="Send Application",
                                code=500),
                user_warning=str(result.error)
            )
        
        max_priority = result.data[0] if result.data[0] is not None else 0
        dates = [(date, max_priority + i + 1) for i, (date, _) in enumerate(dates)]

    def applicant():
        return sql.SQL("((SELECT id \
                             FROM users \
                             WHERE user_uuid = {user_uuid}), {group})").format(
                                 user_uuid = sql.Placeholder(),
                                 group=sql.Placeholder())
    
    def application(group: str | None):
        return sql.SQL("({motto}, {date}, {application_priority}, {applic_group}, {description}, {image})").format(
            motto=sql.Placeholder(),
            date=sql.Placeholder(),
            application_priority=sql.Placeholder(),
            applic_group=sql.SQL("a.application_group") if group is None else sql.Placeholder(),
            description=sql.Placeholder() if description is not None else sql.SQL("NULL"),
            image=sql.Placeholder() if image is not None else sql.SQL("NULL")
        )

    # TODO: insert of application group above is not needed as already performed here
    query = sql.SQL("""
    {applic_insert}
    INSERT INTO stueble.applications (motto, date_of_time, application_priority, application_group, description, image) VALUES {applications}
    RETURNING date_of_time, uuid, id;
    """).format(
        applic_insert=sql.SQL("WITH a AS (INSERT INTO stueble.applicants (user_id, application_group) VALUES {values} ON CONFLICT DO NOTHING) ").format(values=sql.SQL(", ").join(applicant() for _ in hosts)) if hosts is not None else sql.SQL("").format(),
        applications=sql.SQL(", ").join(application(group) for _ in dates)
    )
    result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
            variables=([str(e) for i in found_users for e in [i, group]] if hosts is not None else []) + [ # type: ignore
                    str(e) for i in dates for e in [motto, i[0], i[1], group] + ([description] if description is not None else []) + ([image] if image is not None else [])
                    ]
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
    
    data = [{"date": entry[0].isoformat(), "id": str(entry[1]), "application_id": str(entry[2])} for entry in result.data]
    return FuncRes(
        data=data,
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
        result = users.get_user(user_id=user_id, columns=["user_role"])
        if result.is_error:
            return FuncRes(
                error=result.error,
                status=Status.FULL_ERROR,
                message=Message(name="Get User Error",
                                type="error",
                                category="Delete Application",
                                code=500),
                user_warning=str(result.error)
            )
        user_role = result.data["user_role"]
        if user_role < UserRole.TUTOR:
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

def update_application(
        application_uuid: int,
        user_id: int,
        motto: str | None = None,
        date: str | None = None,
        hosts: list[int] | None = None,
        description: str | None = None,
        image: str | None = None
        ) -> FuncRes:
    """
    Update an application for the stueble.
    
    Args:
        application_uuid (int): The UUID of the application to update.
        user_id (int): The id of the user updating the application.
        motto (str | None): The new motto of the application.
        date (str | None): The new date of the application.
        hosts (list[int] | None): The new host ids for the application.
        description (str | None): The new description of the application.
        image (str | None): The new image of the application.
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
                            category="Update Application",
                            code=500),
            user_warning="Failed to retrieve application information"
        )
    
    application_group = result.data["application_group"]

    if application_group is None:
        return FuncRes(
            error=ValueError("Application not found."),
            status=Status.FULL_ERROR,
            message=Message(name="Get Application Error",
                            type="error",
                            category="Update Application",
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
                            category="Update Application",
                            code=500),
            user_warning="Failed to retrieve applicant information"
        )

    if result.data is None:
        result = users.get_user(user_id=user_id, columns=["user_role"])
        if result.is_error:
            return FuncRes(
                error=result.error,
                status=Status.FULL_ERROR,
                message=Message(name="Get User Error",
                                type="error",
                                category="Delete Application",
                                code=500),
                user_warning=str(result.error)
            )
        user_role = result.data["user_role"]
        if UserRole(user_role) < UserRole.TUTOR:
            return FuncRes(
                error=ValueError("User not entitled to change this application."),
                status=Status.FULL_ERROR,
                message=Message(name="Get Applicant Error",
                                type="error",
                                category="Update Application",
                                code=403),
                user_warning="Not entitled to change this application"
            )

    if date is not None:
        result = db.select(
            table="stueble.dates",
            columns=["application_id"],
            conditions={"application_id": application_group},
            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
        )

        if result.is_error:
            return FuncRes(
                error=result.error,
                status=Status.FULL_ERROR,
                message=Message(name="Get Date Error",
                                type="error",
                                category="Update Application",
                                code=500),
                user_warning="Failed to retrieve date information"
            )

        if result.data is not None:
            return FuncRes(
                error=ValueError("Application already granted, date cannot be changed."),
                status=Status.FULL_ERROR,
                message=Message(name="Get Date Error",
                                type="error",
                                category="Update Application",
                                code=403),
                user_warning="Application already granted, date cannot be changed"
            )
    if hosts is not None and len(hosts) < 2:
        return FuncRes(
                error=ValueError("At least two hosts are required."),
                status=Status.FULL_ERROR,
                message=Message(name="Get Hosts Error",
                                type="error",
                                category="Update Application",
                                code=400),
                user_warning="At least two hosts are required"
            )

    new_application_group = None
    if hosts is not None:
        cont = False
        query = sql.SQL("INSERT INTO stueble.application_groups (group_hash) \
                        VALUES ({group_hash}) \
                        ON CONFLICT (group_hash) DO NOTHING RETURNING id").format(
                            group_hash=sql.Placeholder()
                        )
        result = db.custom_call(
                query=query,
                type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER,
                variables=[":".join(sorted(str(h) for h in hosts))]
        )

        if result.is_error:
            return FuncRes(
                error=result.error,
                status=Status.FULL_ERROR,
                message=Message(name="Get Hosts Error",
                                type="error",
                                category="Update Application",
                                code=500),
                user_warning="Failed to update hosts"
            )
        application_group = result.data[0] if result.data is not None else None
        if result.data is None:
            result = db.select(
                table="stueble.application_groups",
                columns=["id"],
                conditions={"group_hash": ":".join(sorted(str(h) for h in hosts))},
                type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER
            )

            if result.is_error:
                return FuncRes(
                    error=result.error,
                    status=Status.FULL_ERROR,
                    message=Message(name="Get Hosts Error",
                                    type="error",
                                    category="Update Application",
                                    code=500),
                    user_warning="Failed to update hosts"
                )

            if result.data is None:
                return FuncRes(
                    error="Update Application Error",
                    status=Status.FULL_ERROR,
                    message=Message(name="Get Hosts Error",
                                    type="error",
                                    category="Update Application",
                                    code=500),
                    user_warning="Failed to update hosts"
                )
            new_application_group = result.data["id"]
            if new_application_group == application_group:
                cont = True
        if cont is True:
            query = sql.SQL("INSERT INTO stueble.applicants (user_id, application_group) VALUES {values}").format(
                sql.SQL(", ").join(sql.SQL("({user_id}, {group})").format(
                    user_id=sql.Placeholder(),
                    group=sql.Placeholder()
                ) for _ in hosts)
            )
            result = db.custom_call(
                query=query,
                type_of_answer=db.ANSWER_TYPE.NO_ANSWER,
                variables=[str(e) for i in hosts for e in [i, new_application_group]]
            )
            if result.is_error:
                return FuncRes(
                    error=result.error,
                    status=Status.FULL_ERROR,
                    message=Message(name="Update Application Error",
                                    type="error",
                                    category="Update Application",
                                    code=500),
                    user_warning="Failed to update hosts"
                )

    result = db.update(
        table="stueble.applications",
        columns={k: v for k, v in {
            "motto": motto,
            "date_of_time": date,
            "description": description,
            "image": image,
            "application_group": new_application_group if new_application_group != application_group else None
            }.items() if v is not None},
        conditions={"uuid": application_uuid}
    )

    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Update Application Error",
                            type="error",
                            category="Update Application",
                            code=500),
            user_warning="Failed to update application"
        )
    
    return FuncRes(
        status=Status.FULL_SUCCESS,
        message=Message(name="Update Application Success",
                        type="success",
                        category="Update Application",
                        code=200)
    )

def send_application_confirmation(application_uuids: Annotated[list[str] | None, "Explicit with application_ids"] = None, application_ids: Annotated[list[int] | None, "Explicit with application_uuids"] = None) -> FuncRes:
    """
    Send a confirmation for a granted application for the stueble.

    Args:
        application_uuids (list[str]): The UUIDs of the applications to confirm.
        application_ids (list[int]): The ids of the applications to confirm.
    Returns:
        FuncRes: A FuncRes object containing a success message or an error message.
    """

    if (application_uuids is None and application_ids is None) or (application_uuids is not None and application_ids is not None):
        return FuncRes(
            error=ValueError("Either application_uuids or application_ids must be provided, but not both."),
            status=Status.FULL_ERROR,
            message=Message(name="Send Application Confirmation Error",
                            type="error",
                            category="Send Application Confirmation",
                            code=500),
            user_warning="Either application_uuids or application_ids must be provided, but not both."
        )

    query = sql.SQL("SELECT u.id, string_agg(DISTINCT a.uuid::text, ',') AS application_uuids \
                    FROM stueble.applications a \
                    JOIN stueble.applicants ap ON a.application_group = ap.application_group \
                    JOIN users u ON ap.user_id = u.id \
                    WHERE a.{application_column} IN ({application_identifiers}) \
                    GROUP BY u.id").format(
        application_column=sql.Identifier("uuid") if application_uuids is not None else sql.Identifier("id"),
        application_identifiers=sql.SQL(', ').join(sql.Placeholder() * len(application_uuids if application_uuids is not None else application_ids)) # type: ignore
    )

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=application_uuids if application_uuids is not None else application_ids
    )
    if result.is_error:
        return FuncRes(
            error=result.error,
            status=Status.FULL_ERROR,
            message=Message(name="Get Application Users Error",
                            type="error",
                            category="Send Application Confirmation",
                            code=500)        )
    
    data = result.data
    if data is None:
        data = []
    
    data = [{"user_id": entry[0], "application_uuids": entry[1].split(",")} for entry in data]

    for entry in data:
        user_id = entry["user_id"]
        applic_uuids = entry["application_uuids"]
        result = templates.stueble_applications(user_id=user_id, application_uuids=applic_uuids)

        if result.is_error:
            return FuncRes(
                error=result.error,
                status=Status.FULL_ERROR,
                message=Message(name="Get Application Template Error",
                                type="error",
                                category="Send Application Confirmation",
                                code=500 if result.message is None else result.message.code)
            )
        
        data = result.data
        
        result = mail.send_mail(recipient=data["recipient"], subject=data["subject"], body=data["body"], images=data["images"], html=True)

        if result.is_error:
            return FuncRes(
                error=result.error,
                status=Status.FULL_ERROR,
                message=Message(name="Send Confirmation Email Error",
                                type="error",
                                category="Send Application Confirmation",
                                code=500 if result.message is None else result.message.code),
                user_warning="Failed to send confirmation email, but the application was confirmed successfully."
            )
    
    return FuncRes(
        status=Status.FULL_SUCCESS,
        message=Message(name="Send Application Confirmation Success",
                        type="success",
                        category="Send Application Confirmation",
                        code=200)
    )
