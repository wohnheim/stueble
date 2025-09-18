from packages.backend.sql_connection import database as db

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from jwcrypto import jwk
import base64

def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

# Generate private key
private_key = ed25519.Ed25519PrivateKey.generate()

# Extract public key
public_key = private_key.public_key()

# Save private key to PEM (unencrypted)
pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)


# Save public key to PEM
pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

jwk_private = jwk.JWK(
    kty='OKP',
    crv='Ed25519',
    d=b64url_encode(pem_private),
    x=b64url_encode(pem_public))
jwk_private_json = jwk_private.export(private_key=True)

jwk_public = jwk.JWK(
    kty='OKP',
    crv='Ed25519',
    x=b64url_encode(pem_public))
jwk_public_json = jwk_public.export(private_key=False)

conn, cursor = db.connect()
# Store keys in the configurations table
result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table_name="configurations",
    arguments={"key": "private_key", "value": pem_private})

if result["success"] is False:
    raise result["error"]

result = db.insert_table(
connection=conn,
cursor=cursor,
table_name="configurations",
arguments={"key": "public_key", "value": pem_public})

if result["success"] is False:
    raise result["error"]
print("Keys stored in configurations table.")