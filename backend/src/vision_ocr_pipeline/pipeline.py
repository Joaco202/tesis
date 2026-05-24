from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError

import cv2
import numpy as np

from .config import AppConfig
from .db import SupabaseClient
from .detector import Detection, YoloDetector
from .ocr_engine import OCRText, PaddleOCREngine
from .postprocess import PLATE_PATTERNS, best_plate_from_ocr, is_likely_plate, normalize_plate_text, preprocess_plate_crop
from .repository import AccessEventResult, SupabaseRepository


@dataclass(slots=True)
class DetectionResult:
    detection: Detection
    ocr: list[OCRText]
    plate_text: str | None
    plate_confidence: float | None


@dataclass(slots=True)
class PersistenceSummary:
    enabled: bool
    saved_events: list[AccessEventResult]
    errors: list[str]


class VisionOCRPipeline:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.detector = YoloDetector(cfg.detection, device=cfg.runtime.device)
        use_gpu = cfg.runtime.device.startswith("cuda") or cfg.runtime.device == "gpu"
        self.ocr = PaddleOCREngine(cfg.ocr, use_gpu=use_gpu)
        self.repository: SupabaseRepository | None = None

        if cfg.supabase.enabled:
            client = SupabaseClient(
                base_url=cfg.supabase.url,
                service_key=cfg.supabase.service_key,
                timeout_seconds=cfg.supabase.timeout_seconds,
            )
            self.repository = SupabaseRepository(
                client=client,
                vehicles_table=cfg.supabase.vehicles_table,
                accesses_table=cfg.supabase.accesses_table,
            )

    def process_image(self, image_path: str | Path) -> tuple[np.ndarray, list[DetectionResult]]:
        image_path = Path(image_path)
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"No se pudo leer la imagen: {image_path}")

        detections = sorted(self.detector.detect(image), key=lambda det: det.confidence, reverse=True)
        output: list[DetectionResult] = []

        if detections:
            # Procesar todas las detecciones (ordenadas por confianza), exponer OCR por cada una.
            for det in detections:
                crop = image[max(det.y1, 0) : max(det.y2, 0), max(det.x1, 0) : max(det.x2, 0)]
                ocr_input = preprocess_plate_crop(crop) if crop.size else crop
                ocr_text = self.ocr.read_text(ocr_input) if crop.size else []
                plate_text, plate_conf = best_plate_from_ocr(ocr_text)
                output.append(
                    DetectionResult(
                        detection=det,
                        ocr=ocr_text,
                        plate_text=plate_text,
                        plate_confidence=plate_conf,
                    )
                )

        # Fallback: ejecutar búsqueda por regiones OCR cuando ninguna detección tiene texto
        # O cuando la detección primaria no devolvió texto — intentamos el fallback y lo
        # priorizamos si encuentra una placa.
        need_fallback = not any(item.plate_text for item in output) or (output and output[0].plate_text is None)
        if need_fallback:
            fallback_result = self._detect_plate_via_ocr_regions(image)
            if fallback_result:
                # Priorizar el resultado del fallback insertándolo al frente.
                output.insert(0, fallback_result)

        return image, output

    def _detect_plate_via_ocr_regions(self, image: np.ndarray) -> DetectionResult | None:
        """
        Fallback: Detectar patente analizando regiones de texto en la imagen.
        Usa OCR para encontrar cajas de texto, filtra por geometría (aspect ratio, área),
        luego busca patentes válidas dentro de cada región candidata.
        Opción 5: Para casos donde YOLO no detecta pero hay texto visible.
        """
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            return None

        h, w = image.shape[:2]
        use_gpu = self.cfg.runtime.device.startswith("cuda") or self.cfg.runtime.device == "gpu"
        device_str = "gpu" if use_gpu else "cpu"
        try:
            ocr = PaddleOCR(use_angle_cls=self.cfg.ocr.use_angle_cls, lang=self.cfg.ocr.lang, device=device_str)
        except TypeError:
            ocr = PaddleOCR(use_angle_cls=self.cfg.ocr.use_angle_cls, lang=self.cfg.ocr.lang, use_gpu=use_gpu)

        # Detectar cajas de texto con OCR
        try:
            raw = ocr.ocr(image, cls=True)
        except Exception:
            return None

        word_boxes: list[tuple[int, int, int, int]] = []
        full_items_with_boxes: list[tuple[OCRText, tuple[int, int, int, int]]] = []
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
                    full_items_with_boxes.append(
                        (OCRText(text=str(txt), confidence=float(conf)), (x1, y1, x2, y2))
                    )
                    bw = max(1, x2 - x1)
                    bh = max(1, y2 - y1)
                    ar = bw / bh
                    area = bw * bh

                    # Filtrar regiones plausibles para patente (umbrales relajados para mayor recall)
                    if conf < 0.20:
                        continue
                    if ar < 1.2 or ar > 10.0:
                        continue
                    if area < 300:
                        continue

                    word_boxes.append((x1, y1, x2, y2))

        if not word_boxes:
            return None

        def score_candidate(text: str | None, confidence: float | None) -> float:
            if not text:
                return -1.0
            normalized = normalize_plate_text(text)
            score = float(confidence or 0.0)
            if any(pattern.match(normalized) for pattern in PLATE_PATTERNS):
                score += 2.0
            elif is_likely_plate(normalized):
                score += 1.0
            if len(normalized) == 6:
                score += 0.25
            return score

        # Agrupar cajas horizontalmente cercanas
        merged_boxes = self._merge_horizontally_close_boxes(word_boxes)

        def bbox_for_plate(items_with_boxes: list[tuple[OCRText, tuple[int, int, int, int]]], plate_text: str | None) -> tuple[int, int, int, int] | None:
            if not plate_text or not items_with_boxes:
                return None

            normalized_plate = normalize_plate_text(plate_text)
            if not normalized_plate:
                return None

            for item, box in items_with_boxes:
                if normalize_plate_text(item.text) == normalized_plate:
                    return box

            for start in range(len(items_with_boxes)):
                token_text = ""
                window_boxes: list[tuple[int, int, int, int]] = []
                for end in range(start, min(start + 3, len(items_with_boxes))):
                    item, box = items_with_boxes[end]
                    token_text += normalize_plate_text(item.text)
                    window_boxes.append(box)
                    if normalize_plate_text(token_text) == normalized_plate:
                        x1 = min(b[0] for b in window_boxes)
                        y1 = min(b[1] for b in window_boxes)
                        x2 = max(b[2] for b in window_boxes)
                        y2 = max(b[3] for b in window_boxes)
                        return x1, y1, x2, y2

            return None

        # Para cada región candidata, expandir y buscar patente
        best_plate_text: str | None = None
        best_plate_conf: float | None = None
        best_detection: Detection | None = None
        best_score = -1.0

        for box in merged_boxes:
            ex1, ey1, ex2, ey2 = self._expand_box(box, w, h)
            crop = image[ey1:ey2, ex1:ex2]
            if crop.size == 0:
                continue

            try:
                crop_raw = ocr.ocr(crop, cls=True)
            except Exception:
                continue

            ocr_items: list[OCRText] = []
            ocr_items_with_boxes: list[tuple[OCRText, tuple[int, int, int, int]]] = []
            if crop_raw:
                for line in crop_raw:
                    if not line:
                        continue
                    for item in line:
                        if len(item) < 2:
                            continue
                        poly = item[0]
                        text, conf = item[1]
                        xs = [int(p[0]) for p in poly]
                        ys = [int(p[1]) for p in poly]
                        x1b, y1b, x2b, y2b = min(xs), min(ys), max(xs), max(ys)
                        ocr_text = OCRText(text=str(text), confidence=float(conf))
                        ocr_items.append(ocr_text)
                        ocr_items_with_boxes.append((ocr_text, (ex1 + x1b, ey1 + y1b, ex1 + x2b, ey1 + y2b)))

            plate_text, plate_conf = best_plate_from_ocr(ocr_items)
            region_score = score_candidate(plate_text, plate_conf)
            if region_score > best_score:
                best_plate_text = plate_text
                best_plate_conf = plate_conf
                best_score = region_score
                region_bbox = bbox_for_plate(ocr_items_with_boxes, plate_text)
                if region_bbox is not None:
                    ex1, ey1, ex2, ey2 = region_bbox
                best_detection = Detection(
                    cls_id=-1,
                    cls_name="ocr_region_fallback",
                    confidence=plate_conf or 0.0,
                    x1=ex1,
                    y1=ey1,
                    x2=ex2,
                    y2=ey2,
                )

        # También evaluar OCR en toda la imagen y comparar contra las regiones.
        try:
            full_raw = ocr.ocr(image, cls=True)
        except Exception:
            full_raw = None

        if full_raw:
            full_items: list[OCRText] = []
            full_items_with_boxes = []
            for line in full_raw:
                if not line:
                    continue
                for item in line:
                    if len(item) < 2:
                        continue
                    poly = item[0]
                    text, conf = item[1]
                    xs = [int(p[0]) for p in poly]
                    ys = [int(p[1]) for p in poly]
                    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                    full_items.append(OCRText(text=str(text), confidence=float(conf)))
                    full_items_with_boxes.append((OCRText(text=str(text), confidence=float(conf)), (x1, y1, x2, y2)))

            plate_text, plate_conf = best_plate_from_ocr(full_items)
            full_score = score_candidate(plate_text, plate_conf)
            if full_score > best_score:
                best_plate_text = plate_text
                best_plate_conf = plate_conf
                best_score = full_score
                full_bbox = bbox_for_plate(full_items_with_boxes, plate_text)
                if full_bbox is not None:
                    fx1, fy1, fx2, fy2 = full_bbox
                else:
                    fx1, fy1, fx2, fy2 = 0, 0, w - 1, h - 1
                best_detection = Detection(
                    cls_id=-1,
                    cls_name="ocr_region_fallback_full",
                    confidence=plate_conf or 0.0,
                    x1=fx1,
                    y1=fy1,
                    x2=fx2,
                    y2=fy2,
                )

        if best_detection and best_plate_text:
            return DetectionResult(
                detection=best_detection,
                ocr=[OCRText(text=best_plate_text, confidence=best_plate_conf or 0.0)],
                plate_text=best_plate_text,
                plate_confidence=best_plate_conf,
            )

        return None

    @staticmethod
    def _merge_horizontally_close_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
        """Agrupar cajas de texto que están en la misma línea y cercanas."""
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

            if h_overlap / min_h > 0.5 and gap < max(20, int(0.08 * (mx2 - mx1))):
                merged[-1] = (min(mx1, x1), min(my1, y1), max(mx2, x2), max(my2, y2))
            else:
                merged.append(b)

        return merged

    @staticmethod
    def _expand_box(box: tuple[int, int, int, int], w: int, h: int, padx: float = 0.12, pady: float = 0.35) -> tuple[int, int, int, int]:
        """Expandir caja de texto para capturar contexto alrededor."""
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

    def persist_results(
        self,
        *,
        results: list[DetectionResult],
        event_type: str,
        camera_id: str,
        image_origin: str,
        timestamp_utc: datetime | None = None,
    ) -> PersistenceSummary:
        if self.repository is None:
            return PersistenceSummary(enabled=False, saved_events=[], errors=[])

        persisted: list[AccessEventResult] = []
        errors: list[str] = []
        seen_plates: set[str] = set()

        for item in results:
            if not item.plate_text:
                continue

            plate = item.plate_text.strip().upper()
            if not plate or plate in seen_plates:
                continue
            seen_plates.add(plate)

            try:
                saved = self.repository.guardar_acceso(
                    patente=plate,
                    event_type=event_type,
                    camera_id=camera_id,
                    confianza=item.plate_confidence,
                    image_origin=image_origin,
                    timestamp_utc=timestamp_utc,
                )
                persisted.append(saved)
            except HTTPError as exc:
                err_body = exc.read().decode("utf-8", errors="ignore")
                errors.append(f"{plate}: HTTP {exc.code} - {err_body}")
            except (URLError, TimeoutError, ValueError) as exc:
                errors.append(f"{plate}: {exc}")

        return PersistenceSummary(enabled=True, saved_events=persisted, errors=errors)

    def save_outputs(
        self,
        image: np.ndarray,
        results: list[DetectionResult],
        output_dir: str | Path,
        stem: str,
        camera_id: str,
        event_type: str,
        persistence: PersistenceSummary | None = None,
        save_annotated: bool = True,
    ) -> tuple[Path, Path | None]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / f"{stem}.json"
        payload = {
            "camera_id": camera_id,
            "event_type": event_type,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_detections": len(results),
            "events": [],
            "database": {
                "enabled": persistence.enabled if persistence else False,
                "saved_events": [asdict(x) for x in persistence.saved_events] if persistence else [],
                "errors": persistence.errors if persistence else [],
            },
        }
        for item in results:
            best_ocr_raw = max(item.ocr, key=lambda x: x.confidence) if item.ocr else None
            payload["events"].append(
                {
                    "detection": asdict(item.detection),
                    "ocr": [asdict(x) for x in item.ocr],
                    "ocr_best_raw_text": best_ocr_raw.text if best_ocr_raw else None,
                    "ocr_best_raw_confidence": best_ocr_raw.confidence if best_ocr_raw else None,
                    "plate_text": item.plate_text,
                    "plate_confidence": item.plate_confidence,
                }
            )

        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        annotated_path: Path | None = None
        if save_annotated:
            annotated = image.copy()
            for item in results:
                d = item.detection
                cv2.rectangle(annotated, (d.x1, d.y1), (d.x2, d.y2), (0, 180, 0), 2)
                text = item.plate_text or " | ".join(x.text for x in item.ocr[:2])
                label = f"{d.cls_name} {d.confidence:.2f}"
                if text:
                    label = f"{label} - {text[:60]}"
                cv2.putText(
                    annotated,
                    label,
                    (d.x1, max(d.y1 - 8, 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (30, 30, 30),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    annotated,
                    label,
                    (d.x1, max(d.y1 - 8, 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

            annotated_path = output_dir / f"{stem}_annotated.jpg"
            cv2.imwrite(str(annotated_path), annotated)

        return json_path, annotated_path
