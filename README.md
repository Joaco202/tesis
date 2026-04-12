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

Tambien puedes usar el script instalado:

```bash
vision-ocr run --source ruta/a/imagen.jpg --config config.example.yaml --output outputs
```

## Salidas

- JSON de evento (camara, tipo entrada/salida, timestamp, detecciones, OCR y patente normalizada) en `outputs/<nombre>.json`
- Imagen anotada en `outputs/<nombre>_annotated.jpg`

## Estructura

- `src/vision_ocr_pipeline/config.py`: configuracion tipada (Pydantic)
- `src/vision_ocr_pipeline/detector.py`: wrapper YOLOv8
- `src/vision_ocr_pipeline/ocr_engine.py`: wrapper PaddleOCR (CPU)
- `src/vision_ocr_pipeline/pipeline.py`: flujo de inferencia y persistencia
- `src/vision_ocr_pipeline/cli.py`: interfaz CLI con Typer

## Proximo ajuste con tu PDF

Cambios aplicados segun tesis:

- Flujo orientado a reconocimiento de patentes.
- Preprocesamiento OpenCV sobre el recorte antes de OCR.
- Registro de evento con `event_type` (entrada/salida), `camera_id` y `timestamp_utc`.
- Salida JSON estructurada para enviar al backend.

Pendiente para siguiente iteracion:

- Conectar streaming de camara y reglas online para decidir automaticamente entrada/salida.
- Integracion directa con base de datos/backend de eventos.
