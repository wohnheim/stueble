from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend import export
from backend.sql_connection import database as db
from backend.google.google import login

def send_file_to_drive(file_name: str, file_data: str, mime_type: str):
    """
    Upload a file to Google Drive.
    Parameters:
        file_name (str): The name of the file to be uploaded.
        file_data (str): The content of the file.
        mime_type (str): The MIME type of the file.
    Returns:
        dict: A dictionary containing the success status and the file ID or an error message.
    """
    creds = login()

    try:
        service = build("drive", "v3", credentials=creds)

        # TODO: implement resumable file upload
    except HttpError as error:
        return {"success": False, "error": error}

def export_stueble_guests(cursor, stueble_id: int):
    """
    Export the guest list for a specific Stueble event.
    Parameters:
        cursor: Database cursor object.
        stueble_id (int): The ID of the Stueble event.
    """

    keywords = ["id, user_id", "event_type", "submitted"]

    result = db.read_table(
        cursor=cursor,
        table_name="events",
        keywords=keywords,
        conditions={"stueble_id": stueble_id},
        expect_single_answer=False)

    if result["success"] is False:
        return {"success": False, "error": result["error"]}

    data = result["data"]
    data = [{key: value for key, value in zip(keywords, row)} for row in data]
    csv = export.export_csv(data)
    if csv["success"] is False:
        return {"success": False, "error": csv["message"]}

    csv = csv["data"]

