from flask import json
from packages.backend.sql_connection.ultimate_functions import clean_single_data
from packages.backend.data_types import UserRole
from packages.backend.sql_connection import database as db
from typing import Annotated

# TODO: for future also allow sending websockets to all users, therefore only specify user_id when only for one specific user
def add_websocket_message(cursor, event: str, 
                          data: any, 
                          required_role: Annotated[UserRole, "Explicit with user_id"] = None, 
                          user_id: Annotated[int | str, "Explicit with required_role"] = None, 
                          **kwargs) -> dict[str, any]:
    """
    Add a websocket message to the database.

    Parameters:
        cursor: Database cursor to execute the query.
        event (str): The event type of the websocket message.
        data (any): The data payload of the websocket message.
        required_role (UserRole): The minimum user role required to receive the message.
        **kwargs: Additional keyword arguments to be stored as JSONB.
    Returns:
        dict[str, any]: Result of the database operation.
    """

    if all(i is None for i in (required_role, user_id)) is True or all(i is not None for i in (required_role, user_id)):
        raise ValueError("Either required_role or user_id must be provided, not both, not none.")

    # initialize query parts
    query = """"""
    variables = []
    additional_data = None

    if required_role == UserRole.USER:
        query = """WITH _ AS (SELECT set_config('additional.user_id', %s, true))"""
        variables.append(str(user_id))
    
    variables.append(event)

    if required_role is not None:
        variables.append(required_role)

    if kwargs:
        additional_data = json.dumps(kwargs)
        variables.append(additional_data)    

    query += f"""INSERT INTO websocket_messages (event, data {', required_role' if required_role is not None else ''}{', additional_data' if additional_data is not None else ''}) RETURNING ID"""

    result = db.custom_call(cursor=cursor, query=query, variables=variables, type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)

    if result["success"] is True and result["data"] is None:
        return {"success": False, "error": "Error occurred"}
    if result["success"] is True:
        return {"success": True, "data": {"message_id": result["data"]}}

    return result

# NOTE: not needed due to trigger
# # NOTE: when making a user host / tutor, doesn't need to be added for previous messages since their data will be received through http request
# def remove_affected_user(cursor, user_id: int):
#     """
#     Remove affected tutor / host from websockets_affected when tutor / host is made user
#     
#     Parameters:
#         cursor: Database cursor to execute the query.
#         user_id (int): The ID of the user to remove affected websocket messages for.
#     Returns:
# 
#     """
#     query = """DELETE FROM websockets_affected WHERE session_id IN (SELECT id FROM sessions WHERE user_id = %s)"""
#     result = db.custom_call(cursor=cursor, query=query, variables=[user_id], type_of_answer=db.ANSWER_TYPE.NO_ANSWER)
#     return result

def remove_affected_session(cursor, session_id: int, message_id: int):
    """
    Remove affected session from websockets_affected when session sent an acknowledgement
    
    Parameters:
        cursor: Database cursor to execute the query.
        session_id (int): The ID of the session to remove affected websocket messages for.
    """

    result = db.remove_table(cursor=cursor, table="websockets_affected", conditions={"session_id": session_id, "message_id": message_id})
    return result