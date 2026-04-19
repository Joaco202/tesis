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
from .postprocess import best_plate_from_ocr, preprocess_plate_crop
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
        self.ocr = PaddleOCREngine(cfg.ocr)
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

        detections = self.detector.detect(image)
        output: list[DetectionResult] = []

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

        # Fallback: si no se obtuvo ninguna patente util, ejecutar OCR sobre imagen completa.
        if not any(item.plate_text for item in output):
            full_ocr_input = preprocess_plate_crop(image)
            full_ocr_text = self.ocr.read_text(full_ocr_input)
            full_plate_text, full_plate_conf = best_plate_from_ocr(full_ocr_text)
            if full_ocr_text:
                h, w = image.shape[:2]
                output.append(
                    DetectionResult(
                        detection=Detection(
                            cls_id=-1,
                            cls_name="full_image_ocr",
                            confidence=1.0,
                            x1=0,
                            y1=0,
                            x2=max(w - 1, 0),
                            y2=max(h - 1, 0),
                        ),
                        ocr=full_ocr_text,
                        plate_text=full_plate_text,
                        plate_confidence=full_plate_conf,
                    )
                )

        return image, output

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
