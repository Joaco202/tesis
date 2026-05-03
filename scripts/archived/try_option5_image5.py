from __future__ import annotations

from pathlib import Path
import sys
import json

import cv2
import numpy as np
from paddleocr import PaddleOCR

sys.path.insert(0, str(Path('.').resolve()))

from src.vision_ocr_pipeline.postprocess import best_plate_from_ocr, normalize_plate_text
from src.vision_ocr_pipeline.ocr_engine import OCRText

IMAGE_PATH = Path("inputs/raw/5.jpg")
OUT_DIR = Path("outputs/option5")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def merge_horizontally_close_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged: list[tuple[int, int, int, int]] = []

    for b in boxes:
        x1, y1, x2, y2 = b
        if not merged:
            merged.append(b)
            continue

        mx1, my1, mx2, my2 = merged[-1]
        h_overlap = min(y2, my2) - max(y1, my1)
        min_h = max(1, min(y2 - y1, my2 - my1))
        gap = x1 - mx2

        # Merge if boxes are on the same line and close enough.
        if h_overlap / min_h > 0.5 and gap < max(20, int(0.08 * (mx2 - mx1))):
            merged[-1] = (min(mx1, x1), min(my1, y1), max(mx2, x2), max(my2, y2))
        else:
            merged.append(b)

    return merged


def expand_box(box: tuple[int, int, int, int], w: int, h: int, padx: float = 0.12, pady: float = 0.35):
    x1, y1, x2, y2 = box
    bw = x2 - x1
    bh = y2 - y1
    ex = int(bw * padx)
    ey = int(bh * pady)
    nx1 = max(0, x1 - ex)
    ny1 = max(0, y1 - ey)
    nx2 = min(w - 1, x2 + ex)
    ny2 = min(h - 1, y2 + ey)
    return nx1, ny1, nx2, ny2


def main() -> None:
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"No existe {IMAGE_PATH}")

    image = cv2.imread(str(IMAGE_PATH))
    if image is None:
        raise ValueError("No se pudo leer la imagen")

    h, w = image.shape[:2]

    ocr = PaddleOCR(use_angle_cls=True, lang="es", use_gpu=False)
    raw = ocr.ocr(image, cls=True)

    word_boxes: list[tuple[int, int, int, int]] = []
    word_items: list[dict] = []
    if raw:
        for line in raw:
            if not line:
                continue
            for item in line:
                if len(item) < 2:
                    continue
                poly = item[0]
                txt, conf = item[1]
                xs = [int(p[0]) for p in poly]
                ys = [int(p[1]) for p in poly]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                bw = max(1, x2 - x1)
                bh = max(1, y2 - y1)
                ar = bw / bh
                area = bw * bh

                # Keep plausible plate-like text regions.
                if conf < 0.35:
                    continue
                if ar < 1.5 or ar > 8.0:
                    continue
                if area < 700:
                    continue

                word_boxes.append((x1, y1, x2, y2))
                word_items.append(
                    {
                        "text": txt,
                        "normalized": normalize_plate_text(str(txt)),
                        "confidence": float(conf),
                        "bbox": [x1, y1, x2, y2],
                        "ar": ar,
                        "area": area,
                    }
                )

    merged_boxes = merge_horizontally_close_boxes(word_boxes)

    candidates: list[dict] = []
    for i, box in enumerate(merged_boxes):
        ex1, ey1, ex2, ey2 = expand_box(box, w, h)
        crop = image[ey1:ey2, ex1:ex2]
        if crop.size == 0:
            continue

        crop_raw = ocr.ocr(crop, cls=True)
        ocr_items: list[OCRText] = []
        if crop_raw:
            for line in crop_raw:
                if not line:
                    continue
                for item in line:
                    if len(item) < 2:
                        continue
                    text, conf = item[1]
                    ocr_items.append(OCRText(text=str(text), confidence=float(conf)))

        plate_text, plate_conf = best_plate_from_ocr(ocr_items)
        candidates.append(
            {
                "candidate_id": i,
                "candidate_bbox": [ex1, ey1, ex2, ey2],
                "plate_text": plate_text,
                "plate_conf": plate_conf,
                "ocr_tokens": [
                    {
                        "text": t.text,
                        "norm": normalize_plate_text(t.text),
                        "conf": t.confidence,
                    }
                    for t in ocr_items
                ],
            }
        )

    best = None
    valids = [c for c in candidates if c["plate_text"]]
    if valids:
        best = sorted(valids, key=lambda x: x["plate_conf"] or 0.0, reverse=True)[0]

    vis = image.copy()
    for b in merged_boxes:
        cv2.rectangle(vis, (b[0], b[1]), (b[2], b[3]), (0, 170, 255), 2)
    if best:
        x1, y1, x2, y2 = best["candidate_bbox"]
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
        label = f"{best['plate_text']} ({(best['plate_conf'] or 0):.2f})"
        cv2.putText(vis, label, (x1, max(15, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

    out_json = OUT_DIR / "image5_option5_debug.json"
    out_img = OUT_DIR / "image5_option5_debug.jpg"

    payload = {
        "image": str(IMAGE_PATH),
        "merged_boxes": merged_boxes,
        "word_items": word_items,
        "candidates": candidates,
        "best": best,
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    cv2.imwrite(str(out_img), vis)

    print("Merged boxes:", len(merged_boxes))
    print("Candidates:", len(candidates))
    if best:
        print("BEST:", best["plate_text"], best["plate_conf"])
    else:
        print("BEST: None")
    print("Saved:", out_json)
    print("Saved:", out_img)


if __name__ == "__main__":
    main()
