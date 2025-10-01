import io
import os

def stueble_guest(invitee_first_name: str, invitee_last_name: str, first_name: str, last_name: str, stueble_date: str, motto_name: str, qr_code: io.BytesIO) -> dict:
    """
    Returns the email template for inviting a guest to the Stüble event.

    Parameters:
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
    stueble_logo = os.path.expanduser("~/stueble/packages/backend/mail_assets/images/favicon_150.png")
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

def confirm_email(first_name: str, last_name: str, verification_token: str) -> dict:
    """
    Returns the email template for confirming a user's email address.
    Parameters:
        first_name (str): First name of the user.
        last_name (str): Last name of the user.
        verification_token (str): The verification token for email confirmation.
    Returns:
        dict: A dictionary containing the subject, body, and images for the email.
    """
    stueble_logo = os.path.expanduser("~/stueble/packages/backend/mail_assets/images/favicon_150.png")
    image_data = ({"name": "stueble_logo", "value": stueble_logo}, )

    subject = "Neuer Benutzeraccount für das Stüble"
    body = f"""<html lang="de">
    <body style="background-color: #430101; text-align: center; font-family: Arial, sans-serif; padding: 20px; color: #ffffff;">
        <div>
            <img src="cid:{image_data[0]["name"]}" alt="Stüble Logo" width="150">
    </div>
        <h2>Hallo {first_name} {last_name},</h2>
        <p>Du hast einen Account für das Stüble erstellt.</p>
        <p>Um die Registrierung abzuschließen, musst du noch deine Email bestätigen.</p>
        </br>
        <div style="text-align:center; margin: 20px 0;">
      <a href="https://stueble.pages.dev/verify?token={verification_token}"
         style="
           background-color: #0b9a79;
           color: #ffffff;
           padding: 12px 24px;
           text-decoration: none;
           border-radius: 5px;
           display: inline-block;
           font-weight: bold;
           box-shadow: 0 0 10px #da6cff;
           font-family: Arial, sans-serif;
         ">
        Email bestätigen
      </a>
    </div>

        </br>
        <p>Wir freuen uns auf dich!</p>
        <p>Dein Stüble-Team</p>
    </body>
    </html>"""
    return {"subject": subject, "body": body, "images": image_data}

def reset_password(first_name: str, last_name: str, reset_token: str):
    """
    """
    stueble_logo = os.path.expanduser("~/stueble/packages/backend/mail_assets/images/favicon_150.png")
    image_data = ({"name": "stueble_logo", "value": stueble_logo}, )

    subject = "Passwort zurücksetzen"
    body = f"""<html lang="de">
        <body style="background-color: #430101; text-align: center; font-family: Arial, sans-serif; padding: 20px; color: #ffffff;">
            <div>
                <img src="cid:{image_data[0]["name"]}" alt="Stüble Logo" width="150">
        </div>
            <h2>Hallo {first_name} {last_name},</h2>
            <p>hier kannst du ein neues Passwort setzen:</p>
        </br>
        <div style="text-align:center; margin: 20px 0;">
      <a href="https://stueble.pages.dev/reset_password?token={reset_token}"
         style="
           background-color: #0b9a79;
           color: #ffffff;
           padding: 12px 24px;
           text-decoration: none;
           border-radius: 5px;
           display: inline-block;
           font-weight: bold;
           box-shadow: 0 0 10px #da6cff;
           font-family: Arial, sans-serif;
         ">
        Passwort zurücksetzen
      </a>
    </div>
        <p>Falls du keine Passwort-Zurücksetzung angefordert hast, wende dich bitte umgehend an das Tutoren-Team.</p>
        </br>
        <p>Wir freuen uns auf dich!</p>
        <p>Dein Stüble-Team</p>
        </body>
        </html>"""
    return {"subject": subject, "body": body, "images": image_data}