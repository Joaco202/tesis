"""
Descarga el dataset de patentes chilenas desde Roboflow Universe.
Versión robusta con mejor manejo de rutas y versiones.
"""
from roboflow import Roboflow
from pathlib import Path
import sys
import os

API_KEY = "9Z1pntTdUYxGt7z17aeY"
BASE = Path(__file__).resolve().parents[1]
DEST = BASE / "data" / "patentes_chile"
DEST.mkdir(parents=True, exist_ok=True)

rf = Roboflow(api_key=API_KEY)

# Probar versiones disponibles del dataset principal
print("Conectando a Roboflow...")

datasets_to_try = [
    ("pablo-delgadillo", "patentes-chile-75aam", 1),
    ("pablo-delgadillo", "patentes-chile-75aam", 3),
    ("davids-workspace-3e39w", "patentes-chile-fnedz-1ki2h", 1),
    ("migueeechc", "internacional_and_chilean_plate", 1),
    ("migueeechc", "internacional_and_chilean_plate", 2),
]

success = False
for workspace, project_name, version in datasets_to_try:
    try:
        print(f"\nIntentando: {workspace}/{project_name} v{version}...")
        project = rf.workspace(workspace).project(project_name)
        info = project.get_version_information()
        print(f"  Versiones disponibles: {[v.get('id','?') for v in info]}")
        
        dataset = project.version(version).download(
            "yolov8",
            location=str(DEST),
            overwrite=True
        )
        print(f"\n✓ Dataset descargado!")
        
        # Verificar contenido
        yaml_files = list(DEST.rglob("*.yaml"))
        img_count = len(list(DEST.rglob("*.jpg"))) + len(list(DEST.rglob("*.png")))
        print(f"  YAML encontrados: {[f.name for f in yaml_files]}")
        print(f"  Imágenes totales: {img_count}")
        success = True
        break
    except Exception as e:
        print(f"  ✗ Falló: {e}")

if not success:
    # Intentar descarga manual por URL
    print("\nIntentando método alternativo...")
    try:
        workspace = rf.workspace("pablo-delgadillo")
        project = workspace.project("patentes-chile-75aam")
        versions = project.get_version_information()
        print(f"Versiones disponibles: {versions}")
    except Exception as e:
        print(f"Error: {e}")
    sys.exit(1)
