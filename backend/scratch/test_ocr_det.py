import sys
import time
from pathlib import Path
import cv2

# Add base folder to PATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline

def main():
    cfg = load_config("config.yaml")
    pipeline = VisionOCRPipeline(cfg)
    
    # Let's pick a test image containing a plate
    img_path = Path("inputs/raw/WhatsApp Image 2026-05-17 at 13.02.57.jpeg")
    image = cv2.imread(str(img_path))
    if image is None:
        print("Test image not found!")
        return

    print("Running YOLO Detector...")
    detections = pipeline.detector.detect(image)
    if not detections:
        print("No plates detected by YOLO!")
        return

    det = detections[0]
    crop = image[max(det.y1, 0) : max(det.y2, 0), max(det.x1, 0) : max(det.x2, 0)]
    print(f"Crop shape: {crop.shape}")

    # Method 1: with det=True (default)
    print("\n--- Method 1: det=True (default) ---")
    start = time.perf_counter()
    res1 = pipeline.ocr.read_text(crop)
    elapsed1 = time.perf_counter() - start
    print(f"Time: {elapsed1:.3f}s")
    print("Results:", [x.text for x in res1])

    # Method 2: with det=False
    print("\n--- Method 2: det=False ---")
    # Let's call the underlying paddleocr directly or define a test call
    # PaddleOCR supports calling ocr(crop, det=False)
    start = time.perf_counter()
    raw_res = pipeline.ocr._ocr.ocr(crop, det=False)
    elapsed2 = time.perf_counter() - start
    print(f"Time: {elapsed2:.3f}s")
    print("Raw results:", raw_res)

if __name__ == "__main__":
    main()
