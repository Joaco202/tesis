# Archived Scripts

Esta carpeta contiene los scripts individuales que han sido consolidados bajo el CLI unificado.

## Uso del CLI moderno

En lugar de ejecutar estos scripts individualmente, usa el CLI unificado:

```bash
python -m vision_ocr_pipeline --help
```

## Equivalencias

- **Dataset generation**
  - `generate_synthetic_plates.py` → `python -m vision_ocr_pipeline generate synthetic`
  - `download_ccpd.py` → `python -m vision_ocr_pipeline generate download`
  - `process_ccpd.py` → `python -m vision_ocr_pipeline generate process`
  - `batch_convert_coco.py` → `python -m vision_ocr_pipeline generate convert`
  - `create_dataset_yaml_and_splits.py` → `python -m vision_ocr_pipeline generate split`

- **Training**
  - `train_yolo_short.py` → `python -m vision_ocr_pipeline train short`
  - `train_yolo_quick_6epochs.py` → `python -m vision_ocr_pipeline train quick`
  - `train_yolo_full_cpu_optimized.py` → `python -m vision_ocr_pipeline train full-cpu`
  - `train_yolo_full_gpu.py` → `python -m vision_ocr_pipeline train full-gpu`

- **Inference & Evaluation**
  - `run_on_inputs.py` → `python -m vision_ocr_pipeline run infer --source inputs`
  - `run_on_inputs_raw.py` → `python -m vision_ocr_pipeline run infer --source inputs/raw`
  - `try_option5_image5.py` → `python -m vision_ocr_pipeline run option5 --source inputs/raw`
  - `compare_models.py` → `python -m vision_ocr_pipeline run compare`
  - `verify_cuda.py` → `python -m vision_ocr_pipeline verify --check cuda`

## Por qué archivados

Consolidar múltiples scripts en un CLI unificado proporciona:
- **Interfaz consistente**: misma estructura y ayuda para todos los comandos
- **Flujo más limpio**: menos archivos individuales en el proyecto
- **Mantenibilidad**: cambios centralizados en un CLI
- **Documentación unificada**: todos los comandos disponibles en `--help`

Los scripts originales se mantienen aquí como referencia, pero **no deben ser ejecutados directamente** para evitar inconsistencias con el CLI.
