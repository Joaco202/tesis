from __future__ import annotations

import json
from pathlib import Path

import typer
import cv2
from rich.console import Console
from typing import Optional

from .config import load_config
from .pipeline import VisionOCRPipeline

app = typer.Typer(
    help="Vision OCR Pipeline: CLI para inferencia y verificación",
    invoke_without_command=False,
    no_args_is_help=True
)
console = Console()

run_app = typer.Typer(help="Inferencia y evaluación")
verify_app = typer.Typer(help="Verificación del sistema")

app.add_typer(run_app, name="run")
app.add_typer(verify_app, name="verify")


@run_app.command("infer")
def run_infer(
    source: Path = typer.Option(..., "--source", "-s", exists=True, help="Input image or directory"),
    output_dir: Path = typer.Option(Path("outputs"), "--output", "-o", help="Output directory"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file (default: config.yaml)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
) -> None:
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
                console.print(f"[yellow] {img_path.name}: {e}[/yellow]")
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
            console.print(f"[green] {img_path.name}: {primary.plate_text}[/green]")
    
    output_file = output_dir / f'results_{source.name}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    console.print(f"\n[green] Processed {len(results)} images[/green]")
    console.print(f"   Results: {output_file}")
    console.print(f"   Annotated: {annot_dir}")


@run_app.command("option5")
def run_option5(
    source: Path = typer.Option(..., "--source", "-s", exists=True, help="Image or directory"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
) -> None:
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
                console.print(f"[green] {img_path.name}: {result.plate_text} (conf={result.plate_confidence:.2f})[/green]")
            else:
                results.append({'file': str(img_path), 'plate_text': None})
                console.print(f"[yellow]○ {img_path.name}: no plate found[/yellow]")
        except Exception as e:
            results.append({'file': str(img_path), 'error': str(e)})
            console.print(f"[red] {img_path.name}: {e}[/red]")
    
    if debug:
        console.print(json.dumps(results, indent=2))


@verify_app.command("cuda")
def verify_cuda() -> None:
    try:
        from scripts.archived.verify_cuda import main as verify_main
        verify_main()
    except Exception as e:
        console.print(f"[red] CUDA check failed: {e}[/red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
