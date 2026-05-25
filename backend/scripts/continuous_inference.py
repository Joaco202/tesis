from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

# Importar configuración y pipeline agregando la carpeta base al PATH si es necesario
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de inferencia continua para detección de patentes en video o flujo de imágenes."
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Ruta a un archivo de video (.mp4, .avi) o carpeta con imágenes.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Retardo en segundos entre frames (solo para carpetas de imágenes).",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=15.0,
        help="Tiempo de cooldown en segundos para evitar registrar la misma patente repetidamente.",
    )
    parser.add_argument(
        "--camera-id",
        type=str,
        default="cam-acceso-1",
        help="ID de la cámara para registrar en la base de datos.",
    )
    parser.add_argument(
        "--event-type",
        type=str,
        default="entrada",
        choices=["entrada", "salida"],
        help="Tipo de evento (entrada o salida).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Mostrar ventana de visualización en tiempo real.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Desactivar el guardado real de datos en Supabase.",
    )
    args = parser.parse_args()

    # Cargar configuración
    cfg = load_config("config.yaml")
    if args.no_persist:
        cfg.supabase.enabled = False

    print("=" * 60)
    print("Iniciando Pipeline de Inferencia Continua...")
    print(f"Origen de datos: {args.source}")
    print(f"Filtro Cooldown: {args.cooldown} segundos")
    print(f"Supabase habilitado: {cfg.supabase.enabled}")
    print("=" * 60)

    # Cargar pipeline
    pipeline = VisionOCRPipeline(cfg)
    
    # Registro de patentes procesadas para el filtro de cooldown
    # Estructura: {patente: timestamp_ultima_deteccion}
    last_detections: dict[str, float] = {}

    source_path = Path(args.source)
    is_video = source_path.is_file() and source_path.suffix.lower() in {
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
    }

    if is_video:
        print(f"Procesando video: {source_path.name}")
        cap = cv2.VideoCapture(str(source_path))
        if not cap.isOpened():
            print("Error: No se pudo abrir el archivo de video.")
            return

        frame_count = 0
        # Procesar 1 de cada 10 frames para optimizar la velocidad en video
        frame_interval = 10 

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                if frame_count % frame_interval != 0:
                    continue

                # Procesar frame
                start_time = time.perf_counter()
                
                # YOLO Detections + OCR
                detections = sorted(pipeline.detector.detect(frame), key=lambda d: d.confidence, reverse=True)
                results = []
                
                if detections:
                    # Usar la detección de máxima confianza
                    det = detections[0]
                    crop = frame[max(det.y1, 0) : max(det.y2, 0), max(det.x1, 0) : max(det.x2, 0)]
                    from src.vision_ocr_pipeline.postprocess import preprocess_plate_crop, best_plate_from_ocr
                    ocr_input = preprocess_plate_crop(crop) if crop.size else crop
                    ocr_text = pipeline.ocr.read_text(ocr_input) if crop.size else []
                    plate_text, plate_conf = best_plate_from_ocr(ocr_text)
                    
                    from src.vision_ocr_pipeline.pipeline import DetectionResult
                    if plate_text:
                        results.append(
                            DetectionResult(
                                detection=det,
                                ocr=ocr_text,
                                plate_text=plate_text,
                                plate_confidence=plate_conf,
                            )
                        )

                # Si no detectó nada, usar fallback regional
                if not results:
                    fallback = pipeline._detect_plate_via_ocr_regions(frame)
                    if fallback:
                        results.append(fallback)

                elapsed = time.perf_counter() - start_time

                # Procesar lecturas
                if results and results[0].plate_text:
                    res = results[0]
                    plate = res.plate_text.strip().upper()
                    now = time.time()
                    
                    # Comprobar cooldown
                    last_time = last_detections.get(plate, 0.0)
                    if now - last_time > args.cooldown:
                        last_detections[plate] = now
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ DETECTADA: [ {plate} ] (Inferencia: {elapsed:.3f}s)")
                        
                        # Persistir
                        if cfg.supabase.enabled:
                            print(f"  Persistiendo patente {plate} en Supabase...")
                            persist_summary = pipeline.persist_results(
                                results=[res],
                                event_type=args.event_type,
                                camera_id=args.camera_id,
                                image_origin=f"video_{source_path.name}_frame_{frame_count}",
                            )
                            if persist_summary.saved_events:
                                print(f"  ✅ Guardado exitoso. Acceso ID: {persist_summary.saved_events[0].access_id}")
                            if persist_summary.errors:
                                print(f"  ❌ Error: {persist_summary.errors[0]}")
                    else:
                        # Ignorar por cooldown activo
                        pass

                # Visualización
                if args.show:
                    display_frame = frame.copy()
                    if results and results[0].plate_text:
                        res = results[0]
                        d = res.detection
                        cv2.rectangle(display_frame, (d.x1, d.y1), (d.x2, d.y2), (0, 255, 0), 2)
                        cv2.putText(
                            display_frame,
                            f"{res.plate_text} ({res.plate_confidence:.2%})",
                            (d.x1, max(d.y1 - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                    
                    # Redimensionar para mostrar más compacto
                    h, w = display_frame.shape[:2]
                    resized = cv2.resize(display_frame, (w // 2, h // 2))
                    cv2.imshow("Monitoreo de Acceso Vehicular - UBB", resized)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    else:
        # Flujo de imágenes en un directorio
        print(f"Procesando carpeta de imágenes: {source_path}")
        valid_exts = {".jpg", ".jpeg", ".png"}
        images = [p for p in source_path.iterdir() if p.suffix.lower() in valid_exts]
        images = sorted(images, key=lambda x: x.name)

        if not images:
            print("No se encontraron imágenes válidas.")
            return

        print(f"Total imágenes a simular: {len(images)}")
        print("Presione Ctrl+C en cualquier momento para detener la simulación.")
        print("-" * 60)

        try:
            for img_path in images:
                start_time = time.perf_counter()
                image, results = pipeline.process_image(img_path)
                elapsed = time.perf_counter() - start_time

                if results and results[0].plate_text:
                    res = results[0]
                    plate = res.plate_text.strip().upper()
                    now = time.time()

                    # Cooldown check
                    last_time = last_detections.get(plate, 0.0)
                    if now - last_time > args.cooldown:
                        last_detections[plate] = now
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ DETECTADA: [ {plate} ] ({img_path.name})")
                        print(f"  Tiempo Inferencia: {elapsed:.3f}s")
                        
                        # Persistir
                        if cfg.supabase.enabled:
                            print(f"  Persistiendo en Supabase...")
                            persist_summary = pipeline.persist_results(
                                results=[res],
                                event_type=args.event_type,
                                camera_id=args.camera_id,
                                image_origin=img_path.name,
                            )
                            if persist_summary.saved_events:
                                print(f"  ✅ Guardado exitoso. Acceso ID: {persist_summary.saved_events[0].access_id}")
                            if persist_summary.errors:
                                print(f"  ❌ Error: {persist_summary.errors[0]}")
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ↻ Ignorada por Cooldown: [ {plate} ]")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Sin placas detectadas ({img_path.name})")

                # Visualización
                if args.show:
                    display_frame = image.copy()
                    if results and results[0].plate_text:
                        res = results[0]
                        d = res.detection
                        cv2.rectangle(display_frame, (d.x1, d.y1), (d.x2, d.y2), (0, 255, 0), 2)
                        cv2.putText(
                            display_frame,
                            f"{res.plate_text}",
                            (d.x1, max(d.y1 - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 255, 0),
                            2,
                        )
                    h, w = display_frame.shape[:2]
                    resized = cv2.resize(display_frame, (w // 2, h // 2))
                    cv2.imshow("Monitoreo de Acceso Vehicular - UBB", resized)
                    if cv2.waitKey(int(args.delay * 1000)) & 0xFF == ord("q"):
                        break
                else:
                    time.sleep(args.delay)

        except KeyboardInterrupt:
            print("\nSimulación interrumpida por el usuario.")
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
