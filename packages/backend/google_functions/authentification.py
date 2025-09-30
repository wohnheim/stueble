import os.path
from google.oauth2 import service_account
from googleapiclient.discovery import build

def authenticate():
    """
    Log in to the Gmail API using OAuth 2.0 credentials.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    SERVICE_ACCOUNT_FILE = "do_not_track/credentials/credentials.json"

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

if __name__ == "__main__":
    authenticate()