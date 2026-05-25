# Vision OCR Pipeline (CPU only)

Proyecto base en Python para deteccion de objetos con YOLOv8, recorte por bounding boxes con OpenCV y lectura OCR con PaddleOCR.

## Requisitos

- Python 3.12
- CPU-only (pensado para servidor modesto)

Nota: el entorno recomendado y validado para OCR completo es Python 3.12, con `paddleocr==2.8.1` y `paddlepaddle==2.6.2`.

## Instalacion

### Windows PowerShell

```powershell
.\setup.ps1
```

### Instalacion manual

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecucion

El proyecto ahora usa un CLI unificado que consolida 18+ scripts en subcomandos organizados:

```bash
python -m vision_ocr_pipeline --help
```

### Generar o procesar datasets

```bash
# Generar 1000 imagenes sinteticas de patentes
python -m vision_ocr_pipeline generate synthetic --count 1000 --output data/synthetic

# Descargar CCPD2019 (necesita ~40 GB)
python -m vision_ocr_pipeline generate download

# Procesar anotaciones CCPD2019 a formato estandar
python -m vision_ocr_pipeline generate process --input data/CCPD2019

# Convertir anotaciones COCO a formato YOLO
python -m vision_ocr_pipeline generate convert --input data

# Crear splits train/val/test y data.yaml para YOLO
python -m vision_ocr_pipeline generate split
```

### Entrenar modelos

```bash
# Entrenamiento rapido (2 epochs) para validar pipeline
python -m vision_ocr_pipeline train short

# Entrenamiento rapido (6 epochs) para mejora baseline
python -m vision_ocr_pipeline train quick

# Entrenamiento completo en CPU (lento pero portable)
python -m vision_ocr_pipeline train full-cpu

# Entrenamiento completo en GPU (si hay GPU disponible)
python -m vision_ocr_pipeline train full-gpu
```

### Inferencia y evaluacion

```bash
# Procesar imagen o directorio con pipeline standard
python -m vision_ocr_pipeline run infer --source inputs/raw --output outputs

# Usar fallback OCR cuando YOLO no detecta (opcion 5)
python -m vision_ocr_pipeline run option5 --source inputs/raw/5.jpg

# Comparar modelo base (yolov8n.pt) vs mejor modelo entrenado
python -m vision_ocr_pipeline run compare --source inputs/raw

# Con debug output
python -m vision_ocr_pipeline run infer --source inputs/raw --debug
```

### Verificacion del sistema

```bash
# Verificar soporte CUDA y GPU
python -m vision_ocr_pipeline verify --check cuda
```

### CLI Legacy (single-image inference)

Para procesamiento de una imagen con configuracion avanzada:

```bash
python -m vision_ocr_pipeline run --source ruta/a/imagen.jpg --config config.example.yaml --output outputs
python -m vision_ocr_pipeline run --source ruta/a/imagen.jpg --event-type entrada --camera-id camara-1 --output outputs
```

O instalado como comando:

```bash
vision-ocr run --source ruta/a/imagen.jpg --config config.example.yaml --output outputs
```

## Salidas

- JSON de evento (camara, tipo entrada/salida, timestamp, detecciones, OCR y patente normalizada) en `outputs/<nombre>.json`
- Imagen anotada en `outputs/<nombre>_annotated.jpg`
- Si Supabase esta activo, el JSON incluye bloque `database` con resultados de persistencia.

## Scripts consolidados bajo CLI

El proyecto ha consolidado 18+ scripts individuales bajo un CLI unificado. Si necesitas referencia de funcionalidad antigua:

| Script antiguo | Comando CLI actual |
|---|---|
| `generate_synthetic_plates.py` | `python -m vision_ocr_pipeline generate synthetic` |
| `download_ccpd.py` | `python -m vision_ocr_pipeline generate download` |
| `process_ccpd.py` | `python -m vision_ocr_pipeline generate process` |
| `batch_convert_coco.py` | `python -m vision_ocr_pipeline generate convert` |
| `create_dataset_yaml_and_splits.py` | `python -m vision_ocr_pipeline generate split` |
| `train_yolo_short.py` | `python -m vision_ocr_pipeline train short` |
| `train_yolo_quick_6epochs.py` | `python -m vision_ocr_pipeline train quick` |
| `train_yolo_full_cpu_optimized.py` | `python -m vision_ocr_pipeline train full-cpu` |
| `train_yolo_full_gpu.py` | `python -m vision_ocr_pipeline train full-gpu` |
| `run_on_inputs.py` | `python -m vision_ocr_pipeline run infer --source inputs` |
| `run_on_inputs_raw.py` | `python -m vision_ocr_pipeline run infer --source inputs/raw` |
| `try_option5_image5.py` | `python -m vision_ocr_pipeline run option5 --source inputs/raw` |
| `compare_models.py` | `python -m vision_ocr_pipeline run compare` |
| `verify_cuda.py` | `python -m vision_ocr_pipeline verify --check cuda` |

Scripts utilitarios que se mantienen separados:
- `test_detector_integration.py`: prueba de integracion del detector
- `debug_inspect_image5.py`: herramienta de debug para imagen especifica

## Supabase (opcional)

Puedes configurar Supabase en `config.example.yaml` o por variables de entorno:

- `SUPABASE_ENABLED=true`
- `SUPABASE_URL=https://TU-PROYECTO.supabase.co`
- `SUPABASE_SERVICE_KEY=...`
- `SUPABASE_TIMEOUT_SECONDS=10`
- `SUPABASE_VEHICLES_TABLE=vehiculos`
- `SUPABASE_ACCESSES_TABLE=accesos`

La integracion agrega una capa en dos modulos:

- `src/vision_ocr_pipeline/db.py`: cliente HTTP simple para PostgREST (Supabase).
- `src/vision_ocr_pipeline/repository.py`: reglas de persistencia (`guardar_vehiculo_si_no_existe`, `registrar_entrada`, `registrar_salida`).

Desde el pipeline/CLI se invoca `guardar_acceso(...)` justo despues del OCR.

## Estructura

- `src/vision_ocr_pipeline/config.py`: configuracion tipada (Pydantic)
- `src/vision_ocr_pipeline/db.py`: cliente DB para Supabase REST
- `src/vision_ocr_pipeline/detector.py`: wrapper YOLOv8
- `src/vision_ocr_pipeline/ocr_engine.py`: wrapper PaddleOCR (CPU)
- `src/vision_ocr_pipeline/pipeline.py`: flujo de inferencia y persistencia
- `src/vision_ocr_pipeline/repository.py`: repositorio de accesos/vehiculos
- `src/vision_ocr_pipeline/cli.py`: interfaz CLI con Typer

## Proximo ajuste con tu PDF

Cambios aplicados segun tesis:

- Flujo orientado a reconocimiento de patentes.
- Preprocesamiento OpenCV sobre el recorte antes de OCR.
- Registro de evento con `event_type` (entrada/salida), `camera_id` y `timestamp_utc`.
- Salida JSON estructurada para enviar al backend.

Pendiente para siguiente iteracion:

- Conectar streaming de camara y reglas online para decidir automaticamente entrada/salida.
