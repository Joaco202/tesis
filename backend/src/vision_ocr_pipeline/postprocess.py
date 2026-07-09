from __future__ import annotations

import itertools
import re
import cv2
import numpy as np

from .ocr_engine import OCRText
from .config import DEFAULT_CONFIG, OCRConfig

#patrones de patentes chilenas estrictas
STRICT_NEW_PLATE = re.compile(r"^[BCDFGHJKLPRSTVWXYZ]{4}[0-9]{2}$")  #18 consonantes autorizadas
OLD_PLATE = re.compile(r"^[A-Z]{2}[0-9]{4}$")                        #formato antiguo (permite vocales)

PLATE_PATTERNS = [
    STRICT_NEW_PLATE,
    OLD_PLATE,
]

#mapas de sustitución geométrica para corrección de caracteres confusos en OCR
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


def check_and_invert_contrast(crop: np.ndarray) -> np.ndarray:
    """
    Detecta si el recorte de la patente tiene fondo oscuro y texto claro
    (típico de patentes diplomáticas o de zona franca) e invierte los colores
    para que quede texto oscuro sobre fondo claro, mejorando el reconocimiento del OCR.
    """
    if crop is None or crop.size == 0:
        return crop

    #convertir a escala de grises para analizar brillo
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    #calcular promedio de intensidad de los bordes (representa el fondo)
    #tomamos un borde delgado de 2 píxeles
    border_pixels = []
    border_pixels.extend(gray[0:2, :].flatten())
    border_pixels.extend(gray[h-2:h, :].flatten())
    border_pixels.extend(gray[:, 0:2].flatten())
    border_pixels.extend(gray[:, w-2:w].flatten())

    avg_border = np.mean(border_pixels) if border_pixels else 128

    #si el fondo (bordes) es predominantemente oscuro (menor a 100),
    #es muy probable que sea texto claro sobre fondo oscuro (diplomática, Zofri, etc.)
    if avg_border < 100:
        crop = cv2.bitwise_not(crop)

    return crop


def preprocess_plate_crop(crop: np.ndarray) -> np.ndarray:
    """
    Preprocesamiento de la porción de imagen que contiene la patente.
    Redimensiona la imagen si es muy pequeña para mejorar la precisión del OCR,
    manteniendo el formato de 3 canales BGR requerido por PaddleOCR.
    """
    if crop is None or crop.size == 0:
        return crop

    #invertir contraste si es fondo oscuro (diplomáticas, Zofri, etc.)
    crop = check_and_invert_contrast(crop)

    #redimensionar si es muy pequeña
    h, w = crop.shape[:2]
    #si la altura es menor a 80 o el ancho menor a 200, reescalamos con interpolación cúbica
    if h < 80 or w < 200:
        scale = max(2.0, 80.0 / h)
        crop = cv2.resize(crop, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    return crop


def normalize_plate_text(text: str) -> str:
    #elimina caracteres no alfanuméricos y convierte a mayúsculas
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def is_likely_plate(text: str) -> bool:
    #evalua si una cadena tiene estructura de patente chilena.

    #acepta:
    #coincidencia exacta con STRICT_NEW_PLATE (LLLL+DD) o OLD_PLATE (LL+DDDD)
    #fallback estricto: exactamente 6 caracteres con distribución 4+2 (nuevo) o 2+4 (antiguo).
    #no se permite ninguna otra combinación.
    
    if len(text) != 6:
        #los patrones chilenos son siempre de 6 caracteres
        return False

    if any(pattern.match(text) for pattern in PLATE_PATTERNS):
        return True

    letters = sum(ch.isalpha() for ch in text)
    digits = sum(ch.isdigit() for ch in text)

    #solo permitir distribuciones coherentes con formato chileno:
    #nuevo: 4 letras + 2 dígitos → los 4 primeros mayoritariamente letras
    #antiguo: 2 letras + 4 dígitos → los 2 primeros mayoritariamente letras
    if letters + digits < 6:
        #tiene caracteres que no son letra ni dígito → rechazar
        return False

    if letters == 4 and digits == 2:
        #candidato a formato nuevo: exigir que los dígitos estén al final
        return text[4:].replace("O", "0").replace("I", "1").isdigit() or text[4:].isdigit()
    if letters == 2 and digits == 4:
        #candidato a formato antiguo: exigir que las letras estén al inicio
        return text[:2].isalpha()

    return False


def generate_corrected_variants(candidate: str, cfg: OCRConfig | None = None) -> list[str]:
    #genera combinaciones de variantes de corrección basadas en la afinidad del formato.
    #aplica sustituciones para llevar el texto de entrada al formato de patente oficial chilena.
    
    if not candidate or len(candidate) != 6:
        return [candidate]

    #calcular afinidades del formato
    #nuevo: LLLLDD
    score_new = 0
    for i in range(4):
        ch = candidate[i]
        if ch.isalpha() or ch.isdigit():
            score_new += 1
    for i in range(4, 6):
        ch = candidate[i]
        if ch.isdigit() or ch in {"O", "D", "Q", "C", "G", "I", "L", "T", "Z", "B", "E", "A", "S"}:
            score_new += 1

    #antiguo: LLDDDD
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

    #generar opciones por cada una de las 6 posiciones
    pos_options: list[list[str]] = []
    for i in range(6):
        ch = candidate[i]
        opts = [ch]

        if target_new:
            #nuevo formato (LLLLDD)
            if i < 4:
                #se esperan consonantes válidas chilenas
                if ch not in "BCDFGHJKLPRSTVWXYZ":
                    if ch in CONSONANT_CORRECTION_MAP:
                        opts.extend(CONSONANT_CORRECTION_MAP[ch])
            else:
                #se esperan dígitos
                if not ch.isdigit():
                    if ch in DIGIT_CORRECTION_MAP:
                        opts.extend(DIGIT_CORRECTION_MAP[ch])
        else:
            #antiguo formato (LLDDDD)
            if i < 2:
                #se esperan letras (se permite A-Z)
                if not ch.isalpha():
                    if ch in LETTER_CORRECTION_MAP:
                        opts.extend(LETTER_CORRECTION_MAP[ch])
            else:
                #se esperan dígitos
                if not ch.isdigit():
                    if ch in DIGIT_CORRECTION_MAP:
                        opts.extend(DIGIT_CORRECTION_MAP[ch])

        pos_options.append(opts)

    #generar todas las combinaciones posibles limitando combinatoria masiva
    variants: set[str] = set()
    #limitar para evitar explosión de variantes si hay muchos caracteres a corregir
    perm_count = 1
    for opts in pos_options:
        perm_count *= len(opts)

    if perm_count > 64:
        #si es demasiado ambiguo, retornar solo el candidato original
        return [candidate]

    for combo in itertools.product(*pos_options):
        variants.add("".join(combo))

    return sorted(list(variants))


def _reversed_strict_variant(candidate: str) -> str | None:
    #Si el candidato de 6 caracteres NO coincide con ningún patrón estricto pero su
    #versión invertida SÍ coincide (exactamente, sin correcciones adicionales), devuelve
    #la versión invertida.  Esto cubre el caso donde el OCR lee el texto de derecha a
    #izquierda (p.ej. confunde el número de una casa con dígitos de la patente).
    #Solo se activa cuando el candidato original no encaja en ningún patrón para evitar
    #reemplazos indeseados en lecturas correctas.

    if not candidate or len(candidate) != 6:
        return None
    #solo actuar si el original NO es ya una patente estricta
    if any(p.match(candidate) for p in PLATE_PATTERNS):
        return None
    rev = candidate[::-1]
    if any(p.match(rev) for p in PLATE_PATTERNS):
        return rev
    return None


def score_variant(original: str, variant: str, confidence: float) -> float:
    #calcula una puntuación de aptitud para un candidato a patente.
    #aplica una penalización por cada sustitución de caracteres realizada.
    
    subs = sum(1 for a, b in zip(original, variant) if a != b)
    penalty = 0.3 * subs

    #comprobar si la variante coincide exactamente con un patrón estricto
    is_strict = any(pattern.match(variant) for pattern in PLATE_PATTERNS)

    if is_strict:
        #gran bonus de prioridad para patentes en formato oficial chileno
        return confidence + 2.0 - penalty
    elif is_likely_plate(variant):
        #prioridad media para formatos plausibles
        return confidence + 0.5 - penalty

    return confidence - penalty


#penalización extra para lecturas donde se detectó inversión de caracteres
_REVERSAL_PENALTY = 0.4


def best_plate_from_ocr(items: list[OCRText], cfg: OCRConfig | None = None) -> tuple[str | None, float | None]:
    #analiza todos los textos detectados por el OCR y selecciona la patente más apta.
    #aplica heurísticas de corrección de caracteres y prioriza coincidencias estrictas de formato.
    #incluye detección de lecturas invertidas (de derecha a izquierda) que ocurren cuando el OCR
    #confunde texto del entorno con la matrícula.
    
    best_text: str | None = None
    best_score: float = -999.0
    best_conf: float | None = None

    normalized_items: list[tuple[str, float]] = []
    for item in items:
        cand = normalize_plate_text(item.text)
        if cand:
            normalized_items.append((cand, item.confidence))

    def _evaluate(cand: str, conf: float, extra_penalty: float = 0.0) -> None:
        #Evalúa un candidato (y sus variantes corregidas) actualizando el mejor resultado.
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

    #1.evaluar tokens individuales, sus correcciones y sus posibles lecturas invertidas
    for cand, conf in normalized_items:
        _evaluate(cand, conf)
        #intentar lectura invertida solo si el candidato tiene 6 caracteres y no es ya válido
        if len(cand) == 6:
            rev = _reversed_strict_variant(cand)
            if rev:
                score = score_variant(rev, rev, conf) - _REVERSAL_PENALTY
                if score > best_score:
                    best_score = score
                    best_text = rev
                    best_conf = conf

    #2.evaluar composición de tokens contiguos (para patentes divididas)
    for i in range(len(normalized_items)):
        token_text = ""
        token_conf_sum = 0.0
        for j in range(i, min(i + 3, len(normalized_items))):
            piece_text, piece_conf = normalized_items[j]
            token_text += piece_text
            token_conf_sum += piece_conf
            avg_conf = token_conf_sum / (j - i + 1)

            _evaluate(token_text, avg_conf)
            #intentar lectura invertida para tokens concatenados de longitud 6
            if len(token_text) == 6:
                rev = _reversed_strict_variant(token_text)
                if rev:
                    score = score_variant(rev, rev, avg_conf) - _REVERSAL_PENALTY
                    if score > best_score:
                        best_score = score
                        best_text = rev
                        best_conf = avg_conf

    #umbral mínimo de validación para retornar un resultado
    if best_text and best_score >= 0.0:
        return best_text, best_conf

    return None, None
