import base64
import json
import os
from typing import Any, cast

import bcrypt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.datatypes.funcres import FuncRes, Status, Message


def hash_pwd(password: str) -> str:
    hashed_pwd = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed_pwd.decode()

def match_pwd(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_signature(message: str | dict[str, Any]) -> FuncRes:
    """
    Create a digital signature for a given message using Ed25519 private key.

    Args:
        cursor: Database cursor to read the private key.
        message (str | dict): The message to be signed.
    Returns:
        dict: {"success": bool, "data": signature or error message}
    """

    if isinstance(message, dict):
        message = json.dumps(message, separators=(',', ':'), sort_keys=True)

    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        return FuncRes(
            error="Private key not found in environment variables.",
            status=Status.FULL_ERROR,
            message=Message(name="Create Signature Error",
                            type="error",
                            category="Create Signature",
                            code=400)
        )

    private_key = cast(Ed25519PrivateKey, serialization.load_pem_private_key(
        private_key.encode('utf-8'),
        password=None,
    ))

    signature = private_key.sign(message.encode())
    return FuncRes(
        data=base64.b64encode(signature).decode(),
        status=Status.FULL_SUCCESS,
        message=Message(name="Create Signature Success",
                        type="success",
                        category="Create Signature",
                        code=200)
    )
    return {"success": True, "data": base64.b64encode(signature).decode()}
