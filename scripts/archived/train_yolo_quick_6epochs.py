"""
Quick training: 6 epochs on full dataset (310k images) on CPU
"""
from ultralytics import YOLO

print(f"\nQuick YOLOv8 Training (6 epochs)")
print(f"=" * 60)
print(f"Model: yolov8n.pt")
print(f"Dataset: CCPD (217k train / 47k val)")
print(f"Epochs: 6 (fast)")
print(f"Batch size: 8 (CPU)")
print(f"=" * 60 + "\n")

model = YOLO("yolov8n.pt")

results = model.train(
    data=r"data\plates\data.yaml",
    epochs=6,
    imgsz=1280,
    batch=8,
    device="cpu",
    patience=10,
    save=True,
    project=None,
    name="train-quick-6epochs",
    verbose=True,
    cos_lr=True,
    workers=4,
    cache=True,
)

print(f"\n✓ Quick training completed!")
print(f"Best model: runs/detect/train-quick-6epochs/weights/best.pt")
