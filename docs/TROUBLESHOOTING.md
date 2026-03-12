# Troubleshooting

Wenn etwas nicht funktioniert: zuerst `/debug` im Bot schicken.
Der Debug-Befehl testet jeden Schritt einzeln und zeigt genau wo das Problem liegt.

---

## Ollama

### "Ollama nicht erreichbar"
```
ollama serve
```
Falls Ollama schon läuft aber nicht antwortet:
```
# Prozess killen und neu starten
taskkill /f /im ollama.exe
ollama serve
```
Prüfen: http://localhost:11434 im Browser → sollte "Ollama is running" zeigen.

### LLM gibt leere Event-Liste zurück
Modell ist möglicherweise nicht geladen:
```
ollama list              # zeigt installierte Modelle
ollama pull llama3.2     # Modell neu laden
```
Alternative: `OLLAMA_MODEL=mistral` in `.env` – Mistral ist zuverlässiger bei
strukturierter JSON-Ausgabe.

---

## Google Calendar

### `invalid_grant: Bad Request`
Token ist abgelaufen oder ungültig:
```
del token.pickle
python bot.py
```
Browser öffnet sich → neu autorisieren.

Außerdem prüfen: **Systemuhr korrekt?**
`Einstellungen → Zeit & Sprache → Uhrzeit automatisch festlegen → An`

### `insufficient authentication scopes` (403)
Token wurde mit falschen Berechtigungen erstellt:
1. `del token.pickle`
2. In `calendar_client.py` prüfen: `SCOPES = ["https://www.googleapis.com/auth/calendar"]`
3. `python bot.py` → neu autorisieren

### `credentials.json nicht gefunden`
→ [SETUP.md Schritt 4](SETUP.md#schritt-4--google-calendar-api-einrichten) wiederholen.

### Einträge landen im falschen Kalender
In `.env` die explizite Kalender-ID eintragen statt `primary`:
1. Google Calendar öffnen → Kalender-Einstellungen → Kalender-ID kopieren
2. In `.env`: `GOOGLE_CALENDAR_ID=abc123@group.calendar.google.com`

---

## OCR

### Bot antwortet "Konnte keinen Text erkennen"
- Bessere Beleuchtung beim Fotografieren
- Gerade von oben fotografieren (nicht schräg)
- **Microsoft Lens App** verwenden – korrigiert Perspektive automatisch
- Für sehr schlechte Qualität: `USE_PADDLEOCR=true` in `.env` setzen
  (PaddleOCR vorher installieren: `pip install paddleocr`)

### Tesseract nicht gefunden (Windows)
In `ocr.py` Zeile 12 einkommentieren:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Falscher Text / Kauderwelsch
Prüfen ob Deutsch-Sprachpaket installiert ist:
```
tesseract --list-langs
```
`deu` muss in der Liste sein. Falls nicht: Tesseract neu installieren mit
"German" Language Pack.

---

## Telegram

### Bot antwortet gar nicht
1. Token in `.env` prüfen (kein Leerzeichen, vollständig kopiert)
2. `python bot.py` – gibt es eine Fehlermeldung beim Start?
3. Bei @BotFather prüfen: `/mybots` → Bot aktiv?

### "⛔ Nicht autorisiert"
`ALLOWED_USER_ID` in `.env` stimmt nicht mit deiner Telegram-ID überein.
Korrekte ID holen: @userinfobot in Telegram schreiben.

---

## Allgemein

### `ModuleNotFoundError`
Virtuelle Umgebung nicht aktiviert:
```
venv\Scripts\activate
pip install -r requirements.txt
```

### Bot läuft aber erstellt keine Kalendereinträge ohne Fehlermeldung
1. `/debug` ausführen – zeigt genau wo die Pipeline abbricht
2. LLM-Schritt prüfen: Gibt das Modell wirklich Events zurück?
3. Im Terminal nach `INFO calendar_client` Zeilen suchen
