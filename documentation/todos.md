# API

1. hosts GET: No motto found zu 200 und [] als Wert
2. Termine für Anmeldung: /stueble/dates GET: Liste aus Dicts mit Datum: Anzahl Bewerbungen
3. Zu 2. POST Endpoint für Bewerbung /stueble/application content: mutlipart-form-data, {"motto": str, "hosts": host_ids (uuids), dates: array of tuple (yyyy-mm-dd (str), Priorität (int))
4. Zu 3. GET Endpoint für Bewerber /stueble/application: Hosts können ihre eigenen Bewerbungen sehen: Daten aus POST
5. Zu 3. DELETE Endpoint für Bewerber: Datum str
6. Termine für Anmeldung Sicht Tutoren: /tutoren/stueble/dates: GET Liste aus allen Daten + UUID
7. Zu 6. POST zum Speichern der Auswahl mit Dict mit key: Datum, value uuid der Bewerbung

8. Terminkalender allgemein: GET-Request: dict: date: str uhrzeit optional, title: str, content: str optional, image: base64 optional, ort: optional, end: optional date optional mit zeit, category: str

# Websocket
1. Couldn't send stueble status 500 zu 404
2. Auswahl der Stüblebewerbungen: stueble_selection: Dict aus uuid, selected: boolean; UUID der Bewerbung und ob ausgewählt oder nicht
3. Änderung der Stübleauswahl an alle Tutoren mit Hinweis, welcher Tutor, was verändert hat

# Schema
1. Stueble Application: mit UUID
2. Auswahl-Tabelle (geshared unter Tutoren)
3. Ggf. Tabelle mit persistenten Änderungen der Stüble Auswahl (finale Auswahl)
