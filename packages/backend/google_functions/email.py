import smtplib
from email.message import EmailMessage
from packages.backend.data_types import Email
from dotenv import load_dotenv
import os

env_file_path = os.path.expanduser("~/stueble/packages/backend/.env")
load_dotenv(env_file_path)

EMAIL_ADDRESS = "stuebleheshirte@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_mail(recipient: Email, subject: str, body: str):
    """
    Sends an email message.
    Parameters:
        recipient (Email): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The body content of the email.
    """

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient.email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    return {"success": True}