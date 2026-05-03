"""Batch-convert COCO datasets placed under `data/plates/raw/` to YOLO labels

Scans subdirectories of `data/plates/raw/` for COCO JSON files (annotations.json or *.json).
For each dataset found it will:
 - run the existing `scripts/coco_to_yolo.py` to write YOLO `.txt` labels into
   `data/plates/labels/<dataset>`
 - copy referenced images into `data/plates/images/<dataset>` so datasets are
   co-located with the synthetic images.

This script does NOT download external datasets. Put your COCO folders under
`data/plates/raw/<dataset>/` (images + annotations.json) and run this script.
"""
from pathlib import Path
import subprocess
import json
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "plates" / "raw"
OUT_IMAGES = ROOT / "data" / "plates" / "images"
OUT_LABELS = ROOT / "data" / "plates" / "labels"


def find_coco_jsons(dataset_dir: Path):
    # prefer annotations.json, but accept any .json
    candidates = list(dataset_dir.glob("**/annotations*.json"))
    if not candidates:
        candidates = list(dataset_dir.glob("**/*.json"))
    return candidates


def copy_images(coco_json: Path, images_dir: Path, dest_images: Path):
    coco = json.loads(coco_json.read_text(encoding='utf-8'))
    images = coco.get('images', [])
    dest_images.mkdir(parents=True, exist_ok=True)
    copied = 0
    for img in images:
        fname = img.get('file_name')
        if not fname:
            continue
        src = images_dir / fname
        if not src.exists():
            # try relative to coco json parent
            alt = coco_json.parent / fname
            if alt.exists():
                src = alt
        if src.exists():
            try:
                shutil.copy2(src, dest_images / Path(fname).name)
                copied += 1
            except Exception as e:
                print(f"warning: failed to copy {src}: {e}")
    return copied


def convert_dataset(dataset_dir: Path):
    coco_files = find_coco_jsons(dataset_dir)
    if not coco_files:
        print(f"No COCO JSON files found in {dataset_dir}")
        return 0

    dataset_name = dataset_dir.name
    dest_images = OUT_IMAGES / dataset_name
    dest_labels = OUT_LABELS / dataset_name
    dest_labels.mkdir(parents=True, exist_ok=True)

    total_copied = 0
    for coco_json in coco_files:
        # look for images dir: sibling 'images' or same folder
        possible_images = [dataset_dir / 'images', coco_json.parent, dataset_dir]
        images_dir = None
        for p in possible_images:
            if p.exists():
                images_dir = p
                break
        if images_dir is None:
            print(f"Could not locate images directory for {coco_json}; skipping")
            continue

        # run the existing converter
        print(f"Converting {coco_json} -> labels {dest_labels}")
        cmd = [sys.executable, str(ROOT / 'scripts' / 'coco_to_yolo.py'),
               '--coco', str(coco_json),
               '--images-dir', str(images_dir),
               '--out-labels', str(dest_labels)]
        subprocess.run(cmd, check=True)

        # copy images referenced by coco
        copied = copy_images(coco_json, images_dir, dest_images)
        print(f"Copied {copied} images to {dest_images}")
        total_copied += copied

    return total_copied


def main():
    if not RAW_ROOT.exists():
        print("No raw datasets folder found (data/plates/raw). Create it and add your COCO datasets.")
        return

    any_found = False
    for child in sorted(RAW_ROOT.iterdir()):
        if not child.is_dir():
            continue
        any_found = True
        try:
            convert_dataset(child)
        except subprocess.CalledProcessError as e:
            print(f"Conversion failed for {child}: {e}")

    if not any_found:
        print("No datasets found under data/plates/raw/. Add each dataset as a subfolder and rerun.")


if __name__ == '__main__':
    main()
