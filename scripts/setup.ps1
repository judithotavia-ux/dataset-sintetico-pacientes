# Instala tudo (Windows / PowerShell). Execute a partir da raiz do projeto:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Criando ambiente virtual Python (.venv)"
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt

Write-Host "==> Instalando dependências do frontend"
Push-Location frontend
npm install --no-audit --no-fund
Pop-Location

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
Write-Host "Pronto. Rode scripts\run_backend.ps1 e scripts\run_frontend.ps1 (em dois terminais)."
