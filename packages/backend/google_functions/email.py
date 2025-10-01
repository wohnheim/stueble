import smtplib
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Annotated

from packages.backend.data_types import Email
from dotenv import load_dotenv
import os
import io

env_file_path = os.path.expanduser("~/stueble/packages/backend/.env")
load_dotenv(env_file_path)

EMAIL_ADDRESS = "stuebleheshirte@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_mail(recipient: Email, subject: str, body: str, html: bool=False, images: Annotated[dict[str, io.BytesIO | str] | None, "Only possible if html is True"] = None):
    """
    Sends an email message.
    Parameters:
        recipient (Email): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The body content of the email.
        html (bool): Whether the email is html or not.
        images (list[str] | None): The list of images to attach to the email.
    """

    msg = EmailMessage() if not html else MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient.email
    if not html:
        msg.set_content(body)
    else:
        msg.attach(MIMEText(body, "html"))
    if html is True and images is not None:
        for name, value in images.items():
            if isinstance(value, str):
                with open(value, "rb") as f:
                    img_mime = MIMEImage(f.read())
            else:
                img_mime = MIMEImage(value.read(), _subtype="png")
            img_mime.add_header('Content-ID', name)
            img_mime.add_header('Content-Disposition', 'inline', filename=name + "." + value.split(".")[-1] if isinstance(value, str) else "png")
            msg.attach(img_mime)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    return {"success": True}