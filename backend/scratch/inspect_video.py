import cv2
import sys
import os
from pathlib import Path

# Add project directory to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.src.vision_ocr_pipeline.config import load_config
from backend.src.vision_ocr_pipeline.pipeline import VisionOCRPipeline

def main():
    video_path = "../video.mp4"
    artifacts_dir = r"C:\Users\joako\.gemini\antigravity-ide\brain\2f13c44b-d7af-416d-94c6-e44fab9e530d"
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return
        
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"Video Properties:")
    print(f"- File: {video_path}")
    print(f"- Resolution: {width}x{height}")
    print(f"- FPS: {fps:.2f}")
    print(f"- Total Frames: {total_frames}")
    print(f"- Duration: {duration:.2f} seconds")
    
    # Load pipeline
    _cfg_path = Path(__file__).resolve().parents[2] / "backend" / "config.yaml"
    cfg = load_config(str(_cfg_path))
    pipeline = VisionOCRPipeline(cfg)
    
    # Extract 5 frames spaced evenly
    frame_indices = [int(total_frames * i / 6) for i in range(1, 6)]
    print(f"\nExtracting frames at indices: {frame_indices}")
    
    for i, idx in enumerate(frame_indices, 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to read frame at index {idx}")
            continue
            
        # Save frame image to artifacts
        out_name = f"video_frame_{i}_idx_{idx}.jpg"
        out_path = os.path.join(artifacts_dir, out_name)
        cv2.imwrite(out_path, frame)
        print(f"Saved frame {i} to {out_path}")
        
        # Process frame
        results = pipeline.process_frame(frame, run_ocr=True, run_fallback=True)
        if results:
            print(f"  Frame {i} Detections:")
            for r_idx, res in enumerate(results):
                det = res.detection
                print(f"    - Det {r_idx+1}: Box=[{det.x1}, {det.y1}, {det.x2}, {det.y2}], Conf={det.confidence:.2%}")
                conf_str = f"{res.plate_confidence:.2%}" if res.plate_confidence is not None else "N/A"
                print(f"      OCR Plate: '{res.plate_text}' (Conf: {conf_str})")
        else:
            print(f"  Frame {i}: No plates detected.")
            
    cap.release()

if __name__ == "__main__":
    main()
