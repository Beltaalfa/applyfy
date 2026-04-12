#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sincroniza transações da API Admin para a tabela applyfy_tx_facts (cópia local).
Uso típico: cron com venv e .env carregados (ver DEPLOY.md).

  cd /var/www/applyfy && . env.sh && venv/bin/python scripts/sync_transactions.py

Opções:
  --backfill-webhooks   Percorre applyfy_transactions (webhooks) e preenche factos em falta.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"), override=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Applyfy Admin transactions → applyfy_tx_facts")
    parser.add_argument(
        "--backfill-webhooks",
        action="store_true",
        help="Agrega factos a partir dos payloads em applyfy_transactions",
    )
    parser.add_argument("--window-days", type=int, default=None, help="Janela rolling (default: APPLYFY_SYNC_WINDOW_DAYS ou 14)")
    args = parser.parse_args()

    import db
    import applyfy_tx_sync

    db.init_db()
    if args.backfill_webhooks:
        after = 0
        total_u = 0
        total_p = 0
        while True:
            p, u, after = db.backfill_tx_facts_from_webhooks(2000, after)
            total_p += p
            total_u += u
            print(f"backfill batch: processed={p} upserted={u} last_id={after}", flush=True)
            if p < 2000:
                break
        print(f"backfill done: rows_seen={total_p} facts_upserted={total_u}", flush=True)
        return 0

    meta = applyfy_tx_sync.sync_rolling_window_for_all_produtores(window_days=args.window_days)
    print(meta, flush=True)
    return 0 if not meta.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
