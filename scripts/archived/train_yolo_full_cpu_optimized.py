"""
Train YOLOv8n with full dataset (310k images) on CPU (optimized) for 50 epochs
Note: Since GPU (RTX 5070/Blackwell) is not yet supported by available PyTorch versions,
we optimize for CPU training with efficient settings.
"""
from ultralytics import YOLO
import torch

print(f"\nUltralytics YOLO Training on Full Dataset")
print(f"=" * 60)

# Use CPU but with optimizations
device = "cpu"
print(f"✓ Device: CPU (GPU Blackwell support pending)")
print(f"  Note: Training will be slower but thorough")

print(f"\nTraining parameters:")
print(f"  Model: yolov8n.pt")
print(f"  Dataset: CCPD (217k train / 47k val / 47k test)")
print(f"  Epochs: 50")
print(f"  Batch size: 8 (CPU-optimized, memory-efficient)")
print(f"  Image size: 1280x1280")
print(f"  Device: {device}")
print(f"  Workers: 4 (CPU optimization)")
print(f"=" * 60 + "\n")

# Load and train
model = YOLO("yolov8n.pt")

results = model.train(
    data=r"data\plates\data.yaml",
    epochs=50,
    imgsz=1280,
    batch=8,  # Smaller batch for CPU
    device=device,
    patience=50,
    save=True,
    project=None,
    name="train-full-cpu-optimized",
    verbose=True,
    cos_lr=True,
    mosaic=1.0,
    workers=4,  # CPU workers
    cache=True,  # Cache images for speed
)

print(f"\n✓ Training completed!")
print(f"Results saved to: runs/detect/train-full-cpu-optimized")
print(f"Best model: runs/detect/train-full-cpu-optimized/weights/best.pt")
