from cryptography.hazmat.primitives.asymmetric import ed25519
import os
import base64

def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

# Generate private key
private_key = ed25519.Ed25519PrivateKey.generate()

# Extract public key
public_key = private_key.public_key()

os.environ["PRIVATE_KEY"] = private_key
os.environ["PUBLIC_KEY"] = public_key

print("Keys stored in configurations table.")