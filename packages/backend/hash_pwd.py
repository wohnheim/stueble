import base64
import bcrypt
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
import os
import json

def hash_pwd(password: str) -> str:
    password = password.encode()
    hashed_pwd = bcrypt.hashpw(password, bcrypt.gensalt())
    return hashed_pwd.decode()

def match_pwd(password: str, hashed: str) -> bool:
    password = password.encode()
    hashed = hashed.encode()
    return bcrypt.checkpw(password, hashed)

def create_signature(message: str | dict) -> dict:
    """
    Create a digital signature for a given message using RSA private key.

    Parameters:
        cursor: Database cursor to read the private key.
        message (str | dict): The message to be signed.
    Returns:
        dict: {"success": bool, "data": signature or error message}
    """

    if isinstance(message, dict):
        message = json.dumps(message, separators=(',', ':'))

    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        return {"success": False, "error": "Private key not found in environment variables."}
    private_key = serialization.load_pem_private_key(
        private_key.encode('utf-8'),
        password=None,
    )
    signature = private_key.sign(message.encode())
    signature = base64.b64encode(signature).decode()
    return {"success": True, "data": signature}

@DeprecationWarning
def verify_signature(public_key_pem: str, message: str, signature: bytes) -> bool:
    """
    Verify a digital signature using the provided RSA public key.

    Parameters:
        public_key_pem (str): The PEM-encoded public key.
        message (str): The original message that was signed.
        signature (bytes): The digital signature to verify.
    Returns:
        bool: True if the signature is valid, False otherwise.
    """

    public_key = os.getenv("PUBLIC_KEY")
    if not public_key:
        print("Public key not found in environment variables.")
        return False
    public_key = serialization.load_pem_public_key(
        public_key.encode('utf-8')
    )
    message = message.encode()
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False