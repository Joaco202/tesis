import cv2
from ultralytics import YOLO
from pathlib import Path

# Cargar modelo entrenado
model_path = r"runs/detect/runs/detect/train-gpu-rtx5070/weights/best.pt"
print(f"Cargando modelo YOLO: {model_path}")
model = YOLO(model_path)

# Buscar la primera imagen de WhatsApp
valid_exts = {".jpg", ".jpeg", ".png"}
source_dir = Path("inputs/raw")
images = [p for p in source_dir.iterdir() if p.suffix.lower() in valid_exts and "whatsapp" in p.name.lower()]

if not images:
    print("No se encontraron imágenes de WhatsApp.")
else:
    img_path = images[0]
    print(f"Procesando imagen: {img_path.name}")
    img = cv2.imread(str(img_path))
    
    # Predecir con confianza muy baja
    results = model.predict(source=img, conf=0.01, device="cuda")
    
    print("Detecciones encontradas:")
    for idx, r in enumerate(results):
        boxes = r.boxes
        print(f"Resultado {idx}: {len(boxes)} cajas")
        for b_idx, box in enumerate(boxes):
            conf = float(box.conf[0].item())
            cls = int(box.cls[0].item())
            xyxy = box.xyxy[0].tolist()
            print(f"  Caja [{b_idx}]: Clase {cls}, Confianza {conf:.4f}, BBox: {xyxy}")
            
    # Probar también con el PaddleOCR en toda la imagen para ver qué lee
    from paddleocr import PaddleOCR
    print("Inicializando PaddleOCR...")
    ocr = PaddleOCR(use_angle_cls=True, lang="es", device="cpu")
    raw_ocr = ocr.ocr(img)
    print("OCR en imagen completa:")
    print(raw_ocr)
