"""
Evaluar el efecto del entrenamiento comparando:
- Modelo base: yolov8n.pt (sin entrenar en placas)
- Modelo entrenado: runs/detect/train-3/weights/best.pt (2 epochs en CCPD)
"""

from pathlib import Path
import sys
import json
import cv2
from ultralytics import YOLO

sys.path.insert(0, str(Path(".").resolve()))

from src.vision_ocr_pipeline.detector import YoloDetector
from src.vision_ocr_pipeline.config import DetectionConfig

# Paths
INPUT_DIR = Path("inputs/raw")
OUTPUT_DIR = Path("outputs/model_comparison")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_MODEL = "yolov8n.pt"
TRAINED_MODEL = "runs/detect/train-3/weights/best.pt"

images = sorted(INPUT_DIR.glob("*.jpg")) + sorted(INPUT_DIR.glob("*.jpeg")) + sorted(INPUT_DIR.glob("*.png"))

results = {
    "base_model": BASE_MODEL,
    "trained_model": TRAINED_MODEL,
    "comparison": []
}

print(f"Evaluating {len(images)} images...")
print(f"Base model: {BASE_MODEL}")
print(f"Trained model: {TRAINED_MODEL}")
print()

for img_path in images:
    image = cv2.imread(str(img_path))
    if image is None:
        continue

    # Inference with base model
    yolo_base = YOLO(BASE_MODEL)
    res_base = yolo_base.predict(source=image, conf=0.25, iou=0.45, device="cpu", verbose=False)
    dets_base = []
    for result in res_base:
        boxes = getattr(result, "boxes", None)
        if boxes:
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0].item())
                dets_base.append({"bbox": xyxy, "conf": conf})

    # Inference with trained model
    yolo_trained = YOLO(TRAINED_MODEL)
    res_trained = yolo_trained.predict(source=image, conf=0.25, iou=0.45, device="cpu", verbose=False)
    dets_trained = []
    for result in res_trained:
        boxes = getattr(result, "boxes", None)
        if boxes:
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0].item())
                dets_trained.append({"bbox": xyxy, "conf": conf})

    comparison_entry = {
        "image": img_path.name,
        "base_detections": len(dets_base),
        "trained_detections": len(dets_trained),
        "base_dets": dets_base,
        "trained_dets": dets_trained,
        "improvement": "+" if len(dets_trained) > len(dets_base) else ("=" if len(dets_trained) == len(dets_base) else "-"),
    }
    results["comparison"].append(comparison_entry)
    
    # Print summary
    print(f"{img_path.name:20s} | Base: {len(dets_base)} dets | Trained: {len(dets_trained)} dets | {comparison_entry['improvement']}")

# Save results
out_file = OUTPUT_DIR / "model_comparison.json"
out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

# Summary statistics
total_base = sum(c["base_detections"] for c in results["comparison"])
total_trained = sum(c["trained_detections"] for c in results["comparison"])
improvements = sum(1 for c in results["comparison"] if c["improvement"] == "+")
no_change = sum(1 for c in results["comparison"] if c["improvement"] == "=")
regressions = sum(1 for c in results["comparison"] if c["improvement"] == "-")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Total detections (base): {total_base}")
print(f"Total detections (trained): {total_trained}")
print(f"Images with improvement: {improvements}")
print(f"Images with no change: {no_change}")
print(f"Images with regression: {regressions}")
print()

if total_trained > total_base:
    pct_gain = ((total_trained - total_base) / max(1, total_base)) * 100
    print(f"✓ Training IMPROVED detection: +{pct_gain:.1f}%")
elif total_trained == total_base:
    print(f"~ No change in detection count (but quality may differ)")
else:
    pct_loss = ((total_base - total_trained) / max(1, total_base)) * 100
    print(f"✗ Training REDUCED detection: -{pct_loss:.1f}%")

print()
print(f"Results saved to: {out_file}")
