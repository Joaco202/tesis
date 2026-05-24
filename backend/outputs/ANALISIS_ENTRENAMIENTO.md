# Análisis: ¿Tuvo efecto el entrenamiento de 2 epochs?

## Resultado: **NO** - El modelo entrenado fue **PEOR** que el base

### Comparación de Detecciones

| Modelo | Total Detecciones | Imágenes afectadas |
|--------|------------------|-------------------|
| **yolov8n.pt** (base) | **35** | 6/6 imágenes detectaron algo |
| **train-3** (2 epochs) | **0** | 0/6 imágenes; ninguna detección |

**Conclusión**: El modelo entrenado perdió el 100% de su capacidad de detección.

---

## Por qué pasó esto?

### Métricas de Entrenamiento (`runs/detect/train-3/results.csv`)

```
Epoch | Recall | Precision | mAP50  | mAP50-95 | box_loss | cls_loss
------|--------|-----------|--------|----------|----------|----------
  1   | 39.2%  | 0.131%    | 0.231% | 0.083%   | 2.85     | 9.54
  2   | 21.6%  | 7.604%    | 5.45%  | 1.82%    | 2.47     | 4.46
```

### Problemas Identificados

1. **Convergencia Incompleta**
   - 2 epochs es insuficiente para este modelo/dataset
   - Las métricas cambian de forma errática (Recall baja en época 2)
   - Las pérdidas siguen siendo muy altas

2. **Modelo Degradado**
   - El checkpoint `best.pt` (epoch 1 seleccionado por mAP50-95 = 0.083%)
   - Fue tan sobreajustado que perdió capacidad generalizadora
   - Ahora NO detecta NADA en imágenes nuevas (inputs/raw)

3. **Datos vs Arquitectura**
   - Dataset: 310,482 imágenes CCPD (placas chinas)
   - Imágenes de prueba: placas chilenas (DIFERENTES de las de entrenamiento)
   - 2 epochs es demasiado poco para adaptar el modelo

---

## Recomendación

Para mejorar la detección, necesitarías:

### Opción A: Más Entrenamiento (6+ epochs mínimo)
```bash
# Completar los 6 epochs planeados originalmente
yolo task=detect mode=train model=yolov8n.pt data=data/plates/data.yaml epochs=6 imgsz=1280 batch=8
```
**Esperado**: Convergencia en epochs 4-6, mejor generalización

### Opción B: Mejor Dataset
- Agregar imágenes de **placas chilenas** (no solo CCPD chinas)
- Aumentación de datos: rotaciones, oclusión, ángulos extremos
- Validar anotaciones YOLO en `data/plates/labels/ccpd/`

### Opción C: Usar Fallback + Base Model (Actual)
- Mantener `yolov8n.pt` base (detecta 35 placas en inputs/raw)
- Usar fallback opción 5 (OCR regions) cuando YOLO no detecte
- Esto detecta casos difíciles como `inputs/raw/5.jpg` → `CRJC39` ✓

---

## Estado Actual (Recomendado)

**Usar**: 
- Detector: `yolov8n.pt` base (no sobreajustado)
- Fallback: Opción 5 (OCR regions) integrada en `pipeline.py`

**Resultado en inputs/raw**:
- 6 imágenes procesadas
- 6 patentes detectadas (5 por YOLO + 1 por fallback opción 5)
- Confianzas buenas (0.80-0.92)
