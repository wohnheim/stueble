from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import os
import base64

def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

# Generate private key
private_key = ed25519.Ed25519PrivateKey.generate()
pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
private_key = pem_private.decode('utf-8')

# Extract public key
public_key = private_key.public_key()
# PEM format
pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
public_key = pem_public.decode('utf-8')

os.environ["PRIVATE_KEY"] = private_key
os.environ["PUBLIC_KEY"] = public_key

print("Keys stored in configurations table.")