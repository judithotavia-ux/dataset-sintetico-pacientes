# Sobe a API em http://localhost:8000 (documentação em /docs)
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "backend")
& (Join-Path $root ".venv\Scripts\python.exe") -m uvicorn app.main:app --reload --port 8000
