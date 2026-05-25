from __future__ import annotations

import itertools
import re
import cv2
import numpy as np

from .ocr_engine import OCRText
from .config import DEFAULT_CONFIG, OCRConfig

# Patrones de patentes chilenas estrictas
STRICT_NEW_PLATE = re.compile(r"^[BCDFGHJKLPRSTVWXYZ]{4}[0-9]{2}$")  # 18 consonantes autorizadas
OLD_PLATE = re.compile(r"^[A-Z]{2}[0-9]{4}$")                        # Formato antiguo (permite vocales)

PLATE_PATTERNS = [
    STRICT_NEW_PLATE,
    OLD_PLATE,
]

# Mapas de sustitución geométrica para corrección de caracteres confusos en OCR
CONSONANT_CORRECTION_MAP: dict[str, list[str]] = {
    "O": ["D", "G", "C"],
    "I": ["L", "T", "J"],
    "A": ["R", "K", "H"],
    "E": ["G", "F", "K"],
    "U": ["V", "Y"],
    "M": ["W", "H"],
    "N": ["H", "R"],
    "Q": ["G", "D"],
    "0": ["D", "G", "C"],
    "1": ["L", "T", "J"],
    "2": ["Z"],
    "3": ["B"],
    "4": ["R", "K", "H"],
    "5": ["S"],
    "6": ["G"],
    "7": ["T"],
    "8": ["B"],
    "9": ["G"],
}

DIGIT_CORRECTION_MAP: dict[str, list[str]] = {
    "O": ["0"], "D": ["0"], "Q": ["0"], "C": ["0"], "G": ["0"],
    "I": ["1"], "L": ["1"], "T": ["1"],
    "Z": ["2"],
    "B": ["8", "3"], "E": ["3"],
    "A": ["4"],
    "S": ["5"],
    "G": ["6"],
    "T": ["7"],
    "B": ["8"],
    "G": ["9"],
}

LETTER_CORRECTION_MAP: dict[str, list[str]] = {
    "0": ["O", "D"],
    "1": ["I", "L"],
    "2": ["Z"],
    "3": ["B"],
    "4": ["A", "H"],
    "5": ["S"],
    "6": ["G"],
    "7": ["T"],
    "8": ["B"],
    "9": ["G"],
}


def preprocess_plate_crop(crop: np.ndarray) -> np.ndarray:
    """Preprocesamiento de la porción de imagen que contiene la patente."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=60, sigmaSpace=60)
    boosted = cv2.convertScaleAbs(denoised, alpha=1.2, beta=8)
    _, binary = cv2.threshold(boosted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def normalize_plate_text(text: str) -> str:
    """Elimina caracteres no alfanuméricos y convierte a mayúsculas."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def is_likely_plate(text: str) -> bool:
    """Evalúa de forma general si una cadena tiene estructura de patente."""
    if len(text) < 5 or len(text) > 8:
        return False

    if any(pattern.match(text) for pattern in PLATE_PATTERNS):
        return True

    letters = sum(ch.isalpha() for ch in text)
    digits = sum(ch.isdigit() for ch in text)
    return letters >= 2 and digits >= 2


def generate_corrected_variants(candidate: str, cfg: OCRConfig | None = None) -> list[str]:
    """
    Genera combinaciones de variantes de corrección basadas en la afinidad del formato.
    Aplica sustituciones para llevar el texto de entrada al formato de patente oficial chilena.
    """
    if not candidate or len(candidate) != 6:
        return [candidate]

    # Calcular afinidades del formato
    # Nuevo: LLLLDD
    score_new = 0
    for i in range(4):
        ch = candidate[i]
        if ch.isalpha() or ch.isdigit():
            score_new += 1
    for i in range(4, 6):
        ch = candidate[i]
        if ch.isdigit() or ch in {"O", "D", "Q", "C", "G", "I", "L", "T", "Z", "B", "E", "A", "S"}:
            score_new += 1

    # Antiguo: LLDDDD
    score_old = 0
    for i in range(2):
        ch = candidate[i]
        if ch.isalpha() or ch.isdigit():
            score_old += 1
    for i in range(2, 6):
        ch = candidate[i]
        if ch.isdigit() or ch in {"O", "D", "Q", "C", "G", "I", "L", "T", "Z", "B", "E", "A", "S"}:
            score_old += 1

    target_new = score_new >= score_old

    # Generar opciones por cada una de las 6 posiciones
    pos_options: list[list[str]] = []
    for i in range(6):
        ch = candidate[i]
        opts = [ch]

        if target_new:
            # Nuevo Formato (LLLLDD)
            if i < 4:
                # Se esperan consonantes válidas chilenas
                if ch not in "BCDFGHJKLPRSTVWXYZ":
                    if ch in CONSONANT_CORRECTION_MAP:
                        opts.extend(CONSONANT_CORRECTION_MAP[ch])
            else:
                # Se esperan dígitos
                if not ch.isdigit():
                    if ch in DIGIT_CORRECTION_MAP:
                        opts.extend(DIGIT_CORRECTION_MAP[ch])
        else:
            # Antiguo Formato (LLDDDD)
            if i < 2:
                # Se esperan letras (se permite A-Z)
                if not ch.isalpha():
                    if ch in LETTER_CORRECTION_MAP:
                        opts.extend(LETTER_CORRECTION_MAP[ch])
            else:
                # Se esperan dígitos
                if not ch.isdigit():
                    if ch in DIGIT_CORRECTION_MAP:
                        opts.extend(DIGIT_CORRECTION_MAP[ch])

        pos_options.append(opts)

    # Generar todas las combinaciones posibles limitando combinatoria masiva
    variants: set[str] = set()
    # Limitar para evitar explosión de variantes si hay muchos caracteres a corregir
    perm_count = 1
    for opts in pos_options:
        perm_count *= len(opts)

    if perm_count > 64:
        # Si es demasiado ambiguo, retornar solo el candidato original
        return [candidate]

    for combo in itertools.product(*pos_options):
        variants.add("".join(combo))

    return list(variants)


def _reversed_strict_variant(candidate: str) -> str | None:
    """
    Si el candidato de 6 caracteres NO coincide con ningún patrón estricto pero su
    versión invertida SÍ coincide (exactamente, sin correcciones adicionales), devuelve
    la versión invertida.  Esto cubre el caso donde el OCR lee el texto de derecha a
    izquierda (p.ej. confunde el número de una casa con dígitos de la patente).
    Solo se activa cuando el candidato original no encaja en ningún patrón para evitar
    reemplazos indeseados en lecturas correctas.
    """
    if not candidate or len(candidate) != 6:
        return None
    # Solo actuar si el original NO es ya una patente estricta
    if any(p.match(candidate) for p in PLATE_PATTERNS):
        return None
    rev = candidate[::-1]
    if any(p.match(rev) for p in PLATE_PATTERNS):
        return rev
    return None


def score_variant(original: str, variant: str, confidence: float) -> float:
    """
    Calcula una puntuación de aptitud para un candidato a patente.
    Aplica una penalización por cada sustitución de caracteres realizada.
    """
    subs = sum(1 for a, b in zip(original, variant) if a != b)
    penalty = 0.3 * subs

    # Comprobar si la variante coincide exactamente con un patrón estricto
    is_strict = any(pattern.match(variant) for pattern in PLATE_PATTERNS)

    if is_strict:
        # Gran bonus de prioridad para patentes en formato oficial chileno
        return confidence + 2.0 - penalty
    elif is_likely_plate(variant):
        # Prioridad media para formatos plausibles
        return confidence + 0.5 - penalty

    return confidence - penalty


# Penalización extra para lecturas donde se detectó inversión de caracteres
_REVERSAL_PENALTY = 0.4


def best_plate_from_ocr(items: list[OCRText], cfg: OCRConfig | None = None) -> tuple[str | None, float | None]:
    """
    Analiza todos los textos detectados por el OCR y selecciona la patente más apta.
    Aplica heurísticas de corrección de caracteres y prioriza coincidencias estrictas de formato.
    Incluye detección de lecturas invertidas (de derecha a izquierda) que ocurren cuando el OCR
    confunde texto del entorno con la matrícula.
    """
    best_text: str | None = None
    best_score: float = -999.0
    best_conf: float | None = None

    normalized_items: list[tuple[str, float]] = []
    for item in items:
        cand = normalize_plate_text(item.text)
        if cand:
            normalized_items.append((cand, item.confidence))

    def _evaluate(cand: str, conf: float, extra_penalty: float = 0.0) -> None:
        """Evalúa un candidato (y sus variantes corregidas) actualizando el mejor resultado."""
        nonlocal best_score, best_text, best_conf
        variants = generate_corrected_variants(cand, cfg)
        for var in variants:
            if not is_likely_plate(var):
                continue
            score = score_variant(cand, var, conf) - extra_penalty
            if score > best_score:
                best_score = score
                best_text = var
                best_conf = conf

    # 1. Evaluar tokens individuales, sus correcciones y sus posibles lecturas invertidas
    for cand, conf in normalized_items:
        _evaluate(cand, conf)
        # Intentar lectura invertida solo si el candidato tiene 6 caracteres y no es ya válido
        if len(cand) == 6:
            rev = _reversed_strict_variant(cand)
            if rev:
                score = score_variant(rev, rev, conf) - _REVERSAL_PENALTY
                if score > best_score:
                    best_score = score
                    best_text = rev
                    best_conf = conf

    # 2. Evaluar composición de tokens contiguos (para patentes divididas)
    for i in range(len(normalized_items)):
        token_text = ""
        token_conf_sum = 0.0
        for j in range(i, min(i + 3, len(normalized_items))):
            piece_text, piece_conf = normalized_items[j]
            token_text += piece_text
            token_conf_sum += piece_conf
            avg_conf = token_conf_sum / (j - i + 1)

            _evaluate(token_text, avg_conf)
            # Intentar lectura invertida para tokens concatenados de longitud 6
            if len(token_text) == 6:
                rev = _reversed_strict_variant(token_text)
                if rev:
                    score = score_variant(rev, rev, avg_conf) - _REVERSAL_PENALTY
                    if score > best_score:
                        best_score = score
                        best_text = rev
                        best_conf = avg_conf

    # Umbral mínimo de validación para retornar un resultado
    if best_text and best_score >= 0.0:
        return best_text, best_conf

    return None, None
