"""
Create full dataset splits (all 310k images) for training
"""
import os
from pathlib import Path

images_dir = Path(r"C:\Users\joako\Documents\GitHub\tesis\data\plates\images\ccpd")

# Get all images
all_imgs = sorted([str(f.absolute()).replace('\\', '/') for f in images_dir.rglob('*.jpg')])
print(f"Total images found: {len(all_imgs)}")

if not all_imgs:
    print("ERROR: No images found!")
    exit(1)

# Split: 70% train, 15% val, 15% test
total = len(all_imgs)
train_split = int(0.70 * total)
val_split = int(0.85 * total)

train = all_imgs[:train_split]
val = all_imgs[train_split:val_split]
test = all_imgs[val_split:]

print(f"Train: {len(train)}")
print(f"Val: {len(val)}")
print(f"Test: {len(test)}")

# Write files
base_dir = Path(r"C:\Users\joako\Documents\GitHub\tesis\data\plates")
(base_dir / "train.txt").write_text('\n'.join(train), encoding='utf-8')
(base_dir / "val.txt").write_text('\n'.join(val), encoding='utf-8')
(base_dir / "test.txt").write_text('\n'.join(test), encoding='utf-8')

print("✓ Splits created successfully")
