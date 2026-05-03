"""Extract and process CCPD2019.tar.xz dataset to YOLO format.

CCPD annotations are embedded in filenames. This script:
1. Extracts the tar.xz
2. Parses bounding boxes from filenames
3. Converts to YOLO format
4. Organizes images and labels
"""
import tarfile
import shutil
from pathlib import Path
import re
import os

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "CCPD2019.tar.xz"
TEMP_EXTRACT = ROOT / "temp_ccpd_extract"
OUT_IMAGES = ROOT / "data" / "plates" / "images" / "ccpd"
OUT_LABELS = ROOT / "data" / "plates" / "labels" / "ccpd"


def extract_archive():
    """Extract tar.xz to temporary folder."""
    print(f"Extracting {ARCHIVE}...")
    TEMP_EXTRACT.mkdir(exist_ok=True)
    with tarfile.open(ARCHIVE, "r:xz") as tar:
        tar.extractall(TEMP_EXTRACT)
    print(f"Extracted to {TEMP_EXTRACT}")


def parse_ccpd_filename(filename: str):
    """Parse CCPD filename to extract bounding box.
    
    Format: 025-95_113-154&383_386&473-386&473_177&454_154&383_363&402-0_0_22_27_27_33_16-37-15.jpg
    Fields: area-tilt_degree-bbox_coords-vertices-char_indices-brightness-blurriness.jpg
    
    bbox_coords format: x1&y1_x2&y2
    Returns: (x1, y1, x2, y2) in pixels
    """
    # Remove extension
    name = Path(filename).stem
    
    # Split by '-'
    parts = name.split('-')
    if len(parts) < 3:
        return None
    
    # bbox_coords is the 3rd part (index 2): "154&383_386&473"
    bbox_str = parts[2]
    # Split by '_' to get two points
    if '_' not in bbox_str:
        return None
    
    p1, p2 = bbox_str.split('_')
    # p1: "154&383", p2: "386&473"
    if '&' not in p1 or '&' not in p2:
        return None
    
    x1, y1 = map(int, p1.split('&'))
    x2, y2 = map(int, p2.split('&'))
    
    return (x1, y1, x2, y2)


def bbox_to_yolo(bbox, img_width=1920, img_height=1080):
    """Convert pixel bbox (x1, y1, x2, y2) to YOLO format (cx, cy, w, h) normalized."""
    x1, y1, x2, y2 = bbox
    
    # Clamp to image bounds
    x1 = max(0, min(x1, img_width))
    x2 = max(0, min(x2, img_width))
    y1 = max(0, min(y1, img_height))
    y2 = max(0, min(y2, img_height))
    
    # Calculate center and width/height
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    w = x2 - x1
    h = y2 - y1
    
    # Normalize
    nx = cx / img_width
    ny = cy / img_height
    nw = w / img_width
    nh = h / img_height
    
    # Clamp normalized values
    nx = max(0, min(1, nx))
    ny = max(0, min(1, ny))
    nw = max(0, min(1, nw))
    nh = max(0, min(1, nh))
    
    return (nx, ny, nw, nh)


def process_images():
    """Process all images from extracted CCPD dataset."""
    OUT_IMAGES.mkdir(parents=True, exist_ok=True)
    OUT_LABELS.mkdir(parents=True, exist_ok=True)
    
    # Find all image files in temp extract
    image_files = list(TEMP_EXTRACT.rglob("*.jpg"))
    print(f"Found {len(image_files)} images")
    
    processed = 0
    failed = 0
    
    for img_path in sorted(image_files):
        try:
            # Parse filename to get bbox
            bbox = parse_ccpd_filename(img_path.name)
            if bbox is None:
                failed += 1
                continue
            
            # Convert to YOLO format (assuming standard CCPD size 1920x1080)
            yolo_bbox = bbox_to_yolo(bbox, img_width=1920, img_height=1080)
            
            # Copy image
            dest_img = OUT_IMAGES / img_path.name
            shutil.copy2(img_path, dest_img)
            
            # Write label file
            label_file = OUT_LABELS / f"{img_path.stem}.txt"
            # Class 0 = plate
            label_content = f"0 {yolo_bbox[0]:.6f} {yolo_bbox[1]:.6f} {yolo_bbox[2]:.6f} {yolo_bbox[3]:.6f}\n"
            label_file.write_text(label_content, encoding='utf-8')
            
            processed += 1
            if processed % 1000 == 0:
                print(f"  Processed {processed} images...")
        
        except Exception as e:
            print(f"Error processing {img_path.name}: {e}")
            failed += 1
    
    print(f"\nProcessing complete: {processed} succeeded, {failed} failed")
    return processed


def cleanup():
    """Remove temporary extraction folder."""
    if TEMP_EXTRACT.exists():
        print(f"Cleaning up {TEMP_EXTRACT}...")
        shutil.rmtree(TEMP_EXTRACT)


def main():
    if not ARCHIVE.exists():
        print(f"Archive not found: {ARCHIVE}")
        return
    
    try:
        extract_archive()
        processed = process_images()
        print(f"\nResults:")
        print(f"  Images: {OUT_IMAGES}")
        print(f"  Labels: {OUT_LABELS}")
        print(f"  Total: {processed} samples")
    finally:
        cleanup()


if __name__ == '__main__':
    main()
