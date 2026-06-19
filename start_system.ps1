# start_system.ps1
# Script unificado para instalar dependencias e iniciar el frontend y el backend con webcam

param(
    [string]$Source = "0"
)

$ErrorActionPreference = 'Continue'

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Iniciando Sistema de Control de Acceso Vehicular UBB   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$projectRoot = $PSScriptRoot
$frontendPath = Join-Path $projectRoot "frontend"
$backendPath = Join-Path $projectRoot "backend"

# --- 1. CONFIGURACIÓN Y VERIFICACIÓN DEL FRONTEND ---
Write-Host "[1/4] Verificando dependencias del Frontend..." -ForegroundColor Yellow
if (Test-Path $frontendPath) {
    $nodeModules = Join-Path $frontendPath "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "  [i] 'node_modules' no encontrado. Instalando dependencias de Node.js..." -ForegroundColor DarkYellow
        cd $frontendPath
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Fallo la instalacion de dependencias del Frontend."
            exit 1
        }
        Write-Host "  [OK] Dependencias de Frontend instaladas exitosamente." -ForegroundColor Green
    } else {
        Write-Host "  [OK] Dependencias de Frontend ya instaladas." -ForegroundColor Green
    }
} else {
    Write-Error "No se encontro el directorio frontend en '$frontendPath'."
    exit 1
}

# --- 2. CONFIGURACIÓN Y VERIFICACIÓN DEL BACKEND ---
Write-Host "[2/4] Verificando entorno virtual del Backend..." -ForegroundColor Yellow
if (Test-Path $backendPath) {
    cd $backendPath
    $venvPath = Join-Path $backendPath ".venv"
    $venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"

    if (-not (Test-Path $venvPath)) {
        Write-Host "  [i] Entorno virtual (.venv) no encontrado. Creando venv..." -ForegroundColor DarkYellow
        
        # Buscar la mejor instalacion de Python disponible
        $pythonCmd = "python"
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $pythonCmd = "py"
        }
        
        & $pythonCmd -m venv .venv
        if (-not (Test-Path $venvPath)) {
            Write-Error "No se pudo crear el entorno virtual con '$pythonCmd'. Asegurate de tener Python instalado y en tu PATH."
            exit 1
        }
        Write-Host "  [OK] Entorno virtual (.venv) creado." -ForegroundColor Green
    }

    # Instalar o verificar dependencias de python
    Write-Host "  [i] Verificando e instalando dependencias de Python..." -ForegroundColor DarkYellow
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements-cpu.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Hubo algunos problemas instalando dependencias. Intentando continuar..."
    }
    Write-Host "  [OK] Backend preparado." -ForegroundColor Green
} else {
    Write-Error "No se encontro el directorio backend en '$backendPath'."
    exit 1
}

# --- 3. INICIAR EL FRONTEND ---
Write-Host "[3/4] Iniciar el Frontend (Vite) en una ventana separada..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev"
Write-Host "  [OK] Frontend iniciado en segundo plano. Abre la URL indicada en la nueva consola." -ForegroundColor Green

# --- 4. INICIAR EL BACKEND (WEBCAM) ---
Write-Host "[4/4] Iniciando el Backend con la camara web..." -ForegroundColor Yellow
cd $backendPath

# Activar venv en la sesion actual
if (Test-Path $venvActivate) {
    . $venvActivate
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Iniciando script de inferencia continua..." -ForegroundColor Green
Write-Host "Presiona 'q' en la ventana de la camara para detener el backend." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

# Ejecutar el backend con el origen seleccionado y mostrar la ventana en tiempo real
python -X utf8 scripts/continuous_inference.py --source $Source --show
