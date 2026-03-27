from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import os
from pathlib import Path
import smtplib
from typing import Annotated

from backend.datatypes.stueble_types import Email
from backend.datatypes.funcres import FuncRes, Message, Status
from dotenv import load_dotenv
import os
from pathlib import Path
import io

env_file_path = os.path.expanduser("~/stueble/packages/backend/.env")
load_dotenv(env_file_path)

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS") or "stuebleheshirte@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# NOTE: Images must have the size, that is specified in the html and cid and Content-ID must match
def send_mail(recipient: Email, subject: str, body: str, html: bool=False, images: Annotated[tuple[dict[str, str | Path | io.BytesIO]] | None, "Only possible if html is True"] = None) -> FuncRes:
    """
    Sends an email message.

    Args:
        recipient (Email): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The body content of the email.
        html (bool): Whether the email is html or not.
        images (list[str] | None): The list of images to attach to the email.
    Returns:
        FuncRes: A FuncRes object indicating the success or failure of the email sending operation.
    """

    msg = EmailMessage() if not html else MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient.email
    if not html:
        msg.set_content(body) # type: ignore

    else:
        msg.attach(MIMEText(body, "html")) # type: ignore

    if html is True and images is not None:
        for info in images:
            name = info["name"]
            value = info["value"]
            if isinstance(value, str) or isinstance(value, Path):
                with open(value, "rb") as f:
                    img_mime = MIMEImage(f.read())
            else:
                img_mime = MIMEImage(value.read(), _subtype="png")
            img_mime.add_header('Content-ID', name) # type: ignore

            # hardcore hardcoding to png
            img_mime.add_header('Content-Disposition', 'inline', filename="image.png")
            msg.attach(img_mime) # type: ignore

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD) # type: ignore
        smtp.send_message(msg)
    return FuncRes(
        status=Status.FULL_SUCCESS,
        message=Message(name="Send Mail Success",
                        type="success",
                        category="Send Mail",
                        code=200)
    )
