"""
Run at: */5 * * * * (every 5 minutes)
"""
import os
import warnings
from dotenv import load_dotenv
from psycopg import sql

from backend.database import database as db

env_file_path = os.path.expanduser("~/.env")
load_dotenv(env_file_path)

expiration_time = os.getenv("WOHNHEIMAPP_VERIFICATION_CODE_TTL")

query = sql.SQL(
    "DELETE FROM verification_codes WHERE used = True OR (created_at + ({exp_time}  || ' minute')::interval < NOW());").format(
    exp_time=sql.Placeholder()
)

result = db.custom_call(
    query=query,
    variables=(expiration_time,),
    type_of_answer=db.ANSWER_TYPE.NO_ANSWER
)

if result.is_error:
    warnings.warn(UserWarning("Error while deleting expired verification codes: " + str(result.error)))