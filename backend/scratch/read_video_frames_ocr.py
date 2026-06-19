import os
import sys
from pathlib import Path

# Add project directory to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.src.vision_ocr_pipeline.config import load_config
from backend.src.vision_ocr_pipeline.pipeline import VisionOCRPipeline
from backend.src.vision_ocr_pipeline.ocr_engine import normalize_ocr_output

def main():
    artifacts_dir = r"C:\Users\joako\.gemini\antigravity-ide\brain\2f13c44b-d7af-416d-94c6-e44fab9e530d"
    _cfg_path = Path(__file__).resolve().parents[2] / "backend" / "config.yaml"
    cfg = load_config(str(_cfg_path))
    pipeline = VisionOCRPipeline(cfg)
    
    ocr = pipeline.ocr._ocr
    if ocr is None:
        print("Error: OCR not initialized")
        return
        
    import cv2
    
    for i in range(1, 6):
        frame_name = f"video_frame_{i}_idx_{int(1014 * i / 6)}.jpg"  # wait, frame indices were: [169, 338, 507, 676, 845]
        # Let's list files in artifacts matching video_frame_{i}
        import glob
        matches = glob.glob(os.path.join(artifacts_dir, f"video_frame_{i}_idx_*.jpg"))
        if not matches:
            print(f"Frame {i} not found.")
            continue
            
        frame_path = matches[0]
        img = cv2.imread(frame_path)
        if img is None:
            print(f"Failed to read {frame_path}")
            continue
            
        print(f"\n==========================================")
        print(f"TEXT ON FRAME {i} (File: {os.path.basename(frame_path)}):")
        print(f"==========================================")
        
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
            continue
            
        if raw_ocr:
            for line in raw_ocr:
                if not line:
                    continue
                for item in line:
                    text = item[1][0]
                    conf = item[1][1]
                    print(f"  {text} (Conf: {conf:.1%})")
        else:
            print("  [No text detected]")

if __name__ == "__main__":
    main()
