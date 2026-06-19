import cv2
import sys
import os
from pathlib import Path

# Add project directory to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.src.vision_ocr_pipeline.config import load_config
from backend.src.vision_ocr_pipeline.pipeline import VisionOCRPipeline
from backend.src.vision_ocr_pipeline.ocr_engine import normalize_ocr_output

def main():
    artifacts_dir = r"C:\Users\joako\.gemini\antigravity-ide\brain\2f13c44b-d7af-416d-94c6-e44fab9e530d"
    frame_path = os.path.join(artifacts_dir, "video_frame_4_idx_676.jpg")
    
    if not os.path.exists(frame_path):
        print(f"Error: Frame 4 image not found at {frame_path}")
        return
        
    img = cv2.imread(frame_path)
    h, w = img.shape[:2]
    print(f"Loaded Frame 4: {w}x{h}")
    
    # 1. Crop YOLO box: [8, 215, 119, 313]
    yolo_box = [8, 215, 119, 313]
    x1, y1, x2, y2 = yolo_box
    yolo_crop = img[y1:y2, x1:x2]
    yolo_crop_path = os.path.join(artifacts_dir, "yolo_crop_frame4.jpg")
    cv2.imwrite(yolo_crop_path, yolo_crop)
    print(f"Saved YOLO crop to {yolo_crop_path}")
    
    # 2. Get raw OCR text and coordinates of the entire frame
    _cfg_path = Path(__file__).resolve().parents[2] / "backend" / "config.yaml"
    cfg = load_config(str(_cfg_path))
    pipeline = VisionOCRPipeline(cfg)
    
    # Run full OCR on image using pipeline's OCR engine to avoid Mkldnn crash
    ocr = pipeline.ocr._ocr
    
    try:
        if getattr(pipeline.ocr, "is_paddlex", False):
            raw_ocr = normalize_ocr_output(list(ocr.predict(
                img,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False
            )))
        else:
            raw_ocr = normalize_ocr_output(ocr.ocr(img))
    except Exception as e:
        print(f"OCR failed: {e}")
        raw_ocr = None
    
    print("\nRaw OCR Output for entire Frame 4:")
    if raw_ocr:
        for line in raw_ocr:
            if not line:
                continue
            for item in line:
                poly = item[0]
                text, conf = item[1][0], item[1][1]
                xs = [int(p[0]) for p in poly]
                ys = [int(p[1]) for p in poly]
                x1_o, y1_o, x2_o, y2_o = min(xs), min(ys), max(xs), max(ys)
                print(f"  - '{text}' (Conf: {conf:.2%}) at Box=[{x1_o}, {y1_o}, {x2_o}, {y2_o}] (W={x2_o-x1_o}, H={y2_o-y1_o})")
                
if __name__ == "__main__":
    main()
