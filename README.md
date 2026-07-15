# Vision + OCR Pipeline para Detección de Placas y Gestión de Estacionamientos

## Estructura del Sistema

El proyecto está dividido en dos partes principales:

1. **Backend (Visión & OCR)**:
   * **Detección (YOLOv8)**: Localiza la patente en las imágenes capturadas.
   * **Lectura (PaddleOCR)**: Reconoce los caracteres alfanuméricos de la patente utilizando preprocesamiento de OpenCV y heurísticas de formato de patente chilena (nuevo/antiguo).
   * **Persistencia**: Registra automáticamente los ingresos, salidas y niveles de confianza en la base de datos Supabase.

2. **Frontend (Dashboard React + Vite)**:
   * **Panel de Guardia**: Monitoreo en tiempo real de accesos, registro de ingresos/salidas manuales, corrección de patentes leídas erróneamente por la cámara y reporte de incidencias.
   * **Panel de Encargado (Gestión)**: Visualización de estadísticas de uso (KPIs), historial de accesos, gestión de vehículos/funcionarios y resolución de incidencias.
   * **Panel de Administrador (Configuración)**: Control de usuarios de la aplicación, asignación de roles (guardia, encargado, admin) y configuraciones de seguridad.
   * **Pantalla Pública**: Visualización en vivo de cupos libres y estado de ocupación del estacionamiento.

---

## Requisitos y Especificaciones Técnicas

* **Python**: 3.12 (Entorno recomendado y validado con `paddleocr==3.5.0` y `paddlepaddle` para ejecución rápida)
* **Node.js**: 18+ (Para el frontend en React)
* **Aceleración por GPU**: Compatible con CUDA y arquitectura Blackwell (NVIDIA RTX 5070) para inferencias ultra rápidas. También soporta ejecución en CPU.
* **Base de datos**: Supabase (PostgreSQL) con tablas de accesos, vehículos, zonas de estacionamiento e incidencias.

---

## Instalación y Configuración

### 1. Configuración del Backend

#### Instalación Automática (Windows PowerShell)
Desde la raíz del proyecto, ejecuta el script de configuración del entorno virtual e instalación de dependencias en CPU:
```powershell
cd backend
# Para levantar dependencias básicas en CPU
.\setup.ps1
```
*Si tienes GPU NVIDIA y quieres habilitar aceleración CUDA, puedes configurar y arrancar tu sesión usando:*
```powershell
# Activa el entorno virtual cargando las rutas DLL de CUDA en tu PATH temporal de consola
. .\env_gpu.ps1
```

#### Configuración de Variables de Entorno
Crea un archivo `.env` dentro de la carpeta `backend/` con  credenciales de Supabase:
```env
SUPABASE_ENABLED=true
SUPABASE_URL=https://proyecto.supabase.co
SUPABASE_SERVICE_KEY=service-key-secreta
SUPABASE_TIMEOUT_SECONDS=10
SUPABASE_VEHICLES_TABLE=vehiculos
SUPABASE_ACCESSES_TABLE=accesos
```

### 2. Configuración del Frontend

#### Instalación de Dependencias
Ve a la carpeta `frontend/` e instala las dependencias de npm:
```bash
cd frontend
npm install
```

#### Configuración de Variables de Entorno
Crea un archivo `.env` dentro de la carpeta `frontend/` con las claves públicas de Supabase:
```env
VITE_SUPABASE_URL=https://proyecto.supabase.co
VITE_SUPABASE_ANON_KEY=anon-key-publica
```

---

## Ejecución del Sistema

### 1. Iniciar el Frontend (React Dev Server)

Inicia el servidor de desarrollo para interactuar con la aplicación web:
```bash
cd frontend
npm run dev
```
La aplicación estará disponible por defecto en [http://localhost:5173](http://localhost:5173).

### 2. Iniciar el Backend (CLI o Inferencia Continua)

El backend cuenta con una interfaz de comandos (CLI) unificada para tareas de diagnóstico e inferencia, y un script dedicado para captura de cámara web.

#### Ejecución con cámara web (Tiempo Real):
Para procesar la entrada de una cámara de video y persistir en Supabase:
```bash
cd backend
.venv\Scripts\activate
# --source 0 para usar la primera cámara web local
python scripts/continuous_inference.py --source 0 --show
```

#### Comando de Lanzamiento Completo (Inicia Frontend + Backend):
Puedes usar el script raíz para arrancar ambos sistemas de manera simplificada:
```powershell
# En la raíz del repositorio
.\start_system.ps1
```

#### Comandos del CLI para Diagnóstico:
* **Procesar Imagen/Directorio de entrada**:
  ```bash
  python -m vision_ocr_pipeline run infer --source inputs/raw --output outputs --debug
  ```
* **Procesar con fallback OCR en regiones completas (Opción 5)**:
  ```bash
  python -m vision_ocr_pipeline run option5 --source inputs/raw/5.jpg
  ```
* **Verificar compatibilidad CUDA / GPU**:
  ```bash
  python -m vision_ocr_pipeline verify cuda
  ```

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
│   ├── scripts/                   # Scripts utilitarios (inferencia continua, debug de cámara)
│   ├── inputs/                    # Carpeta para colocar imágenes de entrada
│   ├── outputs/                   # Resultados del procesamiento (JSON + imágenes anotadas)
│   └── requirements.txt           # Dependencias de Python para GPU
│
├── frontend/                      # Cliente web (React + Vite)
│   ├── src/
│   │   ├── pages/                 # Páginas de la aplicación (GuardDashboard, ManagerDashboard, etc.)
│   │   ├── context/               # Manejo de estado de autenticación (AuthContext.jsx)
│   │   └── lib/                   # Cliente inicializado de Supabase (supabase.js)
│   └── package.json               # Dependencias de Node
│
└── README.md                      # Esta guía de documentación general
```

---

## Mantenimiento del Almacenamiento

Por límites de almacenamiento en la capa gratuita de Supabase (1 GB), el backend de inferencia continua ejecutará un proceso automático de autolimpieza en cada arranque. 

Este proceso **elimina del Storage las imágenes físicas de patentes con más de 30 días de antigüedad** y pone las columnas `imagen_origen` y `imagen_origen_salida` en `NULL` en la base de datos para liberar espacio. **Los registros numéricos y textuales (patente, fechas, horas, etc.) no se eliminan y se conservan indefinidamente.**
