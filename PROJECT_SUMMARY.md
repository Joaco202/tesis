# Vision + OCR Pipeline para Detección de Placas - Documentación Completa

**Fecha de generación:** Mayo 3, 2026 · **Última actualización:** 24 de mayo de 2026  
**Proyecto:** tesis (Detección de placas vehiculares con visión por computadora y reconocimiento óptico de caracteres)  
**Estado:** ✅ GPU habilitada — PyTorch 2.11+cu128 · PaddleOCR 3.5.0 · PaddlePaddle-GPU 3.0.0 · Python 3.12.10

---

## 1. Descripción General del Proyecto

Este proyecto implementa un pipeline de **dos etapas** para detección y reconocimiento de placas vehiculares:

1. **Etapa 1: Detección (YOLO)** - Localiza placas en imágenes usando YOLOv8n
2. **Etapa 2: OCR (PaddleOCR)** - Extrae y reconoce texto de las regiones detectadas

**Objetivo:** Crear un sistema CPU-only, modular y compatible con servidores modestos, con salida CLI y JSON.

---

## 2. Ambiente y Configuración

### Especificaciones del Sistema
- **SO:** Windows 11 Pro
- **CPU:** AMD Ryzen 7 9800X3D (8 núcleos, 16 threads)
- **GPU:** NVIDIA GeForce RTX 5070 (12 GB VRAM, arquitectura Blackwell sm_120)
  - ✅ Soportada con PyTorch 2.11+cu128 y PaddlePaddle-GPU 3.0.0
- **RAM:** 32 GB
- **Python:** 3.12.10 en virtualenv (`.venv`)

### Dependencias Instaladas (actualizadas mayo 2026)

```
ultralytics==8.4.46              # YOLOv8 — detector y entrenador
torch==2.11.0+cu128              # PyTorch — GPU (CUDA 12.8, Blackwell)
torchvision==0.22.0+cu128        # Visión por computadora — GPU
paddlepaddle-gpu==3.0.0          # PaddlePaddle — GPU (cu126)
paddleocr==3.5.0                 # PaddleOCR — compatible con Paddle 3.x
nvidia-cuda-nvrtc-cu12==12.9.86  # NVRTC para resolución de DLLs CUDA
```

**Ubicación:** todos instalados en `.venv\Lib\site-packages\`  
**Índice especial PyTorch:** `https://download.pytorch.org/whl/cu128`  
**Índice especial Paddle:** `https://www.paddlepaddle.org.cn/packages/stable/cu126/`

### Configuración del Proyecto
- **Archivo Principal:** `config.yaml`
  - Define umbrales de confianza, rutas de modelos, y parámetros de OCR
  - Cargado automáticamente por CLI si no se especifica `--config`

---

## 3. Estructura del Proyecto

```
tesis/
├── backend/                        # Directorio principal del backend (IA y base de datos)
│   ├── config.yaml                 # Configuración global
│   ├── pyproject.toml              # Metadata del proyecto Python
│   ├── requirements.txt            # Dependencias de producción
│   ├── requirements-dev.txt        # Dependencias de desarrollo
│   ├── yolov8n.pt                  # Modelo preentrenado YOLOv8 Nano
│   ├── yolo26n.pt                  # Pesos adicionales
│   ├── .venv/                      # Entorno virtual de Python
│   │
│   ├── src/vision_ocr_pipeline/    # Código fuente principal
│   │   ├── __init__.py
│   │   ├── __main__.py             # Entry point del paquete
│   │   ├── pipeline.py             # Pipeline de dos etapas
│   │   ├── postprocess.py          # Postprocesamiento de OCR
│   │   ├── repository.py           # Persistencia Supabase
│   │   └── db.py                   # Inicialización de BD
│   │
│   ├── scripts/                    # Scripts de utilidad
│   │   ├── archived/               # Scripts legacy e históricos
│   │   └── debug_inspect_image5.py
│   │
│   ├── data/plates/                # Dataset de placas
│   │   ├── images/                 # Imágenes sintéticas y CCPD
│   │   ├── labels/                 # Archivos de labels en formato YOLO
│   │   └── data.yaml               # Config de YOLO (rutas corregidas)
│   │
│   ├── runs/detect/                # Outputs de entrenamiento de YOLOv8
│   │   └── runs/detect/train-gpu-rtx5070/ # Pesos entrenados finales (50 épocas)
│   │
│   └── sql/schema.sql              # Schema de base de datos PostgreSQL
│
├── frontend/                       # Aplicación web interactiva (React + Vite)
│   ├── src/                        # Componentes, vistas e integración Supabase
│   ├── package.json                # Configuración npm
│   └── .env                        # Credenciales de Supabase Client
│
├── README.md                       # Documentación inicial del proyecto completo
├── PROJECT_SUMMARY.md              # Documentación técnica completa (este archivo)
└── APT_JoaquinContreras.pdf        # Documento de tesis
```

---

## 4. Workflow Completo: Paso a Paso

### Fase 1: Preparación del Ambiente (Completado)

#### 1.1 Verificación de Python
```bash
python --version
# Output: Python 3.12.10
```

#### 1.2 Creación de Virtualenv
```bash
python -m venv .venv
.venv\Scripts\activate

#### 1.3 Instalación de Dependencias
```bash
pip install -r requirements.txt
```

**Resultado:** Ambiente listo con todas las dependencias de ML/visión instaladas.

---

### Fase 2: Generación de Datos Sintéticos (Completado)

**Objetivo:** Crear 1,000 imágenes de placas sintéticas sin escrituras en BD.

**Ejecución:**
```python
# Script generador de datos sintéticos
# Características:
# - Resolucion: 640x480 píxeles
# - Placas aleatorias simulando formato chileno
# - Variación: colores, ángulos, iluminación
# - Sin integración Supabase (no se escriben en BD)

# Output:
# data/plates/images/synthetic/  # 1,000 imágenes .jpg
```

**Métricas:**
- Imágenes generadas: 1,000
- Tamaño total: ~150 MB
- Tiempo de generación: ~2-3 minutos

---

### Fase 3: Descarga del Dataset Público CCPD (Completado)

**Objetivo:** Obtener dataset de placas vehiculares reales.

**Dataset Seleccionado:** CCPD2019 (Chinese City Parking Dataset)
- **Cantidad:** 310,482 imágenes
- **Formato:** Placas chinas (4 caracteres)
- **Similitud con placas chilenas:** Estructura comparable (rectangular, números/letras)
- **Tamaño del archivo:** 12 GB (comprimido .tar.xz)

**Descarga:**
```bash
# Descarga manual desde Google Drive
# URL: https://drive.google.com/file/d/1...
# Razón: gdown falló por "Too many users downloading this file"
# Solución: Descarga directa desde navegador web
```

**Ubicación:**
```
C:\Users\joako\Downloads\CCPD2019.tar.xz
```

---

### Fase 4: Procesamiento del Dataset (Completado)

**Script:** `scripts/process_ccpd.py`

```python
import tarfile
import os
from pathlib import Path

# Función principal: extract_archive()
# - Descomprime CCPD2019.tar.xz (12 GB)
# - Genera carpeta temporal con 310,482 imágenes
# - Validación: cuenta de archivos por directorio

# Ejecución:
# .venv\Scripts\python scripts/process_ccpd.py

# Resultado:
# temp_ccpd_extract/  # Estructura jerárquica de CCPD
#   │   ├── 0001/
#   │   ├── 0002/
#   │   └── ... 100+ carpetas
#   └── (310,482 imágenes .jpg)

# Tiempo total: ~15-20 minutos (I/O bound en SSD)
```

**Script:** `scripts/process_ccpd.py` (continuación)

```python
def parse_ccpd_filename(filename):
    """
    Parsea metadata de placas desde nombre de archivo CCPD.
    
    Formato de filename CCPD:
    02-100_113_104_51_174_118_206_156-37_70_394_374_386_402-0_0_29_23_432_0_0_32_0_0-122-37.jpg
    
    Componentes:
    - Bounding box: x1_y1_x2_y2 (pixel coordinates)
    - Metadata de placa: ángulos, puntos de calibración, etc.
    
    Salida:
    - bbox normalizado (YOLO format): cx, cy, w, h en rango [0, 1]
    # Extrae coordenadas absolutas
    # Convierte a YOLO normalized: (cx/width, cy/height, w/width, h/height)
    """
    
    YOLO format:
    class_id cx_norm cy_norm w_norm h_norm
    
    Ejemplo:
    Entrada: bbox=(100, 50, 300, 150), img_size=(640, 480)
    Salida: "0 0.3125 0.208333 0.3125 0.208333"
    """
    pass

# Ejecución:
# Procesa 310,482 imágenes

# Validación:
```

- Tiempo total: ~30-45 minutos
---

### Fase 5: Generación de Splits Train/Val/Test (Completado)

#### 5.1 Script: `create_full_splits.py`

```python
import glob
import random
from pathlib import Path

def create_splits(image_dir, train_ratio=0.7, val_ratio=0.15):
    Genera splits train/val/test para dataset YOLO.
    
    Lógica:
    1. Recorre todas las imágenes
    2. Agrupa por path absoluto
    3. Baraja aleatoriamente (random.seed para reproducibilidad)
    4. Divide en 70% train, 15% val, 15% test
    5. Escribe rutas absolutas en .txt files
    """
    images = glob.glob(os.path.join(image_dir, "*.jpg"))
    val_count = int(len(images) * 0.15)
    
    
    # Escribe en archivos .txt
```

#### 5.2 Splits Resultantes

```
Total imágenes: 310,482

Train: 217,337 imágenes (70%)
  → data/plates/train.txt (217,337 líneas de paths)

Val:   46,572 imágenes (15%)
  → data/plates/val.txt (46,572 líneas de paths)

Test:  46,573 imágenes (15%)
  → data/plates/test.txt (46,573 líneas de paths)
```

**Archivos generados:**
```
data/plates/train.txt
data/plates/val.txt
data/plates/test.txt
```

Cada archivo contiene rutas absolutas a imágenes:
```
C:\Users\joako\Documents\GitHub\tesis\data\plates\images\ccpd\0001\001-95_190_180_238_253_265_274_285-94_155_287_262_282_288-0_0_25_25_420_0_0_30_0_0-117-33.jpg
C:\Users\joako\Documents\GitHub\tesis\data\plates\images\ccpd\0001\002-97_192_181_236_254_264_275_284-95_156_286_263_283_287-0_0_25_25_422_0_0_31_0_0-122-33.jpg
...
```

---

### Fase 6: Entrenamiento de Prueba - Smoke Test (Completado)

#### 6.1 Propósito
Validar el pipeline de entrenamiento con dataset reducido (5k imágenes) en tiempo corto (2 épocas).

#### 6.2 Script: `train_yolo_short.py`

```python
from ultralytics import YOLO

# Configuración
model = YOLO("yolov8n.pt")  # Cargar modelo nano preentrenado

results = model.train(
    data="data/plates/data.yaml",
    epochs=2,
    imgsz=1280,
    batch=32,
    device=0,  # GPU 0 (no disponible en este sistema)
    workers=4,
    cache=False
)

# Parámetros:
# - epochs: 2 (prueba rápida)
# - imgsz: 1280x1280 (detección de placas pequeñas)
# - batch: 32 (tamaño de lote)
# - workers: 4 (threads de carga de datos)
```

#### 6.3 Ejecución
```bash
.venv\Scripts\python scripts\train_yolo_short.py
```

#### 6.4 Resultados del Smoke Test

**Configuración Final:**
- Dataset: 5,000 imágenes (muestra del CCPD completo)
- Épocas: 2
- Batch size: 32
- Dispositivo: CPU (fallback desde GPU)

**Métricas Finales (Validación):**
| Métrica | Valor |
|---------|-------|
| Precisión (P) | 0.076 |
| Recall (R) | 0.232 |
| mAP@0.5 | 0.0544 |
| mAP@0.5-0.95 | 0.0182 |

**Tiempo de entrenamiento:** ~45 minutos en CPU

**Modelo Guardado:**
```
runs/detect/train-3/weights/best.pt     (6.3 MB)
runs/detect/train-3/weights/last.pt     (6.3 MB)
```

**Observaciones:**
- Métricas bajas esperables para smoke test (pocas épocas, datos limitados)
- Modelo converge sin errores
- Validación: Pipeline de entrenamiento funcional ✓

---

### Fase 7: Migración GPU — RTX 5070 Blackwell ✅ (Completado mayo 2026)

#### 7.1 Problema Original
**Hardware:** NVIDIA GeForce RTX 5070 (Blackwell, sm_120)  
**PyTorch anterior:** 2.5.1+cu121 → `torch.cuda.is_available()` devolvía `False`  
**Causa:** La arquitectura Blackwell (sm_120) no estaba soportada en PyTorch 2.5.x

#### 7.2 Solución Aplicada — PyTorch 2.11+cu128
```bash
# Actualización a PyTorch 2.11 con soporte CUDA 12.8 (Blackwell)
pip install torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cu128

# Verificación:
import torch
print(torch.__version__)          # 2.11.0+cu128
print(torch.cuda.is_available())  # True
print(torch.cuda.get_device_name(0))  # NVIDIA GeForce RTX 5070
```

#### 7.3 Actualización de PaddlePaddle a GPU
```bash
# PaddlePaddle GPU 3.0.0 (canal cu126 — funciona con CUDA 12.8)
pip install paddlepaddle-gpu==3.0.0 \
  -i https://www.paddlepaddle.org.cn/packages/stable/cu126/

# PaddleOCR 3.5.0 — compatible con PaddlePaddle 3.x
# (versión anterior 2.8.1 era incompatible con Paddle 3.x)
pip install "paddleocr>=3.0.0" --upgrade
```

#### 7.4 Fix de DLLs CUDA en Windows (WinError 127)
En Windows, PaddlePaddle 3.0.0 falla con `OSError: [WinError 127]` al cargar
`cudnn_cnn64_9.dll` porque el cargador de DLLs busca dependencias antes de que
estén en memoria. Solución: patch en `paddle/__init__.py` que:

1. Registra todos los dirs de `nvidia/*/bin` con `os.add_dll_directory()`
2. Agrega esos dirs al `os.environ['PATH']` del proceso
3. Precarga las DLLs en el **orden correcto de dependencias** con `ctypes.WinDLL`:
   `cudart → cublas → cudnn_base → cudnn_ops → cudnn_adv → ... → cudnn_cnn`
4. Ignora `WinError 126/127` en el bloque de carga de Paddle (ya precargadas)

```python
# Patch aplicado en:
# .venv/Lib/site-packages/paddle/__init__.py  (líneas 36-83)
# — se ejecuta antes de 'from .base import core'
```

**Paquete adicional necesario:**
```bash
pip install nvidia-cuda-nvrtc-cu12  # Dependencia de cadena cudnn
```

#### 7.5 Archivos modificados para soporte GPU

| Archivo | Cambio |
|---------|--------|
| `requirements.txt` | torch→2.11+cu128, paddlepaddle-gpu, paddleocr≥3.0 |
| `setup.ps1` | Instala desde índices cu128/cu126 |
| `src/vision_ocr_pipeline/config.py` | `device` default: `"cpu"` → `"cuda"` |
| `src/vision_ocr_pipeline/ocr_engine.py` | Detección automática GPU para PaddleOCR |
| `src/vision_ocr_pipeline/pipeline.py` | Propaga `device` al detector YOLO y al OCR |
| `src/vision_ocr_pipeline/__init__.py` | `add_dll_directory` patch (complementario) |
| `.venv/.../paddle/__init__.py` | Patch DLL preload + error 127 bypass |
| `env_gpu.ps1` | Script de activación con PATH de nvidia DLLs |

---

### Fase 8: Entrenamiento Principal - 6 Épocas en Dataset Completo (EN PROGRESO)

#### 8.1 Justificación de 6 Épocas
| Configuración | Épocas | Tiempo Est. | Métrica |
|---------------|--------|------------|---------|
| Full GPU (futuro) | 50 | ~2-3 horas | Óptimo |
| CPU actual | 50 | ~25-30 horas | Impracticable |
| **CPU actual** | **6** | **~4 horas** | **Aceptable** |

#### 8.2 Script: `train_yolo_quick_6epochs.py`

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

results = model.train(
    data="data/plates/data.yaml",
    epochs=6,
    imgsz=1280,
    batch=8,              # CPU-optimized
    device='cpu',
    workers=4,
    cache=True,           # Caché dataset en RAM
    cos_lr=True,          # Cosine annealing learning rate
    optimizer='AdamW'     # Optimizador estable para CPU
)

# Dataset:
# - Train: 217,337 imágenes
# - Val:   46,572 imágenes
# - Total: 263,909 imágenes

# Fases de entrenamiento:
# 1. Dataset scanning: ~1 hora (primera ejecución con caché)
# 2. Epoch 1-6: ~3 horas total (~30 min/epoch)
# 3. Validation: ~10-15 min entre épocas
```

#### 8.3 Ejecución
```bash
.venv\Scripts\python scripts/train_yolo_quick_6epochs.py 2>&1 | tee train_quick.txt
```

**Terminal ID:** `12b26bce-4812-4de1-940e-958a0d9e7552`  
**Estado Actual:** EN PROGRESO (fase de escaneo de dataset)  
**Progreso:** ~55% de imágenes escaneadas  
**Tiempo Elapsed:** ~30-40 minutos  
**Tiempo Restante Estimado:** ~3-4 horas hasta completar

#### 8.4 Logs y Monitoreo
```bash
# Log capturado en tiempo real:
tail -f train_quick.txt

# Ejemplo de output esperado:
# Epoch 1/6: 100%|████████████| 27167/27167 [18:45<00:00, 24.15it/s]
# val: Scanning C:\...\ccpd.cache (46572 images)
# Epoch 1 results: loss_cls=1.234, loss_obj=0.456, loss_box=0.789
```

#### 8.5 Salida Esperada
```
runs/detect/train-quick-6epochs/
├── weights/
│   ├── best.pt      # Mejor modelo (menor loss validación)
│   └── last.pt      # Último modelo (última época)
├── results.csv      # Métricas por época
├── confusion_matrix.png
├── results.png      # Gráficos de loss/accuracy
└── events.out.tfevents...  # Logs TensorBoard
```

---

### Fase 9: Entrenamiento Final en GPU - 50 Épocas (Completado Mayo 2026)

**Objetivo:** Obtener un detector de placas de alta precisión aprovechando la potencia de la GPU RTX 5070 (arquitectura Blackwell).

**Configuración:**
- **Modelo:** YOLOv8 Nano (3.01M de parámetros)
- **Épocas:** 50
- **Batch size:** 32 (GPU optimizado)
- **Dispositivo:** GPU (NVIDIA GeForce RTX 5070 con CUDA 12.8)
- **Pesos generados:** `backend/runs/detect/runs/detect/train-gpu-rtx5070/weights/best.pt`

**Métricas Finales en Época 50:**
- **Precisión (P):** `0.999`
- **Recall (R):** `0.999`
- **mAP@0.5:** `0.994`
- **mAP@0.5-0.95:** `0.762`
- **Box Loss (Val):** `0.912`
- **Cls Loss (Val):** `0.279`

---

### Fase 10: Desarrollo del Frontend e Integración Real con Supabase (Completado Mayo 2026)

**Objetivo:** Desarrollar un panel de control web en tiempo real para guardias y directores TI, utilizando la base de datos Supabase como núcleo de persistencia.

**Stack Utilizado:**
- **Base:** Vite + React.js (JavaScript)
- **Estilos:** CSS Puro con estética Glassmorphism, adaptada a la paleta institucional de la UBB (Azul/Naranja), soporte para modo oscuro automático.
- **KPIs y Gráficos:** Implementación interactiva de gráficos de línea y área con Recharts.
- **Iconografía:** Lucide React.

**Características Clave:**
1. **Autenticación e Identidad:** [AuthContext.jsx](file:///c:/Users/joako/Documents/GitHub/tesis/frontend/src/context/AuthContext.jsx) implementa resolución de roles cruzando la tabla `usuarios` con la tabla `roles` en Supabase. Se restringe el acceso de forma segura según el rol (`guardia`, `encargado` o `admin`).
2. **Dashboard de Guardia:** [GuardDashboard.jsx](file:///c:/Users/joako/Documents/GitHub/tesis/frontend/src/pages/GuardDashboard.jsx) ofrece una vista viva de Entradas y Salidas hoy, la capacidad actual de Aula Magna, y una tabla de flujo de vehículos con suscripción web sockets a la tabla `accesos` para actualizaciones instantáneas.
3. **Panel de Encargado (Manager):** [ManagerDashboard.jsx](file:///c:/Users/joako/Documents/GitHub/tesis/frontend/src/pages/ManagerDashboard.jsx) calcula de forma dinámica en el cliente la ocupación pico del día, el número de vehículos únicos, la estadía promedio de los automóviles, y renderiza gráficos de ocupación por horas.
4. **Gestión de Incidencias:** Se diseñó un panel interactivo que permite modificar el estado de las incidencias en tiempo real con un clic (`abierta` ➔ `en_revision` ➔ `cerrada`). Cuenta con un modal para registrar nuevas incidencias y aplica una lógica de auto-registro (`upsert`) sobre la patente en la tabla `vehiculos` para evitar fallas por restricciones de clave foránea.

---

### Fase 11: Reorganización del Repositorio en Subcarpetas (Completado Mayo 2026)

**Objetivo:** Reestructurar el repositorio en directorios `/backend` y `/frontend` independientes para una mejor separación de responsabilidades y modularidad.

**Acciones Tomadas:**
1. **Migración de Archivos:** Traslado completo del código del pipeline de visión por computadora, entorno virtual de Python (`.venv`), scripts históricos, logs de ejecución, base de datos SQL y datasets (`data/plates`) a la subcarpeta `/backend`.
2. **Corrección del Entorno Virtual (.venv):** Modificación de los scripts de activación (`activate.bat`, `activate`) y del archivo `pyvenv.cfg` para apuntar correctamente al nuevo directorio base `/backend/.venv`. Re-enlace del pipeline usando `pip install -e .` desde el directorio `/backend`.
3. **Parchado de Rutas en Dataset (YOLO):** Corrección masiva de rutas absolutas de Windows dentro de [data.yaml](file:///c:/Users/joako/Documents/GitHub/tesis/backend/data/plates/data.yaml), y los archivos de splits (`train.txt`, `val.txt`, `test.txt`), inyectando el prefijo `/backend/` para evitar que la biblioteca Ultralytics pierda la referencia al dataset al entrenar.
4. **Ajuste del CLI y verify_cuda:** Modificación de [cli.py](file:///c:/Users/joako/Documents/GitHub/tesis/backend/src/vision_ocr_pipeline/cli.py) para redirigir imports hacia `scripts.archived` y envoltura del script de comprobación CUDA [verify_cuda.py](file:///c:/Users/joako/Documents/GitHub/tesis/backend/scripts/archived/verify_cuda.py) dentro de una función `main()` para compatibilidad con la CLI.

---

## 5. Modificaciones de Código Realizadas

### 5.1 `src/vision_ocr_pipeline/detector.py` - Auto-Detección de Modelos

**Cambio:** Agregada función `_find_best_model()` que busca automáticamente el modelo entrenado más reciente.

```python
def _find_best_model(self):
    """
    Busca automáticamente el mejor modelo entrenado en runs/detect/train-*/weights/best.pt
    Si no encuentra modelo entrenado, fallback a yolov8n.pt preentrenado.
    
    Lógica:
    1. Scan de directorio: runs/detect/train-*/weights/best.pt
    2. Ordenar por fecha de modificación (más reciente = mejor)
    3. Cargar el modelo más reciente encontrado
    4. Si no existe, usar yolov8n.pt
    
    Beneficio: Seamless model upgrade sin cambios de código
    """
    import os
    from pathlib import Path
    import glob
    
    runs_dir = Path("runs/detect")
    best_models = sorted(
        glob.glob(str(runs_dir / "train-*/weights/best.pt")),
        key=os.path.getmtime,
        reverse=True
    )
    
    if best_models:
        return best_models[0]  # Más reciente
    else:
        return "yolov8n.pt"   # Fallback
```

**Impacto:**
- ✅ No requiere modificación de código CLI
- ✅ Seamless transition entre modelos

---

### 5.2 `test_detector_integration.py` - Script de Validación


```python
from pathlib import Path
from src.vision_ocr_pipeline.config import AppConfig
from src.vision_ocr_pipeline.pipeline import VisionOCRPipeline
import cv2

# Cargar configuración (auto-detecta modelo entrenado)
config = AppConfig()

# Inicializar pipeline
pipeline = VisionOCRPipeline(config)

# Cargar imagen de prueba del dataset CCPD
test_image_path = Path("data/plates/images/ccpd/0001/001-*.jpg")
test_image = cv2.imread(str(test_image_path))

# Ejecutar pipeline
result = pipeline.process(test_image)

# Output esperado:
# {
#   "plate_text": "粤A12345",  # Texto reconocido
#   "confidence": 0.87,
#   "bounding_box": [100, 50, 300, 150],
#   "ocr_confidence": 0.92
# }

print(f"Placa detectada: {result.plate_text}")
print(f"Confianza: {result.confidence:.2%}")
```

**Ejecución (después del entrenamiento):**
```bash
.venv\Scripts\python test_detector_integration.py
```

---

## 6. Dataset: CCPD2019

### 6.1 Características

| Propiedad | Valor |
|-----------|-------|
| **Nombre** | Chinese City Parking Dataset 2019 |
| **Imágenes** | 310,482 |
| **Formato** | JPEG, variable resolution (~1024x720 típico) |
| **Placas** | Chinas (4 caracteres, azul/blanco) |
| **Anotaciones** | Integradas en nombre de archivo (bbox, orientación) |
| **Licencia** | Open source (investigación académica) |
| **Tamaño Total** | 12 GB comprimido, ~30 GB descomprimido |

### 6.2 Similitud con Placas Chilenas

| Aspecto | CCPD | Placas Chilenas |
|---------|------|-----------------|
| Forma | Rectangular | Rectangular ✓ |
| Tamaño | ~400x150 píxeles | Similar ✓ |
| Fondo | Blanco | Blanco ✓ |
| Texto | Caracteres CJK | Alfanuméricos |
| Variación iluminación | Alta | Similar ✓ |
| Ángulos captura | Variados (0-45°) | Similar ✓ |

**Conclusión:** CCPD es proxy razonable para entrenamiento transfer-learning.

---

## 7. Estructura del Pipeline

### 7.1 Arquitectura de Dos Etapas

```
┌──────────────────────────────────────────────────────────────┐
│                    ENTRADA: Imagen                           │
│                    (CV2 np.ndarray)                           │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │     ETAPA 1: YOLOv8 DETECTION         │
        │  (src/vision_ocr_pipeline/detector.py)│
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┴─────────────────────┐
        │                                         │
        ▼                                         ▼
   Detecciones                         ❌ Sin detecciones
   Ordenadas por                          Fallback: OCR
   confianza                              en imagen completa
        │
        ▼
  ┌─────────────────────────────────────┐
  │  SELECCIONAR: Mejor detección       │
  │  (máxima confianza)                 │
  └─────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────┐
  │  CROPEAR: Región ROI de placa       │
  │  (region of interest)               │
  └─────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────┐
  │     ETAPA 2: PaddleOCR                   │
  │  (src/vision_ocr_pipeline/ocr_engine.py) │
  └──────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────┐
  │   POSTPROCESAMIENTO:                 │
  │   - Validación de caracteres         │
  │   - Filtrado de candidatos           │
  │   - Seleccionar mejor resultado      │
  │  (src/vision_ocr_pipeline/postprocess.py)
  └──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│           SALIDA: DetectionResult            │
│   {                                          │
│     "plate_text": "PATENTE12345",           │
│     "confidence": 0.89,                      │
│     "bounding_box": [x, y, x2, y2],         │
│     "ocr_confidence": 0.95                   │
│   }                                          │
└──────────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────┐
  │   PERSISTENCIA OPCIONAL             │
  │   (Supabase, si > 0 detecciones)   │
  └─────────────────────────────────────┘
```

### 7.2 Flujo de Ejecución CLI

```bash
$ python -m vision_ocr_pipeline imagen.jpg --output output.json

# Paso 1: Cargar config
#   ├─ config.yaml (auto)
#   └─ Valores por defecto

# Paso 2: Inicializar modelos
#   ├─ YOLOv8: runs/detect/train-quick-6epochs/weights/best.pt
#   └─ OCR: PaddleOCR (descarga automático)

# Paso 3: Procesar imagen
#   ├─ Lectura: OpenCV imread()
#   ├─ Detección: YOLOv8 inference (~200-500ms)
#   ├─ OCR: PaddleOCR inference (~100-300ms)
#   └─ Postprocess: Validación y filtrado

# Paso 4: Salida
#   ├─ JSON: output.json
#   ├─ Imagen anotada: imagen_resultado.jpg
#   └─ Console: Summary

# Paso 5: Persistencia (opcional)
#   └─ Supabase: si está configurado y tiene detecciones
```

---

## 8. Interfaz CLI Unificada (Refactorización - Mayo 3, 2026)

### 8.0 Consolidación de Scripts

Se han consolidado **18+ scripts individuales** bajo un CLI unificado centralizado para simplificar el flujo de trabajo:

```
python -m vision_ocr_pipeline
├── generate   (5 subcomandos: dataset creation & processing)
├── train      (4 subcomandos: training with multiple profiles)
├── run        (4 subcomandos: inference & evaluation)
└── verify     (system checks & validation)
```

**Ventajas:**
- ✅ Interfaz consistente: mismo `--help` para todos
- ✅ Flujo más limpio: menos archivos en `scripts/`
- ✅ Mantenibilidad mejorada: cambios centralizados
- ✅ Documentación unificada: todos los comandos disponibles

**Scripts archivados:** `scripts/archived/` (17 scripts)

### 8.1 Comando: `generate` - Preparación de Datasets

```bash
# Generar 1,000 imágenes sintéticas
python -m vision_ocr_pipeline generate synthetic --count 1000 --output data/synthetic

# Descargar CCPD2019 (requiere ~40 GB)
python -m vision_ocr_pipeline generate download

# Procesar anotaciones CCPD2019 a formato estándar
python -m vision_ocr_pipeline generate process --input data/CCPD2019

# Convertir anotaciones COCO a formato YOLO
python -m vision_ocr_pipeline generate convert --input data

# Crear splits train/val/test y data.yaml para YOLO
python -m vision_ocr_pipeline generate split
```

**Scripts equivalentes archivados:**
- `generate_synthetic_plates.py` → `generate synthetic`
- `download_ccpd.py` → `generate download`
- `process_ccpd.py` → `generate process`
- `batch_convert_coco.py` → `generate convert`
- `create_dataset_yaml_and_splits.py` → `generate split`

### 8.2 Comando: `train` - Entrenamiento de Modelos

```bash
# Smoke test (2 épocas) - validación rápida
python -m vision_ocr_pipeline train short

# Quick training (6 épocas) - mejora baseline
python -m vision_ocr_pipeline train quick

# Full training en CPU (lento pero portable)
python -m vision_ocr_pipeline train full-cpu

# Full training en GPU (si está disponible)
python -m vision_ocr_pipeline train full-gpu
```

| Perfil | Épocas | Tiempo Est. | Uso |
|--------|--------|-----------|-----|
| short | 2 | ~30 min | Validación pipeline |
| quick | 6 | ~4 horas | Mejora rápida |
| full-cpu | 50+ | ~30+ horas | Producción (portabilidad) |
| full-gpu | 50+ | ~3-5 horas | Producción (futuro) |

**Scripts equivalentes archivados:**
- `train_yolo_short.py` → `train short`
- `train_yolo_quick_6epochs.py` → `train quick`
- `train_yolo_full_cpu_optimized.py` → `train full-cpu`
- `train_yolo_full_gpu.py` → `train full-gpu`

### 8.3 Comando: `run` - Inferencia y Evaluación

#### 8.3.1 Subcomando: `infer` - Pipeline estándar

```bash
# Procesar imagen o directorio
python -m vision_ocr_pipeline run infer --source inputs/raw --output outputs

# Con debug output
python -m vision_ocr_pipeline run infer --source inputs/raw --debug

# Con configuración personalizada
python -m vision_ocr_pipeline run infer --source inputs/raw --config custom.yaml
```

**Salida:**
```
outputs/
├── results_raw.json         # JSON con detecciones
└── annotated/
    ├── imagen1_annot.jpg    # Imagen anotada
    ├── imagen2_annot.jpg
    └── ...
```

#### 8.3.2 Subcomando: `option5` - Fallback OCR-Regions

Cuando YOLO no detecta, usa OCR en toda la imagen como fallback:

```bash
# Detectar placas con OCR fallback
python -m vision_ocr_pipeline run option5 --source inputs/raw/5.jpg

# En directorio (procesa todos)
python -m vision_ocr_pipeline run option5 --source inputs/raw
```

**Ejemplo: Recuperó placa `CRJC39` en imagen 5 (YOLO no detectó)**

#### 8.3.3 Subcomando: `compare` - Evaluación de Modelos

Compara base `yolov8n.pt` vs mejor modelo entrenado:

```bash
python -m vision_ocr_pipeline run compare --source inputs/raw
```

**Scripts equivalentes archivados:**
- `run_on_inputs.py` → `run infer --source inputs`
- `run_on_inputs_raw.py` → `run infer --source inputs/raw`
- `try_option5_image5.py` → `run option5 --source inputs/raw`
- `compare_models.py` → `run compare`

### 8.4 Comando: `verify` - Validación del Sistema

```bash
# Verificar soporte CUDA y GPU
python -m vision_ocr_pipeline verify --check cuda
```

**Scripts equivalentes archivados:**
- `verify_cuda.py` → `verify --check cuda`

### 8.5 CLI Legacy - Single-Image Inference

Para procesamiento avanzado de imagen única (configuración granular):

```bash
# Procesar imagen con config específica
python -m vision_ocr_pipeline run imagen.jpg --config config.example.yaml --output outputs

# Con event-type y camera-id (para persistencia)
python -m vision_ocr_pipeline run imagen.jpg --event-type entrada --camera-id cam-acceso-1 --output outputs

# O instalado como comando
vision-ocr run --source imagen.jpg --config config.example.yaml --output outputs

---

## 11. Troubleshooting y Soluciones Aplicadas

### Problema 1: Descarga CCPD con gdown fallaba
```
Error: "Too many users downloading this file"
Solución: Descarga manual desde navegador Google Drive
```

### Problema 2: Extracción 12GB tardaba mucho
```
Error: Terminal timeout, sin feedback
Solución: Monitoreo de carpeta con PowerShell, conteo de archivos
```

### Problema 3: RTX 5070 no soportada en PyTorch 2.5 ✅ Resuelto
```
Error: torch.cuda.is_available() → False (Blackwell sm_120 no soportado)
Solución: pip install torch==2.11+cu128 --index-url .../cu128
Resultado: GPU detectada, CUDA: True, GPU: NVIDIA GeForce RTX 5070
```

### Problema 4: Dataset scanning time muy largo
```
Error: ~1 hora para escanear 310k imágenes
Solución: Cache habilitado después del primer escaneo
```

### Problema 5: PaddleOCR 2.8.1 incompatible con Paddle 3.0 ✅ Resuelto
```
Error: RuntimeError / conflictos de API entre paddleocr 2.8.1 y paddlepaddle 3.0
Solución: pip install "paddleocr>=3.0.0" → instaló paddleocr 3.5.0
```

### Problema 6: WinError 127 al cargar cudnn_cnn64_9.dll ✅ Resuelto
```
Error: OSError: [WinError 127] Error loading "nvidia\cudnn\bin\cudnn_cnn64_9.dll"
Causa: Paddle carga DLLs en orden alfabético, sin cargar dependencias primero
Solución (3 pasos):
  1. pip install nvidia-cuda-nvrtc-cu12  (DLL faltante en cadena de deps)
  2. Patch en paddle/__init__.py — precargar DLLs en orden de dependencias
     con ctypes.WinDLL() antes de 'from .base import core'
  3. Patch en paddle/__init__.py — ignorar WinError 127 en los raise err
     del bloque Windows (DLLs ya en memoria por el paso 2)
```

### Problema 7: Bloqueo de archivos en Windows al mover el entorno virtual (.venv) ✅ Resuelto
```
Error: PermissionError: [WinError 5] Acceso denegado
Causa: No es posible reubicar la carpeta .venv mediante un script de Python si dicho script se ejecuta bajo el propio intérprete de ese entorno virtual (archivos dll y executables en uso).
Solución: Delegar el movimiento físico de la carpeta .venv a un proceso PowerShell independiente de la instancia activa de Python.
```

### Problema 8: UnicodeEncodeError imprimiendo en consolas Windows (CP1252) ✅ Resuelto
```
Error: UnicodeEncodeError: 'charmap' codec can't encode character '\u2717' in position X
Causa: La biblioteca Rich utiliza caracteres de formato Unicode (como "✗") para logs interactivos, lo cual causa errores al intentar imprimirlos en terminales Windows por defecto bajo codificación CP1252.
Solución: Forzar el uso del modo UTF-8 en el intérprete de Python mediante la bandera '-X utf8' (ej: python -X utf8 -m vision_ocr_pipeline).
```

### Problema 9: Falla de Clave Foránea en Base de Datos al Registrar Incidencias de Patentes Nuevas ✅ Resuelto
```
Error: insert or update on table "incidencias" violates foreign key constraint "incidencias_patente_fkey"
Causa: Al intentar reportar una incidencia para un vehículo cuya patente no existía previamente en la tabla "vehiculos", la base de datos rechazaba la operación por integridad referencial.
Solución: Modificar el flujo del frontend (y asegurar la lógica en el backend) implementando una inserción previa o autoguardado ("upsert") del vehículo utilizando la patente antes de persistir el registro de la incidencia.
```

### Problema 10: Formato de Salida en PaddleOCR 3.x ✅ Resuelto
```
Error: ValueError: not enough values to unpack al procesar OCR con el nuevo SDK de PaddleOCR 3.5.0
Causa: PaddleOCR 3.5.0 devuelve diccionarios con claves rec_texts, rec_scores, dt_polys en lugar de la estructura clásica de lista de listas.
Solución: Implementar el adaptador `normalize_ocr_output` en ocr_engine.py para normalizar dinámicamente cualquier formato de salida.
```

### Problema 11: Inestabilidades en GPU CUDA para PaddleOCR en Windows Blackwell ✅ Resuelto
```
Error: Predicciones vacías de texto al correr PaddleOCR con device="cuda" usando GPU RTX 5070 (Blackwell).
Causa: Incompatibilidades de precisión/arquitectura de compilación en el backend de PaddlePaddle-GPU bajo Windows.
Solución: Configurar PaddleOCR para correr en CPU (device="cpu"). La CPU Ryzen 7 9800X3D procesa la inferencia en milisegundos con total precisión y estabilidad.
```

### Problema 12: Cuello de Botella por Doble Inferencia en Fallback Regional ✅ Resuelto
```
Error: Latencia elevada (~15-20 segundos por imagen) durante el fallback regional por OCR.
Causa: El fallback realizaba inferencia sobre la imagen completa dos veces por frame.
Solución: Reutilizar la inferencia regional de la imagen completa en `full_raw = raw`, reduciendo a la mitad el tiempo de inferencia (promedio ~7.9s por imagen).
```

---

## 12. Próximos Pasos

### Completado en mayo 2026 ✅
1. ✅ Migración a PyTorch 2.11+cu128 (soporte RTX 5070 Blackwell)
2. ✅ Instalación PaddlePaddle-GPU 3.0.0 y PaddleOCR 3.5.0
3. ✅ Resolución del bug de DLLs CUDA en Windows (WinError 127)
4. ✅ Pipeline configurado para usar GPU para detección de placas y CPU para OCR por estabilidad
5. ✅ Entrenamiento final de 50 épocas completado en GPU
6. ✅ Desarrollo de frontend interactivo React + Vite con estilos UBB
7. ✅ Integración total en tiempo real con Supabase en todos los dashboards e incidencias
8. ✅ Reorganización física del proyecto en carpetas independientes `/backend` y `/frontend`
9. ✅ Optimización del postprocesamiento OCR y resolución del cuello de botella por doble inferencia en fallback
10. ✅ Procesamiento masivo del dataset de imágenes reales de WhatsApp con persistencia real en Supabase

### Corto Plazo (1-2 semanas)
- [ ] Ajustar umbrales mínimos de confianza de OCR según tipo de iluminación del acceso.

### Medio Plazo (1-3 meses)
- [ ] Fine-tuning en dataset de placas chilenas reales
- [ ] Benchmarking exhaustivo: velocidad GPU vs CPU vs precisión
- [ ] Explorar PaddlePaddle 3.1+ cuando tenga soporte oficial Blackwell

### Largo Plazo (3-6 meses)
- [ ] Deployment en servidor con GPU
- [ ] API REST para inferencia en tiempo real
- [ ] Monitoreo en producción (drift detection)

---

## 13. Referencias y Recursos

### Datasets
- **CCPD2019:** https://github.com/detectRecog/CCPD
- **Homemade:** http://mmlab.ie.cuhk.edu.hk/datasets/license-plate.html

### Librerías
- **Ultralytics YOLOv8:** https://github.com/ultralytics/ultralytics
- **PaddleOCR:** https://github.com/PaddlePaddle/PaddleOCR
- **PyTorch:** https://pytorch.org/

### Documentación
- YOLOv8 Training: https://docs.ultralytics.com/modes/train/
- PaddleOCR Configuration: https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/README.md

---

## 14. Estado Final

### Entrenamiento: 50 Épocas en GPU (Dataset Completo)

**Estado:** ✅ COMPLETADO

**Parámetros:**
```
Dataset: CCPD2019 (310,482 imágenes)
  - Train: 217,337
  - Val: 46,572
  - Test: 46,573

Modelo: YOLOv8 Nano (3.01M parameters)
Configuración:
  - Epochs: 50
  - Batch size: 32
  - Image size: 1280x1280
  - Optimizer: AdamW
  - Device: GPU (RTX 5070 / CUDA 12.8)
  - Cache: Enabled
  - LR: cosine annealing
```

**Modelos Generados:**
- ✅ `backend/runs/detect/runs/detect/train-gpu-rtx5070/weights/best.pt`
- ✅ `backend/runs/detect/runs/detect/train-gpu-rtx5070/weights/last.pt`

**Métricas Finales (Validación Época 50):**
- **Precisión (P):** `0.999`
- **Recall (R):** `0.999`
- **mAP@0.5:** `0.994`
- **mAP@0.5-95:** `0.762`
- **Box Loss (Val):** `0.912`
- **Cls Loss (Val):** `0.279`

---

## 15. Procesamiento de Dataset Real (WhatsApp)

**Objetivo:** Validar el sistema procesando las imágenes reales de WhatsApp provistas en `backend/inputs/raw`.
**Fecha de Ejecución:** 24 de mayo de 2026

### Resultados Obtenidos
- **Total de Imágenes de WhatsApp:** 114
- **Patentes Detectadas y Registradas:** 86 (Tasa de Éxito: **75.44%**)
- **Tiempo de Inferencia Promedio:** **7.916 s** por imagen (incluyendo inferencia YOLOv8 en GPU, OCR regional fallback en CPU, anotación de imagen y persistencia en base de datos).
- **Persistencia en Supabase:** 100% automatizada. Cada patente detectada se auto-registró en la tabla `vehiculos` (si no existía) e inyectó un evento de acceso de entrada en la tabla `accesos`, obteniendo IDs secuenciales reales visibles al instante en el frontend mediante WebSockets.

### Ejemplo de Log de Inferencia
```text
[114/114] Procesando: WhatsApp Image 2026-05-17 at 13.03.46.jpeg
  ✓ Patente Detectada: [ CWHK53 ]
    Confianza: 94.97% (YOLO: 94.97%)
    Método de localización: ocr_region_fallback_full
    Tiempo de inferencia: 9.490 s
    Persistiendo en Supabase...
    ✅ Guardado con éxito. ID Acceso: 142
    📂 Guardado resultado anotado en: WhatsApp Image 2026-05-17 at 13.03.46_annotated.jpg
```

---

## Resumen Ejecutivo

Este proyecto implementa un **sistema inteligente de control de estacionamiento y OCR de placas vehiculares**, compuesto por un pipeline de visión por computadora acelerado por GPU y una interfaz web corporativa interactiva integrada en tiempo real. Las 12 fases de desarrollo completadas son:

1. ✅ Ambiente configurado con Python 3.12.10 + dependencias ML.
2. ✅ 1,000 imágenes sintéticas generadas.
3. ✅ Dataset público CCPD (310k imágenes) descargado y procesado.
4. ✅ Conversión a formato YOLO completada (310k labels).
5. ✅ Splits train/val/test generados (217k/47k/47k).
6. ✅ Smoke test de entrenamiento validado (2 épocas).
7. ✅ CLI unificado en Python (generate/train/run/verify).
8. ✅ **Migración GPU completa** — PyTorch 2.11+cu128 · Paddle-GPU 3.0 · PaddleOCR 3.5.
9. ✅ **Entrenamiento GPU final completado** — 50 épocas en GPU (RTX 5070) con métricas superiores.
10. ✅ **Frontend corporativo UBB integrado con Supabase** — Dashboards dinámicos en tiempo real y flujo de incidencias.
11. ✅ **Reorganización física del proyecto** — Separación en carpetas independientes `/backend` y `/frontend`.
12. ✅ **Procesamiento de Imágenes Reales** — Inferencia en lote optimizada de 114 fotos de WhatsApp con 75.44% de éxito e inserción real en Supabase.

### Stack Tecnológico Final

| Componente | Versión | Aceleración / Rol |
|---|---|---|
| Python | 3.12.10 | Backend Core |
| YOLOv8 (ultralytics) | 8.4.46 | GPU (RTX 5070) ✅ |
| PyTorch | 2.11.0+cu128 | GPU (RTX 5070) ✅ |
| PaddlePaddle | 3.0.0 GPU | GPU (RTX 5070) ✅ (Detección YOLO) / CPU (OCR) |
| PaddleOCR | 3.5.0 | CPU (estabilidad Blackwell en Windows) |
| React + Vite | 8.0 / 18.x | Frontend Web |
| Supabase | Client JS | Real-Time DB (PostgreSQL) |

**Fecha de Documentación:** 3 de mayo de 2026 · **Última Actualización:** 24 de mayo de 2026  
**Versión del Proyecto:** 1.0 (Producción-ready)  
**Estado de Producción:** ✅ Totalmente operativo  

---

*Para ejecutar el pipeline en GPU:*
`cd backend && .\.venv\Scripts\activate && python -m vision_ocr_pipeline run infer --source inputs/raw --debug`
