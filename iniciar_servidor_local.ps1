param(
    [ValidateRange(1, 65535)]
    [int]$Puerto = 8010
)

$ErrorActionPreference = 'Stop'

# El directorio del script es la única raíz permitida para este servidor.
$RaizProyecto = Split-Path -Parent $PSCommandPath
$Python = Join-Path $RaizProyecto '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Python)) {
    throw "No se encontró el entorno virtual de PROYECTO PARCIAL: $Python"
}

Set-Location -LiteralPath $RaizProyecto
& $Python manage.py runserver "127.0.0.1:$Puerto" --noreload
