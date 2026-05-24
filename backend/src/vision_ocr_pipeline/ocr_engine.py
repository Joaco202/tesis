from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import OCRConfig


@dataclass(slots=True)
class OCRText:
    text: str
    confidence: float


def _detect_gpu_available() -> bool:
    """Detecta si hay GPU disponible via paddle o torch."""
    try:
        import paddle
        return paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
    except Exception:
        pass
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        pass
    return False


class PaddleOCREngine:
    def __init__(self, cfg: OCRConfig, use_gpu: bool | None = None) -> None:
        self.cfg = cfg
        self._ocr = None

        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ImportError(
                "paddleocr no esta instalado. Ejecuta: pip install -r requirements.txt"
            ) from exc

        # Determinar si usar GPU: parámetro explícito > auto-detección
        gpu_available = _detect_gpu_available() if use_gpu is None else use_gpu
        device_str = "gpu" if gpu_available else "cpu"

        if gpu_available:
            print(f"[INFO] PaddleOCR inicializando en GPU.")
        else:
            print("[INFO] PaddleOCR inicializando en CPU (GPU no disponible o no solicitada).")

        try:
            # PaddleOCR 3.x — usa parámetro `device`
            self._ocr = PaddleOCR(
                use_angle_cls=cfg.use_angle_cls,
                lang=cfg.lang,
                device=device_str,
            )
        except TypeError:
            try:
                # PaddleOCR 2.x — usa parámetro `use_gpu`
                self._ocr = PaddleOCR(
                    use_angle_cls=cfg.use_angle_cls,
                    lang=cfg.lang,
                    use_gpu=gpu_available,
                )
            except Exception as exc:
                print(
                    "[WARN] PaddleOCR no se pudo inicializar en GPU, reintentando en CPU. "
                    f"Detalle: {exc}"
                )
                try:
                    self._ocr = PaddleOCR(use_angle_cls=cfg.use_angle_cls, lang=cfg.lang, use_gpu=False)
                except Exception as exc2:
                    print(
                        "[WARN] PaddleOCR no se pudo inicializar en este entorno. "
                        "Se desactiva OCR y se continua con deteccion. "
                        f"Detalle: {exc2}"
                    )
                    self._ocr = None
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
                try:
                    if isinstance(item[1], (list, tuple)) and len(item[1]) >= 2:
                        text, conf = item[1][0], item[1][1]
                    else:
                        text, conf = item[1], 1.0
                    texts.append(OCRText(text=str(text), confidence=float(conf)))
                except Exception:
                    continue

        return texts
