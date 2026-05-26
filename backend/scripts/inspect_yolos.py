from ultralytics import YOLO
import os
import time

models = ["yolov8n.pt", "yolo26n.pt"]

for m_name in models:
    path = os.path.join("c:\\Users\\joako\\Documents\\GitHub\\tesis\\backend", m_name)
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        size = os.path.getsize(path)
        print(f"Model: {m_name}")
        print(f"  Path: {path}")
        print(f"  Size: {size} bytes")
        print(f"  Modified: {time.ctime(mtime)}")
        try:
            model = YOLO(path)
            print(f"  Classes ({len(model.names)}): {model.names}")
        except Exception as e:
            print(f"  Error loading model: {e}")
        print("-" * 50)
