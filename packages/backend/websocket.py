import asyncio
import base64
import os
import websockets
import msgpack
import datetime
from cryptography.hazmat.primitives import serialization

from packages.backend.sql_connection.common_functions import check_permissions
from packages.backend.api import get_motto
from packages.backend.data_types import *
from packages.backend.sql_connection import events, sessions
from packages.backend import hash_pwd as hp
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from packages.backend.sql_connection.conn_cursor_functions import *

load_dotenv("~/stueble/packages/backend/.env")

host_upwards_room = set()
connections = set()
sid_to_websocket = {}
websockets_info = {}

allowed_events = ["connect", "disconnect", "ping", "heartbeat", "requestMotto", "requestQRCode", "requestPublicKey"]

# add archievements
def get_websocket_by_sid(sid: str):
    """
    Get the websocket connection by session id (SID)

    Parameters:
        sid (str): the session id from the cookies
    """
    return sid_to_websocket.get(sid, None)

def parse_cookies(headers):
    """
    Parse cookies from websocket headers

    Parameters:
        headers: the headers from the websocket connection
    """
    cookies = {}
    
    # Check if headers is a dict-like object (common in websockets library)
    if hasattr(headers, 'get'):
        cookie_header = headers.get('cookie') or headers.get('Cookie')
        if cookie_header:
            # Split cookie string by semicolons and parse each pair
            for cookie_pair in cookie_header.split(';'):
                cookie_pair = cookie_pair.strip()
                if '=' in cookie_pair:
                    key, value = cookie_pair.split('=', 1)
                    cookies[key.strip()] = value.strip()
    else:
        # If headers is an iterable of tuples
        try:
            for header_name, header_value in headers:
                if header_name.lower() == "cookie":
                    # Split cookie string by semicolons and parse each pair
                    for cookie_pair in header_value.split(';'):
                        cookie_pair = cookie_pair.strip()
                        if '=' in cookie_pair:
                            key, value = cookie_pair.split('=', 1)
                            cookies[key.strip()] = value.strip()
        except ValueError:
            # If unpacking fails, try to iterate differently
            for header in headers:
                if hasattr(header, '__getitem__') and len(header) >= 2:
                    header_name, header_value = header[0], header[1]
                    if header_name.lower() == "cookie":
                        for cookie_pair in header_value.split(';'):
                            cookie_pair = cookie_pair.strip()
                            if '=' in cookie_pair:
                                key, value = cookie_pair.split('=', 1)
                                cookies[key.strip()] = value.strip()
    
    return cookies

async def send(websocket, event, data, **kwargs):
    """
    sends an event to a websocket

    Parameters:
        websocket: the websocket connection
        event (str): the event to send
        data (dict): the data to send
        **kwargs: additional keyword arguments to send
    """
    message = msgpack.packb({"event": event, **kwargs, "data": data}, use_bin_type=True)
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
        if ws.parse_cookies(ws.request.headers).get("SID", None) != skip_sid:
            await ws.send(message)

async def handle_ws(websocket):
    """
    handles a websocket connection

    Parameters:
        websocket: the websocket connection
    """
    session_id = parse_cookies(headers=websocket.request.headers).get("SID", None)
    result = await handle_connect(websocket)
    if result is False:
        return
    
    # get connection and cursor
    conn, cursor = get_conn_cursor()
    result = sessions.get_session(cursor=cursor, session_id=session_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "500" if result["error"] != "no session found" else "401",
             "message": str(result["error"])})
        return
    
    _, expiration_date = result["data"]
    websockets_info[id(websocket)] = expiration_date

    sid_to_websocket[session_id] = websocket

    connections.add(websocket)


    try:
        async for message in websocket:
            expiration_date = websockets_info.get(id(websocket), None)
            if expiration_date is None:
                await send(websocket=websocket, event="error", data={"code": "500",
                    "message": "Internal server error"})
            elif expiration_date < datetime.datetime.now(ZoneInfo("Europe/Berlin")):   
                await send(websocket=websocket, event="error", data={"code": "401",
                        "message": "Session expired"})
                await websocket.close(code="1000", reason="Session expired")
                await handle_disconnect(websocket=websocket)
                return
            try:
                msg = msgpack.unpackb(message)
                event = msg.get("event", None)
                if event is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "event must be specified"})
                    continue
                if event not in allowed_events:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": f"unknown event: {event}"})
                    continue
                req_id = msg.get("reqId", None)
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
                if req_id is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "reqId must be specified"})
                    continue
                await handle_ping(websocket=websocket, msg=data, req_id=req_id)
            elif event == "heartbeat":
                await handle_heartbeat(websocket=websocket)
            elif event == "requestMotto":
                if req_id is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "reqId must be specified"})
                    continue
                await request_motto(websocket=websocket, msg=data, req_id=req_id)
            elif event == "requestQRCode":
                if req_id is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "reqId must be specified"})
                    continue
                await get_qrcode(websocket=websocket, msg=data, req_id=req_id)
            elif event == "requestPublicKey":
                if req_id is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "reqId must be specified"})
                await get_public_key(websocket=websocket, req_id=req_id)
    finally:
        host_upwards_room.discard(session_id)
        connections.discard(websocket)
        sid_to_websocket.pop(session_id, None)


async def handle_connect(websocket):
    """
    handle a new websocket connection

    Parameters:
        websocket: the websocket connection
    """

    session_id = parse_cookies(headers=websocket.request.headers).get("SID", None)
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
                     "message": str(result["error"]), 
                     "authorized": False})
        return False

    capabilities = [i.value for i in get_leq_roles(result["data"]["user_role"]) if i.value in ["host", "tutor", "admin"]]

    if result["data"]["allowed"] is False:
        await send(websocket=websocket, event="status", data= {
                     "code": "200",
                     "capabilities": capabilities,
                     "authorized": True})
        return True

    if result["data"]["allowed"] is True:
        user_role = result["data"]["user_role"]
        user_role = UserRole(user_role)

        host_upwards_room.add(websocket)

        # can only be "authorized": True but still checking
        await send(websocket=websocket, event="status", data= {
                "authorized": True if user_role >= UserRole.HOST else False,
                "capabilities": capabilities,
                "status_code": "200"})
        return True

async def handle_disconnect(websocket):
    """
    handle a websocket disconnection

    Parameters:
        websocket: the websocket connection
    """
    session_id = parse_cookies(headers=websocket.request.headers).get("SID", None)
    if session_id is None:
        return

    try:
        host_upwards_room.discard(websocket)
    except ValueError:
        pass
    connections.discard(websocket)
    sid_to_websocket.pop(session_id, None)
    del websockets_info[id(websocket)]
    return

async def handle_ping(websocket, req_id):
    """
    handle a ping from the client

    Parameters:
        websocket: websocket connection
        req_id (str): the request id from the client
    """

    await send(websocket=websocket, event="pong", reqId=req_id, data=True)
    return

async def handle_heartbeat(websocket):
    """
    handle a heartbeat from the client

    Parameters:
        websocket: websocket connection
    """

    await send(websocket=websocket, event="heartbeat")
    return

async def request_motto(websocket, msg, req_id):
    """
    request a motto from the server

    Parameters:
        websocket: websocket connection
        msg (dict): the message from the client
        req_id (str): the request id from the client
    """
    if msg is not None:
        date = msg.get("date", "")
    else:
        date = None

    result = get_motto(date=date)
    if result["success"] is False:
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "500",
             "message": str(result["error"])})
        return
    await send(websocket=websocket, event="motto", reqId=req_id, data=result["data"])
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
    session_id = parse_cookies(headers=websocketrequest.headers).get("SID", None)
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

    await broadcast(room=host_upwards_room, websocket=websocket, event="guestVerified", reqId=req_id, data=user_data, skip_sid=session_id)
    return'''

async def get_qrcode(websocket, msg, req_id):
    """
    get a new qr-code for a guest

    Parameters:
        websocket: websocket connection
        msg (dict): the message from the client
        req_id (str): the request id from the client
    """

    if msg is not None:
        stueble_id = msg.get("stuebleId", None)
    else:
        stueble_id = None
    # get connection, cursor

    conn, cursor = get_conn_cursor()
    session_id = parse_cookies(headers=websocket.request.headers).get("SID", None)
    result = sessions.get_user(cursor=cursor, session_id=session_id, keywords=["id", "user_uuid"])
    if result["success"] is False:
        close_conn_cursor(conn, cursor)
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "500" if result["error"] != "no matching session and user found" else "401",
                "message": str(result["error"])})
        return
    user_id = result["data"][0]
    user_uuid = result["data"][1]


    result = events.check_guest(cursor=cursor,
                                user_id=user_id,
                                stueble_id=stueble_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False and result["error"] == "no stueble party found":
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "404",
             "message": result["error"]})
        return
    elif result["success"] is False and result["error"] == "user not on guest_list":
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "403",
             "message": "Guest not on guest list"})
        return
    elif result["success"] is False:
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "500",
             "message": str(result["error"])})
        return

    if result["data"] is False:
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "403",
             "message": "Guest not on guest list"})
        return

    timestamp = int(datetime.datetime.now().timestamp())

    signature = hp.create_signature(message={"id": user_uuid, "timestamp": timestamp})

    data = {"data":
                {"id": user_uuid,
                 "timestamp": timestamp},
            "signature": signature}

    await send(websocket=websocket, event="requestQRCode", reqId=req_id, data=data)
    return

async def get_public_key(websocket, req_id):
    """
    sends the public key

    Parameters:
        websocket: websocket connection
        req_id (str): the request id from the client
    """

    public_key = os.getenv("PUBLIC_KEY")
    if not public_key:
        await send(websocket=websocket, event="error", reqId=req_id, data=
            {"code": "500",
             "message": "Public key not found in environment variables."})
    public_key = serialization.load_pem_public_key(
        public_key.encode('utf-8')
    )
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    # Base64url encode (no padding)
    def base64url_encode(data):
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')
    
    # Create JWK
    jwk = {
        "kty": "OKP",                           # Key Type: Octet Key Pair
        "crv": "Ed25519",                       # Curve: Ed25519
        "x": base64url_encode(public_key_bytes), # Public key value
        "use": "sig",                           # Usage: signature
        "key_ops": ["verify"]                   # Key operations
    }

    await send(websocket=websocket, event="publicKey", reqId=req_id, data=jwk)
    return

# Start server
async def main():
    async with websockets.serve(handle_ws, "127.0.0.1", 3001, ping_interval=25, ping_timeout=20, close_timeout=9):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
