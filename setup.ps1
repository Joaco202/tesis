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

Write-Host 'Instalando dependencias...'
& $venvPython -m pip install -r requirements.txt -f 'https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html'

if (-not $SkipSmokeTest) {
    Write-Host 'Ejecutando prueba rapida...'
    if (-not (Test-Path 'sample.jpg')) {
        throw 'No existe sample.jpg para la prueba rapida.'
    }

    $env:PYTHONPATH = 'src'
    & $venvPython -m vision_ocr_pipeline run --source sample.jpg --config config.example.yaml --event-type entrada --camera-id cam-acceso-1 --output outputs
}

Write-Host 'Listo. Activa el entorno con:'
Write-Host '.\\.venv\\Scripts\\Activate.ps1'
