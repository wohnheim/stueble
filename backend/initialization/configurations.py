from backend.sql_connection import database as db

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096
)

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

conn, cursor = db.connect()
# Store keys in the configurations table
result = db.insert_table(
    connection=conn,
    cursor=cursor,
    table="configurations",
    arguments={"private_key": pem_private, "public_key": pem_public})

if result["success"] is False:
    raise result["error"]
print("Keys stored in configurations table.")