from packages import backend as db


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
    result = db.delete_table(
        connection=connection,
        cursor=cursor,
        table_name='websocket_sids',
        conditions={"sid": sid})
    return result