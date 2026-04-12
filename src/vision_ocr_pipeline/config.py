from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class OCRConfig(BaseModel):
    lang: str = "es"
    use_angle_cls: bool = True


class DetectionConfig(BaseModel):
    model: str = "yolov8n.pt"
    confidence: float = Field(default=0.25, ge=0.0, le=1.0)
    iou: float = Field(default=0.45, ge=0.0, le=1.0)
    classes: list[int] | None = None


class RuntimeConfig(BaseModel):
    device: str = "cpu"
    save_annotated: bool = True
    default_camera_id: str = "cam-acceso-1"
    default_event_type: str = "entrada"


class AppConfig(BaseModel):
    detection: DetectionConfig = DetectionConfig()
    ocr: OCRConfig = OCRConfig()
    runtime: RuntimeConfig = RuntimeConfig()


DEFAULT_CONFIG = AppConfig()


def load_config(path: str | Path | None) -> AppConfig:
    if path is None:
        return DEFAULT_CONFIG

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"No existe el archivo de configuracion: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    return AppConfig.model_validate(raw)
