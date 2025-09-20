from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import os
import base64
from dotenv import load_dotenv, set_key

def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

env_file_path = os.path.expanduser("~/stueble/packages/backend/.env")
with open(env_file_path, "w") as file:
    pass

# Load existing .env file (if it exists)
load_dotenv(env_file_path)

# Generate private key
private_key_obj = ed25519.Ed25519PrivateKey.generate()
# Extract public key
public_key_obj = private_key_obj.public_key()

pem_private = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
private_key_string = pem_private.decode('utf-8')

# PEM format
pem_public = public_key_obj.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
public_key_string = pem_public.decode('utf-8')

# Save to .env file
set_key(env_file_path, "PRIVATE_KEY", private_key_string)
set_key(env_file_path, "PUBLIC_KEY", public_key_string)

print("Keys saved to .env file!")