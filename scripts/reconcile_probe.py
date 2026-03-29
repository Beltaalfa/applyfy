#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Imprime contagens básicas para inspeção de reconciliação (somente leitura)."""
from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE, ".env"), override=True)

import db  # noqa: E402


def main() -> int:
    if not db.get_database_url():
        print("DATABASE_URL não configurado.")
        return 1
    db.init_db()
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM saldos_historico;")
        n_saldos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM applyfy_transactions;")
        n_tx = cur.fetchone()[0]
        cur.execute("SELECT MAX(run_at) FROM export_runs;")
        last_ex = cur.fetchone()[0]
        cur.execute("SELECT MAX(received_at) FROM applyfy_transactions;")
        last_wh = cur.fetchone()[0]
    print("saldos_historico rows:", n_saldos)
    print("applyfy_transactions rows:", n_tx)
    print("last export_runs.run_at:", last_ex)
    print("last webhook received_at:", last_wh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
