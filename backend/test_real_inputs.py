from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Prueba del pipeline con imágenes reales.")
    parser.add_argument(
        "--source",
        type=str,
        default="inputs/raw",
        help="Directorio con imágenes reales a procesar.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Límite de imágenes a procesar.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Desactivar la persistencia en Supabase durante la prueba.",
    )
    parser.add_argument(
        "--camera-id",
        type=str,
        default="cam-acceso-1",
        help="ID de la cámara para registrar el acceso.",
    )
    parser.add_argument(
        "--event-type",
        type=str,
        default="entrada",
        choices=["entrada", "salida"],
        help="Tipo de evento de acceso.",
    )
    args = parser.parse_args()

    # Cargar configuración y forzar desactivación si se pasa --no-persist
    cfg = load_config("config.yaml")
    if args.no_persist:
        cfg.supabase.enabled = False

    print("=" * 60)
    print("Inicializando Vision + OCR Pipeline...")
    print(f"Dispositivo de Inferencia: {cfg.runtime.device}")
    print(f"Supabase habilitado: {cfg.supabase.enabled}")
    if cfg.supabase.enabled:
        print(f"URL Supabase: {cfg.supabase.url}")
        print(f"Tabla Accesos: {cfg.supabase.accesses_table}")
    print("=" * 60)

    # Iniciar pipeline
    pipeline = VisionOCRPipeline(cfg)
    print(f"Detector cargado con pesos: {pipeline.detector._model_path}")
    print(f"PaddleOCR configurado con idioma: {pipeline.ocr.cfg.lang}")
    print("=" * 60)

    source_dir = Path(args.source)
    if not source_dir.exists():
        print(f"Error: El directorio {source_dir} no existe.")
        return

    # Buscar imágenes de forma case-insensitive
    valid_exts = {".jpg", ".jpeg", ".png"}
    images = [p for p in source_dir.iterdir() if p.suffix.lower() in valid_exts]
    images = sorted(images, key=lambda x: x.name)

    if not images:
        print(f"No se encontraron imágenes válidas en {source_dir}.")
        return

    if args.limit:
        images = images[: args.limit]

    print(f"Procesando {len(images)} imágenes...")
    print("-" * 60)

    total_time = 0.0
    detected_count = 0

    for idx, img_path in enumerate(images, 1):
        print(f"[{idx}/{len(images)}] Procesando: {img_path.name}")
        
        start_time = time.perf_counter()
        try:
            image, results = pipeline.process_image(img_path)
            elapsed = time.perf_counter() - start_time
            total_time += elapsed
            
            # Buscar resultado con texto de patente
            main_result = next((r for r in results if r.plate_text), None)
            
            if main_result:
                detected_count += 1
                confidence = main_result.plate_confidence or 0.0
                print(f"  ✓ Patente Detectada: [ {main_result.plate_text} ]")
                print(f"    Confianza: {confidence:.2%} (YOLO: {main_result.detection.confidence:.2%})")
                print(f"    Método de localización: {main_result.detection.cls_name}")
                print(f"    Tiempo de inferencia: {elapsed:.3f} s")
                
                # Persistencia
                if cfg.supabase.enabled:
                    print("    Persistiendo en Supabase...")
                    persist_summary = pipeline.persist_results(
                        results=[main_result],
                        event_type=args.event_type,
                        camera_id=args.camera_id,
                        image_origin=img_path.name,
                    )
                    
                    if persist_summary.saved_events:
                        evt = persist_summary.saved_events[0]
                        print(f"    ✅ Guardado con éxito. ID Acceso: {evt.acceso_id}")
                    if persist_summary.errors:
                        for err in persist_summary.errors:
                            print(f"    ❌ Error al guardar: {err}")
            else:
                print(f"  ✗ No se detectó patente válida.")
                print(f"    Tiempo de inferencia: {elapsed:.3f} s")
                
        except Exception as e:
            print(f"  ❌ Error inesperado al procesar {img_path.name}: {e}")
        
        print("-" * 60)

    # Resumen final
    avg_time = total_time / len(images) if images else 0.0
    detection_rate = detected_count / len(images) if images else 0.0
    print("=" * 60)
    print("Resumen de Ejecución:")
    print(f"  Total procesadas: {len(images)}")
    print(f"  Total detectadas: {detected_count} ({detection_rate:.2%})")
    print(f"  Tiempo total: {total_time:.3f} s")
    print(f"  Tiempo promedio por imagen: {avg_time:.3f} s")
    print("=" * 60)


if __name__ == "__main__":
    main()
