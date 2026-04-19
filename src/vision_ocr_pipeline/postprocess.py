from __future__ import annotations

import re

import cv2
import numpy as np

from .ocr_engine import OCRText


PLATE_PATTERNS = [
    re.compile(r"^[A-Z]{4}[0-9]{2}$"),
    re.compile(r"^[A-Z]{2}[0-9]{4}$"),
    re.compile(r"^[A-Z]{2}[A-Z]{2}[0-9]{2}$"),
]


def preprocess_plate_crop(crop: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=60, sigmaSpace=60)
    boosted = cv2.convertScaleAbs(denoised, alpha=1.2, beta=8)
    _, binary = cv2.threshold(boosted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def normalize_plate_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def is_likely_plate(text: str) -> bool:
    if len(text) < 5 or len(text) > 8:
        return False

    if any(pattern.match(text) for pattern in PLATE_PATTERNS):
        return True

    letters = sum(ch.isalpha() for ch in text)
    digits = sum(ch.isdigit() for ch in text)
    return letters >= 2 and digits >= 2


def best_plate_from_ocr(items: list[OCRText]) -> tuple[str | None, float | None]:
    best_text: str | None = None
    best_conf: float | None = None

    normalized_items: list[tuple[str, float]] = []
    for item in items:
        candidate = normalize_plate_text(item.text)
        if candidate:
            normalized_items.append((candidate, item.confidence))

        if not is_likely_plate(candidate):
            continue
        if best_conf is None or item.confidence > best_conf:
            best_text = candidate
            best_conf = item.confidence

    # Si OCR separa la patente en varios trozos, intentar recomponer tokens contiguos.
    for i in range(len(normalized_items)):
        token_text = ""
        token_conf_sum = 0.0
        for j in range(i, min(i + 3, len(normalized_items))):
            piece_text, piece_conf = normalized_items[j]
            token_text += piece_text
            token_conf_sum += piece_conf
            avg_conf = token_conf_sum / (j - i + 1)
            if not is_likely_plate(token_text):
                continue
            if best_conf is None or avg_conf > best_conf:
                best_text = token_text
                best_conf = avg_conf

    return best_text, best_conf
