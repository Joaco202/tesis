from __future__ import annotations

import re

import cv2
import numpy as np

from .ocr_engine import OCRText
from .config import DEFAULT_CONFIG


PLATE_PATTERNS = [
    re.compile(r"^[B-DF-HJ-NP-TV-Z]{4}[0-9]{2}$"),  # Patente nueva chilena (consonantes)
    re.compile(r"^[A-Z]{4}[0-9]{2}$"),              # Patente nueva general (tolerancia OCR)
    re.compile(r"^[A-Z]{2}[0-9]{4}$"),              # Patente vieja chilena
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


def _generate_confusion_variants(text: str, max_subs: int = 2) -> list[str]:
    """Genera variantes del texto aplicando sustituciones típicas OCR.
    Usa el mapa definido en la configuración y, si `aggressive_confusion` está activado,
    prueba sustituciones en ambas direcciones (digit<->letter).
    """
    # Preferir mapa desde la configuración global
    cfg_map = getattr(DEFAULT_CONFIG.ocr, "confusion_map", None) or {}
    max_subs = max_subs or getattr(DEFAULT_CONFIG.ocr, "max_confusion_subs", 2)
    aggressive = getattr(DEFAULT_CONFIG.ocr, "aggressive_confusion", False)

    # Construir mapa inverso si estamos en modo agresivo
    reverse_map: dict[str, str] = {}
    if aggressive:
        for k, v in cfg_map.items():
            # sólo añadir si no sobreescribe
            if v not in reverse_map:
                reverse_map[v] = k

    # índices candidatas para sustitución (letras o dígitos según mapa)
    indices = [i for i, ch in enumerate(text) if ch in cfg_map or (aggressive and ch in reverse_map)]
    variants = set()

    # función ayuda para aplicar sustitución en posición i con dirección adecuada
    def substitute_at(s: str, pos: int, to_char: str) -> str:
        lst = list(s)
        lst[pos] = to_char
        return "".join(lst)

    # Single substitutions
    for i in indices:
        ch = text[i]
        if ch in cfg_map:
            variants.add(substitute_at(text, i, cfg_map[ch]))
        if aggressive and ch in reverse_map:
            variants.add(substitute_at(text, i, reverse_map[ch]))

    # Double substitutions (combinatorial limitado)
    if max_subs >= 2:
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                s = text
                ia = indices[a]
                ib = indices[b]
                ca = s[ia]
                cb = s[ib]
                # aplicar combinación de direcciones posibles
                opts_a = [cfg_map[ca]] if ca in cfg_map else ([] if not aggressive else ([reverse_map[ca]] if ca in reverse_map else []))
                opts_b = [cfg_map[cb]] if cb in cfg_map else ([] if not aggressive else ([reverse_map[cb]] if cb in reverse_map else []))
                for oa in opts_a:
                    for ob in opts_b:
                        lst = list(s)
                        lst[ia] = oa
                        lst[ib] = ob
                        variants.add("".join(lst))

    return list(variants)


def _try_fix_confusions(candidate: str) -> str | None:
    """Intenta corregir confusiones OCR en `candidate`. Devuelve la primera variante que
    matchee alguno de los `PLATE_PATTERNS` o que pase `is_likely_plate`.
    """
    if not candidate:
        return None

    # Primero comprobar si ya es válida
    if any(p.match(candidate) for p in PLATE_PATTERNS) or is_likely_plate(candidate):
        return candidate

    for var in _generate_confusion_variants(candidate):
        if any(p.match(var) for p in PLATE_PATTERNS) or is_likely_plate(var):
            return var

    return None


def _force_plate_format(candidate: str) -> str | None:
    """Intento dirigido: para cadenas de longitud 6, evaluar si se asemeja más a una patente nueva
    (LLLLDD) o a una patente antigua (LLDDDD) y aplicar el mapa de sustituciones correspondientemente.
    """
    if not candidate or len(candidate) != 6:
        return None

    cfg_map = getattr(DEFAULT_CONFIG.ocr, "confusion_map", {})
    reverse_map = {v: k for k, v in cfg_map.items()}

    # Evaluar afinidad con LLLLDD (Nueva)
    # Posiciones 0, 1, 2, 3: letras (o dígitos mapeables a letras)
    # Posiciones 4, 5: dígitos (o letras mapeables a dígitos)
    score_new = 0
    for i in range(4):
        if candidate[i].isalpha() or candidate[i] in cfg_map:
            score_new += 1
    for i in range(4, 6):
        if candidate[i].isdigit() or candidate[i] in reverse_map:
            score_new += 1

    # Evaluar afinidad con LLDDDD (Antigua)
    # Posiciones 0, 1: letras (o dígitos mapeables a letras)
    # Posiciones 2, 3, 4, 5: dígitos (o letras mapeables a dígitos)
    score_old = 0
    for i in range(2):
        if candidate[i].isalpha() or candidate[i] in cfg_map:
            score_old += 1
    for i in range(2, 6):
        if candidate[i].isdigit() or candidate[i] in reverse_map:
            score_old += 1

    s = list(candidate)
    changed = False

    if score_new >= score_old:
        # Forzar formato LLLLDD (Nuevo)
        for i in range(4):
            ch = s[i]
            if ch.isdigit() and ch in cfg_map:
                s[i] = cfg_map[ch]
                changed = True
        for i in range(4, 6):
            ch = s[i]
            if ch.isalpha() and ch in reverse_map:
                s[i] = reverse_map[ch]
                changed = True
    else:
        # Forzar formato LLDDDD (Antiguo)
        for i in range(2):
            ch = s[i]
            if ch.isdigit() and ch in cfg_map:
                s[i] = cfg_map[ch]
                changed = True
        for i in range(2, 6):
            ch = s[i]
            if ch.isalpha() and ch in reverse_map:
                s[i] = reverse_map[ch]
                changed = True

    candidate_forced = "".join(s)
    if changed and any(p.match(candidate_forced) for p in PLATE_PATTERNS):
        return candidate_forced
    return None


def best_plate_from_ocr(items: list[OCRText]) -> tuple[str | None, float | None]:
    best_text: str | None = None
    best_conf: float | None = None

    def is_exact_plate(candidate: str) -> bool:
        return any(pattern.match(candidate) for pattern in PLATE_PATTERNS)

    normalized_items: list[tuple[str, float]] = []
    for item in items:
        candidate = normalize_plate_text(item.text)
        if candidate:
            normalized_items.append((candidate, item.confidence))

        if is_exact_plate(candidate):
            candidate_fixed = candidate
        else:
            candidate_fixed = _force_plate_format(candidate) or _try_fix_confusions(candidate)
        if candidate_fixed:
            candidate = candidate_fixed

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
            if is_exact_plate(token_text):
                fixed = token_text
            else:
                fixed = _force_plate_format(token_text) or _try_fix_confusions(token_text)
            if fixed is not None:
                token_text = fixed
            elif not is_likely_plate(token_text):
                continue
            if best_conf is None or avg_conf > best_conf:
                best_text = token_text
                best_conf = avg_conf

    # Si no encontramos nada directo, intentar corregir tokens individuales
    if best_text is None:
        for cand, conf in normalized_items:
            if is_exact_plate(cand):
                fixed = cand
            else:
                fixed = _force_plate_format(cand) or _try_fix_confusions(cand)
            if fixed:
                return fixed, conf

    return best_text, best_conf
