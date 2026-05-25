param(
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$usePyLauncher312 = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        & py -3.12 -c "import sys; print(sys.version)" | Out-Null
        $usePyLauncher312 = $true
    } catch {
        $usePyLauncher312 = $false
    }
}

if (-not $usePyLauncher312) {
    throw 'No se encontro Python 3.12 mediante `py -3.12`. Instala Python 3.12 antes de ejecutar este script.'
}

Write-Host 'Creando o actualizando entorno virtual...'
if (Test-Path '.venv') {
    Remove-Item -Recurse -Force '.venv'
}

if ($usePyLauncher312) {
    & py -3.12 -m venv .venv
}

$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'

Write-Host 'Actualizando pip...'
& $venvPython -m ensurepip --upgrade | Out-Null

Write-Host 'Actualizando pip a version reciente...'
& $venvPython -m pip install --upgrade pip | Out-Null

Write-Host 'Instalando PyTorch 2.7+ con soporte CUDA 12.8 (RTX 5070 / Blackwell)...'
& $venvPython -m pip install 'torch>=2.7.0' torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

Write-Host 'Instalando PaddlePaddle 3.x GPU (CUDA 12.6 wheel, compatible con RTX 5070)...'
& $venvPython -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/

Write-Host 'Instalando resto de dependencias...'
& $venvPython -m pip install ultralytics>=8.3.0 'opencv-python-headless==4.10.0.84' 'paddleocr>=2.8.1' 'pydantic>=2.9.0' 'pyyaml>=6.0.2' 'numpy>=1.26.0,<2.0' 'typer>=0.12.5' 'rich>=13.9.2'

if (-not $SkipSmokeTest) {
    Write-Host 'Ejecutando prueba rapida...'
    if (-not (Test-Path 'sample.jpg')) {
        throw 'No existe sample.jpg para la prueba rapida.'
    }

    $env:PYTHONPATH = 'src'
    & $venvPython -m vision_ocr_pipeline run --source sample.jpg --config config.example.yaml --event-type entrada --camera-id camara-1 --output outputs
}

Write-Host 'Listo. Activa el entorno con:'
Write-Host '.\\.venv\\Scripts\\Activate.ps1'
