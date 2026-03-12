# LetterBot 📬 → 📅

> Telegram-Bot der Fotos und Textnachrichten empfängt, mit einem **lokalen KI-Modell** analysiert und automatisch Termine in **Google Calendar** einträgt – vollständig privat, keine Cloud, keine API-Kosten.

```
Handy-Foto / Text  →  Telegram Bot  →  OCR  →  Ollama (lokal)  →  Google Calendar
```

## Features

- 📷 **Foto-Input** – fotografiere Briefe, Einladungen, Dokumente
- ✍️ **Text-Input** – schreib oder kopiere Text direkt in Telegram
- 🤖 **Lokale KI** – läuft komplett auf deiner GPU, keine Cloud, keine Kosten
- 📅 **Google Calendar** – Einträge landen automatisch im Kalender
- 🔒 **Privat** – Bot akzeptiert nur Nachrichten von deiner Telegram-ID
- 🔬 **Debug-Befehl** – `/debug` testet alle Pipeline-Schritte einzeln
- 🎨 **Prioritäts-Farben** – hoch=rot, mittel=gelb, niedrig=grün

## Voraussetzungen

| Komponente | Version |
|---|---|
| Python | 3.11+ |
| Ollama | aktuell |
| Tesseract | 5.x |
| GPU | RTX 4070 empfohlen (12 GB VRAM) |

> Läuft komplett nativ unter **Windows** – kein WSL nötig.

## Schnellstart

```bash
git clone https://github.com/deinname/letterbot.git
cd letterbot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# .env ausfüllen, dann:
ollama serve        # separates Terminal
python bot.py
```

Detaillierte Anleitung: [docs/SETUP.md](docs/SETUP.md)

## Projektstruktur

```
letterbot/
├── bot.py                  # Telegram-Bot, Handler, Pipeline
├── ocr.py                  # Bildvorverarbeitung + Tesseract
├── llm.py                  # Ollama-Integration, JSON-Parsing
├── calendar_client.py      # Google Calendar API
├── requirements.txt
├── .env.example
└── docs/
    ├── SETUP.md
    ├── ARCHITECTURE.md
    └── TROUBLESHOOTING.md
```

## Lizenz

MIT – siehe [LICENSE](LICENSE)
