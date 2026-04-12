# -*- coding: utf-8 -*-
"""
Normalização de transações (webhook ou item da API Admin) para factos diários (vendas_net / chargeback).
Mesma lógica conceptual que app._tx_net_amount / _tx_is_refund_or_chargeback.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

__all__ = [
    "parse_tx_day",
    "tx_net_amount",
    "tx_is_refund_or_chargeback",
    "fact_from_api_item",
    "fact_from_webhook_payload",
    "daily_series_from_items",
]


def parse_tx_day(iso_ts: str | None) -> str | None:
    if not iso_ts:
        return None
    s = str(iso_ts).strip()
    return s[:10] if len(s) >= 10 else None


def tx_net_amount(it: dict[str, Any]) -> float:
    fin = it.get("financial") or {}
    for k in ("netSaleAmount", "clientPaidAmount", "grossAmount"):
        v = fin.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    for k in ("chargeAmount", "amount"):
        v = it.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return 0.0


def tx_is_refund_or_chargeback(it: dict[str, Any]) -> bool:
    st = (it.get("status") or "").upper()
    ss = (it.get("subStatus") or "").upper()
    if st in ("REFUNDED", "CANCELED", "DISPUTE", "CHARGEBACK"):
        return True
    if any(x in st for x in ("REFUND", "CHARGEBACK", "DISPUTE")):
        return True
    if any(x in ss for x in ("REFUND", "CHARGEBACK", "DISPUTE")):
        return True
    return False


def _item_from_webhook_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    event = payload.get("event") or ""
    if event == "PRODUCER_CREATED":
        return None
    trans = payload.get("transaction") or {}
    tid = trans.get("id")
    if not tid:
        return None
    producer = payload.get("producer") or {}
    email = (producer.get("email") or it_email(payload) or "").strip()
    if not email:
        return None
    fin = trans.get("financial") if isinstance(trans.get("financial"), dict) else {}
    if not fin.get("netSaleAmount") and trans.get("amount") is not None:
        fin = {**fin, "netSaleAmount": trans.get("amount")}
    return {
        "id": str(tid),
        "createdAt": trans.get("createdAt") or trans.get("createAt") or trans.get("payedAt") or trans.get("payed_at"),
        "date": trans.get("date"),
        "status": trans.get("status"),
        "subStatus": trans.get("subStatus"),
        "financial": fin,
        "chargeAmount": trans.get("amount"),
        "amount": trans.get("amount"),
        "producerEmail": email,
    }


def it_email(payload_or_item: dict[str, Any]) -> str:
    v = (payload_or_item.get("producerEmail") or payload_or_item.get("producer_email") or "").strip()
    return v


def fact_from_api_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Retorna dict para upsert em applyfy_tx_facts ou None."""
    tid = item.get("id") or item.get("transactionId") or item.get("transaction_id")
    if not tid:
        return None
    prod = item.get("producer") if isinstance(item.get("producer"), dict) else {}
    email = (it_email(item) or (prod.get("email") or "")).strip().lower()
    if not email:
        return None
    day = parse_tx_day(item.get("createdAt") or item.get("date") or item.get("created_at"))
    if not day:
        return None
    amt = tx_net_amount(item)
    if tx_is_refund_or_chargeback(item):
        vendas_net, chargeback = 0.0, abs(amt)
    else:
        vendas_net, chargeback = max(amt, 0.0), 0.0
    return {
        "transaction_id": str(tid),
        "producer_email": email,
        "tx_day": day,
        "vendas_net": round(vendas_net, 2),
        "chargeback": round(chargeback, 2),
        "source": "api_sync",
    }


def fact_from_webhook_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    it = _item_from_webhook_payload(payload)
    if not it:
        return None
    day = parse_tx_day(it.get("createdAt") or it.get("date"))
    if not day:
        return None
    amt = tx_net_amount(it)
    if tx_is_refund_or_chargeback(it):
        vendas_net, chargeback = 0.0, abs(amt)
    else:
        vendas_net, chargeback = max(amt, 0.0), 0.0
    email = (it.get("producerEmail") or "").strip().lower()
    return {
        "transaction_id": str(it["id"]),
        "producer_email": email,
        "tx_day": day,
        "vendas_net": round(vendas_net, 2),
        "chargeback": round(chargeback, 2),
        "source": "webhook",
    }


def daily_series_from_items(items: list, d_from: str, d_to: str) -> list[dict]:
    """Agrega lista de itens API (mesmo formato que list_transactions items) por dia."""
    d0 = date.fromisoformat(d_from[:10])
    d1 = date.fromisoformat(d_to[:10])
    daily_vendas: dict[str, float] = {}
    daily_cb: dict[str, float] = {}
    for it in items:
        day = parse_tx_day(it.get("createdAt") or it.get("date"))
        if not day or day < d_from[:10] or day > d_to[:10]:
            continue
        amt = tx_net_amount(it)
        if tx_is_refund_or_chargeback(it):
            daily_cb[day] = daily_cb.get(day, 0.0) + abs(amt)
        else:
            daily_vendas[day] = daily_vendas.get(day, 0.0) + max(amt, 0.0)
    out: list[dict] = []
    cur = d0
    while cur <= d1:
        ks = cur.isoformat()
        out.append(
            {
                "date": ks,
                "vendas_net": round(daily_vendas.get(ks, 0.0), 2),
                "chargeback": round(daily_cb.get(ks, 0.0), 2),
            }
        )
        cur += timedelta(days=1)
    return out
