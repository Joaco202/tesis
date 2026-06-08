import sys
import time
from pathlib import Path
import cv2

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline

def main():
    cfg = load_config("config.yaml")
    pipeline = VisionOCRPipeline(cfg)
    
    img_path = Path("inputs/raw/WhatsApp Image 2026-05-17 at 13.02.57.jpeg")
    image = cv2.imread(str(img_path))
    if image is None:
        print("Test image not found!")
        return

    det = pipeline.detector.detect(image)[0]
    crop = image[max(det.y1, 0) : max(det.y2, 0), max(det.x1, 0) : max(det.x2, 0)]
    print(f"Crop shape: {crop.shape}")

    # Method 1: Default call
    print("\n--- Default ocr() ---")
    start = time.perf_counter()
    res = pipeline.ocr._ocr.ocr(crop)
    print(f"Time: {time.perf_counter() - start:.3f}s")
    print("Res:", res)

    # Method 2: Disabling unwarping and orientation classify
    print("\n--- Disabling doc pipeline features ---")
    start = time.perf_counter()
    res2 = list(pipeline.ocr._ocr.predict(
        crop,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    ))
    print(f"Time: {time.perf_counter() - start:.3f}s")
    print("Res2:", res2)

if __name__ == "__main__":
    main()
