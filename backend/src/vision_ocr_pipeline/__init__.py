"""Vision OCR pipeline package."""

from __future__ import annotations

import os
import sys


def _patch_nvidia_dll_path() -> None:
    """
    Registra los directorios de DLLs de NVIDIA con os.add_dll_directory() en Windows.

    PaddlePaddle 3.x instala las DLLs de CUDA/cuDNN como paquetes nvidia-* en
    site-packages, pero no las registra con el cargador de DLLs de Windows.
    os.add_dll_directory() es el mecanismo correcto para Python 3.8+ en Windows
    y funciona incluso antes de que se importen los módulos de extensión.
    """
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return

    site_packages_dirs = [p for p in sys.path if "site-packages" in p]
    if not site_packages_dirs:
        return

    nvidia_subdirs = [
        "nvidia/cudnn/bin",
        "nvidia/cublas/bin",
        "nvidia/cufft/bin",
        "nvidia/curand/bin",
        "nvidia/cusolver/bin",
        "nvidia/cusparse/bin",
        "nvidia/cuda_runtime/bin",
        "nvidia/nvjitlink/bin",
    ]

    for site_pkg in site_packages_dirs:
        for sub in nvidia_subdirs:
            full = os.path.normpath(os.path.join(site_pkg, sub))
            if os.path.isdir(full):
                try:
                    os.add_dll_directory(full)
                except OSError:
                    pass


_patch_nvidia_dll_path()

__all__ = [
    "config",
    "db",
    "detector",
    "ocr_engine",
    "postprocess",
    "pipeline",
    "repository",
]
