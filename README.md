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

```bash
python -m vision_ocr_pipeline --help
python -m vision_ocr_pipeline run --source ruta/a/imagen.jpg --config config.example.yaml --output outputs
python -m vision_ocr_pipeline run --source ruta/a/imagen.jpg --event-type entrada --camera-id cam-acceso-1 --output outputs
```

Si activas Supabase en config o variables de entorno, el flujo queda:

1. Detecta y hace OCR.
2. Si hay patente, guarda evento en BD.
3. Genera JSON + imagen anotada.

Tambien puedes usar el script instalado:

```bash
vision-ocr run --source ruta/a/imagen.jpg --config config.example.yaml --output outputs
```

## Salidas

- JSON de evento (camara, tipo entrada/salida, timestamp, detecciones, OCR y patente normalizada) en `outputs/<nombre>.json`
- Imagen anotada en `outputs/<nombre>_annotated.jpg`
- Si Supabase esta activo, el JSON incluye bloque `database` con resultados de persistencia.

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
