from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaInMemoryUpload
import datetime
from zoneinfo import ZoneInfo

from packages.backend import export
from packages.backend.sql_connection import database as db
from packages.backend.google_functions.authentification import authenticate

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

    # authenticate
    creds = authenticate()

    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)

        # specify folder metadata
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        # create a folder
        folder = service.files().create(body=folder_metadata, fields="id").execute()

        # create a file in the created folder
        file_metadata = {
            "name": file_name,
            "parents": [folder.get("id")]
        }

        # add content to the file and upload it
        media = MediaInMemoryUpload(content.encode('utf-8'), mimetype=mime_type)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return {"success": True, "data": {"folder_id": folder.get("id"), "file_id": file.get("id")}}

    except HttpError as error:
        return {"success": False, "error": error}

def export_stueble_guests(cursor, stueble_id: int):
    """
    Export the guest list for a specific Stueble event.
    Parameters:
        cursor: Database cursor object.
        stueble_id (int): The ID of the Stueble event.
        date (date): The date of the event.
    """

    # set timezone to Berlin time
    default_tz = ZoneInfo("Europe/Berlin")

    # get date of stueble event
    # TODO: e.g. replace with get_motto
    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=["date_of_time"],
        conditions={"id": stueble_id},
        expect_single_answer=True)

    if result["success"] is False:
        return {"success": False, "error": result["error"]}
    date = result["data"][0]

    # if the date is today or in the future or yesterday but before 11am, return error
    if date > (datetime.datetime.now(default_tz).date() - datetime.timedelta(days=1)) or (date == (datetime.datetime.now(default_tz).date() - datetime.timedelta(days=1)) and (datetime.datetime.now(default_tz).hour < 11)):
        return {"success": False, "error": "Can only export guest lists for past stueble events (e.g. if stueble was on 01.01.2000 then guest list can be exported earliest at 02.01.2000 11:00)."}

    # set the keywords for the list
    # TODO: change to split into users, hosts, tutors, externs...
    keywords_events = ["id", "event_type", "submitted"]
    keywords_users = ["first_name", "last_name", "email", "room", "residence"]

    query = f"""SELECT {', '.join(['events.' + keyword for keyword in keywords_events])}, {', '.join(['users.' + keyword for keyword in keywords_users])}
                FROM (SELECT * FROM events WHERE stueble_id = %s) AS events
                LEFT JOIN users ON events.user_id = users.id;
                """

    result = db.custom_call(
        connection=None,
        cursor=cursor,
        query=query,
        variables=[stueble_id],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER)

    if result["success"] is False:
        return {"success": False, "error": result["error"]}

    data = result["data"]
    data = [{key: value for key, value in zip(keywords_events + keywords_users, row)} for row in data]
    csv = export.export_csv(data)
    if csv["success"] is False:
        return {"success": False, "error": csv["message"]}

    csv = csv["data"]

    result = db.read_table(
        cursor=cursor,
        table_name="stueble_motto",
        keywords=["date_of_time"],
        conditions={"id": stueble_id},
        expect_single_answer=True)
    if result["success"] is False:
        return {"success": False, "error": result["error"]}

    date = result["data"][0]
    """print(date)
    print(type(date))
    print(date.day, date.month, date.year)"""

    upload = upload_file_folder(
        file_name=f"guest_list_stueble_{stueble_id}__{date.day}_{date.month}_{date.year}.csv",
        folder_name=f"stueble_{stueble_id}__{date.day}_{date.month}_{date.year}",
        content=csv,
        mime_type="text/csv")

    return upload
