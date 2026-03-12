"""
LetterBot – Telegram → Ollama → Google Calendar
================================================
Schicke Fotos oder Textnachrichten an diesen Bot.
Er extrahiert Aufgaben/Termine und trägt sie in deinen Kalender ein.
"""

import logging
import os
import tempfile
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

from ocr import extract_text_from_image
from llm import extract_events_from_text
from calendar_client import create_calendar_event

load_dotenv()

logging.basicConfig(
    format="%(asctime)s  %(levelname)s  %(name)s  %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])


# ── Sicherheitscheck ──────────────────────────────────────────────────────────
def only_owner(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ALLOWED_USER_ID:
            await update.message.reply_text("⛔ Nicht autorisiert.")
            return
        return await func(update, ctx)
    return wrapper


# ── /start ────────────────────────────────────────────────────────────────────
@only_owner
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/start", "/hilfe", "/debug"]]
    await update.message.reply_text(
        "👋 *LetterBot bereit!*\n\n"
        "Schick mir:\n"
        "📷 Ein *Foto* eines Briefes\n"
        "✍️ Eine *Textnachricht* mit Terminen\n\n"
        "Tipp: `/debug` um die Verbindung zu testen.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


# ── /hilfe ────────────────────────────────────────────────────────────────────
@only_owner
async def cmd_hilfe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Hilfe*\n\n"
        "*Foto schicken:* Fotografiere einen Brief, ein Dokument oder eine Einladung.\n"
        "*Text schicken:* Schreib oder kopiere einen Text mit Terminen.\n\n"
        "Der Bot erkennt:\n"
        "• Konkrete Termine mit Datum & Uhrzeit\n"
        "• Deadlines ('bis zum ...')\n"
        "• Aufgaben ('bitte ... bis ...')\n\n"
        "Alle erkannten Einträge landen direkt in deinem Google Kalender.\n\n"
        "Bei Problemen: `/debug`",
        parse_mode="Markdown",
    )


# ── /debug ────────────────────────────────────────────────────────────────────
@only_owner
async def cmd_debug(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Testet alle Pipeline-Schritte einzeln und zeigt genau wo ein Problem liegt."""
    test_text = "Testtermin am 20. März 2026 um 14:00 Uhr – Arzttermin bei Dr. Müller"
    lines = ["🔬 *Debug – Pipeline-Test*\n"]

    # ── 1. Ollama ──
    lines.append("*Schritt 1: Ollama Verbindung*")
    try:
        import httpx as _httpx
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        r = _httpx.get(ollama_url, timeout=5)
        lines.append(f"✅ Erreichbar unter `{ollama_url}`")
        lines.append(f"   Antwort: `{r.text[:60]}`")
    except Exception as e:
        lines.append(f"❌ FEHLER: `{e}`")
        lines.append("→ `ollama serve` im Terminal starten!")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── 2. LLM ──
    lines.append("\n*Schritt 2: LLM Event-Extraktion*")
    lines.append(f"Eingabe: `{test_text}`")
    events = []
    try:
        events = extract_events_from_text(test_text)
        if events:
            lines.append(f"✅ {len(events)} Event(s) erkannt:")
            for e in events:
                lines.append(
                    f"  • `{e.get('title')}` | "
                    f"{e.get('start_date') or 'kein Datum'} "
                    f"{e.get('start_time') or ''}"
                )
        else:
            lines.append("❌ LLM gab leere Liste zurück!")
            lines.append(f"   Genutztes Modell: `{os.getenv('OLLAMA_MODEL','llama3.2')}`")
            lines.append("→ Im Terminal prüfen: `ollama list`")
            lines.append("→ Modell laden: `ollama pull llama3.2`")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
            return
    except Exception as e:
        lines.append(f"❌ FEHLER: `{e}`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── 3. Google Calendar Auth ──
    lines.append("\n*Schritt 3: Google Calendar Verbindung*")
    service = None
    try:
        from calendar_client import _get_service, _get_calendar_id
        service = _get_service()
        cal = service.calendars().get(calendarId=_get_calendar_id()).execute()
        lines.append(f"✅ Kalender gefunden!")
        lines.append(f"   Name: *{cal.get('summary')}*")
        lines.append(f"   ID: `{cal.get('id')}`")
        lines.append(f"   Zeitzone: `{cal.get('timeZone')}`")
    except FileNotFoundError as e:
        lines.append(f"❌ credentials.json nicht gefunden!")
        lines.append("→ Google Cloud Console → Anmeldedaten → OAuth Client → JSON herunterladen")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return
    except Exception as e:
        lines.append(f"❌ FEHLER: `{e}`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── 4. Test-Event anlegen ──
    lines.append("\n*Schritt 4: Test-Event anlegen*")
    try:
        link = create_calendar_event(events[0])
        if link:
            lines.append(f"✅ Event erfolgreich angelegt!")
            lines.append(f"🔗 [Jetzt im Kalender ansehen]({link})")
        else:
            lines.append("⚠️ API-Call erfolgreich aber kein Link zurück")
            lines.append("→ Kalender manuell prüfen ob Event erschienen ist")
    except Exception as e:
        lines.append(f"❌ FEHLER beim Anlegen: `{e}`")

    lines.append("\n— Debug abgeschlossen —")
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True
    )


# ── Foto-Handler ──────────────────────────────────────────────────────────────
@only_owner
async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📷 Foto empfangen – lese Text aus...")
    photo = update.message.photo[-1]
    tg_file = await ctx.bot.get_file(photo.file_id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await tg_file.download_to_drive(tmp.name)
        image_path = tmp.name

    try:
        await msg.edit_text("🔍 Erkenne Text per OCR...")
        raw_text = extract_text_from_image(image_path)
        log.info("OCR Ergebnis (%d Zeichen): %s", len(raw_text), raw_text[:200])

        if not raw_text.strip():
            await msg.edit_text(
                "❌ Konnte keinen Text erkennen.\n\n"
                "💡 Tipps:\n"
                "• Bessere Beleuchtung\n"
                "• Gerade Perspektive (von oben)\n"
                "• Microsoft Lens App vorher nutzen"
            )
            return

        await _process_text(msg, raw_text, source="Foto")
    finally:
        Path(image_path).unlink(missing_ok=True)


# ── Text-Handler ──────────────────────────────────────────────────────────────
@only_owner
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    log.info("Text empfangen (%d Zeichen): %s", len(raw_text), raw_text[:100])
    msg = await update.message.reply_text("📝 Analysiere Text...")
    await _process_text(msg, raw_text, source="Text")


# ── Pipeline ──────────────────────────────────────────────────────────────────
async def _process_text(msg, raw_text: str, source: str):
    await msg.edit_text("🤖 KI analysiert Inhalt...")

    try:
        events = extract_events_from_text(raw_text)
    except Exception as e:
        log.error("LLM Fehler: %s", e)
        await msg.edit_text(
            f"❌ KI-Fehler: `{e}`\n\n"
            "Bitte `/debug` ausführen um die Verbindung zu prüfen.",
            parse_mode="Markdown"
        )
        return

    log.info("Events vom LLM: %s", events)

    if not events:
        await msg.edit_text(
            f"ℹ️ *Keine Termine gefunden* in: {source}\n\n"
            f"Erkannter Text:\n```\n{raw_text[:400]}\n```\n\n"
            "Falls das falsch ist: `/debug` ausführen um das Modell zu prüfen.",
            parse_mode="Markdown",
        )
        return

    await msg.edit_text(f"📅 Lege {len(events)} Eintrag/Einträge an...")

    results, errors = [], []
    for event in events:
        try:
            link = create_calendar_event(event)
            results.append((event, link))
            log.info("Kalender-Event angelegt: %s -> %s", event.get("title"), link)
        except Exception as e:
            log.error("Kalender-Fehler: %s – %s", event.get("title"), e)
            errors.append(f"{event.get('title','?')}: `{e}`")

    lines = [f"✅ *{len(results)} Termin(e) angelegt* ({source})\n"]
    for event, link in results:
        date_str = event.get("start_date", "")
        time_str = event.get("start_time", "")
        when = f"{date_str} {time_str}".strip() or "kein Datum"
        lines.append(f"📌 *{event['title']}*")
        lines.append(f"   🕐 {when}")
        if event.get("location"):
            lines.append(f"   📍 {event['location']}")
        if link:
            lines.append(f"   🔗 [Öffnen]({link})")
        lines.append("")

    if errors:
        lines.append("⚠️ *Fehler bei:*")
        for err in errors:
            lines.append(f"  • {err}")

    await msg.edit_text(
        "\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True
    )


# ── Start ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("hilfe",  cmd_hilfe))
    app.add_handler(CommandHandler("debug",  cmd_debug))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("Bot gestartet.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
