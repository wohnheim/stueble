import asyncio
import os
import websockets
import msgpack
import json
import datetime

from packages.backend.api import get_conn_cursor, check_permissions, close_conn_cursor, get_motto
from packages.backend.data_types import *
from packages.backend.http_to_websocket import *
from packages.backend.sql_connection import users, events
from packages.backend import hash_pwd as hp

host_upwards_room = set()
connections = set()
sid_to_websocket = {}

allowed_events = ["connect", "disconnect", "ping", "heartbeat", "requestMotto", "requestQRCode", "requestPublicKey"]

def get_websocket_by_sid(sid):
    return sid_to_websocket.get(sid, None)

def parse_cookies(headers):
    return dict(pair.strip().split("=", 1) for header in headers for pair in header[1] if "=" in pair if header[0].lower() == "cookie")

async def send(websocket, event, data, **kwargs):
    message = msgpack.packb({"event": event, **kwargs, "data": {"event": event, "data": data}}, use_bin_type=True)
    await websocket.send(message)

async def broadcast(event, data, skip_sid=None, room=None, **kwargs):
    """
    broadcasts an event to a room

    Parameters:
        event (str): the event to broadcast
        data (dict): the data to send
        skip_sid (str): the session id to skip (optional)
        room (set): the room to broadcast to (optional, defaults to all connections)
        **kwargs: additional keyword arguments to send
    """
    if room is None:
        room = host_upwards_room

    message = msgpack.packb({"event": event, **kwargs, "data": {"event": event, "data": data}}, use_bin_type=True)
    for ws in list(room):
        if ws.parse_cookies(ws.request_headers.items()).get("SID", None) != skip_sid:
            await ws.send(message)

async def handle_ws(websocket):
    session_id = parse_cookies(headers=websocket.request_headers.items()).get("SID", None)
    result = await handle_connect(websocket)
    if result is False:
        return

    sid_to_websocket[session_id] = websocket

    connections.add(websocket)


    try:
        async for message in websocket:
            try:
                msg = msgpack.unpack(message, raw=False)
                event = msg.get("event", None)
                if event is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "event must be specified"})
                    continue
                if event not in allowed_events:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": f"unknown event: {event}"})
                    continue
                data = msg.get("data", None)
            except:
                await send(websocket=websocket, event="error", data={"code": "500",
                     "message": "Invalid msgpack format"})
                continue
            if event == "connect":
                await handle_connect(websocket=websocket)
            elif event == "disconnect":
                await handle_disconnect(websocket=websocket)
            elif event == "ping":
                if data is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "data must be specified"})
                    continue
                await handle_ping(websocket=websocket, msg=data)
            elif event == "heartbeat":
                await handle_heartbeat(websocket=websocket)
            elif event == "requestMotto":
                if data is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "data must be specified"})
                    continue
                await request_motto(websocket=websocket, msg=data)
            elif event == "requestQRCode":
                if data is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "data must be specified"})
                    continue
                await get_qrcode(websocket=websocket, msg=data)
            elif event == "requestPublicKey":
                await get_public_key(websocket=websocket, msg=data)
    finally:
        host_upwards_room.discard(session_id)
        connections.discard(websocket)
        sid_to_websocket.pop(session_id, None)


async def handle_connect(websocket):
    """
    handle a new websocket connection

    Parameters:
        websocket: the websocket connection
        path: the path of the websocket connection
    """

    session_id = parse_cookies(headers=websocket.request_headers.items()).get("SID", None)
    if session_id is None:
        await send(websocket=websocket, event="error", data={
                     "code": "401",
                     "message": "missing SID cookie"})
        return False

    # get connection and cursor
    conn, cursor = get_conn_cursor()

    # check permissions
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)

    close_conn_cursor(conn, cursor)
    if result["success"] is False and result["error"] == "no matching session and user found":
        await send(websocket=websocket, event="status", data= {"code": "200",
                          "capabilities": [],
                          "authorized": False})
        return True

    if result["success"] is False:
        await send(websocket=websocket, event="error", data= {
                     "code": "500",
                     "message": str(result["error"])})
        return False

    capabilities = [i.value for i in get_leq_roles(result["data"]["role"]) if i.value in ["host", "tutor", "admin"]]

    if result["data"]["allowed"] is False:
        await send(websocket=websocket, event="status", data= {
                     "code": "200",
                     "capabilities": capabilities,
                     "authorized": True})
        return True

    if result["data"]["allowed"] is True:
        user_role = result["data"]["user_role"]
        user_role = UserRole(user_role)

        host_upwards_room.append(websocket)

        # can only be "authorized": True but still checking
        await send(websocket=websocket, event="status", data= {
                "authorized": True if user_role >= UserRole.HOST else False,
                "capabilities": capabilities,
                "status_code": "200"})
        return True

async def handle_disconnect(websocket):
    """
    handle a websocket disconnection
    """
    session_id = parse_cookies(headers=websocket.request_headers.items()).get("SID", None)
    if session_id is None:
        return

    try:
        host_upwards_room.remove(websocket)
    except ValueError:
        pass
    connections.discard(websocket)
    sid_to_websocket.pop(session_id, None)
    return

@DeprecationWarning
async def handle_ping(websocket, msg):
    """
    handle a ping from the client
    """

    req_id = msg.get("reqId", None)

    if req_id is None:
        await send(websocket=websocket, event="error", data={"code": "401",
             "message": f"The req_id must be specified"})
        return

    await send(websocket=websocket, event="pong", data={"req_id": req_id})
    return

async def handle_heartbeat(websocket):
    """
    handle a heartbeat from the client
    """

    await send(websocket=websocket, event="heartbeat", data={})
    return

async def request_motto(websocket, msg):

    req_id = msg.get("reqId", None)
    date = msg.get("date", "")

    if req_id is None:
        await send(websocket=websocket, event="error", data=
            {"code": "401",
             "message": "req_id must be specified"})
        return

    result = get_motto(date=date)
    await send(websocket=websocket, event="motto", data=http_to_data(response=result))
    return

'''@DeprecationWarning
async def verify_guest(websocket, msg):
    """
    sets guest verified to True
    """
    req_id = msg.get("reqId", None)
    if req_id is None:
        await send(websocket=websocket, event="error",
                   data={"code": "401",
                         "message": "req_id must be specified"})
        return
    user_data = msg.get("data", None)
    if user_data is None:
        await send(websocket=websocket, event="error", data=
            {"code": "400",
             "message": "data must be specified"})
        return
    user_uuid = msg.get("id", None)
    verification_method = msg.get("method", None)
    session_id = parse_cookies(headers=websocket.request_headers.items()).get("SID", None)
    if session_id is None:
        await send(websocket=websocket, event="error", data={
            "code": "401",
            "message": "missing SID cookie"})
        return

    if user_uuid is None or verification_method is None:
        await send(websocket=websocket, event="error", data=
            {"code": "400",
             "message": "id and method must be specified"})
        return

    if not valid_verification_method(verification_method) or verification_method == "kolping":
        await send(websocket=websocket, event="error", data=
            {"code": "400",
             "message": "invalid verification method"})
        return

    verification_method = VerificationMethod(verification_method)

    # get connection, cursor
    conn, cursor = get_conn_cursor()

    # check permissions
    result = check_permissions(cursor=cursor, session_id=session_id, required_role=UserRole.HOST)
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        await send(websocket=websocket, event="error", data=
            {"code": "401",
             "message": str(result["error"])})
        return
    if result["data"]["allowed"] is False:
        close_conn_cursor(conn, cursor)
        await send(websocket=websocket, event="error", data=
            {"code": "403",
             "message": "invalid permissions, need role host or above"})
        return

    result = users.add_verification_method(connection=conn, cursor=cursor, user_uuid=user_uuid, method=verification_method)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        await send(websocket=websocket, event="error", data=
            {"code": "500",
             "message": str(result["error"])})
        return

    await send(websocket=websocket, event="guestVerification", data={})

    await broadcast(room=host_upwards_room, websocket=websocket, event="guestVerified", req_id=req_id, data=user_data, skip_sid=session_id)
    return'''

async def get_qrcode(websocket, msg):
    """
    get a new qr-code for a guest

    Parameters:
        msg (bytes): msgpack packed data containing:
            - reqId (str): request id to identify the request
            - data (dict): data containing:
                - id (uuid): user_uuid
    """
    user_uuid = msg.get("id", None)
    req_id = msg.get("reqId", None)
    if req_id is None or user_uuid is None:
        await send(websocket=websocket, event="error", data=
            {"code": "401",
             "message": "reqId and id must be specified"})
        return

    stueble_id = msg.get("stuebleId", None)

    # get connection, cursor
    conn, cursor = get_conn_cursor()

    result = events.check_guest(cursor=cursor,
                                user_uuid=user_uuid,
                                stueble_id=stueble_id)
    if result["success"] is False:
        await send(websocket=websocket, event="error", data=
            {"code": "500",
             "message": str(result["error"])})
        return

    if result["data"] is False:
        await send(websocket=websocket, event="error", data=
            {"code": "401",
             "message": "Guest not on guest_list"})
        return

    timestamp = int(datetime.datetime.now().timestamp())

    signature = hp.create_signature(message={"id": user_uuid, "timestamp": timestamp})

    data = {"data":
                {"id": user_uuid,
                 "timestamp": timestamp},
            "signature": signature}

    await send(websocket=websocket, event="requestQRCode", req_id= req_id, data=data)
    return

async def get_public_key(websocket):
    """
    sends the public key
    """

    public_key = os.getenv("PUBLIC_KEY")

    await send(websocket=websocket, event="publicKey", data={
        "publicKey": public_key
    })
    return

# Start server
async def main():
    async with websockets.serve(handle_ws, "0.0.0.0", 3001, ping_interval=25, ping_timeout=20, close_timeout=9):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())