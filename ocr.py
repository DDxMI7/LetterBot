"""
ocr.py – Text aus Bildern extrahieren
"""

import logging
import os
import pytesseract
from PIL import Image
import cv2
import numpy as np

log = logging.getLogger(__name__)

# Windows: Pfad einkommentieren falls tesseract nicht im PATH ist
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TESSERACT_CONFIG = "--oem 3 --psm 3 -l deu+eng"


def extract_text_from_image(image_path: str) -> str:
    """
    Versucht mehrere Strategien und gibt den besten Text zurück.
    Bei sauberen Scans/Screenshots reicht oft das Original-Bild.
    """
    log.info("OCR für: %s", image_path)

    results = []

    # Strategie 1: Original-Bild ohne jede Vorverarbeitung
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, config=TESSERACT_CONFIG)
        if text.strip():
            results.append(text.strip())
            log.info("Strategie 1 (Original): %d Zeichen", len(text))
    except Exception as e:
        log.warning("Strategie 1 fehlgeschlagen: %s", e)

    # Strategie 2: Hochskaliert (besser für kleine Texte)
    try:
        img = Image.open(image_path)
        w, h = img.size
        if max(w, h) < 2000:  # Nur skalieren wenn Bild klein
            img = img.resize((w * 2, h * 2), Image.LANCZOS)
        text = pytesseract.image_to_string(img, config=TESSERACT_CONFIG)
        if text.strip():
            results.append(text.strip())
            log.info("Strategie 2 (Skaliert): %d Zeichen", len(text))
    except Exception as e:
        log.warning("Strategie 2 fehlgeschlagen: %s", e)

    # Strategie 3: Graustufen + leichte Schärfung (für Fotos)
    try:
        img_cv = cv2.imread(image_path)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        # Nur leichte Schärfung, keine aggressive Binarisierung
        sharpened = cv2.filter2D(gray, -1, np.array([[0,-1,0],[-1,5,-1],[0,-1,0]]))
        text = pytesseract.image_to_string(
            Image.fromarray(sharpened), config=TESSERACT_CONFIG
        )
        if text.strip():
            results.append(text.strip())
            log.info("Strategie 3 (Geschärft): %d Zeichen", len(text))
    except Exception as e:
        log.warning("Strategie 3 fehlgeschlagen: %s", e)

    # Strategie 4: Deskew für schiefe Fotos
    try:
        img_cv = cv2.imread(image_path)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        deskewed = _deskew(gray)
        text = pytesseract.image_to_string(
            Image.fromarray(deskewed), config=TESSERACT_CONFIG
        )
        if text.strip():
            results.append(text.strip())
            log.info("Strategie 4 (Deskewed): %d Zeichen", len(text))
    except Exception as e:
        log.warning("Strategie 4 fehlgeschlagen: %s", e)

    if not results:
        return ""

    # Besten Text wählen: längster ist meistens der vollständigste
    best = max(results, key=lambda t: len(t))
    cleaned = _clean_text(best)
    log.info("Bestes Ergebnis: %d Zeichen nach Cleanup", len(cleaned))
    return cleaned


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Begradigt schiefe Fotos."""
    try:
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 10:
            return gray
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 20:
            return gray  # Zu schief → original behalten
        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return gray


def _clean_text(text: str) -> str:
    """
    Bereinigt OCR-Ausgabe für bessere LLM-Verarbeitung.
    - Entfernt übermäßige Leerzeilen
    - Entfernt Steuerzeichen
    - Normalisiert Leerzeichen
    """
    import re
    # Steuerzeichen entfernen (außer Newline)
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Mehr als 2 aufeinanderfolgende Leerzeilen → eine Leerzeile
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Zeilen trimmen
    lines = [line.strip() for line in text.splitlines()]
    # Leere Zeilen am Anfang/Ende entfernen
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)
