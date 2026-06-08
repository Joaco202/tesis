from __future__ import annotations

import argparse
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
import cv2

# Agregar carpeta base al PATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline, DetectionResult


class SharedState:
    def __init__(self):
        self.running = True
        self.producer_done = False
        self.latest_frame = None         # Frame crudo para inferencia
        self.display_frame = None        # Frame anotado para mostrar en GUI
        self.plate_overlay = None        # Info de patente detectada para overlay en pantalla: (texto, conf, timestamp)
        self.lock = threading.Lock()


def grabber_thread_func(state: SharedState, is_video: bool, source_path: Path, delay: float, limit: int | None = None):
    """Hilo Productor: Captura imágenes desde video o directorio de forma continua."""
    try:
        if is_video:
            cap = cv2.VideoCapture(str(source_path))
            if not cap.isOpened():
                print("Error: No se pudo abrir el archivo de video.")
                return
                
            frame_interval = 10  # Procesar 1 de cada 10 frames de video para mantener fluidez
            frame_count = 0
            
            try:
                while state.running:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_count += 1
                    if frame_count % frame_interval != 0:
                        continue
                        
                    with state.lock:
                        state.latest_frame = frame.copy()
                    # Pequeño sleep para no saturar I/O
                    time.sleep(0.01)
            finally:
                cap.release()
        else:
            # Directorio de imágenes
            valid_exts = {".jpg", ".jpeg", ".png"}
            all_images = [p for p in source_path.iterdir() if p.suffix.lower() in valid_exts]
            
            # Priorizar imágenes de WhatsApp si existen (como en test_real_inputs.py)
            whatsapp_images = [p for p in all_images if "whatsapp" in p.name.lower()]
            if whatsapp_images:
                images = sorted(whatsapp_images, key=lambda x: x.name)
            else:
                images = sorted(all_images, key=lambda x: x.name)
            
            if not images:
                print("No se encontraron imágenes válidas en el directorio.")
                return
                
            if limit is not None:
                images = images[:limit]
                
            img_idx = 0
            while state.running and img_idx < len(images):
                img_path = images[img_idx]
                frame = cv2.imread(str(img_path))
                if frame is not None:
                    with state.lock:
                        state.latest_frame = (frame.copy(), img_path.name)
                img_idx += 1
                # Esperar el delay especificado para simular el paso continuo de vehículos
                time.sleep(delay)
    finally:
        with state.lock:
            state.producer_done = True


def worker_thread_func(pipeline: VisionOCRPipeline, state: SharedState, args, last_detections: dict[str, float]):
    """Hilo Consumidor: Procesa frames usando el pipeline y escribe a Supabase."""
    while True:
        frame = None
        img_origin = "continuous_inference"
        
        with state.lock:
            if state.latest_frame is not None:
                if isinstance(state.latest_frame, tuple):
                    frame, img_origin = state.latest_frame
                else:
                    frame = state.latest_frame
                state.latest_frame = None  # Consumir el frame
            elif state.producer_done or not state.running:
                break
                
        if frame is None:
            time.sleep(0.05)
            continue
            
        # Inferencia
        start_time = time.perf_counter()
        results = pipeline.process_frame(frame)
        elapsed = time.perf_counter() - start_time
        
        # Anotar el frame para mostrar en la interfaz
        annotated = frame.copy()
        plate_found = None
        
        if results and results[0].plate_text:
            res = results[0]
            d = res.detection
            plate = res.plate_text.strip().upper()
            plate_found = (plate, res.plate_confidence, elapsed)
            
            # Dibujar bounding box
            cv2.rectangle(annotated, (d.x1, d.y1), (d.x2, d.y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"{plate} ({res.plate_confidence:.2%})",
                (d.x1, max(d.y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            
            # Procesar persistencia si pasa el cooldown
            now = time.time()
            last_time = last_detections.get(plate, 0.0)
            if now - last_time > args.cooldown:
                last_detections[plate] = now
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ DETECTADA: [ {plate} ] (Inferencia: {elapsed:.3f}s)")
                
                # Persistencia asíncrona
                if pipeline.cfg.supabase.enabled:
                    print(f"  Persistiendo patente {plate} en Supabase...")
                    try:
                        persist_summary = pipeline.persist_results(
                            results=[res],
                            event_type=args.event_type,
                            camera_id=args.camera_id,
                            image_origin=img_origin,
                            image=frame,
                        )
                        if persist_summary.saved_events:
                            print(f"  ✅ Guardado exitoso. Acceso ID: {persist_summary.saved_events[0].access_id}")
                        if persist_summary.errors:
                            print(f"  ❌ Error de persistencia: {persist_summary.errors[0]}")
                    except Exception as err:
                        print(f"  ❌ Error inesperado persistiendo en Supabase: {err}")
            else:
                # Ignorada por cooldown activo
                pass
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Sin patente detectada (Inferencia: {elapsed:.3f}s) - {img_origin}")
                
        with state.lock:
            state.display_frame = annotated
            if plate_found:
                state.plate_overlay = plate_found


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de inferencia continua asíncrona para detección de patentes en video o flujo de imágenes."
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
        default=5.0,
        help="Tiempo de cooldown en segundos para evitar registrar la misma patente repetidamente.",
    )
    parser.add_argument(
        "--camera-id",
        type=str,
        default="camara-1",
        help="ID de la cámara para registrar en la base de datos.",
    )
    parser.add_argument(
        "--event-type",
        type=str,
        default="auto",
        choices=["entrada", "salida", "auto"],
        help="Tipo de evento (entrada, salida o auto).",
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
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Límite de imágenes a procesar.",
    )
    args = parser.parse_args()

    # Cargar configuración (ruta absoluta relativa al script para soportar cualquier cwd)
    _cfg_path = Path(__file__).resolve().parents[1] / "config.yaml"
    cfg = load_config(str(_cfg_path))
    if args.no_persist:
        cfg.supabase.enabled = False

    # Cargar pipeline
    pipeline = VisionOCRPipeline(cfg)
    
    source_path = Path(args.source)
    is_video = source_path.is_file() and source_path.suffix.lower() in {
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
    }
    
    state = SharedState()
    last_detections: dict[str, float] = {}
    
    # Crear e iniciar hilos
    grabber_thread = threading.Thread(
        target=grabber_thread_func,
        args=(state, is_video, source_path, args.delay, args.limit),
        daemon=True
    )
    worker_thread = threading.Thread(
        target=worker_thread_func,
        args=(pipeline, state, args, last_detections),
        daemon=True
    )
    
    print("=" * 60)
    print("Iniciando Inferencia Continua Asíncrona (Multihilo)...")
    print(f"Origen de datos: {args.source}")
    print(f"Filtro Cooldown: {args.cooldown} segundos")
    print(f"Supabase habilitado: {cfg.supabase.enabled}")
    print("=" * 60)
    
    grabber_thread.start()
    worker_thread.start()
    
    # Hilo Principal: GUI Event Loop (OpenCV imshow)
    try:
        while state.running:
            # Verificar condición de salida: productor terminado, sin frames pendientes
            # y worker ya inactivo. Se chequea is_alive() fuera del lock para no retenerlo.
            _producer_done_and_empty = False
            with state.lock:
                if state.producer_done and state.latest_frame is None:
                    _producer_done_and_empty = True
            if _producer_done_and_empty and not worker_thread.is_alive():
                state.running = False
                break
            frame_to_show = None
            overlay_info = None
            
            with state.lock:
                if state.display_frame is not None:
                    frame_to_show = state.display_frame.copy()
                elif state.latest_frame is not None:
                    # Si no hay frame procesado aún, mostrar el crudo para mantener la fluidez
                    if isinstance(state.latest_frame, tuple):
                        frame_to_show = state.latest_frame[0].copy()
                    else:
                        frame_to_show = state.latest_frame.copy()
                overlay_info = state.plate_overlay
            
            if frame_to_show is not None:
                # Dibujar banner superior con la última lectura de patente si está disponible
                if overlay_info:
                    plate_txt, plate_conf, elapsed = overlay_info
                    cv2.rectangle(frame_to_show, (0, 0), (frame_to_show.shape[1], 40), (30, 30, 30), -1)
                    cv2.putText(
                        frame_to_show,
                        f"ULTIMA LECTURA: {plate_txt} ({plate_conf:.1%}) | INF: {elapsed:.2f}s",
                        (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )
                
                # Mostrar en ventana
                if args.show:
                    h, w = frame_to_show.shape[:2]
                    resized = cv2.resize(frame_to_show, (w // 2, h // 2))
                    cv2.imshow("Monitoreo de Acceso Vehicular - UBB (Asincrono)", resized)
                    # waitKey con tasa pequeña para capturar teclas rápidamente
                    if cv2.waitKey(30) & 0xFF == ord("q"):
                        state.running = False
                        break
                else:
                    # Si no se muestra la ventana, dormir brevemente
                    time.sleep(0.03)
            else:
                time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nSimulación interrumpida por el usuario.")
    finally:
        state.running = False
        cv2.destroyAllWindows()
        # Esperar que los hilos terminen con un timeout corto
        grabber_thread.join(timeout=1.0)
        worker_thread.join(timeout=1.0)
        print("Sistema de inferencia continua detenido de forma segura.")


if __name__ == "__main__":
    main()
