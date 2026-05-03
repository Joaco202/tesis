"""Run a short YOLOv8 training to validate dataset and pipeline.

Usage:
  .venv/Scripts/python scripts/train_yolo_short.py
"""
import sys
from pathlib import Path

def main():
    try:
        from ultralytics import YOLO
    except Exception as e:
        print('Failed to import ultralytics:', e)
        sys.exit(1)

    data_yaml = Path('data/plates/data.yaml')
    if not data_yaml.exists():
        print('Data YAML not found:', data_yaml)
        sys.exit(1)

    model_path = 'yolov8n.pt'
    print('Starting short training: model=%s data=%s' % (model_path, data_yaml))
    try:
        model = YOLO(model_path)
        model.train(data=str(data_yaml), epochs=2, imgsz=1280)
        print('Training finished')
    except Exception as e:
        print('Training failed:', e)
        sys.exit(2)


if __name__ == '__main__':
    main()
