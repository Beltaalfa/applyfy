#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Percorre todas as rotas registadas no Flask (url_map) com test_client.
Ignora POST que alteram estado (jobs, limpar logs, retry DLQ).
Uso: na raiz do projeto com venv: python scripts/validate_all_functions.py
"""
from __future__ import annotations

import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(BASE, ".env"), override=True)

from app import app  # noqa: E402

SKIP_POST_ENDPOINTS = frozenset(
    {
        "api_job_start",
        "api_job_stop",
        "api_job_vendas_start",
        "api_job_vendas_stop",
        "api_log_clear",
        "api_vendas_log_clear",
        "api_admin_webhook_dlq_retry",
    }
)


def path_from_rule(rule) -> str:
    """Converte padrão Werkzeug em path de teste (int=inexistente, path=ficheiro em static)."""

    def repl(m: re.Match) -> str:
        inner = m.group(1)
        if inner.startswith("int:"):
            return "999999999"
        if inner.startswith("float:"):
            return "1.0"
        if inner.startswith("path:") or inner.split(":", 1)[0] == "path":
            return "financeiro.js"
        return "p1"

    return re.sub(r"<([^>]+)>", repl, rule.rule)


def response_ok(path: str, status: int, endpoint: str) -> tuple[bool, str]:
    """Sucesso = handler respondeu; 503 admin sem token e 502 Applyfy são aceites neste smoke test."""
    if path == "/api/health" and status == 503:
        return True, "health_degraded_503"
    if status == 503 and path.startswith("/api/admin/"):
        return True, "admin_optional_503"
    if status == 502 and endpoint in ("api_produtor_taxas", "api_produtor_detalhes"):
        return True, "applyfy_upstream_502"
    if status >= 500:
        return False, f"server_error_{status}"
    return True, "ok"


def main() -> int:
    failures: list[dict] = []
    skipped: list[dict] = []

    with app.test_client() as client:
        for rule in sorted(app.url_map.iter_rules(), key=lambda x: (x.rule, x.endpoint)):
            path = path_from_rule(rule)
            for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
                ep = rule.endpoint or ""
                if method == "POST" and ep in SKIP_POST_ENDPOINTS:
                    skipped.append({"method": method, "path": path, "endpoint": ep})
                    continue

                kwargs = {"follow_redirects": True}
                if method == "GET":
                    resp = client.get(path, **kwargs)
                elif method == "POST":
                    if path == "/api/webhooks/applyfy":
                        resp = client.post(path, json={}, content_type="application/json")
                    elif path == "/api/financeiro/ofx/upload":
                        resp = client.post(path, data={})
                    elif "/conciliar" in path:
                        resp = client.post(path, json={}, content_type="application/json")
                    elif "/desconciliar" in path:
                        resp = client.post(path, json={}, content_type="application/json")
                    else:
                        resp = client.post(path, json={}, content_type="application/json")
                elif method == "PUT":
                    resp = client.put(path, json={}, content_type="application/json")
                elif method == "DELETE":
                    resp = client.delete(path)
                else:
                    resp = client.open(path, method=method, **kwargs)

                try:
                    prev = (resp.get_data(as_text=True) or "")[:120]
                except Exception:
                    prev = ""
                ok, _reason = response_ok(path, resp.status_code, ep)
                if not ok:
                    failures.append(
                        {
                            "method": method,
                            "path": path,
                            "endpoint": ep,
                            "status": resp.status_code,
                            "preview": prev,
                        }
                    )

    if failures:
        for f in failures:
            print(f"FALHA {f['method']} {f['path']} ({f['endpoint']}) -> {f['status']}")
        return 1
    print(f"OK — {len(skipped)} POST omitidos (efeitos colaterais).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
