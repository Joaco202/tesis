# Dataset preparation for license-plate detector

This document describes how to prepare data for training a YOLOv8 license-plate detector.

1) Structure

```
data/plates/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
  data.yaml
```

2) Convert COCO -> YOLO

If you have COCO annotations, use the script:

```bash
python scripts/coco_to_yolo.py --coco /path/annotations.json --images-dir /path/images --out-labels data/plates/labels/train --category plate
```

3) Generate synthetic plates (optional)

```bash
python scripts/generate_synthetic_plates.py --out data/plates --count 2000 --size 1280 720
```

5) Download public CCPD archives

CCPD is the most accessible public dataset that can be downloaded without Kaggle credentials or approval emails.

```bash
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python scripts/download_ccpd.py --extract
```

To download the green subset instead:

```bash
.venv/Scripts/python scripts/download_ccpd.py --green --extract
```

4) Create `data/plates/data.yaml` (already present) and then train with Ultralytics:

```bash
# activate venv
.venv/Scripts/python -m pip install ultralytics
yolo task=detect mode=train model=yolov8n.pt data=data/plates/data.yaml epochs=50 imgsz=1280
```