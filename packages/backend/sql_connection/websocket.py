import json

from packages.backend.sql_connection import database as db
from packages.backend.sql_connection.ultimate_functions import clean_single_data
from packages.backend.data_types import *

from typing import Annotated


def get_websocket_sids(cursor):
    """
    Retrieve all WebSocket session IDs from the database.

    Parameters:
        cursor: Database cursor object.
    """
    result = db.read_table(cursor=cursor,
                  table_name='websocket_sids',
                  keywords=["sid"],
                  expect_single_answer=False)
    # if no data was found for cursor.fetchall() empty list is returned
    return result

def add_websocket_sid(connection, cursor, sid: str, user_id: int, session_id: int):
    """
    Add a new WebSocket session ID to the database.

    Parameters:
        cursor: Database cursor object.
        sid (str): WebSocket session ID to add.
        user_id (int): ID of the user associated with the session.
        session_id (int): ID of the session associated with the WebSocket.
    """
    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name='websocket_sids',
        arguments={"sid": sid, "user_id": user_id, "session_id": session_id})
    return result

def remove_websocket_sid(connection, cursor, sid: str):
    """
    Remove a WebSocket session ID from the database.

    Parameters:
        cursor: Database cursor object.
        sid (str): WebSocket session ID to remove.
    """
    result = db.remove_table(
        connection=connection,
        cursor=cursor,
        table_name='websocket_sids',
        conditions={"sid": sid})
    return result

def get_sid_by_session_id(cursor, session_id: str):
    """
    Retrieve the WebSocket session ID associated with a given session ID.

    Parameters:
        cursor: Database cursor object.
        session_id (str): ID of the session to look up.
    """
    result = db.read_table(cursor=cursor,
                  table_name='websocket_sids',
                  keywords=["sid"],
                  conditions={"sid": session_id},
                  expect_single_answer=True)
    # data is allowed to be None
    """if result["success"] and result["data"] is None:
        return {"success": False, "error": "no sid found"}"""
    if result["data"] is not None:
        return clean_single_data(result)
    return result

def add_websocket_event(connection, cursor, user_id: int, action_type: Action_Type, message_content: dict | None, required_role: UserRole):
    """
    Add a new WebSocket event to the database.

    Parameters:
        connection: Database connection object.
        cursor: Database cursor object.
        user_id (int): id of the user associated with the event.
        action_type (Action_Type): Type of the action.
        message_content (dict | None): Content of the message associated with the event.
        required_role (UserRole): Required user role for the event.
    """
    result = db.insert_table(
        connection=connection,
        cursor=cursor,
        table_name='websocket_events',
        arguments={"user_id": user_id, "action": Action_Type.value, "message_content": json.dumps(message_content) if message_content is not None else None, "required_role": required_role.value},
        returning_column="id")
    return result

def get_websocket_events(cursor, user_role: UserRole, since_id: Annotated[int | None, "Explicit with since_timestamp"] = None, since_timestamp: Annotated[int | None, "Explicit with since_id"] = None):
    """
    Retrieve WebSocket events from the database.

    Parameters:
        cursor: Database cursor object.
        user_role (UserRole): Role of the user requesting the events.
        since_id (int | None): Optional ID to filter events that occurred after this ID.
        since_timestamp (int | None): Optional timestamp to filter events that occurred after this timestamp.
    """

    if since_id is not None and since_timestamp is not None:
        return {"success": False, "error": "only one of since_id or since_timestamp must be provided"}
    if since_id is not None and since_timestamp is not None:
        return {"success": False, "error": "only one of since_id or since_timestamp must be provided"}

    value = {}
    if since_id is not None:
        value["id"] = since_id
    else:
        value["created_at"] = since_timestamp

    keywords = ["id", "user_id", "action", "message_content", "required_role", "created_at"]
    result = db.read_table(cursor=cursor,
                  table_name='websocket_events',
                  keywords=keywords,
                  specific_where=f"""{list(value.keys())[0]} > %s""",
                  variables=list(value.values())[0],
                  expect_single_answer=False)
    if result["success"]:
        # filter events by user role
        filtered_data = [event for event in result["data"] if UserRole(event["required_role"]) <= user_role]
        diction = [{key: value for key, value in zip(keywords, i)} for i in filtered_data]
        result["data"] = diction
    return result