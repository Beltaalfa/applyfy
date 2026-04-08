#!/usr/bin/env bash
# Prepara o painel para testar OFX/CSV: dependências, compile, rotas, init_db (se DATABASE_URL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/venv/bin/python3"
PIP="${ROOT}/venv/bin/pip"
if [[ ! -x "$PY" ]]; then
  PY="python3"
  PIP="pip3"
fi
echo "== pip install =="
"$PIP" install -r requirements.txt -q
echo "== compileall =="
"$PY" -m compileall -q .
echo "== validate_painel =="
"$PY" scripts/validate_painel.py
echo "== init_db (se Postgres configurado) =="
"$PY" << 'PY'
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.cwd() / ".env", override=True)
import db
if db.get_database_url():
    db.init_db()
    print("OK: init_db executado (tabelas extrato incluídas).")
else:
    print("AVISO: defina DATABASE_URL (ou PG_*) no .env — sem isso o extrato não grava.")
PY
echo ""
echo "Reinicie o serviço e teste no browser:"
echo "  sudo systemctl restart applyfy-painel"
echo "  Abra /financeiro → Extrato OFX / CSV → Ctrl+F5 se a página estiver em cache."
