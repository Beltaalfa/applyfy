# -*- coding: utf-8 -*-
"""Notificações pós-export (resumo + metas) e alertas opcionais via WAHA."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import config
import waha_client


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _fmt_money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _run_at_label(run_at: Any) -> str:
    if run_at is None:
        return "–"
    if hasattr(run_at, "strftime"):
        return run_at.strftime("%d/%m/%Y %H:%M")
    return str(run_at)


def build_export_summary(
    resultados: list[dict],
    log_rows: list[dict],
    run_at: Any,
) -> str:
    ok_c = sum(1 for r in log_rows if r.get("status") == "OK")
    timeout_c = sum(1 for r in log_rows if r.get("status") == "TIMEOUT")
    erro_c = sum(1 for r in log_rows if r.get("status") == "ERRO")
    lines = [
        "Applyfy — exportação de saldos concluída",
        f"Run: {_run_at_label(run_at)}",
        f"Produtores: {len(resultados)}",
        f"Linhas log — OK: {ok_c} | TIMEOUT: {timeout_c} | ERRO: {erro_c}",
    ]
    return "\n".join(lines)


def build_metas_hit_message(
    resultados: list[dict],
    meta_valor: float,
    max_lines: int = 12,
) -> str | None:
    if meta_valor <= 0:
        return None
    hits: list[tuple[str, str, float]] = []
    for row in resultados:
        try:
            vl = float(row.get("Vendas líquidas") or 0)
        except (TypeError, ValueError):
            vl = 0.0
        if vl >= meta_valor:
            nome = (row.get("Nome") or "–").strip()
            email = (row.get("Email") or "").strip()
            hits.append((nome, email, vl))
    if not hits:
        return None
    hits.sort(key=lambda x: -x[2])
    extra = max(0, len(hits) - max_lines)
    shown = hits[:max_lines]
    lines = [
        f"Metas batidas (≥ {_fmt_money(meta_valor)} vendas líquidas): {len(hits)} produtor(es)",
    ]
    for nome, email, vl in shown:
        lines.append(f"• {nome} — {_fmt_money(vl)}" + (f" ({email})" if email else ""))
    if extra:
        lines.append(f"… e mais {extra} (ver painel /meta)")
    return "\n".join(lines)


def notify_export_success(
    resultados: list[dict],
    log_rows: list[dict],
    run_at: Any,
) -> None:
    """Envia WAHA após export bem-sucedido (resumo + opcional lista de metas)."""
    if not waha_client.is_waha_configured():
        return
    summary = build_export_summary(resultados, log_rows, run_at)
    ok, err = waha_client.send_text(summary)
    if not ok:
        print(f"[WAHA] Falha ao enviar resumo: {err}", flush=True)
    meta = config.get_meta_vendas_liquidas()
    meta_msg = build_metas_hit_message(resultados, meta)
    if meta_msg:
        ok2, err2 = waha_client.send_text(meta_msg)
        if not ok2:
            print(f"[WAHA] Falha ao enviar metas: {err2}", flush=True)


def notify_failure(message: str) -> None:
    """Alerta curto (login falhou, limite de horas, etc.) se WAHA_ALERT_ON_FAILURE=1."""
    if not _truthy("WAHA_ALERT_ON_FAILURE"):
        return
    if not waha_client.is_waha_configured():
        return
    text = f"Applyfy — ALERTA\n{message}"
    ok, err = waha_client.send_text(text)
    if not ok:
        print(f"[WAHA] Falha alerta: {err}", flush=True)
