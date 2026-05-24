"""Create small dataset splits (sample) for quick training runs.

This will sample up to N images from available images with labels, write
train/val/test lists under `data/plates/` and keep proportions 80/10/10.
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
        # check any label exists
        if any(l.stem == stem for l in LABELS_ROOT.glob("**/*.txt")):
            imgs.append(img_path.resolve())
    return imgs


def write_list(paths, out_file: Path):
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        for p in paths:
            f.write(str(p).replace('\\', '/') + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=5000, help='Maximum total samples')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    imgs = gather_image_label_pairs()
    if not imgs:
        print('No images with labels found')
        return

    random.seed(args.seed)
    random.shuffle(imgs)

    n = min(len(imgs), args.max)
    imgs = imgs[:n]
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    n_test = n - n_train - n_val

    train = imgs[:n_train]
    val = imgs[n_train:n_train + n_val]
    test = imgs[n_train + n_val:]

    write_list(train, OUT_DIR / 'train.txt')
    write_list(val, OUT_DIR / 'val.txt')
    write_list(test, OUT_DIR / 'test.txt')

    print(f'Wrote small splits: {len(train)} train, {len(val)} val, {len(test)} test')


if __name__ == '__main__':
    main()
