from __future__ import annotations

import argparse
import sys
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy  # Evita OverflowError al inicializar float128 en Windows importándolo antes que OpenCV
import cv2
import queue

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
                if isinstance(source_val, int):
                    # Usar CAP_DSHOW en Windows para inicio rápido de webcam local
                    cap = cv2.VideoCapture(source_val, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(source_val)
                else:
                    # Cámara IP (http, https, rtsp)
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


def ocr_subprocess_worker(config_path, input_queue, output_queue):
    """Proceso independiente para ejecutar PaddleOCR sin bloquear el GIL del proceso principal."""
    import sys
    import time
    from pathlib import Path
    
    # Asegurar que el PATH incluya el backend
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
        
    import numpy as np
    from src.vision_ocr_pipeline.config import load_config
    from src.vision_ocr_pipeline.ocr_engine import PaddleOCREngine
    from src.vision_ocr_pipeline.postprocess import preprocess_plate_crop, best_plate_from_ocr
    
    # Cargar configuración
    cfg = load_config(config_path)
    
    # Forzar CPU en este proceso secundario para máxima estabilidad
    ocr_engine = PaddleOCREngine(cfg.ocr, use_gpu=False)
    
    print("[OCR Process] Inicializado correctamente en CPU.")
    
    while True:
        try:
            item = input_queue.get()
        except (KeyboardInterrupt, SystemExit, Exception):
            break
            
        if item is None:
            # Señal de apagado
            break
            
        crop, det_info, frame, img_origin, now_t = item
        try:
            h, w = crop.shape[:2]
            aspect_ratio = w / h if h > 0 else 0
            
            start_t = time.perf_counter()
            if 0 < aspect_ratio < 2.0:
                mid_y = h // 2
                top_half = crop[0:mid_y, :]
                bottom_half = crop[mid_y:h, :]
                
                top_prep = preprocess_plate_crop(top_half)
                bottom_prep = preprocess_plate_crop(bottom_half)
                
                ocr_top = ocr_engine.read_text(top_prep)
                ocr_bottom = ocr_engine.read_text(bottom_prep)
                ocr_text = ocr_top + ocr_bottom
            else:
                ocr_input = preprocess_plate_crop(crop)
                ocr_text = ocr_engine.read_text(ocr_input)
                
            plate_text, plate_conf = best_plate_from_ocr(ocr_text, cfg.ocr)
            elapsed = time.perf_counter() - start_t
            
            output_queue.put((plate_text, plate_conf, ocr_text, det_info, frame, img_origin, elapsed, now_t))
        except Exception as err:
            print(f"[OCR Process] Error procesando crop: {err}")
            output_queue.put((None, 0.0, [], det_info, frame, img_origin, 0.0, now_t))


def worker_thread_func(pipeline: VisionOCRPipeline, state: SharedState, args, last_detections: dict[str, float], input_queue, output_queue):
    """Hilo Consumidor: Procesa frames usando YOLO y delega el OCR al proceso secundario."""
    OCR_INTERVAL = 0.5
    last_ocr_time = 0.0
    ocr_in_progress = False

    while True:
        # 1. Comprobar si el proceso OCR secundario tiene resultados
        try:
            while True:
                res_ocr = output_queue.get_nowait()
                ocr_in_progress = False
                
                plate_text, plate_conf, ocr_text, det_info, frame_stored, img_origin, elapsed, now_t = res_ocr
                
                if plate_text:
                    plate = plate_text.strip().upper()
                    
                    # Validación de formato estricto chileno
                    is_valid_format = bool(STRICT_NEW_PLATE.match(plate) or OLD_PLATE.match(plate))
                    
                    if not is_valid_format:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Lectura descartada (formato inválido): [ {plate} ]")
                    else:
                        last_time = last_detections.get(plate, 0.0)
                        if now_t - last_time > args.cooldown:
                            last_detections[plate] = now_t
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] DETECTADA: [ {plate} ] (OCR: {elapsed:.3f}s)")
                            
                            with state.lock:
                                state.plate_overlay = (plate, plate_conf, elapsed)
                            
                            if pipeline.cfg.supabase.enabled:
                                print(f"  Persistiendo patente {plate} en Supabase...")
                                try:
                                    from src.vision_ocr_pipeline.pipeline import DetectionResult
                                    from src.vision_ocr_pipeline.detector import Detection
                                    
                                    d = Detection(
                                        x1=det_info["x1"], y1=det_info["y1"],
                                        x2=det_info["x2"], y2=det_info["y2"],
                                        confidence=det_info["confidence"],
                                        cls_id=det_info["cls_id"],
                                        cls_name=det_info["cls_name"]
                                    )
                                    res_obj = DetectionResult(
                                        detection=d,
                                        ocr=ocr_text,
                                        plate_text=plate_text,
                                        plate_confidence=plate_conf
                                    )
                                    persist_summary = pipeline.persist_results(
                                        results=[res_obj],
                                        event_type=args.event_type,
                                        camera_id=args.camera_id,
                                        image_origin=img_origin,
                                        image=frame_stored,
                                    )
                                    if persist_summary.saved_events:
                                        print(f"  Guardado exitoso. Acceso ID: {persist_summary.saved_events[0].access_id}")
                                    if persist_summary.errors:
                                        print(f"  Error de persistencia: {persist_summary.errors[0]}")
                                except Exception as err:
                                    print(f"  Error inesperado persistiendo en Supabase: {err}")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sin patente detectada (OCR: {elapsed:.3f}s) - {img_origin}")
        except queue.Empty:
            pass

        # 2. Obtener el siguiente frame para YOLO
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
            
        # 3. Inferencia de YOLO (GPU, muy rápida, no bloquea el display)
        # run_ocr=False para no hacer OCR síncrono
        results = pipeline.process_frame(frame, run_ocr=False, run_fallback=False)
        
        bbox_found = None
        if results:
            res = results[0]
            d = res.detection
            bbox_found = (d.x1, d.y1, d.x2, d.y2)
            
            with state.lock:
                state.last_bbox = bbox_found
                
            # Delegar OCR al proceso secundario si está libre y fuera de cooldown
            now_t = time.time()
            if not ocr_in_progress and (now_t - last_ocr_time >= OCR_INTERVAL):
                crop = frame[max(d.y1, 0) : max(d.y2, 0), max(d.x1, 0) : max(d.x2, 0)]
                if crop.size:
                    ocr_in_progress = True
                    last_ocr_time = now_t
                    det_info = {
                        "x1": d.x1, "y1": d.y1, "x2": d.x2, "y2": d.y2,
                        "confidence": d.confidence, "cls_id": d.cls_id, "cls_name": d.cls_name
                    }
                    input_queue.put((crop, det_info, frame.copy(), img_origin, now_t))
        else:
            with state.lock:
                state.last_bbox = None


def main() -> None:
    import multiprocessing
    multiprocessing.freeze_support()

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
        default=3.0,
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

    # Cargar configuración
    _cfg_path = Path(__file__).resolve().parents[1] / "config.yaml"
    cfg = load_config(str(_cfg_path))
    if args.no_persist:
        cfg.supabase.enabled = False

    # Cargar pipeline
    pipeline = VisionOCRPipeline(cfg)
    
    is_ip_camera = args.source.startswith("http://") or args.source.startswith("https://") or args.source.startswith("rtsp://")
    is_camera = args.source.isdigit() or is_ip_camera
    is_video = False
    source_val = None
    
    if args.source.isdigit():
        source_val = int(args.source)
    elif is_ip_camera:
        source_val = args.source
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
    last_cleanup: float = 0.0

    # Inicializar colas y proceso OCR
    input_queue = multiprocessing.Queue()
    output_queue = multiprocessing.Queue()

    ocr_process = multiprocessing.Process(
        target=ocr_subprocess_worker,
        args=(str(_cfg_path), input_queue, output_queue),
        daemon=True
    )
    ocr_process.start()
    
    # Crear e iniciar hilos
    grabber_thread = threading.Thread(
        target=grabber_thread_func,
        args=(state, is_video, is_camera, source_val, args.delay, args.limit),
        daemon=True
    )
    worker_thread = threading.Thread(
        target=worker_thread_func,
        args=(pipeline, state, args, last_detections, input_queue, output_queue),
        daemon=True
    )
    
    print("=" * 60)
    print("Iniciando Inferencia Continua Asíncrona (Multiprocesamiento)...")
    print(f"Origen de datos: {args.source}")
    print(f"Filtro Cooldown: {args.cooldown} segundos")
    print(f"Supabase habilitado: {cfg.supabase.enabled}")
    print("=" * 60)
    
    grabber_thread.start()
    worker_thread.start()
    
    # Hilo de Sincronización de Cola Offline (si Supabase está habilitado)
    if pipeline.offline_queue:
        def sync_loop():
            time.sleep(2.0)
            while state.running:
                try:
                    pipeline.offline_queue.sync_queue()
                except Exception as sync_err:
                    print(f"Error en hilo de sincronización offline: {sync_err}")
                
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
    _display_fps_t = time.perf_counter()
    _display_fps_count = 0
    _display_fps_label = "-- FPS"
    try:
        while state.running:
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
                if state.display_frame is not None:
                    frame_to_show = state.display_frame.copy()
                overlay_info = state.plate_overlay
                bbox = state.last_bbox

            if frame_to_show is not None:
                if bbox is not None:
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(frame_to_show, (x1, y1), (x2, y2), (0, 255, 80), 2)

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

                _display_fps_count += 1
                now_t = time.perf_counter()
                if now_t - _display_fps_t >= 1.0:
                    _display_fps_label = f"{_display_fps_count} FPS"
                    _display_fps_count = 0
                    _display_fps_t = now_t
                h_f, w_f = frame_to_show.shape[:2]
                (text_w, text_h), baseline = cv2.getTextSize(_display_fps_label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                margin = 4
                cv2.rectangle(
                    frame_to_show,
                    (w_f - 80 - margin, h_f - 10 - text_h - margin),
                    (w_f - 80 + text_w + margin, h_f - 10 + baseline + margin),
                    (15, 15, 15),
                    -1
                )
                cv2.putText(
                    frame_to_show, _display_fps_label,
                    (w_f - 80, h_f - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 80), 1,
                )

                if args.show:
                    h, w = frame_to_show.shape[:2]
                    resized = cv2.resize(frame_to_show, (w // 2, h // 2))
                    cv2.imshow("Monitoreo de Acceso Vehicular - UBB", resized)
                    if cv2.waitKey(33) & 0xFF == ord("q"):
                        state.running = False
                        break
                else:
                    time.sleep(0.03)
            else:
                time.sleep(0.01)

            if cfg.supabase.enabled and (time.time() - last_cleanup) > 86400:
                last_cleanup = time.time()
                try:
                    eliminadas = pipeline.repository.limpiar_imagenes_antiguas(dias=30)
                    if eliminadas:
                        print(f"[Mantenimiento] {eliminadas} imagen(es) antiguas eliminadas del Storage.")
                except Exception as err:
                    print(f"[Mantenimiento] Error en limpieza de imágenes: {err}")
    except KeyboardInterrupt:
        print("\nSimulación interrumpida por el usuario.")
    finally:
        state.running = False
        try:
            input_queue.put(None)
        except Exception:
            pass
        cv2.destroyAllWindows()
        grabber_thread.join(timeout=1.0)
        worker_thread.join(timeout=1.0)
        if ocr_process.is_alive():
            ocr_process.terminate()
            ocr_process.join(timeout=1.0)
        print("Sistema de inferencia continua detenido de forma segura.")


if __name__ == "__main__":
    main()
