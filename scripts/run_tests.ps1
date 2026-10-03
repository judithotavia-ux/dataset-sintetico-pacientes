# Executa a suíte de testes automatizados
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& .\.venv\Scripts\python.exe -m pytest -v
