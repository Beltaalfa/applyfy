#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test automático do gate Hub (sem browser). Uso: ./venv/bin/python scripts/hub_auth_smoke.py

Com APPLYFY_AUTH_ENABLED=1 no .env: /api/me sem cookie = authenticated false;
GET / com auth sem cookie = redirect para HUB_LOGIN_URL; /health = 200.

Com auth desligada: apenas confirma /health e /api/me básicos.
"""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE, ".env"), override=True)

import auth_hub  # noqa: E402
from app import app  # noqa: E402


def main() -> int:
    client = app.test_client()
    r_health = client.get("/health")
    if r_health.status_code != 200:
        print(f"FALHA /health -> {r_health.status_code}")
        return 1
    r_me = client.get("/api/me")
    if r_me.status_code != 200:
        print(f"FALHA /api/me -> {r_me.status_code}")
        return 1
    me = r_me.get_json()
    if not isinstance(me, dict):
        print("FALHA /api/me JSON inválido")
        return 1

    if not auth_hub.auth_enabled():
        print("OK (auth Hub desligada): /health e /api/me")
        return 0

    if me.get("auth_enabled") is not True:
        print("FALHA: APPLYFY_AUTH_ENABLED=1 mas /api/me não reporta auth_enabled true")
        return 1
    if me.get("authenticated") is not False:
        print("FALHA: sem cookie, esperava authenticated=false em /api/me")
        return 1

    r_root = client.get("/", follow_redirects=False)
    if r_root.status_code not in (301, 302, 303, 307, 308):
        print(f"FALHA GET / sem sessão -> esperava redirect, obteve {r_root.status_code}")
        return 1
    loc = (r_root.headers.get("Location") or "").strip()
    hub = (os.environ.get("HUB_LOGIN_URL") or "").strip()
    if hub and hub not in loc and not loc.startswith("http"):
        pass  # relativo ao Hub ok
    if hub and hub.split("?")[0] not in loc and "login" not in loc.lower():
        print(f"AVISO: Location pode não ser o login Hub: {loc[:120]!r}")

    # Sem cookie JWT, /auth/callback deve redirecionar para o login do Hub (não aplica destino até haver sessão).
    r_cb = client.get("/auth/callback?returnUrl=%2Fhistorico", follow_redirects=False)
    if r_cb.status_code not in (301, 302, 303, 307, 308):
        print(f"FALHA /auth/callback -> {r_cb.status_code}")
        return 1

    print("OK (auth Hub ligada): /health, /api/me sem sessão, redirect em / e /auth/callback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
