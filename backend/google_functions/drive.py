from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaInMemoryUpload
from datetime import date

from backend import export
from backend.sql_connection import database as db
from backend.google.google import login

def upload_file_folder(file_name: str, folder_name: str, content: str, mime_type: str):
    """
    Upload a file to a specific folder in Google Drive.
    Parameters:
        file_name (str): The name of the file to be uploaded.
        folder_name (str): The name of the folder where the file will be uploaded; The folder will be created.
        content (str): The content of the file.
        mime_type (str): The MIME type of the file.
    Returns:
        dict: A dictionary containing the success status and the file ID or an error message.
    """
    creds = login()

    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google_functions-apps.folder",
        }

        folder = service.files().create(body=folder_metadata, fields="id").execute()

        file_metadata = {
            "name": file_name,
            "parents": [folder.get("id")]
        }

        media = MediaInMemoryUpload(content.encode('utf-8'), mimetype=mime_type)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return {"success": True, "data": {"folder_id": folder.get("id"), "file_id": file.get("id")}}

    except HttpError as error:
        return {"success": False, "error": error}

def export_stueble_guests(cursor, stueble_id: int, date: date):
    """
    Export the guest list for a specific Stueble event.
    Parameters:
        cursor: Database cursor object.
        stueble_id (int): The ID of the Stueble event.
        date (date): The date of the event.
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

    upload = upload_file_folder(
        file_name=f"guest_list_stueble_{stueble_id}__{date.day}_{date.month}_{date.year}.csv",
        folder_name=f"stueble_{stueble_id}__{date.day}_{date.month}_{date.year}",
        content=csv,
        mime_type="text/csv")

    return upload