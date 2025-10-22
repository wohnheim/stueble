from packages.backend.sql_connection.common_types import (
    SingleSuccess,
    SingleSuccessCleaned,
)

def clean_single_data(data: dict | list) -> dict:
    return {"success": data["success"], "data": data["data"][0] if data["data"] is not None else None }
