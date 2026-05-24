"""Convert .webp images in inputs/raw to .jpg (keeps originals).
Usage: .venv\Scripts\python scripts\convert_webp_to_jpg.py
"""
from pathlib import Path
from PIL import Image

SRC = Path('inputs/raw')
if not SRC.exists():
    print('inputs/raw not found')
    raise SystemExit(1)

converted = []
for p in sorted(SRC.glob('*.webp')):
    out = p.with_suffix('.jpg')
    try:
        im = Image.open(p).convert('RGB')
        im.save(out, format='JPEG', quality=95)
        converted.append(str(out))
    except Exception as e:
        print(f'Failed: {p} -> {e}')

if converted:
    print('Converted:')
    for c in converted:
        print(' -', c)
else:
    print('No .webp files found or nothing converted')
