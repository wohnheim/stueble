from flask import Response
import msgpack
import json

def http_to_websocket_response(response: Response, event: str) -> bytes:
    """
    Turns an HTTP response into a WebSocket-compatible response.

    Parameters:
        response (Response): The original HTTP response object.
    Returns:
        bytes: A bytes object containing the packed event and response data.
    """
    # Extract status code, headers, and body from the HTTP response
    status_code = response.status_code
    body = json.loads(response.get_data(as_text=True))
    body["code"] = status_code

    diction = msgpack.packb({"event": event, "data": body}, use_bin_type=True)

    return diction