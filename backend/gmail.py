from backend.data_types import Email

import os.path
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Update scope to allow sending
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def create_message(sender, to, subject, message_text):
    """Create a MIME email message."""
    message = MIMEText(message_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}

def send_message(service, user_id, message):
    """Send an email message."""
    try:
        sent = service.users().messages().send(userId=user_id, body=message).execute()
        print(f"Message sent! ID: {sent['id']}")
        return sent
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def send_mail(recipient: Email, subject: str, body: str):
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("../do_not_track/credentials/token.json"):
    creds = Credentials.from_authorized_user_file("../do_not_track/credentials/token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "../do_not_track/credentials/credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("../do_not_track/credentials/token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("gmail", "v1", credentials=creds)

    # Create the message
    message = create_message(
      sender="me",  # "me" means the authenticated account
      to=recipient.email,
      subject=subject,
      message_text=body
    )

    # Send the message
    send_message(service, "me", message)
    return {"success": True}
  except HttpError as error:
    return {"success": False, "error": error}