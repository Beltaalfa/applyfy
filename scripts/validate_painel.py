#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validação rápida do painel (rotas principais). Uso: python scripts/validate_painel.py (venv ativo)."""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE, ".env"), override=True)

from app import app  # noqa: E402


def main() -> int:
    paths = [
        "/health",
        "/api/health",
        "/api/settings",
        "/api/integracao-status",
        "/",
        "/historico",
        "/vendas",
        "/log-vendas",
        "/integracoes",
        "/meta",
        "/api/ultimo-relatorio",
    ]
    with app.test_client() as client:
        for path in paths:
            resp = client.get(path, follow_redirects=True)
            if path == "/api/health" and resp.status_code == 503:
                j = resp.get_json(silent=True) or {}
                if "ok" in j:
                    continue
            if resp.status_code >= 400:
                print(f"FALHA {path} -> HTTP {resp.status_code}")
                return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
