from pathlib import Path
from rich.console import Console
from rich.progress import track

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline

console = Console()

INPUT_DIR = Path("inputs/raw")
OUTPUT_DIR = Path("outputs")
CONFIG_PATH = Path("config.yaml")
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

def main():
    if not INPUT_DIR.exists():
        console.print(f"[red]Error:[/red] {INPUT_DIR} no existe.", style="bold")
        return
    
    cfg = load_config(CONFIG_PATH if CONFIG_PATH.exists() else None)
    pipeline = VisionOCRPipeline(cfg)
    
    images = [
        f for f in INPUT_DIR.iterdir() 
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    ]
    
    if not images:
        console.print(f"[yellow]Advertencia:[/yellow] No se encontraron imágenes en {INPUT_DIR}")
        return
    
    console.print(f"[cyan]Procesando {len(images)} imagen(es)...[/cyan]\n")
    
    successful = 0
    failed = 0
    
    for image_path in track(images, description="Procesando"):
        try:
            image, results = pipeline.process_image(image_path)
            persistence = pipeline.persist_results(
                results=results,
                event_type=cfg.runtime.default_event_type,
                camera_id=cfg.runtime.default_camera_id,
                image_origin=str(image_path),
                image=image,
            )
            
            json_path, annotated_path = pipeline.save_outputs(
                image=image,
                results=results,
                output_dir=OUTPUT_DIR,
                stem=image_path.stem,
                camera_id=cfg.runtime.default_camera_id,
                event_type=cfg.runtime.default_event_type,
                persistence=persistence,
                save_annotated=cfg.runtime.save_annotated,
            )
            
            successful += 1
            console.print(f"[green]✓[/green] {image_path.name} → {len(results)} detecciones")
            
        except Exception as e:
            failed += 1
            console.print(f"[red]✗[/red] {image_path.name}: {str(e)}")
    
    console.print(f"\n[cyan]{'='*60}[/cyan]")
    console.print(f"[green]Exitosas:[/green] {successful}/{len(images)}")
    if failed > 0:
        console.print(f"[red]Fallidas:[/red] {failed}/{len(images)}")
    console.print(f"[cyan]Resultados en:[/cyan] {OUTPUT_DIR}")
    
    if cfg.supabase.enabled and pipeline.offline_queue:
        pipeline.offline_queue.sync_queue()

if __name__ == "__main__":
    main()
