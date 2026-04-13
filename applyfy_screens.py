# -*- coding: utf-8 -*-
"""
Ecrãs canónicos do painel e mapeamento API → ecrã.
Manter sincronizado com north/hub/src/lib/applyfy-screens.ts
"""
from __future__ import annotations

from typing import Any

# (id, label, coarse)
APPLYFY_SCREENS: tuple[tuple[str, str, str], ...] = (
    ("/", "Painel", "applyfy.painel"),
    ("/dashboard", "Dashboard", "applyfy.painel"),
    ("/historico", "Histórico", "applyfy.painel"),
    ("/evolucao", "Evolução", "applyfy.painel"),
    ("/transacoes", "Transações", "applyfy.painel"),
    ("/meta", "Meta", "applyfy.painel"),
    ("/comercial", "Comercial", "applyfy.painel"),
    ("/produtores", "Consultar produtores", "applyfy.painel"),
    ("/saldo", "Saldo", "applyfy.painel"),
    ("/taxas", "Taxas", "applyfy.painel"),
    ("/financeiro", "Financeiro", "applyfy.financeiro"),
    ("/log", "Log saldos", "applyfy.painel"),
    ("/permissoes", "Permissões", "applyfy.painel"),
)

APPLYFY_SCREEN_IDS: frozenset[str] = frozenset(s[0] for s in APPLYFY_SCREENS)

# prefix → screen_id (ordenar por prefix length desc no runtime)
_API_PREFIX_TO_SCREEN_RAW: tuple[tuple[str, str], ...] = (
    ("/api/gateway/transactions", "/transacoes"),
    ("/api/gateway/producers", "/produtores"),
    ("/api/gateway/producer", "/produtores"),
    ("/api/financeiro", "/financeiro"),
    ("/api/job-vendas", "/"),
    ("/api/job", "/"),
    ("/api/comercial", "/comercial"),
    ("/api/hub/applyfy-commercial-users", "/comercial"),
    ("/api/vendas/log", "/"),
    ("/api/vendas-log", "/"),
    ("/api/vendas/import-log", "/"),
    ("/api/vendas-import-log", "/"),
    ("/api/vendas", "/"),
    ("/api/transacoes", "/transacoes"),
    ("/api/evolucao", "/evolucao"),
    ("/api/dashboard", "/dashboard"),
    ("/api/produtores-webhook", "/produtores"),
    ("/api/produtor", "/produtores"),
    ("/api/produtores", "/produtores"),
    ("/api/log", "/log"),
    ("/api/relatorio", "/"),
    ("/api/ultimo-relatorio", "/"),
    ("/api/exportar", "/"),
    ("/api/datas", "/"),
    ("/api/settings", "/"),
    ("/api/integracao-status", "/"),
)


def _sorted_api_prefixes() -> list[tuple[str, str]]:
    return sorted(_API_PREFIX_TO_SCREEN_RAW, key=lambda x: len(x[0]), reverse=True)


def normalize_applyfy_path(path: str) -> str:
    p = (path.split("?")[0] or "/").strip()
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    if p == "/index.html" or p.endswith("/index.html"):
        return "/"
    if p == "/vendas.html" or p.endswith("/vendas.html"):
        return "/vendas"
    if p == "/evolucao.html" or p.endswith("/evolucao.html"):
        return "/evolucao"
    if p == "/dashboard.html" or p.endswith("/dashboard.html"):
        return "/dashboard"
    return p or "/"


def api_path_to_screen_id(api_path: str) -> str | None:
    p = normalize_applyfy_path(api_path)
    for prefix, screen_id in _sorted_api_prefixes():
        if p == prefix or p.startswith(prefix + "/"):
            return screen_id
    if p.startswith("/api/"):
        return "/"
    return None


def path_to_screen_id(path: str) -> str | None:
    """Path HTTP (HTML ou API) → id de ecrã para verificação de lista applyfy_screens."""
    p = normalize_applyfy_path(path)
    if p.startswith("/api/"):
        return api_path_to_screen_id(p)
    # Ecrãs extra: mesmo acesso granular que o painel principal (JWT com "/")
    if p == "/vendas":
        return "/"
    if p in APPLYFY_SCREEN_IDS:
        return p
    if p.startswith("/financeiro/"):
        return "/financeiro"
    if p.startswith("/comercial/"):
        return "/comercial"
    return None


def legacy_screens_from_permissions(permissions: list[str]) -> list[str]:
    """Fallback quando JWT não traz applyfy_screens (tokens antigos)."""
    perms = set(permissions)
    out: list[str] = []
    if "applyfy.admin" in perms:
        return list(APPLYFY_SCREEN_IDS)
    for sid, _label, coarse in APPLYFY_SCREENS:
        if coarse in perms:
            out.append(sid)
    return out
