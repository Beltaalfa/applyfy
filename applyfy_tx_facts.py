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

_DBG_H5_LOGS = 0
_DBG_H5_LOG_CAP = 8


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
        "acquirer": trans.get("acquirer"),
        "paymentMethod": trans.get("paymentMethod") or trans.get("payment_method"),
    }


def it_email(payload_or_item: dict[str, Any]) -> str:
    v = (payload_or_item.get("producerEmail") or payload_or_item.get("producer_email") or "").strip()
    return v


def _coerce_acquirer_value(v: Any) -> str | None:
    """Aceita string ou objeto (ex.: ``{{name, slug}}``) como na API Admin."""
    if v is None:
        return None
    if isinstance(v, dict):
        for k in ("name", "slug", "id", "code", "key", "value"):
            x = v.get(k)
            if x is not None and str(x).strip():
                return str(x).strip()
        return None
    s = str(v).strip()
    return s or None


def _extract_acquirer_payment_from_api_item(item: dict[str, Any]) -> tuple[str | None, str | None]:
    """
    GET /transactions devolve muitas vezes ``acquirer`` / ``paymentMethod`` dentro de ``transaction``,
    não no raiz do item — alinhar ao webhook (``payload['transaction']``).
    Algumas respostas aninham ainda em ``payment``, ``data`` ou usam ``gateway`` / ``acquirerName``.
    """
    trans = item.get("transaction")
    trans = trans if isinstance(trans, dict) else {}
    data = item.get("data") if isinstance(item.get("data"), dict) else {}
    pay_t = trans.get("payment") if isinstance(trans.get("payment"), dict) else {}
    pay_i = item.get("payment") if isinstance(item.get("payment"), dict) else {}

    def _pm_from(d: dict[str, Any]) -> str | None:
        pm = d.get("paymentMethod") or d.get("payment_method")
        if isinstance(pm, dict):
            pm = pm.get("name") or pm.get("code") or pm.get("id")
        if pm is None:
            return None
        s = str(pm).strip()
        return s or None

    acq = None
    for cand in (
        item.get("acquirer"),
        trans.get("acquirer"),
        pay_t.get("acquirer"),
        pay_i.get("acquirer"),
        data.get("acquirer"),
        item.get("gateway"),
        trans.get("gateway"),
        data.get("gateway"),
        item.get("acquirerName"),
        item.get("acquirer_name"),
        trans.get("acquirerName"),
        trans.get("acquirer_name"),
    ):
        acq = _coerce_acquirer_value(cand)
        if acq:
            break

    pm = _pm_from(item) or _pm_from(trans) or _pm_from(data) or _pm_from(pay_t) or _pm_from(pay_i)
    return acq, pm


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
    acq_raw, pm_raw = _extract_acquirer_payment_from_api_item(item)

    # #region agent log
    global _DBG_H5_LOGS
    try:
        trans = item.get("transaction") if isinstance(item.get("transaction"), dict) else {}
        top_a = item.get("acquirer")
        nested_a = trans.get("acquirer") if trans else None
        if (
            _DBG_H5_LOGS < _DBG_H5_LOG_CAP
            and (not (top_a is not None and str(top_a).strip()))
            and (nested_a is not None and str(nested_a).strip())
        ):
            import json
            import time as _time

            _DBG_H5_LOGS += 1
            _pl = {
                "sessionId": "d1495d",
                "hypothesisId": "H5",
                "location": "applyfy_tx_facts.py:fact_from_api_item",
                "message": "adquirente só no objeto transaction (API)",
                "data": {"resolved_acquirer": acq_raw, "transaction_id": str(tid)[:32]},
                "timestamp": int(_time.time() * 1000),
            }
            with open("/var/www/.cursor/debug-d1495d.log", "a", encoding="utf-8") as _df:
                _df.write(json.dumps(_pl, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion

    return {
        "transaction_id": str(tid),
        "producer_email": email,
        "tx_day": day,
        "vendas_net": round(vendas_net, 2),
        "chargeback": round(chargeback, 2),
        "source": "api_sync",
        "acquirer": acq_raw,
        "payment_method": pm_raw,
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
    acq_raw = it.get("acquirer")
    pm_raw = it.get("paymentMethod") or it.get("payment_method")
    return {
        "transaction_id": str(it["id"]),
        "producer_email": email,
        "tx_day": day,
        "vendas_net": round(vendas_net, 2),
        "chargeback": round(chargeback, 2),
        "source": "webhook",
        "acquirer": str(acq_raw).strip() if acq_raw is not None and str(acq_raw).strip() else None,
        "payment_method": str(pm_raw).strip() if pm_raw is not None and str(pm_raw).strip() else None,
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
