# -*- coding: utf-8 -*-
"""Parse de ficheiros OFX (extrato bancário)."""
from __future__ import annotations

from datetime import date, datetime
from io import StringIO
from typing import Any

from ofxparse import OfxParser


def _decode_ofx_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def _to_date(d: Any) -> date:
    if d is None:
        return date.today()
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    s = str(d)[:10].replace("-", "")
    if len(s) >= 8 and s[:8].isdigit():
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return date.today()


def parse_ofx_bytes(data: bytes) -> list[dict[str, Any]]:
    text = _decode_ofx_bytes(data)
    ofx = OfxParser.parse(StringIO(text))
    out: list[dict[str, Any]] = []
    for acc in ofx.accounts or []:
        stmt = acc.statement
        bank_id = (getattr(acc, "routing_number", None) or getattr(acc, "bank_id", None) or "") or ""
        acct_id = (getattr(acc, "account_id", None) or getattr(acc, "number", None) or "") or ""
        conta_ref = f"{bank_id}|{acct_id}".strip("|") or "sem_conta"
        txs = []
        for t in stmt.transactions or []:
            amt = float(t.amount) if t.amount is not None else 0.0
            tipo = "credito" if amt > 0 else "debito"
            fitid = getattr(t, "id", None) or getattr(t, "fit_id", None)
            if fitid is not None:
                fitid = str(fitid).strip()[:128] or None
            memo = ((getattr(t, "memo", None) or "") or "").strip()
            payee = ((getattr(t, "payee", None) or "") or "").strip()
            if not memo and payee:
                memo = payee
            txs.append(
                {
                    "data_mov": _to_date(getattr(t, "date", None)),
                    "valor": round(amt, 2),
                    "tipo": tipo,
                    "memo": memo[:2000] or None,
                    "payee": payee[:500] or None,
                    "fitid": fitid,
                }
            )
        balance_end = getattr(stmt, "balance", None)
        balance_date = _to_date(getattr(stmt, "balance_date", None)) if getattr(stmt, "balance_date", None) else None
        start = getattr(stmt, "start_date", None)
        end = getattr(stmt, "end_date", None)
        out.append(
            {
                "conta_ref": conta_ref[:200],
                "bank_id": str(bank_id)[:64] or None,
                "account_id": str(acct_id)[:64] or None,
                "routing_number": str(bank_id)[:32] or None,
                "currency": (getattr(stmt, "currency", None) or getattr(acc, "currency", None) or "BRL")[:8],
                "balance_end": float(balance_end) if balance_end is not None else None,
                "balance_date": balance_date.isoformat() if balance_date else None,
                "periodo_inicio": _to_date(start).isoformat() if start else None,
                "periodo_fim": _to_date(end).isoformat() if end else None,
                "transacoes": txs,
            }
        )
    return out
