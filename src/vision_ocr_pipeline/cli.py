"""Unified CLI for vision-ocr-pipeline: dataset generation, training, and inference.

Consolidated interface combining 18+ individual scripts into organized subcommands.
Supports: dataset generation, model training (multiple profiles), and batch inference.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
import cv2
from rich.console import Console
from typing import Optional

from .config import load_config
from .pipeline import VisionOCRPipeline

app = typer.Typer(
    help="Vision OCR Pipeline: unified CLI for dataset, training, and inference",
    invoke_without_command=False,
    no_args_is_help=True
)
console = Console()

# Sub-apps for command groups
generate_app = typer.Typer(help="Dataset generation and processing commands")
train_app = typer.Typer(help="Model training with multiple profiles")
run_app = typer.Typer(help="Inference and evaluation")
verify_app = typer.Typer(help="System verification and checks")

app.add_typer(generate_app, name="generate")
app.add_typer(train_app, name="train")
app.add_typer(run_app, name="run")
app.add_typer(verify_app, name="verify")


# ============================================================================
# GENERATE commands: dataset preparation
# ============================================================================

@generate_app.command("synthetic")
def generate_synthetic(
    count: int = typer.Option(1000, "--count", "-c", help="Number of synthetic plates to generate"),
    output: Path = typer.Option(Path("data/synthetic"), "--output", "-o", help="Output directory"),
) -> None:
    """Generate synthetic license plate images for training."""
    try:
        from scripts.generate_synthetic_plates import main as gen_main
        sys.argv = ["generate_synthetic", str(count), str(output)]
        gen_main()
        console.print(f"[green]✓ Generated {count} synthetic plates → {output}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Synthetic generation failed: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("download")
def generate_download() -> None:
    """Download CCPD2019 dataset."""
    try:
        from scripts.download_ccpd import main as dl_main
        dl_main()
        console.print("[green]✓ CCPD2019 downloaded[/green]")
    except Exception as e:
        console.print(f"[red]✗ Download failed: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("process")
def generate_process(
    input_dir: Path = typer.Option(Path("data/CCPD2019"), "--input", "-i", help="CCPD2019 directory"),
) -> None:
    """Convert CCPD2019 annotations to standard format."""
    try:
        from scripts.process_ccpd import main as proc_main
        sys.argv = ["process_ccpd", str(input_dir)]
        proc_main()
        console.print(f"[green]✓ Processed CCPD2019 from {input_dir}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Processing failed: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("convert")
def generate_convert(
    input_dir: Path = typer.Option(Path("data"), "--input", "-i", help="Input directory with COCO format"),
) -> None:
    """Convert COCO annotations to YOLO format."""
    try:
        from scripts.batch_convert_coco import main as conv_main
        sys.argv = ["batch_convert_coco", str(input_dir)]
        conv_main()
        console.print(f"[green]✓ Converted COCO → YOLO format[/green]")
    except Exception as e:
        console.print(f"[red]✗ Conversion failed: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("split")
def generate_split() -> None:
    """Create train/val/test splits and data.yaml for YOLO."""
    try:
        from scripts.create_dataset_yaml_and_splits import main as split_main
        split_main()
        console.print("[green]✓ Dataset splits and data.yaml created[/green]")
    except Exception as e:
        console.print(f"[red]✗ Split creation failed: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# TRAIN commands: model training
# ============================================================================

@train_app.command("short")
def train_short() -> None:
    """Quick smoke test (2 epochs) to validate pipeline."""
    try:
        from scripts.train_yolo_short import main as train_main
        console.print("[cyan]Starting 2-epoch smoke test...[/cyan]")
        train_main()
        console.print("[green]✓ Short training completed[/green]")
    except Exception as e:
        console.print(f"[red]✗ Training failed: {e}[/red]")
        raise typer.Exit(1)


@train_app.command("quick")
def train_quick() -> None:
    """Quick training (6 epochs) for baseline improvement."""
    try:
        from scripts.train_yolo_quick_6epochs import main as train_main
        console.print("[cyan]Starting 6-epoch quick training...[/cyan]")
        train_main()
        console.print("[green]✓ Quick training completed[/green]")
    except Exception as e:
        console.print(f"[red]✗ Training failed: {e}[/red]")
        raise typer.Exit(1)


@train_app.command("full-cpu")
def train_full_cpu() -> None:
    """Full training on CPU (slow but portable)."""
    try:
        from scripts.train_yolo_full_cpu_optimized import main as train_main
        console.print("[cyan]Starting full CPU training (this will take a while)...[/cyan]")
        train_main()
        console.print("[green]✓ Full CPU training completed[/green]")
    except Exception as e:
        console.print(f"[red]✗ Training failed: {e}[/red]")
        raise typer.Exit(1)


@train_app.command("full-gpu")
def train_full_gpu() -> None:
    """Full training on GPU (if available)."""
    try:
        from scripts.train_yolo_full_gpu import main as train_main
        console.print("[cyan]Starting full GPU training...[/cyan]")
        train_main()
        console.print("[green]✓ Full GPU training completed[/green]")
    except Exception as e:
        console.print(f"[red]✗ Training failed: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# RUN commands: inference and evaluation
# ============================================================================

@run_app.command("infer")
def run_infer(
    source: Path = typer.Option(..., "--source", "-s", exists=True, help="Input image or directory"),
    output_dir: Path = typer.Option(Path("outputs"), "--output", "-o", help="Output directory"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file (default: config.yaml)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
) -> None:
    """Run pipeline inference on images with annotation and JSON results."""
    config_path = config
    if config_path is None:
        default_config = Path("config.yaml")
        if default_config.exists():
            config_path = default_config

    cfg = load_config(config_path)
    pipeline = VisionOCRPipeline(cfg)
    
    output_dir = Path(output_dir)
    annot_dir = output_dir / "annotated"
    output_dir.mkdir(parents=True, exist_ok=True)
    annot_dir.mkdir(parents=True, exist_ok=True)
    
    source = Path(source)
    images = list(source.glob('*')) if source.is_dir() else [source]
    
    results = []
    for img_path in sorted(images):
        if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']:
            continue
        
        try:
            image, detection_results = pipeline.process_image(str(img_path))
        except Exception as e:
            results.append({'file': str(img_path), 'error': str(e)})
            if debug:
                console.print(f"[yellow]⚠ {img_path.name}: {e}[/yellow]")
            continue
        
        if not detection_results:
            results.append({
                'file': str(img_path),
                'plate_text': None,
                'confidence': None,
                'ocr_confidence': None,
                'bbox': None
            })
            ann_file = annot_dir / (img_path.stem + '_annot.jpg')
            cv2.imwrite(str(ann_file), image)
            if debug:
                console.print(f"[yellow]○ {img_path.name}: no detections[/yellow]")
            continue
        
        primary = detection_results[0]
        out = {
            'file': str(img_path),
            'plate_text': primary.plate_text,
            'confidence': primary.plate_confidence,
            'ocr_confidence': max((o.confidence for o in primary.ocr), default=None) if primary.ocr else None,
            'bbox': (primary.detection.x1, primary.detection.y1, primary.detection.x2, primary.detection.y2),
        }
        results.append(out)
        
        # Annotate
        annotated = image.copy()
        d = primary.detection
        try:
            cv2.rectangle(annotated, (d.x1, d.y1), (d.x2, d.y2), (0, 255, 0), 2)
            cv2.putText(annotated, primary.plate_text or '?', (d.x1, d.y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        except Exception:
            pass
        
        ann_file = annot_dir / (img_path.stem + '_annot.jpg')
        cv2.imwrite(str(ann_file), annotated)
        
        if debug:
            console.print(f"[green]✓ {img_path.name}: {primary.plate_text}[/green]")
    
    # Save results
    output_file = output_dir / f'results_{source.name}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    console.print(f"\n[green]✓ Processed {len(results)} images[/green]")
    console.print(f"   Results: {output_file}")
    console.print(f"   Annotated: {annot_dir}")


@run_app.command("option5")
def run_option5(
    source: Path = typer.Option(..., "--source", "-s", exists=True, help="Image or directory"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
) -> None:
    """Use OCR-region fallback to detect plates missed by YOLO (Option 5)."""
    config_path = config
    if config_path is None:
        default_config = Path("config.yaml")
        if default_config.exists():
            config_path = default_config

    cfg = load_config(config_path)
    pipeline = VisionOCRPipeline(cfg)
    
    source = Path(source)
    images = list(source.glob('*')) if source.is_dir() else [source]
    
    results = []
    for img_path in sorted(images):
        if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
            continue
        
        try:
            image = cv2.imread(str(img_path))
            result = pipeline._detect_plate_via_ocr_regions(image)
            
            if result:
                results.append({
                    'file': str(img_path),
                    'method': 'ocr-regions',
                    'plate_text': result.plate_text,
                    'confidence': result.plate_confidence
                })
                console.print(f"[green]✓ {img_path.name}: {result.plate_text} (conf={result.plate_confidence:.2f})[/green]")
            else:
                results.append({'file': str(img_path), 'plate_text': None})
                console.print(f"[yellow]○ {img_path.name}: no plate found[/yellow]")
        except Exception as e:
            results.append({'file': str(img_path), 'error': str(e)})
            console.print(f"[red]✗ {img_path.name}: {e}[/red]")
    
    if debug:
        console.print(json.dumps(results, indent=2))


@run_app.command("compare")
def run_compare(
    source: Path = typer.Option(Path("inputs/raw"), "--source", "-s", exists=True, help="Directory to evaluate"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
) -> None:
    """Compare base yolov8n.pt vs. best trained model on same images."""
    try:
        from scripts.compare_models import main as cmp_main
        sys.argv = ["compare_models", str(source)]
        cmp_main()
        console.print("[green]✓ Model comparison completed[/green]")
    except Exception as e:
        console.print(f"[red]✗ Comparison failed: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# VERIFY commands: system checks
# ============================================================================

@verify_app.command("cuda")
def verify_cuda() -> None:
    """Check CUDA and GPU availability."""
    try:
        from scripts.verify_cuda import main as verify_main
        verify_main()
    except Exception as e:
        console.print(f"[red]✗ CUDA check failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
