# Setup-Anleitung

## Schritt 1 – Ollama installieren

1. Installer herunterladen: https://ollama.com/download
2. Installieren (läuft danach als Windows-Dienst)
3. Modell laden:

```bash
ollama pull llama3.2
```

Testen:
```bash
ollama run llama3.2 "Sag Hallo auf Deutsch"
```

## Schritt 2 – Tesseract installieren

1. Windows-Installer: https://github.com/UB-Mannheim/tesseract/wiki
2. Bei Installation **"German"** und **"English"** Language Packs anhaken
3. Standard-Pfad: `C:\Program Files\Tesseract-OCR\`

Falls Tesseract nicht automatisch gefunden wird, in `ocr.py` Zeile 12 einkommentieren:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Schritt 3 – Telegram Bot erstellen

1. Telegram öffnen → **@BotFather** schreiben
2. `/newbot` → Name eingeben (z.B. `Mein Letter Bot`)
3. Username eingeben (muss auf `bot` enden)
4. **Token kopieren** → kommt ins `.env`

Eigene Telegram-User-ID herausfinden:
1. **@userinfobot** in Telegram schreiben
2. Angezeigte ID ins `.env` eintragen → `ALLOWED_USER_ID`

## Schritt 4 – Google Calendar API einrichten

### 4a – Projekt anlegen
1. https://console.cloud.google.com aufrufen
2. Oben links: **Projekt auswählen → Neues Projekt** → Name: `LetterBot`

### 4b – API aktivieren
1. **APIs & Services → Bibliothek**
2. `Google Calendar API` suchen → **Aktivieren**

### 4c – OAuth-Anmeldedaten erstellen
1. **APIs & Services → Anmeldedaten → Anmeldedaten erstellen → OAuth-Client-ID**
2. Anwendungstyp: **Desktop-App**
3. Name: `LetterBot`
4. **JSON herunterladen** → Datei als `credentials.json` in den Bot-Ordner kopieren

### 4d – Zustimmungsbildschirm konfigurieren
1. **APIs & Services → OAuth-Zustimmungsbildschirm**
2. Benutzertyp: **Extern**
3. App-Name, E-Mail ausfüllen
4. **Scopes → Scopes hinzufügen** → `https://www.googleapis.com/auth/calendar`
5. **Testnutzer → Add Users** → deine Google-E-Mail eintragen
6. Speichern

## Schritt 5 – Bot konfigurieren

```bash
copy .env.example .env
notepad .env
```

Folgende Werte eintragen:

```env
TELEGRAM_TOKEN=1234567890:ABCdef...     # Von @BotFather
ALLOWED_USER_ID=987654321               # Von @userinfobot
OLLAMA_MODEL=llama3.2                   # Oder: mistral, llama3.1:8b
TIMEZONE=Europe/Berlin
```

## Schritt 6 – Starten & Autorisieren

```bash
# Terminal 1: Ollama (falls nicht als Dienst aktiv)
ollama serve

# Terminal 2: Bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

Beim **ersten Start** öffnet sich ein Browser:
1. Google-Account auswählen
2. Warnung "App nicht verifiziert" → **Erweitert → Weiter zu LetterBot**
3. Kalender-Zugriff **erlauben**
4. Browser schließen → Bot läuft

## Schritt 7 – Autostart (optional)

`start_letterbot.bat` im Bot-Ordner erstellen:

```batch
@echo off
cd C:\Pfad\zu\letterbot
call venv\Scripts\activate
start "" "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak
python bot.py
```

Verknüpfung in Autostart-Ordner legen:
`Win + R` → `shell:startup` → Verknüpfung zu `start_letterbot.bat` dort ablegen

## Schritt 8 – Testen

Im Telegram-Bot:
1. `/debug` – testet alle Pipeline-Schritte
2. Kurze Textnachricht: `"Arzttermin am 20. März um 10:30 Uhr"`
3. Prüfen ob Eintrag im Google Kalender erscheint
