# API

| Task | Status |
| ---- | ------ |
|  hosts GET: No motto found zu 200 und [] als Wert | DONE |
|  Termine für Anmeldung: /stueble/dates GET: Liste aus Dicts mit Datum: Anzahl Bewerbungen | DONE |
|  Zu 2. POST Endpoint für Bewerbung /stueble/application content: mutlipart-form-data, {"motto": str, "hosts": host_ids (uuids), dates: array of tuple (yyyy-mm-dd (str), Priorität (int)) | DONE |
|  Zu 3. GET Endpoint für Bewerber /stueble/application: Hosts können ihre eigenen Bewerbungen sehen: Daten aus POST | DONE |
|  Zu 3. DELETE Endpoint für Bewerber: UUID | DONE |
|  Termine für Anmeldung Sicht Tutoren: /tutoren/stueble/dates: GET Liste aus allen Daten + UUID | - |
|  Zu 6. POST zum Speichern der Auswahl mit Dict mit key: Datum, value uuid der Bewerbung | - |
|  Terminkalender allg.: GET-Request: dict: date: str Uhrzeit / None, title: str, content: str / None, image: base64 / None, ort: / None, end: / None date / None mit zeit, category: str | DONE |

# Websocket

| Task | Status |
|  Couldn't send stueble status 500 zu 404
|  Auswahl der Stüblebewerbungen: stueble_selection: Dict aus uuid, selected: boolean; UUID der Bewerbung und ob ausgewählt oder nicht
|  Änderung der Stübleauswahl an alle Tutoren mit Hinweis, welcher Tutor, was verändert hat

# Schema

| Task | Status |
| ---- | ------ |
|  Stueble Application: mit UUID | DONE |
|  Auswahl-Tabelle (geshared unter Tutoren) | - |
|  Ggf. Tabelle mit persistenten Änderungen der Stüble Auswahl (finale Auswahl) | - |
