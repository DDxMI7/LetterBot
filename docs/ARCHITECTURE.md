# Architektur

## Überblick

```
┌─────────────┐     Foto/Text      ┌─────────────────────────────────────────┐
│  Telegram   │ ────────────────►  │              bot.py                     │
│  (Handy)    │                    │  - Sicherheitscheck (User-ID)           │
└─────────────┘                    │  - Handler: Foto / Text / Commands      │
                                   └──────────┬──────────────────────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │                   │                   │
                    Foto-Pfad             Rohtext            Rohtext
                          ▼                   │                   │
                   ┌────────────┐             │                   │
                   │  ocr.py   │             │                   │
                   │ Tesseract  │             │                   │
                   │ 4 Strat.  │             │                   │
                   └─────┬──────┘             │                   │
                         │ Rohtext            │                   │
                         └───────────────────►▼                   │
                                        ┌──────────┐              │
                                        │  llm.py  │◄─────────────┘
                                        │  Ollama  │
                                        │  JSON    │
                                        └────┬─────┘
                                             │ Event-Liste
                                             ▼
                                   ┌──────────────────┐
                                   │ calendar_client  │
                                   │ Google Cal. API  │
                                   └──────────────────┘
```

## Komponenten

### bot.py
Einstiegspunkt und Koordinator. Registriert Handler für Telegram-Updates und
steuert die Pipeline. Enthält den `/debug`-Befehl der alle Schritte einzeln testet.

**Sicherheit:** Jeder Handler ist mit `@only_owner` dekoriert. Nachrichten von
fremden Telegram-User-IDs werden sofort abgelehnt.

### ocr.py
Wandelt Bilder in Text um. Versucht vier Strategien und wählt das längste Ergebnis:

| Strategie | Für |
|---|---|
| Original | Saubere Scans, Screenshots, gedruckte Dokumente |
| Hochskaliert | Kleine oder niedrigauflösende Bilder |
| Leicht geschärft | Handy-Fotos mit Weichzeichnung |
| Deskewed | Schiefe Fotos |

Bewusste Entscheidung: **keine** aggressive Binarisierung oder CLAHE, da diese
saubere Dokumente verschlechtern.

### llm.py
Kommuniziert mit Ollama über HTTP (`/api/chat`). Sendet einen System-Prompt der
das Modell anweist, **nur JSON** zurückzugeben. Robustes Parsing mit drei Fallback-
Strategien für den Fall dass das Modell trotzdem Markdown-Blöcke ausgibt.

**Prompt-Strategie:**
- `temperature: 0.1` für konsistente, strukturierte Ausgabe
- Datum-Auflösung im Prompt (heute = konkretes Datum)
- Fehlende Felder werden mit Defaults befüllt

**Extrahierte Felder pro Event:**
```json
{
  "title": "string",
  "start_date": "DD.MM.YYYY | null",
  "start_time": "HH:MM | null",
  "end_date": "DD.MM.YYYY | null",
  "end_time": "HH:MM | null",
  "description": "string",
  "location": "string | null",
  "is_all_day": "boolean",
  "priority": "hoch | mittel | niedrig"
}
```

### calendar_client.py
Authentifiziert sich via OAuth2 gegen die Google Calendar API. Token wird in
`token.pickle` gespeichert und automatisch erneuert.

**Datumskonvertierung:**
- `DD.MM.YYYY` → Google Calendar Format `YYYY-MM-DD`
- Mit Uhrzeit → `dateTime` mit Zeitzone
- Ohne Uhrzeit → `date` (ganztägig)
- Kein Enddatum → +1 Stunde (Termine) oder +1 Tag (ganztägig)

**Farb-Mapping:**
- `hoch` → Tomato (rot, colorId 11)
- `mittel` → Banana (gelb, colorId 5)
- `niedrig` → Sage (grün, colorId 2)

## Datenfluss – Beispiel

**Eingabe:** Foto eines Arztbriefs mit "Termin am 15. März um 10:30 Uhr"

```
1. Telegram liefert photo file_id
2. Bot lädt Bild herunter → /tmp/xyz.jpg
3. ocr.py: Strategie 1 (Original) → "Datum: 15. März\nUhrzeit: 10:30 Uhr\nOrt: Praxis Dr. Müller"
4. llm.py: Ollama antwortet →
   [{"title": "Arzttermin Praxis Dr. Müller",
     "start_date": "15.03.2026", "start_time": "10:30",
     "location": "Praxis Dr. Müller", "priority": "hoch"}]
5. calendar_client.py: POST /calendar/v3/calendars/primary/events
6. Google gibt htmlLink zurück
7. Bot antwortet mit Bestätigung + Link
```

## Technologie-Entscheidungen

**Warum Ollama statt OpenAI API?**
Datenschutz und Kosten. Briefe enthalten oft persönliche Informationen.
Ollama läuft komplett lokal, kein Datentransfer nach außen.

**Warum Tesseract statt Cloud-OCR?**
Gleicher Grund. Außerdem ist Tesseract für saubere gedruckte Dokumente
sehr präzise und komplett kostenlos.

**Warum keine Datenbank?**
Für den privaten Einzelnutzer-Use-Case nicht nötig. Der Kalender
selbst ist die Datenbank.
