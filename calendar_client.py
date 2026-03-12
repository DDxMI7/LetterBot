"""
calendar_client.py – Google Calendar Integration
==================================================
Legt Kalendereinträge per Google Calendar API an.
Gibt den Link zum Eintrag zurück.
"""

import logging
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache

class _NoCache(Cache):
    """Deaktiviert den File-Cache um die oauth2client-Warnung zu unterdrücken."""
    def get(self, url):       return None
    def set(self, url, cont): pass
from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE       = os.getenv("GOOGLE_TOKEN_FILE",       "token.pickle")
def _get_calendar_id() -> str:
    cal_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    log.debug("Nutze Kalender-ID: %s", cal_id)
    return cal_id

# Priorität → Kalenderfarbe (Google Calendar Farbcodes 1-11)
PRIORITY_COLOR = {
    "hoch":    "11",  # Tomato (rot)
    "mittel":  "5",   # Banana (gelb)
    "niedrig": "2",   # Sage (grün)
}


def _get_service():
    """Google Calendar Service mit OAuth2-Auth."""
    creds = None

    if Path(TOKEN_FILE).exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(CREDENTIALS_FILE).exists():
                raise FileNotFoundError(
                    f"'{CREDENTIALS_FILE}' nicht gefunden!\n"
                    "Bitte credentials.json aus der Google Cloud Console herunterladen.\n"
                    "Anleitung: siehe README.md → Schritt 3"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        log.info("Google-Token gespeichert: %s", TOKEN_FILE)

    return build("calendar", "v3", credentials=creds, cache=_NoCache())


def _parse_datetime(date_str: str | None, time_str: str | None) -> dict:
    """
    Konvertiert Datumsstrings in Google Calendar API Format.
    Gibt entweder {'date': ...} oder {'dateTime': ..., 'timeZone': ...} zurück.
    """
    tz = os.getenv("TIMEZONE", "Europe/Berlin")

    if not date_str:
        # Kein Datum → heute ganztägig
        today = datetime.now().strftime("%Y-%m-%d")
        return {"date": today}

    # Datum parsen (DD.MM.YYYY)
    try:
        dt_date = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        try:
            dt_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            log.warning("Unbekanntes Datumsformat: %s", date_str)
            today = datetime.now().strftime("%Y-%m-%d")
            return {"date": today}

    if not time_str:
        return {"date": dt_date.strftime("%Y-%m-%d")}

    # Zeit parsen (HH:MM)
    try:
        dt_time = datetime.strptime(time_str, "%H:%M")
        combined = dt_date.replace(
            hour=dt_time.hour,
            minute=dt_time.minute,
            second=0,
        )
        return {
            "dateTime": combined.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": tz,
        }
    except ValueError:
        return {"date": dt_date.strftime("%Y-%m-%d")}


def create_calendar_event(event: dict) -> str | None:
    """
    Legt einen Kalendereintrag an.
    Gibt den HTML-Link zum Event zurück.
    """
    service = _get_service()

    start = _parse_datetime(event.get("start_date"), event.get("start_time"))
    end   = _parse_datetime(event.get("end_date")   or event.get("start_date"),
                            event.get("end_time")   or event.get("start_time"))

    # Bei ganztägigen Ereignissen: Ende = nächster Tag
    if "date" in end and end["date"] == start.get("date"):
        end_dt = datetime.strptime(end["date"], "%Y-%m-%d") + timedelta(days=1)
        end = {"date": end_dt.strftime("%Y-%m-%d")}

    # Bei Uhrzeitevents ohne Ende: +1 Stunde
    if "dateTime" in start and "date" in end:
        start_dt = datetime.strptime(start["dateTime"], "%Y-%m-%dT%H:%M:%S")
        end_dt   = start_dt + timedelta(hours=1)
        end = {
            "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": start.get("timeZone", "Europe/Berlin"),
        }

    body = {
        "summary":     event["title"],
        "description": event.get("description", ""),
        "start":       start,
        "end":         end,
        "colorId":     PRIORITY_COLOR.get(event.get("priority", "mittel"), "5"),
        "source": {
            "title": "LetterBot",
            "url":   "https://t.me/",
        },
    }

    if event.get("location"):
        body["location"] = event["location"]

    try:
        result = service.events().insert(
            calendarId=_get_calendar_id(),
            body=body,
        ).execute()

        link = result.get("htmlLink")
        log.info("Event angelegt: %s  →  %s", event["title"], link)
        return link

    except HttpError as e:
        log.error("Google Calendar API Fehler: %s", e)
        raise
