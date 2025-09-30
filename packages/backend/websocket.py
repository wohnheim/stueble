import asyncio
import base64
import os
from typing import Literal

import websockets
import msgpack
import datetime
from cryptography.hazmat.primitives import serialization
import inspect
from functools import wraps
from enum import Enum

from packages.backend.sql_connection.common_functions import check_permissions, get_motto
from packages.backend.data_types import *
from packages.backend.sql_connection import events, sessions, database as db, users
from packages.backend import hash_pwd as hp
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from packages.backend.sql_connection.conn_cursor_functions import *

# load environment variables
_ = load_dotenv("~/stueble/packages/backend/.env")

# initialize variables
host_upwards_room = set()
admins_room = set()

connections = set()
sid_to_websocket = {}
websockets_info = {}
message_log = {}

# set room datatype
class Room(str, Enum):
    HOST_UPWARDS = "host_upwards"
    ADMINS = "admins"

def update_hosts(hosts: list[str], method: Literal["add", "remove"]):
    """
    Update the list of hosts

    Parameters:
        hosts (list): list of host session ids
        method (str): "add" to add hosts, "remove" to remove hosts
    """

    if method not in ["add", "remove"]:
        return {"success": False, "error": "method must be 'add' or 'remove'"}

    for i in hosts:
        if not i in sid_to_websocket.keys():
            continue
        if method == "add":
            host_upwards_room.add(sid_to_websocket[i])
        else:
            host_upwards_room.discard(sid_to_websocket[i])
    return {"success": True}

def is_valid_room(room: str) -> bool:
    return room in Room._value2member_map_

# handle websocket_info and sid_to_websocket garbage collection

allowed_events = ["connect", "disconnect", "ping", "heartbeat", "requestMotto", "requestQRCode", "requestPublicKey", "acknowledgement"]

# add achievements
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
    cookies: dict[str, str] = {}
    
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

# gives each message a unique id and therefore allows tracking, which websocket has already received the message
def add_to_message_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # get name of the function, that called this function
        caller_name = inspect.stack()[1].function

        # excluded_functions
        excluded_functions = allowed_events.copy() + ["handle_ws"]
        excluded_functions = [re.sub(r'(?<!^)(?=[A-Z])', '_', i).lower() for i in excluded_functions]
        excluded_functions.remove("request_q_r_code")
        excluded_functions.append("request_qr_code")

        # since these messages have a req_id, ignore them
        if caller_name in excluded_functions:
            return func(*args, **kwargs)

        # bind parameter names to values
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        params = bound.arguments

        # initialize room
        room = set()

        # set room based on function
        if func.__name__ == "broadcast":
            if params.get("room", None) is None:
                room = host_upwards_room
            if "skip_sid" in params:
                room.discard(params["skip_sid"])
        elif func.__name__ == "send":
            if "websocket" in kwargs:
                room = {kwargs["websocket"]}
            else:
                room = {args[0]} if len(args) > 0 else None

        # retrieve session_ids that receive the message
        session_ids = [websockets_info.get(i, {}).get("session_id", None) for i in room]
        session_ids = [i for i in session_ids if i is not None]
        if "room" in params:
            del params["room"]
        if len(message_log.keys()) == 0:
            message_id = 0
        else:
            message_id = max(list(message_log.keys())) + 1

        # set message log
        message_log[message_id] = {"params": params, "session_ids": session_ids}

        result = func(*args, resId=message_id, **kwargs)
        return result
    return wrapper

@add_to_message_log
async def send(websocket, event: str, data: dict | bool, **kwargs):
    """
    sends an event to a websocket

    Parameters:
        websocket: the websocket connection
        event (str): the event to send
        data (dict | bool): the data to send
        **kwargs: additional keyword arguments to send
    """
    message = msgpack.packb({"event": event, **kwargs, "data": data}, use_bin_type=True)
    await websocket.send(message)

@add_to_message_log
async def broadcast(event, data, room: None | Room=None, skip_sid=None, **kwargs):
    """
    broadcasts an event to a room
le_
    Parameters:
        event (str): the event to broadcast
        data (dict): the data to send
        skip_sid (str): the session id to skip (optional)
        room (set): the room to broadcast to (optional, defaults to all connections)
        **kwargs: additional keyword arguments to send
    """
    if room is None or room == Room.HOST_UPWARDS:
        room = host_upwards_room
    elif room == Room.ADMINS:
        room = admins_room
    else:
        raise NotImplementedError(f"room {room} not implemented")


    message = msgpack.packb({"event": event, **kwargs, "data": data}, use_bin_type=True)
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
    result = await connect(websocket)
    if result is False:
        return
    
    # get connection and cursor
    conn, cursor = get_conn_cursor()
    result = sessions.get_session(cursor=cursor, session_id=session_id)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        await send(websocket=websocket, event="error", data=
            {"code": "500" if result["error"] != "no session found" else "401",
             "message": str(result["error"])})
        return
    
    _, expiration_date = result["data"]
    websockets_info[id(websocket)] = {"expiration_date": expiration_date, "session_id": session_id}

    sid_to_websocket[session_id] = websocket

    connections.add(websocket)

    # for each unsuccessfully past sent message, send it again
    unsent_messages = [value["params"] for key, value in message_log.items() if session_id in value["session_ids"]]
    for message in unsent_messages:
        await send(websocket=websocket, **message)

    try:
        async for message in websocket:
            expiration_date = websockets_info.get(id(websocket), {}).get("expiration_date", None)
            if expiration_date is None:
                await send(websocket=websocket, event="error", data={"code": "500",
                    "message": "Internal server error"})
            elif expiration_date < datetime.datetime.now(ZoneInfo("Europe/Berlin")):   
                await send(websocket=websocket, event="error", data={"code": "401",
                        "message": "Session expired"})
                await websocket.close(code="1000", reason="Session expired")
                await disconnect(websocket=websocket)
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
                await connect(websocket=websocket)
            elif event == "disconnect":
                await disconnect(websocket=websocket)
            elif event == "ping":
                if req_id is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "reqId must be specified"})
                    continue
                await ping(websocket=websocket, req_id=req_id)
            elif event == "heartbeat":
                await heartbeat(websocket=websocket)
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
                await request_qrcode(websocket=websocket, msg=data, req_id=req_id)
            elif event == "requestPublicKey":
                if req_id is None:
                    await send(websocket=websocket, event="error", data={"code": "400",
                         "message": "reqId must be specified"})
                await request_public_key(websocket=websocket, req_id=req_id)
    finally:
        host_upwards_room.discard(websocket)
        admins_room.discard(session_id)
        connections.discard(websocket)
        sid_to_websocket.pop(session_id, None)

        # get connection, cursor
        conn, cursor = get_conn_cursor()

        # get all valid session_ids
        result = db.read_table(cursor=cursor, 
                               table_name="sessions", 
                               keywords=["id"], 
                               expect_single_answer=False)
        close_conn_cursor(conn, cursor)
        if result["success"] is False:
            # remove after debugging
            print("ERROR OCCURRED")
        if result["success"] is True:
            allowed_session_ids = result["data"]
            for key, value in message_log.items():
                if any(i not in allowed_session_ids for i in value["session_ids"]):
                    message_log[key]["session_ids"] = [i for i in value["session_ids"] if i in allowed_session_ids]
                    if message_log[key]["session_ids"] == []:
                        del message_log[key]

async def acknowledgement(websocket, res_id: str | int):
    """
    handle acknowledgement

    Parameters:
        websocket (websocket): websocket connection
        res_id (str | int): response id of the message called message_id in backend
    """
    session_id = parse_cookies(headers=websocket.request.headers).get("SID", None)
    if session_id is None:
        await send(websocket=websocket, event="error", data={
                     "code": "401",
                     "message": "missing SID cookie"})
        return False
    message_id = res_id
    if message_id is None:
        await send(websocket=websocket, event="error", data={
            "code": "400",
            "message": "missing resId"
        })
    try:
        message_log[message_id]["session_ids"].remove(session_id)
    except ValueError:
        await send(websocket=websocket, event="error", data={
            "code": "400",
            "message": "invalid resId"
        })
    return True


async def connect(websocket):
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

    capabilities = [i.value for i in get_leq_roles(result["data"]["user_role"]) if i.value in ["user", "host", "tutor", "admin"]]

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

        if user_role == UserRole.ADMIN:
            admins_room.add(websocket)

        # can only be "authorized": True but still checking
        await send(websocket=websocket, event="status", data= {
                "authorized": True if user_role >= UserRole.HOST else False,
                "capabilities": capabilities,
                "status_code": "200"})
        return True

async def disconnect(websocket):
    """
    handle a websocket disconnection

    Parameters:
        websocket: the websocket connection
    """
    session_id = parse_cookies(headers=websocket.request.headers).get("SID", None)
    if session_id is None:
        return

    host_upwards_room.discard(websocket)
    admins_room.discard(websocket)
    connections.discard(websocket)
    sid_to_websocket.pop(session_id, None)
    del websockets_info[id(websocket)]
    return

async def ping(websocket, req_id):
    """
    handle a ping from the client

    Parameters:
        websocket: websocket connection
        req_id (str): the request id from the client
    """

    await send(websocket=websocket, event="pong", reqId=req_id, data=True)
    return

async def heartbeat(websocket):
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
    motto = {"motto": result["data"]["motto"], "description": result["data"]["description"], "date": result["data"]["date"].isoformat()}
    await send(websocket=websocket, event="motto", reqId=req_id, data=motto)
    return


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
    session_id = parse_cookies(headers=websocket.request.headers).get("SID", None)
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

    result = users.add_verification_method(cursor=cursor, user_uuid=user_uuid, method=verification_method)
    close_conn_cursor(conn, cursor)
    if result["success"] is False:
        await send(websocket=websocket, event="error", data=
            {"code": "500",
             "message": str(result["error"])})
        return

    await send(websocket=websocket, event="guestVerification", data={})

    await broadcast(room=host_upwards_room, websocket=websocket, event="guestVerified", reqId=req_id, data=user_data, skip_sid=session_id)
    return

async def request_qrcode(websocket, msg, req_id):
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
    if signature["success"] is False:
        await send(websocket=websocket, event="error", reqId=req_id, 
                   data={"code": "500","message": str(signature["error"])})
        return

    data = {
        "data": {
            "id": user_uuid,
            "timestamp": timestamp
        },
        "signature": signature["data"]
    }

    await send(websocket=websocket, event="qrCode", reqId=req_id, data=data)
    return

async def request_public_key(websocket, req_id):
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
