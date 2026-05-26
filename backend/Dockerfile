# Dockerfile
# Imagen de Docker optimizada para el backend de visión + OCR en servidores CPU-only.

FROM python:3.12-slim

# Evitar escritura de bytecode de Python y asegurar que los logs se emitan inmediatamente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=UTF-8 \
    PYTHONUTF8=1 \
    PADDLE_WITH_CUDA=OFF \
    OMP_NUM_THREADS=4

WORKDIR /app

# Instalar dependencias del sistema para OpenCV y PaddlePaddle
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python optimizadas para CPU
COPY requirements-cpu.txt .
RUN pip install --no-cache-dir -r requirements-cpu.txt

# Copiar el paquete del pipeline y configuración
COPY config.yaml .
COPY yolov8n.pt .
COPY runs/ runs/
COPY src/ src/

# Instalar el paquete en modo editable/desarrollo local dentro del contenedor
RUN pip install -e .

# Crear directorios para entradas y salidas
RUN mkdir -p inputs/raw outputs

# Comando por defecto para correr el pipeline sobre una imagen o carpeta
ENTRYPOINT ["python", "-X", "utf8", "-m", "vision_ocr_pipeline"]
CMD ["run", "infer", "--source", "inputs/raw", "--output", "outputs"]
