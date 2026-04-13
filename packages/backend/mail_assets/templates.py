import io
from pathlib import Path

file_path = Path(__file__).resolve().parent

def stueble_guest(invitee_first_name: str, invitee_last_name: str, first_name: str, last_name: str, stueble_date: str, motto_name: str, qr_code: io.BytesIO) -> dict:
    """
    Returns the email template for inviting a guest to the Stüble event.

    Args:
        invitee_first_name (str): First name of the invitee.
        invitee_last_name (str): Last name of the invitee.
        first_name (str): First name of the inviter.
        last_name (str): Last name of the inviter.
        stueble_date (str): Date of the Stüble event.
        motto_name (str): Motto of the Stüble event.
        qr_code (io.BytesIO): QR code image as a byte stream.
    Returns:
        dict: A dictionary containing the subject, body, and images for the email.
    """
    stueble_logo = file_path / "images" / "favicon_150.png"
    image_data = ({"name": "stueble_logo", "value": stueble_logo}, {"name": "qr_code", "value": qr_code})

    subject = f"Einladung zum Stüble am {stueble_date}"
    html_template = f"""<html lang="de">
        <head>
    <meta charset="UTF-8">
 </head>
<body style="background-color: #430101; text-align: center; font-family: Arial, sans-serif; padding: 20px; color: #ffffff;">
    <div>
            <img src="cid:{image_data[0]["name"]}" alt="Stüble Logo" width="150">
    </div>
    <h2>Hallo {invitee_first_name} {invitee_last_name},</h2>
    <p>Du wurdest von {first_name} {last_name} zu unserem nächsten Stüble am {stueble_date} eingeladen 🥳.</p>
    <p>Das Motto lautet {motto_name}.</p>
    </br>
    <p>Zeige bitte diesen QR-Code beim Einlass vor:</p>
    <img src="cid:{image_data[1]["name"]}" alt="QR-Code" width="300">
    </br>
    <p>Wir freuen uns auf dich!</p>
    <p>Dein Stüble-Team</p>
</body>
</html>"""
    return {"subject": subject, "body": html_template, "images": image_data}
