"""
Train YOLOv8n with full dataset (310k images) on GPU for 50 epochs
"""
from ultralytics import YOLO
import torch

print(f"\nUltralytics YOLO Training on Full Dataset")
print(f"=" * 60)

# Check GPU
if torch.cuda.is_available():
    device = 0
    print(f"✓ Using GPU: {torch.cuda.get_device_name(0)}")
    print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    device = "cpu"
    print("⚠ GPU not available, using CPU (much slower)")

print(f"\nTraining parameters:")
print(f"  Model: yolov8n.pt")
print(f"  Dataset: CCPD (217k train / 47k val / 47k test)")
print(f"  Epochs: 50")
print(f"  Batch size: 32 (GPU optimized)")
print(f"  Image size: 1280x1280")
print(f"  Device: {device}")
print(f"=" * 60 + "\n")

# Load and train
model = YOLO("yolov8n.pt")

results = model.train(
    data=r"data\plates\data.yaml",
    epochs=50,
    imgsz=1280,
    batch=32,  # Larger batch for GPU
    device=device,
    patience=50,
    save=True,
    project=None,  # Use default runs dir
    name="train-full-gpu",
    verbose=True,
    cos_lr=True,
    mosaic=1.0,
)

print(f"\n✓ Training completed!")
print(f"Results saved to: runs/detect/train-full-gpu")
print(f"Best model: runs/detect/train-full-gpu/weights/best.pt")
