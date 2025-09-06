import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate():
    """
    Log in to the Gmail API using OAuth 2.0 credentials.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/drive"]

    if os.path.exists("../../do_not_track/credentials/token.json"):
        creds = Credentials.from_authorized_user_file("../../do_not_track/credentials/token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "../../do_not_track/credentials/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("../../do_not_track/credentials/token.json", "w") as token:
            token.write(creds.to_json())
    return creds