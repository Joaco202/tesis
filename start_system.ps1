# start_system.ps1
# Script unificado para iniciar el sistema de Detección de Placas UBB

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Iniciando Sistema de Control de Acceso Vehicular UBB   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Iniciar el Frontend (React + Vite) en una ventana de PowerShell separada
Write-Host "[1/2] Iniciando servidor de desarrollo Frontend en ventana separada..." -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot "frontend"

if (Test-Path $frontendPath) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev"
    Write-Host "  ✓ Servidor de Vite iniciado en una nueva consola." -ForegroundColor Green
} else {
    Write-Error "No se encontró el directorio frontend en '$frontendPath'."
}

# 2. Activar el entorno virtual del Backend en la consola actual
Write-Host "[2/2] Configurando entorno de desarrollo del Backend en esta consola..." -ForegroundColor Yellow
$backendPath = Join-Path $PSScriptRoot "backend"

if (Test-Path $backendPath) {
    Set-Location $backendPath
    $venvActivate = Join-Path $backendPath ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) {
        . $venvActivate
        Write-Host "  ✓ Entorno virtual (.venv) activado." -ForegroundColor Green
        Write-Host "  ✓ Directorio actual cambiado a: $backendPath" -ForegroundColor Green
        Write-Host "  ✓ Python optimizado con modo UTF-8 activo." -ForegroundColor Green
        Write-Host ""
        Write-Host "Para correr una inferencia de prueba sobre las imágenes reales:" -ForegroundColor Cyan
        Write-Host "  python -X utf8 test_real_inputs.py --limit 3" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Para iniciar la simulación de flujo continuo / video:" -ForegroundColor Cyan
        Write-Host "  python -X utf8 scripts/continuous_inference.py --source inputs/raw --delay 2.0" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Warning "No se encontró el script de activación en '$venvActivate'."
    }
} else {
    Write-Error "No se encontró el directorio backend en '$backendPath'."
}

Write-Host "==========================================================" -ForegroundColor Cyan
