from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import OCRConfig


@dataclass(slots=True)
class OCRText:
    text: str
    confidence: float


class PaddleOCREngine:
    def __init__(self, cfg: OCRConfig) -> None:
        self.cfg = cfg
        self._ocr = None
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ImportError(
                "paddleocr no esta instalado. Ejecuta: pip install -r requirements.txt"
            ) from exc

        try:
            # PaddleOCR 3.x
            self._ocr = PaddleOCR(use_angle_cls=cfg.use_angle_cls, lang=cfg.lang, device="cpu")
        except TypeError:
            # PaddleOCR 2.x
            self._ocr = PaddleOCR(use_angle_cls=cfg.use_angle_cls, lang=cfg.lang, use_gpu=False)
        except Exception as exc:
            print(
                "[WARN] PaddleOCR no se pudo inicializar en este entorno. "
                "Se desactiva OCR y se continua con deteccion. "
                f"Detalle: {exc}"
            )
            self._ocr = None

    def read_text(self, image: np.ndarray) -> list[OCRText]:
        if self._ocr is None:
            return []

        try:
            result = self._ocr.ocr(image)
        except TypeError:
            result = self._ocr.ocr(image, cls=self.cfg.use_angle_cls)
        except Exception as exc:
            print(f"[WARN] OCR fallo en inferencia y se omite este recorte. Detalle: {exc}")
            return []
        texts: list[OCRText] = []
        if not result:
            return texts

        for line in result:
            if not line:
                continue
            for item in line:
                if len(item) < 2:
                    continue
                text, conf = item[1]
                texts.append(OCRText(text=str(text), confidence=float(conf)))

        return texts
