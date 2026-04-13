import io
from pathlib import Path
from typing import Annotated
from psycopg import sql

from backend.datatypes.funcres import FuncRes, Status, Message
from backend.database import database as db
from backend.sql_connection import users
from backend.datatypes.stueble_types import Email

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

def stueble_applications(user_id: int | str,
                         application_ids: Annotated[list[int] | None, "Explicit with application_uuids"] = None,
                         application_uuids: Annotated[list[str] | None, "Explicit with application_uuids"] = None
                         ) -> FuncRes:
    """
    Returns the email template for confirming a user's application for a Stüble event.

    Args:
        user_id (int | str): The ID of the user.
        application_ids (list[int] | None): A list of application IDs for the granted stueble applications
        application_uuids (list[str] | None): A list of application UUIDs for the granted stueble applications

    Returns:
        dict: A dictionary containing the subject, body, and images for the email.
    """

    if application_ids is None and application_uuids is None:
        response = FuncRes(
            error="Either application_ids or application_uuids must be provided",
            status=Status.FULL_ERROR,
            message=Message(
                name="Stueble Applications Error",
                type="error",
                code=400
            )
        )
        return response

    result = users.get_user(user_id=user_id, # type: ignore
                            columns=["first_name", "last_name", "user_uuid", "email"],
                            type_of_answer=db.ANSWER_TYPE.SINGLE_ANSWER)
    if result.is_error:
        raise ValueError(f"User with id {user_id} not found")
    first_name = result.data["first_name"]
    last_name = result.data["last_name"]
    recipient = result.data["email"]

    stueble_logo = file_path / "images" / "favicon_150.png"
    image_data = ({"name": "stueble_logo", "value": stueble_logo}, )

    subject = "Deine Stüble-Termine als Wirt"

    result = db.select(
        table="stueble.motto",
        columns=["motto", "description", "date_of_time", "id"],
        specific_where=sql.SQL("{col} IN ({ids})").format(
            col=sql.Identifier("id" if application_ids is not None else "uuid"),
            ids=sql.SQL(', ').join(sql.Placeholder() * len(application_ids if application_ids is not None else application_uuids))), # type: ignore
        variables=[str(i) for i in application_ids] if application_ids else application_uuids,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER
        )
    
    if result.is_error:
        response = FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(
                name="Stueble Applications Error",
                type="error",
                code=500
            )
        )
        return response
    
    if result.data is None or len(result.data) != len(application_ids if application_ids is not None else application_uuids): # type: ignore
        response = FuncRes(
            error="Not all applications were found",
            status=Status.FULL_ERROR,
            message=Message(
                name="Stueble Applications Error",
                type="error",
                code=404
            )
        )
        return response

    stueble_events = result.data
    
    stueble_ids = set(i["id"] for i in result.data)

    query = sql.SQL("""
    SELECT first_name, last_name, stueble_id
    FROM stueble.hosts
    JOIN users ON stueble.hosts.user_id = users.id
    WHERE stueble_id IN ({ids})
""").format(ids=sql.SQL(', ').join(sql.Placeholder() * len(stueble_ids)))

    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[str(i) for i in stueble_ids]
    )

    if result.is_error:
        response = FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(
                name="Stueble Hosts Error",
                type="error",
                code=500
            )
        )
        return response

    for i in stueble_events:
        i["hosts"] = [(host[0], host[1]) for host in result.data if host[2] == i["id"]]

    def block(first_block: bool, motto: str, description: str, hosts: list[tuple[str, str]]) -> str:
        """
        Returns the HTML block for a stueble event.
        
        Args:
            first_block (bool): Whether this is the first block (for styling purposes).
            motto (str): The motto of the stueble event.
            description (str): The description of the stueble event.
            hosts (list[tuple[str, str]]): A list of hosts for the stueble event, where each host is a tuple of (first_name, last_name).
        Returns:
            str: The HTML block for the stueble event."""
        
        return f"""
<!-- Stüble Termin Block 1 -->
		<div class="mx-auto max-w-3xl rounded-2xl border-2 p-6 px-15 {' mt-8' if first_block is False else ''}
			border-teal-300 bg-emerald-400/15 shadow-[inset_0_0_20px_#000000]">
			<h2 class="mb-8 text-2xl font-bold text-gray-200 text-center">20.02.2026</h2>

			<!-- Stüble Motto -->
			<div class="mr-14 font-normal px-10 mb-10">
				<p class="font-bold text-white-200 text-xl mb-3">Details</p>
				<div class="grid grid-cols-[auto,1fr] gap-y-1 gap-x-10">
					<p>Motto: </p>
					<p>{motto}</p>
					<p>Beschreibung: </p>
					<p>{description}</p>

				</div>

			</div>

			<!-- Stüble Wirte -->
			<div class="mr-5 font-normal px-10 mb-10">
				<p class="font-bold text-white-200 text-xl mb-2">Stüble-Wirte</p>
				<ul class="list-disc text-left text-gray-300 ml-5">
					{"\n".join(f'<li>{host[0]} {host[1]}</li>' for host in hosts)}
				</ul>
			</div>
		"""

    body = f"""
<!DOCTYPE html>

<head>
	<meta charset="utf-8">
	<html lang="de">

	</html>
	<script src="https://cdn.tailwindcss.com"></script>
	<title>Bewerbung auf Stüble-Termine</title>
</head>

<body style="background-color:#1e293b; color:#e5e7eb; font-weight:500;">
  <div style="display:flex; align-items:center; justify-content:center; margin-top:1.75rem;">
    <img src='cid:{image_data[0]["name"]}' alt="Stüble Logo" width="150" />
  </div>
  <div style="margin:0 auto 2.5rem auto; max-width:768px; padding:2.5rem; font-size:1.125rem;">
    Hallo {first_name} {last_name},<br/><br/>
    Dir wurden folgende Stüble-Termine als Wirt zugeteilt.<br/>
    Zusätzlich darfst Du deswegen das gesamte Semester über 3 anstatt 2 Gäste zu Stüble-Terminen einladen.<br/><br/>
    Wir freuen uns auf Dich.<br/>
    Dein Tutoren-Team <br/><br/>
    <span style="font-size:12px;">
      Falls ein Fehler vorliegt oder Du Dich nicht mit einer Gruppe auf ein Stüble beworben hast, teile das bitte umgehend den Tutoren unter
      <a href="mailto:tutorenhes+stuebleapplication@gmail.com" style="color:#60a5fa; text-decoration:underline;">
        tutorenhes@gmail.com
      </a> mit.
    </span>
  </div>
</body>
    {"\n".join(block(first_block=index == 0, motto=event["motto"], description=event["description"], hosts=event["hosts"]) for index, event in enumerate(stueble_events))}
</body>
"""
   
    return FuncRes(
        data={"recipient": Email(recipient), "subject": subject, "body": body, "images": image_data},
        status=Status.FULL_SUCCESS,
        message=Message(
            name="Stueble Application Success",
            type="success",
            code=200
        )
    )


def confirm_email(first_name: str, last_name: str, verification_token: str) -> dict:
    """
    Returns the email template for confirming a user's email address.
    Args:
        first_name (str): First name of the user.
        last_name (str): Last name of the user.
        verification_token (str): The verification token for email confirmation.
    Returns:
        dict: A dictionary containing the subject, body, and images for the email.
    """
    stueble_logo = file_path / "images" / "favicon_150.png"
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
    stueble_logo = file_path / "images" / "favicon_150.png"
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
      <a href="https://stueble.pages.dev/setup/password-reset?token={reset_token}"
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