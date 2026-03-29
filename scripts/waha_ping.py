#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Envia mensagem de teste ao WAHA (mesmas env vars do run_daily). Uso: . env.sh && python scripts/waha_ping.py"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE, ".env"), override=True)

import waha_client  # noqa: E402


def main() -> int:
    if not waha_client.is_waha_configured():
        print(
            "WAHA não configurado: WAHA_NOTIFY_ENABLED=1, WAHA_BASE_URL, WAHA_NOTIFY_CHAT_ID ou WAHA_NOTIFY_CHAT_IDS.",
            file=sys.stderr,
        )
        return 1
    n = len(waha_client.notify_chat_ids())
    if n > 1:
        print(f"A enviar teste para {n} destinos…")
    ok, err = waha_client.send_text("Applyfy: teste manual (scripts/waha_ping.py)")
    if ok:
        print("Mensagem enviada.")
        return 0
    print(err, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
