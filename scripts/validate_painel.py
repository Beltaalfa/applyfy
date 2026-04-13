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

from app import app  # noqa: E402 — app.py volta a carregar .env e pode ligar APPLYFY_AUTH_ENABLED

# Smoke test sem cookie Hub: após import, forçar gate desligado (auth_hub lê env a cada pedido).
os.environ["APPLYFY_AUTH_ENABLED"] = "0"


def main() -> int:
    paths = [
        "/health",
        "/api/health",
        "/api/settings",
        "/api/me",
        "/api/integracao-status",
        "/",
        "/dashboard",
        "/dashboard/",
        "/api/dashboard?from=2020-01-01&to=2020-01-31",
        "/historico",
        "/evolucao",
        "/transacoes",
        "/vendas",
        "/produtores",
        "/saldo",
        "/taxas",
        "/permissoes",
        "/config-comercial",
        "/meta",
        "/comercial",
        "/comercial/",
        "/static/painel-shell.js",
        "/static/painel-theme.css",
        "/static/table-utils.js",
        "/financeiro",
        "/api/ultimo-relatorio",
        "/api/comercial/carteira",
        "/api/financeiro/extrato/contas",
        "/api/financeiro/extrato/resumo",
        "/api/financeiro/extrato?limit=5",
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
        js = client.get("/static/painel-shell.js")
        if js.status_code != 200 or b"/comercial" not in js.data or b"/dashboard" not in js.data:
            print("FALHA painel-shell.js incompleto ou inacessível em /static/")
            return 1
        if b"/transacoes" not in js.data or b"firstSortAsc" not in client.get("/static/table-utils.js").data:
            print("FALHA table-utils ou menu incompleto")
            return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
