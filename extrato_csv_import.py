# -*- coding: utf-8 -*-
"""CSV Nubank: Data, Valor, Identificador, Descrição."""
from __future__ import annotations

import csv
import io
import re
from datetime import date

NU_FILENAME_ACCOUNT_RE = re.compile(r"NU_(\d+)_", re.IGNORECASE)


def _parse_br_float(s: str) -> float:
    s = (s or "").strip().replace(" ", "").replace("\xa0", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def _parse_br_date(s: str) -> date:
    parts = (s or "").strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Data inválida: {s!r}")
    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
    if y < 100:
        y += 2000
    return date(y, m, d)


def _conta_ref_from_filename(filename: str) -> str:
    m = NU_FILENAME_ACCOUNT_RE.search(filename or "")
    if m:
        return f"nubank|{m.group(1)}"
    return "nubank|csv"


def parse_nubank_csv_bytes(data: bytes, filename: str = "") -> dict | None:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")
    f = io.StringIO(text)
    reader = csv.DictReader(f, delimiter=",")
    if not reader.fieldnames:
        return None
    lower = {(h or "").strip().lower(): h for h in reader.fieldnames}

    def pick(*names: str):
        for n in names:
            if n in lower:
                return lower[n]
        return None

    c_data = pick("data")
    c_val = pick("valor")
    c_id = pick("identificador")
    c_desc = pick("descrição", "descricao")
    if not c_data or not c_val or not c_id:
        return None
    if not c_desc:
        for k, orig in lower.items():
            if "descr" in k:
                c_desc = orig
                break
    if not c_desc:
        return None
    txs = []
    for row in reader:
        try:
            ds = (row.get(c_data) or "").strip()
            if not ds:
                continue
            dm = _parse_br_date(ds)
            val = _parse_br_float(row.get(c_val) or "0")
            tipo = "credito" if val > 0 else "debito"
            fid = (row.get(c_id) or "").strip()[:128] or None
            memo = (row.get(c_desc) or "").strip()[:2000] or None
            txs.append(
                {"data_mov": dm, "valor": round(val, 2), "tipo": tipo, "fitid": fid, "memo": memo, "payee": None}
            )
        except (ValueError, TypeError, KeyError):
            continue
    if not txs:
        return None
    m = NU_FILENAME_ACCOUNT_RE.search(filename or "")
    return {
        "conta_ref": _conta_ref_from_filename(filename)[:200],
        "account_id": m.group(1) if m else None,
        "transacoes": txs,
    }
