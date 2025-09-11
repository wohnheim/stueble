from packages.backend.data_types import Email
from packages.backend.google_functions.authentification import authenticate
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
  creds = authenticate()

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