"""Download CCPD datasets into data/plates/raw/.

This script downloads the public Google Drive archives for CCPD and CCPD-Green.
It does not require Kaggle credentials or manual approval.

Usage:
  .venv/Scripts/python scripts/download_ccpd.py
  .venv/Scripts/python scripts/download_ccpd.py --green
  .venv/Scripts/python scripts/download_ccpd.py --extract
"""
from __future__ import annotations

import argparse
from pathlib import Path


CCPD_FILE_ID = "1rdEsCUcIUaYOVRkx5IMTRNA7PcGMmSgc"
CCPD_GREEN_FILE_ID = "1m8w1kFxnCEiqz_-t2vTcgrgqNIv986PR"


def _ensure_gdown():
    try:
        import gdown  # type: ignore
    except ImportError as exc:  # pragma: no cover - validated by runtime
        raise SystemExit(
            "Missing dependency 'gdown'. Install it with: .venv/Scripts/python -m pip install -r requirements-dev.txt"
        ) from exc
    return gdown


def _download(file_id: str, output_path: Path):
    gdown = _ensure_gdown()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://drive.google.com/uc?id={file_id}"
    print(f"Downloading {url} -> {output_path}")
    gdown.download(url, str(output_path), quiet=False)


def _extract(archive_path: Path, extract_dir: Path):
    import tarfile

    print(f"Extracting {archive_path} -> {extract_dir}")
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:*") as tar:
        tar.extractall(path=extract_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download CCPD archives")
    parser.add_argument("--out", default="data/plates/raw/ccpd", help="Output directory")
    parser.add_argument("--green", action="store_true", help="Download CCPD-Green instead of CCPD")
    parser.add_argument("--extract", action="store_true", help="Extract the tar.xz after download")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.green:
        archive = out_dir / "CCPD-Green.tar.xz"
        _download(CCPD_GREEN_FILE_ID, archive)
        if args.extract:
            _extract(archive, out_dir / "CCPD-Green")
    else:
        archive = out_dir / "CCPD2019.tar.xz"
        _download(CCPD_FILE_ID, archive)
        if args.extract:
            _extract(archive, out_dir / "CCPD2019")


if __name__ == "__main__":
    main()
