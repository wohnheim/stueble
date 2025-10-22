from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import os
import base64
from dotenv import load_dotenv, set_key

def b64url_encode(data):
    """
    URL-safe base64 encoding without padding.
    Parameters:
        data (bytes): Data to encode.
    Returns:
        str: URL-safe base64 encoded string without padding.
    """
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

# specify the path to the .env file
env_file_path = os.path.expanduser("~/stueble/packages/backend/.env")
with open(env_file_path, "w") as file:
    pass

# Load existing .env file (if it exists)
load_dotenv(env_file_path)

# Generate private key
private_key_obj = ed25519.Ed25519PrivateKey.generate()
# Extract public key
public_key_obj = private_key_obj.public_key()

# create the private key
pem_private = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())
# convert to string
private_key_string = pem_private.decode('utf-8')

# create the public key
pem_public = public_key_obj.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
# convert to string
public_key_string = pem_public.decode('utf-8')

# Save to .env file
set_key(env_file_path, "PRIVATE_KEY", private_key_string)
set_key(env_file_path, "PUBLIC_KEY", public_key_string)

# Set the login information for the database
set_key(env_file_path, "USERDB", "stueble")
set_key(env_file_path, "HOST", "localhost")
set_key(env_file_path, "PORT", "5432")
set_key(env_file_path, "DBNAME", "stueble_data")

# Set the password fot the database
inputted_data = input("Enter the password for the postgres user 'stueble': ")
# save to .env file
set_key(env_file_path, "PASSWORD", inputted_data)

# Set the password for the service account of the email account
inputted_email_data = input("Enter the password for the email account: ")
# save to .env file
set_key(env_file_path, "EMAIL_PASSWORD", inputted_email_data)

# print success message
print("Keys saved to .env file.")