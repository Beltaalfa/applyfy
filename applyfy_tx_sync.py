# -*- coding: utf-8 -*-
"""Sincronização de transações da API Admin para applyfy_tx_facts (cópia local)."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import applyfy_tx_facts


def fetch_all_transactions_period(
    producer_email: str,
    d_from: str,
    d_to: str,
    max_pages: int | None = None,
    page_size: int = 50,
) -> tuple[list | None, dict | str | None]:
    """Pagina GET /transactions (producerEmail + intervalo). Retorna (items, erro)."""
    import applyfy_api

    mp = max_pages if max_pages is not None else int(os.environ.get("APPLYFY_SYNC_MAX_PAGES", "500"))
    start = f"{d_from[:10]}T00:00:00"
    end = f"{d_to[:10]}T23:59:59"
    all_items: list = []
    page = 1
    while page <= mp:
        raw = {
            "producerEmail": producer_email.strip(),
            "start": start,
            "end": end,
            "page": page,
            "pageSize": page_size,
        }
        res, err = applyfy_api.list_transactions(raw)
        if err:
            return None, err
        if not res or res.get("success") is False:
            msg = (res or {}).get("error") if isinstance((res or {}).get("error"), str) else None
            if msg is None and isinstance((res or {}).get("error"), dict):
                msg = (res or {}).get("error", {}).get("message")
            return None, {"message": msg or "Resposta inválida da API de transações"}
        data = res.get("data") or {}
        items = data.get("items") or []
        all_items.extend(items)
        pag = data.get("pagination") or {}
        try:
            tp = int(pag.get("totalPages") or 1)
        except (TypeError, ValueError):
            tp = 1
        if page >= tp or not items:
            break
        page += 1
    return all_items, None


def upsert_items_into_facts(items: list) -> int:
    """Extrai factos e grava na base. Retorna quantidade upserted."""
    import db

    n = 0
    for it in items:
        fact = applyfy_tx_facts.fact_from_api_item(it)
        if fact:
            db.upsert_tx_fact(fact)
            n += 1
    return n


def sync_producer_email_window(producer_email: str, d_from: str, d_to: str) -> tuple[int, str | None]:
    """Sincroniza um intervalo para um produtor. Retorna (upsert_count, erro)."""
    items, err = fetch_all_transactions_period(producer_email, d_from, d_to)
    if err:
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return 0, msg
    n = upsert_items_into_facts(items or [])
    return n, None


def sync_rolling_window_for_all_produtores(
    window_days: int | None = None,
    max_producers: int | None = None,
) -> dict[str, Any]:
    """
    Para cada email em saldos_historico, sincroniza [hoje - window_days, hoje].
    max_producers: se definido (>0), processa só os primeiros N (modo rápido no painel).
    """
    import db

    wd = window_days if window_days is not None else int(os.environ.get("APPLYFY_SYNC_WINDOW_DAYS", "14"))
    end = date.today()
    start = end - timedelta(days=max(wd, 1))
    d_from = start.isoformat()
    d_to = end.isoformat()
    all_producers = db.get_produtores_emails()
    producers_total = len(all_producers)
    if max_producers is not None and max_producers > 0:
        producers = all_producers[:max_producers]
    else:
        producers = all_producers
    total_upsert = 0
    errors: list[dict[str, str]] = []
    per_email: list[dict[str, Any]] = []
    for p in producers:
        em = (p.get("email") or "").strip()
        if not em:
            continue
        n, err = sync_producer_email_window(em, d_from, d_to)
        total_upsert += n
        per_email.append({"email": em, "upserted": n, "error": err})
        if err:
            errors.append({"email": em, "error": err})
    capped = max_producers is not None and max_producers > 0 and producers_total > len(producers)
    meta = {
        "window_days": wd,
        "from": d_from,
        "to": d_to,
        "producers": len(producers),
        "producers_total": producers_total,
        "sync_partial": capped,
        "total_upserted": total_upsert,
        "errors": errors,
        "per_email": per_email,
    }
    db.set_sync_state(
        "last_rolling_sync",
        {
            "at": end.isoformat(),
            **meta,
        },
    )
    return meta
