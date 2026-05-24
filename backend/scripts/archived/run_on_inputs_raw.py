from pathlib import Path
import json
import cv2
import sys
sys.path.insert(0, '.')
from src.vision_ocr_pipeline.config import AppConfig
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline

INPUT_DIR = Path('inputs/raw')
OUTPUT_DIR = Path('outputs')
ANNOT_DIR = OUTPUT_DIR / 'annotated'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ANNOT_DIR.mkdir(parents=True, exist_ok=True)

config = AppConfig()
pipeline = VisionOCRPipeline(config)

results = []
if not INPUT_DIR.exists():
    print(f"INPUT_MISSING:{INPUT_DIR}")
    raise SystemExit(1)

for img_path in sorted(INPUT_DIR.glob('*')):
    if img_path.suffix.lower() not in ['.jpg','.jpeg','.png','.bmp','.tif','.tiff']:
        continue
    try:
        image, detection_results = pipeline.process_image(str(img_path))
    except Exception as e:
        results.append({'file': str(img_path), 'error': str(e)})
        continue

    if not detection_results:
        # still save a record with no detections
        results.append({'file': str(img_path), 'plate_text': None, 'confidence': None, 'ocr_confidence': None, 'bbox': None})
        # save annotated (original) image
        ann_file = ANNOT_DIR / (img_path.stem + '_annot.jpg')
        cv2.imwrite(str(ann_file), image)
        continue

    # take first detection as primary for summary
    primary = detection_results[0]
    out = {
        'file': str(img_path),
        'plate_text': primary.plate_text,
        'confidence': primary.plate_confidence,
        'ocr_confidence': max((o.confidence for o in primary.ocr), default=None) if primary.ocr else None,
        'bbox': (primary.detection.x1, primary.detection.y1, primary.detection.x2, primary.detection.y2),
    }
    results.append(out)

    # annotate and save
    annotated = image.copy()
    d = primary.detection
    cv2.rectangle(annotated, (d.x1, d.y1), (d.x2, d.y2), (0, 180, 0), 2)
    label = f"{d.cls_name} {d.confidence:.2f}"
    if primary.plate_text:
        label = f"{label} - {primary.plate_text}"
    cv2.putText(annotated, label, (d.x1, max(d.y1 - 8, 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
    ann_file = ANNOT_DIR / (img_path.stem + '_annot.jpg')
    cv2.imwrite(str(ann_file), annotated)

with open(OUTPUT_DIR / 'integration_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print('DONE', len(results), 'images processed')
