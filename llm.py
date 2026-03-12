"""
llm.py – Ollama-Integration
============================
Schickt Text an ein lokales LLM und extrahiert strukturierte Kalendereinträge.
Läuft komplett lokal auf deiner RTX 4070 – keine Cloud, keine Kosten.
"""

import json
import logging
import os
from datetime import datetime

import httpx

log = logging.getLogger(__name__)

OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

TODAY = datetime.now().strftime("%d.%m.%Y")
WEEKDAY = datetime.now().strftime("%A")  # z.B. "Monday"

SYSTEM_PROMPT = f"""Du bist ein präziser Assistent der Termine, Aufgaben und Deadlines aus Texten extrahiert.
Heute ist {WEEKDAY}, der {TODAY}.

Analysiere den Text und extrahiere ALLE Termine, Fristen, Aufgaben und Veranstaltungen.

Antworte NUR mit einem JSON-Array. Kein erklärender Text, keine Markdown-Backticks, nur reines JSON.

Jedes Objekt im Array hat diese Felder:
{{
  "title": "Kurzer, klarer Titel (max 60 Zeichen)",
  "start_date": "DD.MM.YYYY oder null",
  "start_time": "HH:MM oder null",
  "end_date": "DD.MM.YYYY oder null",
  "end_time": "HH:MM oder null",
  "description": "Kontext aus dem Originaltext (max 200 Zeichen)",
  "location": "Ort falls angegeben, sonst null",
  "is_all_day": true oder false,
  "priority": "hoch" | "mittel" | "niedrig"
}}

Wichtige Regeln:
- Relative Daten auflösen: "nächsten Montag" → konkretes Datum
- "bis Ende des Monats" → letzter Tag des aktuellen Monats
- Falls keine Uhrzeit: is_all_day = true, start_time = null
- Falls kein Datum erkennbar: start_date = null
- Deadlines als ganztägige Ereignisse mit Titel "DEADLINE: ..."
- Leeres Array [] wenn gar nichts gefunden
- Wenn kein Termin festgestellt werden kann, soll auch kein Termin im Kalender angelegt werden
"""


def extract_events_from_text(text: str) -> list[dict]:
    """
    Hauptfunktion: Sendet Text an Ollama, parst JSON-Antwort.
    Gibt Liste von Event-Dicts zurück.
    """
    if not text.strip():
        return []

    log.info("Sende %d Zeichen an Ollama (%s)", len(text), OLLAMA_MODEL)

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": f"Extrahiere alle Termine aus diesem Text:\n\n{text}"},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,   # Niedrig = konsistente, strukturierte Ausgabe
                    "num_ctx": 4096,
                },
            },
            timeout=120.0,
        )
        response.raise_for_status()

    except httpx.ConnectError:
        log.error("Ollama nicht erreichbar. Läuft 'ollama serve'?")
        raise RuntimeError(
            "Ollama nicht erreichbar unter " + OLLAMA_URL +
            "\nBitte 'ollama serve' im Terminal starten."
        )
    except httpx.TimeoutException:
        log.error("Ollama Timeout nach 120s")
        raise RuntimeError("Ollama hat zu lange gebraucht. Ist die GPU aktiv?")

    raw = response.json()["message"]["content"].strip()
    log.debug("Ollama Antwort: %s", raw[:500])

    return _parse_json_response(raw)


def _parse_json_response(raw: str) -> list[dict]:
    """
    Robust JSON-Parser: Versucht mehrere Strategien falls Ollama
    trotz Anweisung Markdown-Blöcke ausgibt.
    """
    # Strategie 1: Direktes JSON-Parsen
    try:
        data = json.loads(raw)
        return _validate_events(data if isinstance(data, list) else [])
    except json.JSONDecodeError:
        pass

    # Strategie 2: JSON aus Markdown-Block extrahieren
    import re
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return _validate_events(data)
        except json.JSONDecodeError:
            pass

    # Strategie 3: Erstes [ ... ] im Text finden
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return _validate_events(data)
        except json.JSONDecodeError:
            pass

    log.warning("Konnte JSON nicht parsen. Rohantwort: %s", raw[:300])
    return []


def _validate_events(events: list) -> list[dict]:
    """Bereinigt und validiert die Event-Liste."""
    valid = []
    for e in events:
        if not isinstance(e, dict):
            continue
        if not e.get("title"):
            continue
        # Fehlende Felder mit Defaults füllen
        e.setdefault("start_date", None)
        e.setdefault("start_time", None)
        e.setdefault("end_date", None)
        e.setdefault("end_time", None)
        e.setdefault("description", "")
        e.setdefault("location", None)
        e.setdefault("is_all_day", e.get("start_time") is None)
        e.setdefault("priority", "mittel")
        valid.append(e)

    log.info("%d gültige Events extrahiert", len(valid))
    return valid
