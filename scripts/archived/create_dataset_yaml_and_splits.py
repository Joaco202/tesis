"""Create train/val/test splits and a YOLO data.yaml for combined datasets.

The script finds images under `data/plates/images/*` and checks that a
corresponding label file exists in `data/plates/labels/*` (matching stem).
It then shuffles and splits the dataset (default 80/10/10) and writes:

- `data/plates/train.txt`, `val.txt`, `test.txt` (one absolute path per line)
- `data/plates/data.yaml` referencing those files and class names

Usage:
  .venv/Scripts/python scripts/create_dataset_yaml_and_splits.py
"""
from pathlib import Path
import random
import argparse


ROOT = Path(__file__).resolve().parents[1]
IMAGES_ROOT = ROOT / "data" / "plates" / "images"
LABELS_ROOT = ROOT / "data" / "plates" / "labels"
OUT_DIR = ROOT / "data" / "plates"


def gather_image_label_pairs():
    imgs = []
    for img_path in IMAGES_ROOT.rglob("*.jpg"):
        stem = img_path.stem
        # try to find a label in any labels subfolder
        label_path = None
        for l in LABELS_ROOT.glob("**/*.txt"):
            if l.stem == stem:
                label_path = l
                break
        if label_path and label_path.exists():
            imgs.append(img_path.resolve())
    return imgs


def write_list(paths, out_file: Path):
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        for p in paths:
            f.write(str(p).replace('\\', '/') + "\n")


def create_yaml(train_file: Path, val_file: Path, test_file: Path, out_yaml: Path):
    content = f"train: {str(train_file).replace('\\', '/')}\n"
    content += f"val: {str(val_file).replace('\\', '/')}\n"
    content += f"test: {str(test_file).replace('\\', '/')}\n"
    content += "nc: 1\n"
    content += "names: ['plate']\n"
    out_yaml.write_text(content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--train', type=float, default=0.8)
    parser.add_argument('--val', type=float, default=0.1)
    parser.add_argument('--test', type=float, default=0.1)
    args = parser.parse_args()

    imgs = gather_image_label_pairs()
    if not imgs:
        print("No images with labels found under data/plates/images and data/plates/labels")
        return

    random.seed(args.seed)
    random.shuffle(imgs)

    n = len(imgs)
    n_train = int(n * args.train)
    n_val = int(n * args.val)
    n_test = n - n_train - n_val

    train = imgs[:n_train]
    val = imgs[n_train:n_train + n_val]
    test = imgs[n_train + n_val:]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train_file = OUT_DIR / "train.txt"
    val_file = OUT_DIR / "val.txt"
    test_file = OUT_DIR / "test.txt"
    yaml_file = OUT_DIR / "data.yaml"

    write_list(train, train_file)
    write_list(val, val_file)
    write_list(test, test_file)
    create_yaml(train_file, val_file, test_file, yaml_file)

    print(f"Wrote {len(train)} train, {len(val)} val, {len(test)} test samples")
    print(f"Data YAML: {yaml_file}")


if __name__ == '__main__':
    main()
