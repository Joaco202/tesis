"""
Fine-tuning del modelo YOLO para detección de patentes chilenas.

Estrategia: Transfer learning desde best.pt (entrenado en CCPD)
sobre el dataset de Roboflow "Patentes Chile" (819 imágenes, 1 clase).

Uso:
    cd backend
    .venv/Scripts/python scripts/finetune_chilean_plates.py
"""
from __future__ import annotations

from pathlib import Path
import sys

# ── Rutas ────────────────────────────────────────────────────────────────────
BACKEND_DIR  = Path(__file__).resolve().parents[1]
DATA_YAML    = BACKEND_DIR / "data" / "patentes_chile" / "data.yaml"
BASE_WEIGHTS = BACKEND_DIR / "runs" / "detect" / "runs" / "detect" / "train-gpu-rtx5070" / "weights" / "best.pt"
OUTPUT_NAME  = "finetune-chilean"

# ── Hiperparámetros de fine-tuning ───────────────────────────────────────────
EPOCHS   = 60       # Fine-tuning corto — el modelo ya sabe detectar patentes
IMGSZ    = 640
BATCH    = 16       # RTX 5070 tiene VRAM suficiente para batch 16 con YOLOv8n
LR0      = 0.001    # LR más bajo que el entrenamiento inicial para preservar pesos
LRF      = 0.01     # Factor de decaimiento final
WARMUP   = 3
DEVICE   = "cuda"

# ── Validaciones ─────────────────────────────────────────────────────────────
if not DATA_YAML.exists():
    print(f"✗ No se encontró data.yaml en: {DATA_YAML}")
    print("  Ejecuta primero: python scripts/download_roboflow_dataset.py")
    sys.exit(1)

if not BASE_WEIGHTS.exists():
    print(f"⚠ Pesos base no encontrados en: {BASE_WEIGHTS}")
    print("  Usando yolov8n.pt pre-entrenado de Ultralytics como fallback...")
    BASE_WEIGHTS = BACKEND_DIR / "yolov8n.pt"
    if not BASE_WEIGHTS.exists():
        BASE_WEIGHTS = "yolov8n.pt"  # Descarga automática de Ultralytics

print("=" * 65)
print("FINE-TUNING YOLO — PATENTES CHILENAS")
print("=" * 65)
print(f"  Dataset    : {DATA_YAML}")
print(f"  Pesos base : {BASE_WEIGHTS}")
print(f"  Epochs     : {EPOCHS}")
print(f"  Batch      : {BATCH}")
print(f"  Imgsz      : {IMGSZ}")
print(f"  Device     : {DEVICE}")
print(f"  Output     : runs/detect/{OUTPUT_NAME}/")
print("=" * 65)

if __name__ == "__main__":
    # Necesario en Windows: PyTorch lanza DataLoader workers con spawn,
    # lo que re-importa el módulo principal. Sin este guard provoca RuntimeError.
    import multiprocessing
    multiprocessing.freeze_support()

    from ultralytics import YOLO

    model = YOLO(str(BASE_WEIGHTS))

    results = model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        lr0=LR0,
        lrf=LRF,
        warmup_epochs=WARMUP,
        device=DEVICE,
        project=str(BACKEND_DIR / "runs" / "detect"),
        name=OUTPUT_NAME,
        exist_ok=True,
        workers=4,       # Número de workers del DataLoader
        # Augmentaciones — útiles para dataset pequeño
        flipud=0.0,      # No invertir verticalmente (patentes siempre hacia arriba)
        fliplr=0.5,      # Espejo horizontal sí es válido
        mosaic=1.0,
        mixup=0.1,
        degrees=5.0,     # Rotación leve (ángulos de cámara)
        translate=0.1,
        scale=0.5,
        shear=2.0,
        perspective=0.0005,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        # Logging
        plots=True,
        save=True,
        save_period=10,
        verbose=True,
    )

    print("\n" + "=" * 65)
    print("ENTRENAMIENTO COMPLETADO")
    print("=" * 65)
    best = BACKEND_DIR / "runs" / "detect" / OUTPUT_NAME / "weights" / "best.pt"
    if best.exists():
        print(f"✓ Pesos guardados en: {best}")
        print(f"\n  Para usar en el pipeline, actualiza config.yaml:")
        print(f"  detection:")
        print(f"    model: {best.relative_to(BACKEND_DIR)}")
    else:
        print("⚠ No se encontró best.pt — revisa los logs de entrenamiento.")

    # Mostrar métricas finales
    try:
        metrics = results.results_dict
        print(f"\n  mAP50   : {metrics.get('metrics/mAP50(B)', '?'):.4f}")
        print(f"  mAP50-95: {metrics.get('metrics/mAP50-95(B)', '?'):.4f}")
        print(f"  Precision: {metrics.get('metrics/precision(B)', '?'):.4f}")
        print(f"  Recall   : {metrics.get('metrics/recall(B)', '?'):.4f}")
    except Exception:
        pass

