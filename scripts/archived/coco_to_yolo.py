"""Convert COCO annotations to YOLO format (one .txt per image).
Usage:
  python coco_to_yolo.py --coco annotations.json --images-dir /path/to/images --out-labels labels_dir
"""
import argparse
import json
from pathlib import Path


def coco_to_yolo(coco_path: Path, images_dir: Path, out_labels: Path, category_name: str | None = None):
    coco = json.loads(coco_path.read_text(encoding='utf-8'))
    images = {img['id']: img for img in coco.get('images', [])}
    categories = {c['id']: c['name'] for c in coco.get('categories', [])}

    # determine category ids to keep
    if category_name:
        cat_ids = [cid for cid, name in categories.items() if name == category_name]
    else:
        # if no category given, try to use 'plate' or take all
        cat_ids = [cid for cid, name in categories.items() if name.lower() == 'plate'] or list(categories.keys())

    ann_by_image: dict[int, list] = {}
    for ann in coco.get('annotations', []):
        img_id = ann['image_id']
        ann_by_image.setdefault(img_id, []).append(ann)

    out_labels.mkdir(parents=True, exist_ok=True)

    for img_id, anns in ann_by_image.items():
        img = images.get(img_id)
        if img is None:
            continue
        img_w = img.get('width')
        img_h = img.get('height')
        img_file = img.get('file_name')
        if not img_file:
            continue
        label_lines = []
        for ann in anns:
            if ann.get('category_id') not in cat_ids:
                continue
            bbox = ann.get('bbox', [])  # COCO: [x, y, w, h]
            if not bbox or img_w in (0, None) or img_h in (0, None):
                continue
            x, y, w, h = bbox
            cx = x + w / 2.0
            cy = y + h / 2.0
            # normalize
            nx = cx / img_w
            ny = cy / img_h
            nw = w / img_w
            nh = h / img_h
            # single class (plate=0)
            label_lines.append(f"0 {nx:.6f} {ny:.6f} {nw:.6f} {nh:.6f}")

        if label_lines:
            img_stem = Path(img_file).stem
            out_file = out_labels / f"{img_stem}.txt"
            out_file.write_text("\n".join(label_lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coco', required=True, help='Path to COCO annotations json')
    parser.add_argument('--images-dir', required=True, help='Directory with images')
    parser.add_argument('--out-labels', required=True, help='Output labels directory')
    parser.add_argument('--category', default=None, help='Category name to filter (default: plate or all)')
    args = parser.parse_args()

    coco_to_yolo(Path(args.coco), Path(args.images_dir), Path(args.out_labels), args.category)


if __name__ == '__main__':
    main()
