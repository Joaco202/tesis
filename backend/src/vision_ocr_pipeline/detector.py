from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import DetectionConfig


@dataclass(slots=True)
class Detection:
    cls_id: int
    cls_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


class YoloDetector:
    def __init__(self, cfg: DetectionConfig, device: str = "cpu") -> None:
        self.cfg = cfg
        self.device = device
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics no esta instalado. Ejecuta: pip install -r requirements.txt"
            ) from exc

        # Try to use trained plate detector model if available, fallback to default
        model_path = self._find_best_model(cfg.model)
        self._model = YOLO(model_path)
        self._model_path = model_path

    @staticmethod
    def _find_best_model(default_model: str) -> str:
        """Find the best trained plate detector model, fallback to default."""
        from pathlib import Path
        
        runs_dir = Path("runs/detect")
        if runs_dir.exists():
            # Look for latest training run with best.pt recursively
            models = sorted(runs_dir.glob("**/weights/best.pt"), key=lambda x: x.stat().st_mtime, reverse=True)
            if models:
                return str(models[0].absolute())
        
        return default_model

    def detect(self, image: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            source=image,
            conf=self.cfg.confidence,
            iou=self.cfg.iou,
            classes=self.cfg.classes,
            device=self.device,
            verbose=False,
        )

        out: list[Detection] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            names = getattr(result, "names", {})
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                out.append(
                    Detection(
                        cls_id=cls_id,
                        cls_name=str(names.get(cls_id, cls_id)),
                        confidence=conf,
                        x1=int(xyxy[0]),
                        y1=int(xyxy[1]),
                        x2=int(xyxy[2]),
                        y2=int(xyxy[3]),
                    )
                )

        return out
