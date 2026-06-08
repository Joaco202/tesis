from __future__ import annotations

import argparse
import sys
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy  # Evita OverflowError al inicializar float128 en Windows importándolo antes que OpenCV
import cv2

# Agregar carpeta base al PATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.vision_ocr_pipeline.config import load_config
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline, DetectionResult
from src.vision_ocr_pipeline.postprocess import STRICT_NEW_PLATE, OLD_PLATE


class SharedState:
    def __init__(self):
        self.running = True
        self.producer_done = False
        # Buffer para el hilo WORKER (se consume: el worker lo pone en None al leerlo)
        self.inference_frame = None
        # Buffer para el DISPLAY (nunca se borra, solo el grabber lo sobreescribe).
        # El display SIEMPRE tiene el frame más reciente de la cámara → 30 FPS garantizados.
        self.display_frame = None
        self.last_bbox = None            # Último bounding box: (x1, y1, x2, y2) o None
        self.plate_overlay = None        # (texto, confianza, elapsed) del último acierto
        self.lock = threading.Lock()


def grabber_thread_func(state: SharedState, is_video: bool, is_camera: bool, source_val, delay: float, limit: int | None = None):
    """Hilo Productor: Captura imágenes desde cámara, video o directorio de forma continua."""
    try:
        if is_camera or is_video:
            if is_camera:
                # Usar CAP_DSHOW en Windows para inicio rápido de webcam
                cap = cv2.VideoCapture(source_val, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(source_val)
            else:
                cap = cv2.VideoCapture(str(source_val))
                
            if not cap.isOpened():
                print(f"Error: No se pudo abrir el origen de captura: {source_val}")
                return
                
            frame_interval = 10 if is_video else 1  # Sin saltarse frames en webcam
            frame_count = 0
            
            try:
                while state.running:
                    ret, frame = cap.read()
                    if not ret:
                        if is_video:
                            break
                        else:
                            time.sleep(0.1)
                            continue
                    frame_count += 1
                    if frame_count % frame_interval != 0:
                        continue
                    
                    frame_copy = frame.copy()
                    with state.lock:
                        # display_frame: siempre el más reciente, NUNCA se pone en None
                        state.display_frame = frame_copy
                        # inference_frame: solo se actualiza si el worker ya consumió el anterior
                        # (evita que el grabber sature al worker con frames que no puede procesar)
                        if state.inference_frame is None:
                            state.inference_frame = frame_copy
                    if is_video:
                        time.sleep(0.01)
            finally:
                cap.release()
        else:
            # Directorio de imágenes
            source_path = Path(source_val)
            valid_exts = {".jpg", ".jpeg", ".png"}
            all_images = [p for p in source_path.iterdir() if p.suffix.lower() in valid_exts]
            
            # Priorizar imágenes de WhatsApp si existen
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
                        state.display_frame = frame.copy()
                        state.inference_frame = (frame.copy(), img_path.name)
                img_idx += 1
                time.sleep(delay)
    finally:
        with state.lock:
            state.producer_done = True


def worker_thread_func(pipeline: VisionOCRPipeline, state: SharedState, args, last_detections: dict[str, float]):
    """Hilo Consumidor: Procesa frames usando el pipeline y escribe a Supabase.
    
    Estrategia de rendimiento:
    - YOLO corre en CADA frame (~7ms, GPU, sin GIL significativo) → bbox fluido en display
    - OCR corre cada OCR_INTERVAL segundos máximo → evita que PaddleOCR bloquee el GIL y congele el display
    """
    # Intervalo mínimo entre llamadas al OCR (segundos).
    # Con 0.5s: el OCR puede correr hasta 2 veces/segundo, pero YOLO siempre corre.
    OCR_INTERVAL = 0.5
    last_ocr_time = 0.0  # Timestamp de la última vez que se ejecutó el OCR

    while True:
        frame = None
        img_origin = "continuous_inference"
        
        with state.lock:
            if state.inference_frame is not None:
                if isinstance(state.inference_frame, tuple):
                    frame, img_origin = state.inference_frame
                else:
                    frame = state.inference_frame
                state.inference_frame = None
            elif state.producer_done or not state.running:
                break
                
        if frame is None:
            time.sleep(0.02)
            continue
            
        # ── Decidir si correr OCR en este frame ──
        now_t = time.time()
        run_ocr = (now_t - last_ocr_time) >= OCR_INTERVAL

        # Inferencia (YOLO siempre; OCR según throttle; sin fallback pesado de escaneo completo por CPU)
        start_time = time.perf_counter()
        results = pipeline.process_frame(frame, run_ocr=run_ocr, run_fallback=False)
        elapsed = time.perf_counter() - start_time

        if run_ocr:
            last_ocr_time = time.time()

        plate_found = None
        bbox_found = None
        
        if results:
            res = results[0]
            d = res.detection
            bbox_found = (d.x1, d.y1, d.x2, d.y2)

            if res.plate_text:
                plate = res.plate_text.strip().upper()

                # ── Validación de formato estricto (antes de persistir) ──
                # Solo se guardan en DB placas que coincidan exactamente con
                # los patrones oficiales chilenos: LLLL+DD (nuevo) o LL+DDDD (antiguo)
                is_valid_format = bool(STRICT_NEW_PLATE.match(plate) or OLD_PLATE.match(plate))

                if not is_valid_format:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ Lectura descartada (formato inválido): [ {plate} ]")
                else:
                    plate_found = (plate, res.plate_confidence, elapsed)
                    
                    # Procesar persistencia si pasa el cooldown
                    last_time = last_detections.get(plate, 0.0)
                    if now_t - last_time > args.cooldown:
                        last_detections[plate] = now_t
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ DETECTADA: [ {plate} ] (OCR: {elapsed:.3f}s)")
                        
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

            elif run_ocr:
                # Solo loguear "sin patente" cuando realmente corrió el OCR
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Sin patente detectada (OCR: {elapsed:.3f}s) - {img_origin}")
                
        with state.lock:
            if plate_found:
                state.plate_overlay = plate_found
                state.last_bbox = bbox_found
            elif bbox_found:
                # Actualizar bbox aunque no haya patente (muestra el cuadro verde del YOLO)
                state.last_bbox = bbox_found
            else:
                state.last_bbox = None



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de inferencia continua asíncrona para detección de patentes en video o flujo de imágenes."
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Ruta a un archivo de video (.mp4, .avi), carpeta con imágenes, o índice de cámara (ej. 0).",
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
    
    is_camera = args.source.isdigit()
    is_video = False
    source_val = None
    
    if is_camera:
        source_val = int(args.source)
    else:
        source_path = Path(args.source)
        source_val = source_path
        is_video = source_path.is_file() and source_path.suffix.lower() in {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
        }
    
    state = SharedState()
    last_detections: dict[str, float] = {}
    last_cleanup: float = 0.0  # Timestamp de la última limpieza de imágenes antiguas
    
    # Crear e iniciar hilos
    grabber_thread = threading.Thread(
        target=grabber_thread_func,
        args=(state, is_video, is_camera, source_val, args.delay, args.limit),
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
    
    # Hilo de Sincronización de Cola Offline (si Supabase está habilitado)
    if pipeline.offline_queue:
        def sync_loop():
            # Esperar 2 segundos antes de intentar sincronizar al inicio
            time.sleep(2.0)
            while state.running:
                try:
                    pipeline.offline_queue.sync_queue()
                except Exception as sync_err:
                    print(f"⚠️ Error en hilo de sincronización offline: {sync_err}")
                
                # Dormir 20 segundos en pequeños intervalos para apagado rápido
                for _ in range(20):
                    if not state.running:
                        break
                    time.sleep(1.0)
        
        sync_thread = threading.Thread(
            target=sync_loop,
            daemon=True
        )
        sync_thread.start()
    
    # Hilo Principal: GUI Event Loop (OpenCV imshow)
    # Siempre muestra el frame CRUDO más reciente a ~30 FPS.
    # Las anotaciones (bbox + banner) se dibujan ENCIMA del frame crudo — sin mezcla, sin ghosting.
    _display_fps_t = time.perf_counter()
    _display_fps_count = 0
    _display_fps_label = "-- FPS"
    try:
        while state.running:
            # Verificar condición de salida
            _producer_done_and_empty = False
            with state.lock:
                if state.producer_done and state.inference_frame is None:
                    _producer_done_and_empty = True
            if _producer_done_and_empty and not worker_thread.is_alive():
                state.running = False
                break

            frame_to_show = None
            overlay_info = None
            bbox = None

            with state.lock:
                # display_frame SIEMPRE tiene el frame más reciente de la cámara
                # (el grabber lo actualiza continuamente, nunca lo borra)
                if state.display_frame is not None:
                    frame_to_show = state.display_frame.copy()
                overlay_info = state.plate_overlay
                bbox = state.last_bbox

            if frame_to_show is not None:
                # ── Dibujar bounding box directamente sobre el frame crudo (sin blend) ──
                if bbox is not None:
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(frame_to_show, (x1, y1), (x2, y2), (0, 255, 80), 2)

                # ── Banner superior con última patente detectada ──
                if overlay_info:
                    plate_txt, plate_conf, inf_elapsed = overlay_info
                    banner_h = 44
                    cv2.rectangle(frame_to_show, (0, 0), (frame_to_show.shape[1], banner_h), (15, 15, 15), -1)
                    cv2.putText(
                        frame_to_show,
                        f"  ULTIMA: {plate_txt}  ({plate_conf:.1%})  |  INF: {inf_elapsed:.2f}s",
                        (4, 29),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.68,
                        (0, 235, 0),
                        2,
                    )

                # ── FPS counter (esquina inf-derecha) ──
                _display_fps_count += 1
                now_t = time.perf_counter()
                if now_t - _display_fps_t >= 1.0:
                    _display_fps_label = f"{_display_fps_count} FPS"
                    _display_fps_count = 0
                    _display_fps_t = now_t
                h_f, w_f = frame_to_show.shape[:2]
                cv2.putText(
                    frame_to_show, _display_fps_label,
                    (w_f - 80, h_f - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 80), 1,
                )

                if args.show:
                    h, w = frame_to_show.shape[:2]
                    resized = cv2.resize(frame_to_show, (w // 2, h // 2))
                    cv2.imshow("Monitoreo de Acceso Vehicular - UBB", resized)
                    # 33ms = 30 FPS máx en el display, completamente independiente de la IA
                    if cv2.waitKey(33) & 0xFF == ord("q"):
                        state.running = False
                        break
                else:
                    time.sleep(0.03)
            else:
                time.sleep(0.01)

            # Limpieza de imágenes antiguas: ejecutar una vez cada 24 horas
            if cfg.supabase.enabled and (time.time() - last_cleanup) > 86400:
                last_cleanup = time.time()
                try:
                    eliminadas = pipeline.repository.limpiar_imagenes_antiguas(dias=30)
                    if eliminadas:
                        print(f"[Mantenimiento] 🗑️  {eliminadas} imagen(es) antiguas eliminadas del Storage.")
                except Exception as err:
                    print(f"[Mantenimiento] ⚠️  Error en limpieza de imágenes: {err}")
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
