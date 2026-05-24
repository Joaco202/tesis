"""
Test script to verify plate detector integration in pipeline
"""
import cv2
from pathlib import Path
from src.vision_ocr_pipeline.config import AppConfig, DetectionConfig
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline

print("=" * 70)
print("PLATE DETECTOR INTEGRATION TEST")
print("=" * 70)

# Create config with default detection settings
cfg = AppConfig()
print(f"\n✓ Configuration loaded")
print(f"  Detection model: {cfg.detection.model}")
print(f"  Device: {cfg.runtime.device}")

# Initialize pipeline
pipeline = VisionOCRPipeline(cfg)
print(f"✓ Pipeline initialized")
print(f"  Detector model path: {pipeline.detector._model_path}")

# Test with a sample image from the dataset (search recursively)
test_image = list(Path("data/plates/images/ccpd").rglob("*.jpg"))[:1]
if test_image:
    print(f"\n✓ Testing with image: {test_image[0].name}")
    try:
        annotated_img, results = pipeline.process_image(str(test_image[0]))
        
        if results:
            print(f"\n✓ Detection successful!")
            for i, result in enumerate(results, 1):
                print(f"\n  Detection #{i}:")
                print(f"    - Confidence: {result.detection.confidence:.4f}")
                print(f"    - Box: ({result.detection.x1}, {result.detection.y1}) -> ({result.detection.x2}, {result.detection.y2})")
                print(f"    - Plate text: {result.plate_text}")
                print(f"    - Plate confidence: {result.plate_confidence}")
        else:
            print("⚠ No plates detected in image")
            
    except Exception as e:
        print(f"✗ Error during processing: {e}")
else:
    print("⚠ No test images found in dataset")

print("\n" + "=" * 70)
print("Test completed!")
print("=" * 70)
