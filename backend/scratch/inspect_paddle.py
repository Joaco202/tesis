import sys
from pathlib import Path
import inspect

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.ocr_engine import PaddleOCREngine

def main():
    cfg = load_config("config.yaml")
    engine = PaddleOCREngine(cfg.ocr)
    
    if engine._ocr is not None:
        print("Class:", engine._ocr.__class__)
        print("\nMethods and signature of ocr:")
        try:
            print(inspect.signature(engine._ocr.ocr))
        except Exception as e:
            print("Could not get signature of ocr:", e)

        print("\nMethods and signature of predict:")
        try:
            print(inspect.signature(engine._ocr.predict))
        except Exception as e:
            print("Could not get signature of predict:", e)

        print("\nAttributes of the class:")
        for attr in dir(engine._ocr):
            if not attr.startswith("_"):
                print(attr)

if __name__ == "__main__":
    main()
