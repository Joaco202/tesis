# env_gpu.ps1 — Activa el venv Y agrega las DLLs de NVIDIA al PATH
# Uso: . .\env_gpu.ps1   (el punto es importante para que afecte la sesion actual)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sitePackages = Join-Path $projectRoot ".venv\Lib\site-packages"

# Directorios de DLLs de NVIDIA instalados por pip (nvidia-cudnn-cu12, etc.)
$nvidiaDirs = @(
    "nvidia\cudnn\bin",
    "nvidia\cublas\bin",
    "nvidia\cufft\bin",
    "nvidia\curand\bin",
    "nvidia\cusolver\bin",
    "nvidia\cusparse\bin",
    "nvidia\cuda_runtime\bin",
    "nvidia\nvjitlink\bin"
)

Write-Host "[GPU] Agregando DLLs de NVIDIA al PATH..." -ForegroundColor Cyan
foreach ($sub in $nvidiaDirs) {
    $full = Join-Path $sitePackages $sub
    if (Test-Path $full) {
        if ($env:PATH -notlike "*$full*") {
            $env:PATH = "$full;$env:PATH"
            Write-Host "  + $full" -ForegroundColor DarkGray
        }
    }
}

# Activar el venv
$activateScript = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
. $activateScript

Write-Host "[GPU] Entorno listo. PyTorch + PaddlePaddle con RTX 5070." -ForegroundColor Green
