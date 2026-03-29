#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aviso via WAHA se não houver webhooks há X horas.
Agendar no cron (ex.: 0 */6 * * *) com . env.sh && python scripts/alert_webhook_silence.py

Requer: WAHA_ALERT_WEBHOOK_SILENCE=1 e mesma config WAHA que run_daily.
Variável APPLYFY_WEBHOOK_SILENCE_HOURS (default 24).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE, ".env"), override=True)

import db  # noqa: E402
import waha_client  # noqa: E402


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    if not _truthy("WAHA_ALERT_WEBHOOK_SILENCE"):
        return 0
    if not waha_client.is_waha_configured():
        print("WAHA não configurado ou WAHA_NOTIFY_ENABLED inativo.", file=sys.stderr)
        return 1
    try:
        hours = float((os.environ.get("APPLYFY_WEBHOOK_SILENCE_HOURS") or "24").replace(",", "."))
    except ValueError:
        hours = 24.0
    if hours <= 0:
        return 0
    last = db.get_last_webhook_received_at()
    now = datetime.now(timezone.utc)
    if last is None:
        msg = "Applyfy — ALERTA: nenhum webhook registrado no banco ainda."
        ok, err = waha_client.send_text(msg)
        if not ok:
            print(err, file=sys.stderr)
            return 2
        print("Alerta enviado (sem webhooks nunca).")
        return 0
    aware = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
    delta = now - aware
    if delta <= timedelta(hours=hours):
        print("Dentro do limite; sem alerta.")
        return 0
    msg = (
        f"Applyfy — ALERTA: silêncio de webhooks há {delta.days}d {delta.seconds // 3600}h "
        f"(limite {hours}h). Último: {aware.isoformat()}"
    )
    ok, err = waha_client.send_text(msg)
    if not ok:
        print(err, file=sys.stderr)
        return 2
    print("Alerta de silêncio enviado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
