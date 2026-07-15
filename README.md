# Vision + OCR Pipeline para Detección de Placas y Gestión de Estacionamientos

Este proyecto implementa un sistema inteligente y automatizado para la gestión de accesos vehiculares en la Universidad del Bío-Bío, Campus Fernando May. El sistema consta de un pipeline de visión por computadora para la detección y lectura de patentes (OCR), integrado con una base de datos Supabase y un panel de control web responsivo para guardias y administradores.

---

## Estructura del Sistema

El proyecto está dividido en dos partes principales:

1. **Backend (Visión & OCR)**:
   * **Detección (YOLOv8)**: Localiza la patente en las imágenes capturadas.
   * **Lectura (PaddleOCR)**: Reconoce los caracteres alfanuméricos de la patente utilizando preprocesamiento de OpenCV.
   * **Persistencia**: Registra automáticamente los ingresos, salidas y niveles de confianza en la base de datos Supabase.

2. **Frontend (Dashboard React + Vite)**:
   * **Panel de Guardia**: Monitoreo en tiempo real de accesos, registro de ingresos/salidas manuales, corrección de patentes leídas erróneamente por la cámara y reporte de incidencias.
   * **Panel de Administrador/Encargado**: Visualización de estadísticas de uso (KPIs), historial de accesos, gestión de vehículos/funcionarios y resolución de incidencias.
   * **Pantalla Pública**: Visualización en vivo de cupos libres y estado de ocupación del estacionamiento.

---

## Requisitos y Especificaciones Técnicas

* **Python**: 3.12+ (Entorno recomendado y validado con `paddleocr==3.5.0` y `paddlepaddle-gpu==3.0.0` para aceleración gráfica)
* **Node.js**: 18+ (Para el frontend en React)
* **Aceleración por GPU**: Compatible con CUDA 12.8 y arquitectura Blackwell (NVIDIA RTX 5070) para inferencias ultra rápidas. También soporta ejecución en CPU.
* **Base de datos**: Supabase (PostgreSQL) con tablas de accesos, vehículos, zonas de estacionamiento e incidencias.

---

## Instalación y Configuración

### 1. Configuración del Backend

#### Instalación Automática (Windows PowerShell)
Desde la raíz del proyecto, ejecuta el script de configuración del entorno virtual e instalación de dependencias:
```powershell
cd backend
.\setup.ps1
```
*Si tienes GPU NVIDIA y quieres habilitar aceleración CUDA, puedes configurar el entorno usando `.\env_gpu.ps1`.*

#### Configuración de Variables de Entorno
Crea un archivo `.env` dentro de la carpeta `backend/` (usa `.env.example` como base) con tus credenciales de Supabase:
```env
SUPABASE_ENABLED=true
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_KEY=tu-service-key-secreta
SUPABASE_TIMEOUT_SECONDS=10
SUPABASE_VEHICLES_TABLE=vehiculos
SUPABASE_ACCESSES_TABLE=accesos
```

### 2. Configuración del Frontend

#### Instalación de Dependencias
Navega a la carpeta `frontend/` e instala las dependencias de npm:
```bash
cd frontend
npm install
```

#### Configuración de Variables de Entorno
Crea un archivo `.env` dentro de la carpeta `frontend/` con las claves públicas de Supabase:
```env
VITE_SUPABASE_URL=https://tu-proyecto.supabase.co
VITE_SUPABASE_ANON_KEY=tu-anon-key-publica
```

---

## Ejecución del Sistema

### 1. Iniciar el Backend (CLI Unificado)

El backend cuenta con una interfaz de comandos (CLI) unificada para todas las tareas:

```bash
# Activar entorno virtual
cd backend
.venv\Scripts\activate

# Ver todos los comandos disponibles
python -m vision_ocr_pipeline --help
```

#### Comandos Principales:
* **Ejecutar Inferencia (Procesar Imagen/Directorio)**:
  ```bash
  python -m vision_ocr_pipeline run infer --source inputs/raw --output outputs
  ```
* **Ejecutar con Fallback OCR (Opción 5 - cuando YOLO falla)**:
  ```bash
  python -m vision_ocr_pipeline run option5 --source inputs/raw/5.jpg
  ```
* **Generar Imágenes Sintéticas de Patentes**:
  ```bash
  python -m vision_ocr_pipeline generate synthetic --count 1000 --output data/synthetic
  ```
* **Entrenar Modelo YOLOv8**:
  ```bash
  # Entrenamiento rápido para validar
  python -m vision_ocr_pipeline train quick
  
  # Entrenamiento completo en GPU
  python -m vision_ocr_pipeline train full-gpu
  ```

### 2. Iniciar el Frontend (React Dev Server)

Inicia el servidor de desarrollo para interactuar con la aplicación web:
```bash
cd frontend
npm run dev
```
La aplicación estará disponible por defecto en [http://localhost:5173](http://localhost:5173).

---

## Estructura de Directorios

```
tesis/
├── backend/                       # Directorio del pipeline de IA y scripts del servidor
│   ├── src/vision_ocr_pipeline/   # Código fuente del pipeline de visión y base de datos
│   │   ├── pipeline.py            # Orquestador del flujo YOLO + OpenCV + OCR + Supabase
│   │   ├── detector.py            # Integración de YOLOv8 para localización de placas
│   │   ├── ocr_engine.py          # Extracción de texto con PaddleOCR
│   │   ├── repository.py          # Lógica de base de datos (accesos, vehículos)
│   │   └── db.py                  # Cliente HTTP de Supabase (PostgREST)
│   ├── scripts/                   # Scripts utilitarios (entrenamiento, debug)
│   ├── inputs/                    # Carpeta para colocar imágenes de entrada
│   ├── outputs/                   # Resultados del procesamiento (JSON + imágenes anotadas)
│   └── requirements.txt           # Dependencias de Python
│
├── frontend/                      # Cliente web (React + Vite)
│   ├── src/
│   │   ├── pages/                 # Páginas de la aplicación (GuardDashboard, ManagerDashboard, etc.)
│   │   ├── context/               # Manejo de estado de autenticación (AuthContext.jsx)
│   │   └── lib/                   # Cliente inicializado de Supabase (supabase.js)
│   └── package.json               # Dependencias de Node
│
├── README.md                      # Esta guía de documentación general
└── PROJECT_SUMMARY.md             # Resumen técnico detallado de especificaciones del sistema
```

---

## Soporte y Base de Datos

El diseño del esquema de la base de datos se encuentra detallado en [backend/sql/schema.sql](file:///c:/Users/joako/Documents/GitHub/tesis/backend/sql/schema.sql). La integración de base de datos maneja:
* **Entrada**: Guarda la fecha de ingreso, ID de la cámara de entrada, confianza del OCR y la imagen de origen.
* **Salida**: Registra la salida en el mismo registro calculando el tiempo de estadía, confianza y cámara de salida.
* **Vehículos**: Almacena información de vehículos autorizados, tipo de vehículo e información de funcionarios.
* **Incidencias**: Permite reportar problemas detectados en los estacionamientos y hacer seguimiento de su resolución.
