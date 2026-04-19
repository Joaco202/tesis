from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


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


class SupabaseConfig(BaseModel):
    enabled: bool = False
    url: str = ""
    service_key: str = ""
    timeout_seconds: float = Field(default=10.0, gt=0.0)
    vehicles_table: str = "vehiculos"
    accesses_table: str = "accesos"

    @model_validator(mode="after")
    def validate_required_fields(self) -> "SupabaseConfig":
        if self.enabled and (not self.url or not self.service_key):
            raise ValueError(
                "Supabase habilitado requiere url y service_key (YAML o variables de entorno)."
            )
        return self


class AppConfig(BaseModel):
    detection: DetectionConfig = DetectionConfig()
    ocr: OCRConfig = OCRConfig()
    runtime: RuntimeConfig = RuntimeConfig()
    supabase: SupabaseConfig = SupabaseConfig()


DEFAULT_CONFIG = AppConfig()


def load_config(path: str | Path | None) -> AppConfig:
    env_supabase = {
        "enabled": os.getenv("SUPABASE_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
        "url": os.getenv("SUPABASE_URL", ""),
        "service_key": os.getenv("SUPABASE_SERVICE_KEY", ""),
        "timeout_seconds": float(os.getenv("SUPABASE_TIMEOUT_SECONDS", "10")),
        "vehicles_table": os.getenv("SUPABASE_VEHICLES_TABLE", "vehiculos"),
        "accesses_table": os.getenv("SUPABASE_ACCESSES_TABLE", "accesos"),
    }
    base_raw: dict[str, Any] = {"supabase": env_supabase}

    if path is None:
        return AppConfig.model_validate(base_raw)

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"No existe el archivo de configuracion: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    merged = {**base_raw, **raw}
    merged_supabase = {**env_supabase, **(raw.get("supabase", {}) if isinstance(raw, dict) else {})}
    merged["supabase"] = merged_supabase

    return AppConfig.model_validate(merged)
