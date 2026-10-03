#!/usr/bin/env bash
# Instala tudo (Linux/macOS). Execute a partir da raiz do projeto: bash scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements-dev.txt
(cd frontend && npm install --no-audit --no-fund)
[ -f .env ] || cp .env.example .env
echo "Pronto. Rode scripts/run_backend.sh e scripts/run_frontend.sh (em dois terminais)."
