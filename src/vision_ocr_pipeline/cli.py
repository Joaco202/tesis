from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .config import load_config
from .pipeline import VisionOCRPipeline

app = typer.Typer(help="Pipeline CPU-only de deteccion YOLO + OCR con PaddleOCR")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print("Usa --help para ver comandos disponibles.")
        raise typer.Exit()


@app.command("run")
def run_command(
    source: Path = typer.Option(..., "--source", "-s", exists=True, help="Imagen de entrada"),
    output_dir: Path = typer.Option(Path("outputs"), "--output", "-o", help="Carpeta de salida"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Archivo YAML de configuracion"),
    event_type: str | None = typer.Option(
        None,
        "--event-type",
        help="Tipo de evento a registrar: entrada o salida",
    ),
    camera_id: str | None = typer.Option(
        None,
        "--camera-id",
        help="Identificador de camara para trazabilidad",
    ),
) -> None:
    cfg = load_config(config)
    pipeline = VisionOCRPipeline(cfg)
    selected_event_type = event_type or cfg.runtime.default_event_type
    selected_camera_id = camera_id or cfg.runtime.default_camera_id

    image, results = pipeline.process_image(source)
    persistence = pipeline.persist_results(
        results=results,
        event_type=selected_event_type,
        camera_id=selected_camera_id,
        image_origin=str(source),
    )

    json_path, annotated_path = pipeline.save_outputs(
        image=image,
        results=results,
        output_dir=output_dir,
        stem=source.stem,
        camera_id=selected_camera_id,
        event_type=selected_event_type,
        persistence=persistence,
        save_annotated=cfg.runtime.save_annotated,
    )

    console.print(f"[green]OK[/green] JSON generado: {json_path}")
    if annotated_path is not None:
        console.print(f"[green]OK[/green] Imagen anotada: {annotated_path}")
    console.print(f"[cyan]Detecciones:[/cyan] {len(results)}")
    if persistence.enabled:
        console.print(f"[cyan]Eventos guardados en BD:[/cyan] {len(persistence.saved_events)}")
        if persistence.errors:
            console.print("[yellow]Advertencias DB:[/yellow]")
            for err in persistence.errors:
                console.print(f"- {err}")


if __name__ == "__main__":
    app()
