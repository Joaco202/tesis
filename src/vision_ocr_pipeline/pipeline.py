from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import AppConfig
from .detector import Detection, YoloDetector
from .ocr_engine import OCRText, PaddleOCREngine
from .postprocess import best_plate_from_ocr, preprocess_plate_crop


@dataclass(slots=True)
class DetectionResult:
    detection: Detection
    ocr: list[OCRText]
    plate_text: str | None
    plate_confidence: float | None


class VisionOCRPipeline:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.detector = YoloDetector(cfg.detection, device=cfg.runtime.device)
        self.ocr = PaddleOCREngine(cfg.ocr)

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

        return image, output

    def save_outputs(
        self,
        image: np.ndarray,
        results: list[DetectionResult],
        output_dir: str | Path,
        stem: str,
        camera_id: str,
        event_type: str,
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
        }
        for item in results:
            payload["events"].append(
                {
                    "detection": asdict(item.detection),
                    "ocr": [asdict(x) for x in item.ocr],
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
