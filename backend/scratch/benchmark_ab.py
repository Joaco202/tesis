"""
Benchmark A/B: Compara la precisión y velocidad del OCR con y sin
los preprocesadores de documentos de PaddleX (UVDoc, doc_ori, textline_ori).

Método A (ANTES): pipeline completo con preprocesadores habilitados
Método B (DESPUÉS): preprocesadores desactivados (optimización actual)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.detector import YoloDetector
from src.vision_ocr_pipeline.ocr_engine import OCRText, normalize_ocr_output
from src.vision_ocr_pipeline.postprocess import best_plate_from_ocr, preprocess_plate_crop


def run_ocr_method_a(ocr_engine, crop):
    """Método A: pipeline COMPLETO con preprocesadores (UVDoc, doc_ori, textline_ori)."""
    start = time.perf_counter()
    raw = ocr_engine._ocr.ocr(crop)
    elapsed = time.perf_counter() - start
    result = normalize_ocr_output(raw)
    texts = []
    if result:
        for line in result:
            if not line:
                continue
            for item in line:
                if len(item) < 2:
                    continue
                try:
                    if isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
                        text, conf = item[1][0], item[1][1]
                    else:
                        text, conf = item[1], 1.0
                    texts.append(OCRText(text=str(text), confidence=float(conf)))
                except Exception:
                    continue
    return texts, elapsed


def run_ocr_method_b(ocr_engine, crop):
    """Método B: predict() SIN preprocesadores (optimización actual)."""
    start = time.perf_counter()
    raw = list(ocr_engine._ocr.predict(
        crop,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    ))
    elapsed = time.perf_counter() - start
    result = normalize_ocr_output(raw)
    texts = []
    if result:
        for line in result:
            if not line:
                continue
            for item in line:
                if len(item) < 2:
                    continue
                try:
                    if isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
                        text, conf = item[1][0], item[1][1]
                    else:
                        text, conf = item[1], 1.0
                    texts.append(OCRText(text=str(text), confidence=float(conf)))
                except Exception:
                    continue
    return texts, elapsed


def main():
    cfg = load_config("config.yaml")
    detector = YoloDetector(cfg.detection, device=cfg.runtime.device)

    # Warmup GPU
    import numpy as _np
    detector.detect(_np.zeros((480, 640, 3), dtype=_np.uint8))

    from src.vision_ocr_pipeline.ocr_engine import PaddleOCREngine
    ocr_engine = PaddleOCREngine(cfg.ocr)

    source_dir = Path("inputs/raw")
    valid_exts = {".jpg", ".jpeg", ".png"}
    images = sorted(
        [p for p in source_dir.iterdir() if p.suffix.lower() in valid_exts],
        key=lambda x: x.name,
    )

    print(f"{'='*90}")
    print(f"BENCHMARK A/B: {len(images)} imágenes")
    print(f"Método A = OCR completo (con UVDoc + doc_ori + textline_ori)")
    print(f"Método B = OCR optimizado (sin preprocesadores)")
    print(f"{'='*90}")
    print()

    results_a = []
    results_b = []
    total_time_a = 0.0
    total_time_b = 0.0

    for idx, img_path in enumerate(images, 1):
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        detections = sorted(detector.detect(image), key=lambda d: d.confidence, reverse=True)
        if not detections:
            continue

        det = detections[0]
        crop = image[max(det.y1, 0):max(det.y2, 0), max(det.x1, 0):max(det.x2, 0)]
        if not crop.size:
            continue

        h, w = crop.shape[:2]
        aspect_ratio = w / h if h > 0 else 0

        if 0 < aspect_ratio < 2.0:
            mid_y = h // 2
            top_prep = preprocess_plate_crop(crop[0:mid_y, :])
            bottom_prep = preprocess_plate_crop(crop[mid_y:h, :])

            texts_a_top, t1 = run_ocr_method_a(ocr_engine, top_prep)
            texts_a_bot, t2 = run_ocr_method_a(ocr_engine, bottom_prep)
            texts_a = texts_a_top + texts_a_bot
            time_a = t1 + t2

            texts_b_top, t3 = run_ocr_method_b(ocr_engine, top_prep)
            texts_b_bot, t4 = run_ocr_method_b(ocr_engine, bottom_prep)
            texts_b = texts_b_top + texts_b_bot
            time_b = t3 + t4
        else:
            ocr_input = preprocess_plate_crop(crop)
            texts_a, time_a = run_ocr_method_a(ocr_engine, ocr_input)
            texts_b, time_b = run_ocr_method_b(ocr_engine, ocr_input)

        plate_a, conf_a = best_plate_from_ocr(texts_a, cfg.ocr)
        plate_b, conf_b = best_plate_from_ocr(texts_b, cfg.ocr)

        total_time_a += time_a
        total_time_b += time_b

        results_a.append((img_path.name, plate_a, conf_a, time_a))
        results_b.append((img_path.name, plate_b, conf_b, time_b))

        # Mostrar solo diferencias o detecciones
        marker = ""
        if plate_a != plate_b:
            marker = " ⚠️ DIFERENCIA"
        elif plate_a:
            marker = " ✓"

        if plate_a or plate_b or marker:
            raw_a = ", ".join(f"'{t.text}'" for t in texts_a[:3])
            raw_b = ", ".join(f"'{t.text}'" for t in texts_b[:3])
            print(f"[{idx:3d}] {img_path.name[:55]:55s}")
            print(f"       A: {plate_a or '---':8s} ({conf_a or 0:.1%}) [{time_a:.3f}s] raw=[{raw_a}]")
            print(f"       B: {plate_b or '---':8s} ({conf_b or 0:.1%}) [{time_b:.3f}s] raw=[{raw_b}]{marker}")
            print()

    # Resumen
    detected_a = sum(1 for _, p, _, _ in results_a if p)
    detected_b = sum(1 for _, p, _, _ in results_b if p)
    avg_conf_a = sum(c or 0 for _, _, c, _ in results_a if c) / max(detected_a, 1)
    avg_conf_b = sum(c or 0 for _, _, c, _ in results_b if c) / max(detected_b, 1)
    matches = sum(1 for (_, pa, _, _), (_, pb, _, _) in zip(results_a, results_b) if pa == pb and pa)
    diffs = sum(1 for (_, pa, _, _), (_, pb, _, _) in zip(results_a, results_b) if pa != pb)

    print(f"{'='*90}")
    print(f"RESUMEN")
    print(f"{'='*90}")
    print(f"Total imágenes con detección YOLO: {len(results_a)}")
    print()
    print(f"{'Métrica':<35s} {'A (completo)':>14s} {'B (optimizado)':>14s}")
    print(f"{'-'*65}")
    print(f"{'Patentes detectadas':<35s} {detected_a:>14d} {detected_b:>14d}")
    print(f"{'Confianza promedio':<35s} {avg_conf_a:>13.1%} {avg_conf_b:>13.1%}")
    print(f"{'Tiempo OCR total':<35s} {total_time_a:>13.1f}s {total_time_b:>13.1f}s")
    print(f"{'Tiempo OCR promedio/imagen':<35s} {total_time_a/max(len(results_a),1):>13.3f}s {total_time_b/max(len(results_a),1):>13.3f}s")
    print(f"{'Coincidencias exactas':<35s} {matches:>14d}")
    print(f"{'Diferencias':<35s} {diffs:>14d}")
    print(f"{'Speedup':<35s} {'':>14s} {total_time_a/max(total_time_b,0.001):>13.1f}x")
    print(f"{'='*90}")


if __name__ == "__main__":
    main()
