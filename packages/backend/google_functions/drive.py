from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaInMemoryUpload
import datetime
from zoneinfo import ZoneInfo

from backend import export
from backend.database import database as db
from backend.google_functions.authentification import authenticate
from backend.datatypes.funcres import FuncRes, Status, Message

def upload_file_folder(file_name: str, folder_name: str, content: str, mime_type: str) -> FuncRes:
    """
    Upload a file to a specific folder in Google Drive.
    Args:
        file_name (str): The name of the file to be uploaded.
        folder_name (str): The name of the folder where the file will be uploaded; The folder will be created.
        content (str): The content of the file.
        mime_type (str): The MIME type of the file.
    Returns:
        FuncRes: Object containing the file ID or an error message.
    """
    creds = authenticate()

    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        folder = service.files().create(body=folder_metadata, fields="id").execute()

        file_metadata = {
            "name": file_name,
            "parents": [folder.get("id")]
        }

        media = MediaInMemoryUpload(content.encode('utf-8'), mimetype=mime_type)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return FuncRes(
            data={"folder_id": folder.get("id"), "file_id": file.get("id")},
            status=Status.FULL_SUCCESS,
            message=Message(name="Google Drive Upload Success",
                            type="success",
                            category="Google Drive",
                            code=200)
            )

    except HttpError as error:
        return FuncRes(
            error=str(error),
            status=Status.FULL_ERROR,
            message=Message(name="Google Drive Upload Error",
                            type="error",
                            category="Google Drive",
                            code=500)
        )

def export_stueble_guests(stueble_id: int) -> FuncRes:
    """
    Export the guest list for a specific Stueble event.

    Args:
        stueble_id (int): The ID of the Stueble event.
        date (date): The date of the event.
    Returns:
        FuncRes: Object containing the file ID or an error message.
    """

    default_tz = ZoneInfo("Europe/Berlin")

    result = db.select(
        table="stueble.motto",
        columns=["date_of_time"],
        conditions={"id": stueble_id},
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Google Drive Export Error",
                            type="error",
                            category="Google Drive",
                            code=500)
        )
    date = result.data[0]
    if date > (datetime.datetime.now(default_tz).date() - datetime.timedelta(days=1)) or (date == (datetime.datetime.now(default_tz).date() - datetime.timedelta(days=1)) and (datetime.datetime.now(default_tz).hour < 11)):
        return FuncRes(
            error="Can only export guest lists for past stueble events (e.g. if stueble was on 01.01.2000 then guest list can be exported earliest at 02.01.2000 11:00).",
            status=Status.FULL_ERROR,
            message=Message(name="Google Drive Export Error",
                            type="error",
                            category="Google Drive",
                            code=400)
        )
    keywords_events = ["id", "event_type", "submitted"]
    keywords_users = ["first_name", "last_name", "email", "room", "residence"]

    query = f"""SELECT {', '.join(['events.' + keyword for keyword in keywords_events])}, {', '.join(['users.' + keyword for keyword in keywords_users])}
                FROM (SELECT * FROM stueble.events WHERE stueble_id = %s) AS events
                LEFT JOIN users ON events.user_id = users.id;
                """

    result = db.custom_call(
        query=query,
        variables=[stueble_id],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Google Drive Export Error",
                            type="error",
                            category="Google Drive",
                            code=500)
        )

    data = result.data
    data = [{key: value for key, value in zip(keywords_events + keywords_users, row)} for row in data]
    csv = export.export_csv(data)
    if csv["success"] is False:
        return FuncRes(
            error=str(csv["message"]),
            status=Status.FULL_ERROR,
            message=Message(name="Google Drive Export Error",
                            type="error",
                            category="Google Drive",
                            code=500)
        )

    csv = csv["data"]

    result = db.select(
        table="stueble.motto",
        columns=["date_of_time"],
        conditions={"id": stueble_id},
        type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Google Drive Export Error",
                            type="error",
                            category="Google Drive",
                            code=500)
        )

    date = result.data[0]
    print(date)
    print(type(date))
    print(date.day, date.month, date.year)

    upload = upload_file_folder(
        file_name=f"guest_list_stueble_{stueble_id}__{date.day}_{date.month}_{date.year}.csv",
        folder_name=f"stueble_{stueble_id}__{date.day}_{date.month}_{date.year}",
        content=csv,
        mime_type="text/csv")

    return upload
