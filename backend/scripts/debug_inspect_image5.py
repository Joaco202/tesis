from pathlib import Path
import sys
from pathlib import Path as P
sys.path.insert(0, str(P('.').resolve()))
from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline

cfg = load_config(None)
pipeline = VisionOCRPipeline(cfg)
img = Path('inputs/raw/5.jpg')
image, results = pipeline.process_image(str(img))
print('Results count:', len(results))
for i, r in enumerate(results):
    print(f'--- Result {i} ---')
    print('Detection:', r.detection)
    print('Plate text:', r.plate_text)
    print('Plate conf:', r.plate_confidence)
    print('OCR items:')
    for o in r.ocr:
        print('  ->', repr(o.text), o.confidence)

# Also show normalized tokens and pattern check
from src.vision_ocr_pipeline.postprocess import normalize_plate_text, is_likely_plate

for r in results:
    tokens = [normalize_plate_text(o.text) for o in r.ocr]
    print('Normalized tokens:', tokens)
    for t in tokens:
        print(t, 'is_likely_plate=', is_likely_plate(t))

# Extra: try detector with lower confidence thresholds
from src.vision_ocr_pipeline.config import DetectionConfig
from src.vision_ocr_pipeline.detector import YoloDetector
import cv2
img_arr = cv2.imread(str(img))
for conf in (0.25, 0.1, 0.05):
    cfgd = DetectionConfig(model=cfg.detection.model, confidence=conf, iou=cfg.detection.iou, classes=cfg.detection.classes)
    det = YoloDetector(cfgd, device=cfg.runtime.device)
    det_res = det.detect(img_arr)
    print(f'Confidence {conf}: {len(det_res)} detections')
    for d in det_res:
        print('  ->', d)
