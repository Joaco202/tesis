"""Generate synthetic license plate images and YOLO labels.
This produces simple images with a plate-like rectangle and random text.
"""
import argparse
import random
import string
from pathlib import Path

import cv2
import numpy as np


def random_plate_text():
    # Simple generator: 2 letters + 4 digits (adapt as needed)
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    digits = ''.join(random.choices(string.digits, k=4))
    return f"{letters}{digits}"


def make_background(w, h):
    # random noise background
    base = np.full((h, w, 3), 200, dtype=np.uint8)
    noise = np.random.randint(0, 40, (h, w, 1), dtype=np.uint8)
    base = cv2.add(base, np.repeat(noise, 3, axis=2))
    # small blur
    base = cv2.GaussianBlur(base, (3, 3), 0)
    return base


def draw_plate(img, text):
    h, w = img.shape[:2]
    plate_w = int(w * 0.4)
    plate_h = int(h * 0.12)
    x = random.randint(int(w * 0.05), int(w * 0.6))
    y = random.randint(int(h * 0.6), int(h * 0.85 - plate_h))

    # plate rectangle
    cv2.rectangle(img, (x, y), (x + plate_w, y + plate_h), (255, 255, 255), -1)
    cv2.rectangle(img, (x, y), (x + plate_w, y + plate_h), (120, 120, 120), 2)

    # put text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = plate_h / 40
    thickness = max(1, int(font_scale))
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    tx = x + (plate_w - text_size[0]) // 2
    ty = y + (plate_h + text_size[1]) // 2
    cv2.putText(img, text, (tx, ty), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

    # return bbox in pixels
    return x, y, plate_w, plate_h


def save_yolo_label(path: Path, bbox, img_w, img_h):
    x, y, w, h = bbox
    cx = x + w / 2.0
    cy = y + h / 2.0
    nx = cx / img_w
    ny = cy / img_h
    nw = w / img_w
    nh = h / img_h
    path.write_text(f"0 {nx:.6f} {ny:.6f} {nw:.6f} {nh:.6f}", encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='data/plates', help='Base output directory')
    parser.add_argument('--count', type=int, default=1000, help='Number of synthetic images')
    parser.add_argument('--size', type=int, nargs=2, default=[1280, 720], help='Image size W H')
    args = parser.parse_args()

    out = Path(args.out)
    img_dir = out / 'images' / 'synthetic'
    lbl_dir = out / 'labels' / 'synthetic'
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    w, h = args.size
    for i in range(args.count):
        bg = make_background(w, h)
        text = random_plate_text()
        bbox = draw_plate(bg, text)
        filename = f"synth_{i:06d}.jpg"
        cv2.imwrite(str(img_dir / filename), bg)
        save_yolo_label(lbl_dir / (Path(filename).stem + '.txt'), bbox, w, h)

    print(f"Generated {args.count} synthetic images in {img_dir}")


if __name__ == '__main__':
    main()
