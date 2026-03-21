# -*- coding: utf-8 -*-
"""Orquestrador de exportação de vendas ApplyFy com UPSERT em PostgreSQL."""
from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any

from playwright.sync_api import Page, TimeoutError as PWTimeout, sync_playwright

import config
from applyfy_models import ImportStats, VendaConsolidada
from applyfy_parser import parse_order_detail
from applyfy_repository import (
    get_next_row_index_for_export_resume,
    init_applyfy_vendas_db,
    log_import_event,
    upsert_venda,
)

BASE_URL = "https://app.applyfy.com.br"
ORDERS_PAGE_SIZE = int(os.environ.get("ORDERS_PAGE_SIZE", "50"))
CHECKPOINT_FILE = os.path.join(config.DATA_DIR, "orders_export_checkpoint.json")
LOG_TXT = config.ORDERS_LOG_TXT
LOG_CSV = config.ORDERS_LOG_CSV
LOG_JSON = config.ORDERS_LOG_JSON
SEL_TIMEOUT = int(os.environ.get("EXPORT_VENDAS_SEL_TIMEOUT_MS", "120000"))
ORDERS_SEL_TIMEOUT = int(os.environ.get("EXPORT_VENDAS_ORDERS_SEL_TIMEOUT_MS", str(SEL_TIMEOUT)))
NAV_TIMEOUT = 180000
ORDERS_PAGE_LOAD_RETRIES = max(1, int(os.environ.get("EXPORT_VENDAS_ORDERS_LOAD_RETRIES", "3")))
ORDERS_SETTLE_MS = int(os.environ.get("EXPORT_VENDAS_ORDERS_SETTLE_MS", "2500"))
GOTO_RETRIES = max(1, int(os.environ.get("EXPORT_VENDAS_GOTO_RETRIES", "5")))
GOTO_RETRY_BASE_SEC = max(0.5, float(os.environ.get("EXPORT_VENDAS_GOTO_RETRY_SEC", "2")))
DETAIL_CLICK_MS = int(os.environ.get("EXPORT_VENDAS_DETAIL_CLICK_MS", "60000"))


def _is_transient_navigation_error(exc: BaseException) -> bool:
    """Erros de rede/DNS comuns no Chromium que costumam sumir ao repetir o goto."""
    msg = str(exc).lower()
    markers = (
        "err_network_changed",
        "err_connection_reset",
        "err_internet_disconnected",
        "err_connection_refused",
        "err_address_unreachable",
        "err_name_not_resolved",
        "err_timed_out",
        "err_tunnel_connection_failed",
        "err_ssl_protocol_error",
        "net::err",
        "target page, context or browser has been closed",
        "navigation failed",
    )
    return any(m in msg for m in markers)


def _goto_with_retry(page: Page, url: str, *, label: str = "") -> None:
    """page.goto com novas tentativas para falhas transitórias (ex.: net::ERR_NETWORK_CHANGED)."""
    last: BaseException | None = None
    suffix = f" ({label})" if label else ""
    for attempt in range(1, GOTO_RETRIES + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            if attempt > 1:
                _log(f"Navegação OK na tentativa {attempt}/{GOTO_RETRIES}{suffix}")
            return
        except PWTimeout as e:
            last = e
            _log(f"goto timeout tentativa {attempt}/{GOTO_RETRIES}{suffix}: {e!s}")
            if attempt >= GOTO_RETRIES:
                raise
            time.sleep(GOTO_RETRY_BASE_SEC * attempt)
        except Exception as e:
            last = e
            if not _is_transient_navigation_error(e) or attempt >= GOTO_RETRIES:
                raise
            _log(f"goto rede transitória tentativa {attempt}/{GOTO_RETRIES}{suffix}: {e!s}")
            time.sleep(GOTO_RETRY_BASE_SEC * attempt)
    if last:
        raise last


def _log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_checkpoint() -> tuple[int, int]:
    if not os.path.isfile(CHECKPOINT_FILE):
        return 1, 0
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("pagina", 1)), int(data.get("linha", 0))
    except Exception:
        return 1, 0


def _save_checkpoint(pagina: int, linha: int) -> None:
    payload = {"pagina": pagina, "linha": linha, "saved_at": datetime.now().isoformat()}
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _clear_checkpoint() -> None:
    if os.path.isfile(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)


def _resolve_export_start() -> tuple[int, int]:
    """
    Define (página, próximo_índice_linha 0-based).

    Se EXPORT_VENDAS_START_PAGINA estiver definido (ex.: 29), ignora o checkpoint em disco
    e calcula a linha inicial com base no último registro OK em applyfy_import_log nessa página.
    """
    raw = os.environ.get("EXPORT_VENDAS_START_PAGINA", "").strip()
    if raw:
        p = max(1, int(raw))
        try:
            r = get_next_row_index_for_export_resume(p)
        except Exception as e:
            _log(f"Aviso: não foi possível ler applyfy_import_log ({e}). Começando na linha 1 da página {p}.")
            r = 0
        _log(
            f"Retomada por env: página {p} (EXPORT_VENDAS_START_PAGINA), "
            f"próximo índice de linha na lista={r} (equivalente à linha {r + 1} na UI), "
            f"derivado do último status=OK no Postgres."
        )
        _save_checkpoint(p, r)
        return p, r
    return _load_checkpoint()


def _write_log_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "timestamp",
        "pagina",
        "linha",
        "movimento",
        "total_movimentos",
        "codigo_venda",
        "transaction_id",
        "status",
        "source_strategy",
        "duracao_segundos",
        "mensagem",
    ]
    with open(LOG_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _save_json_snapshot(vendas: list[VendaConsolidada]) -> None:
    with open(LOG_JSON, "w", encoding="utf-8") as f:
        json.dump([asdict(v) for v in vendas], f, ensure_ascii=False, default=str, indent=2)


def _is_auth_or_2fa(page: Page) -> bool:
    url = page.url.lower()
    if "/auth/" in url:
        return True
    try:
        return page.get_by_text("Autenticação de 2 fatores", exact=False).count() > 0
    except Exception:
        return False


def _raise_session_expired(page: Page, onde: str) -> None:
    """Erro explícito em PT: cookie/storage da ApplyFy não vale mais."""
    raise RuntimeError(
        f"Sessão ApplyFy expirada ou não carregada ({onde}).\n"
        f"URL atual: {page.url!r}\n\n"
        "O que fazer no SERVIDOR (mesmo usuário Linux que roda o export, ex.: tactical ou www-data):\n"
        "  cd /var/www/applyfy && source venv/bin/activate && python3 01_salvar_sessao.py\n"
        "Complete login + 2FA no navegador; isso atualiza data/sessao_applyfy.json.\n\n"
        "Confira também:\n"
        "  • APPLYFY_DATA_DIR aponta para a pasta onde está sessao_applyfy.json (se usar);\n"
        "  • Quem clica 'Iniciar export' no painel é o mesmo usuário do gunicorn — a sessão tem de ser dele.\n"
    )


def _require_orders_session(page: Page, onde: str) -> None:
    if _is_auth_or_2fa(page):
        _raise_session_expired(page, onde)


# Vários padrões: Next/React pode usar table, div com role=row ou linhas só com link de pedido.
_ORDERS_ROW_SELECTORS = (
    "table tbody tr",
    "tbody tr",
    "table tr",
    "[role='row']",
    "[role=row]",
    "tr:has(a[href*='/admin/orders/'])",
)


def _log_orders_page_debug(page: Page, pagina: int, extra: str = "") -> None:
    """Grava pista no .txt e opcionalmente screenshot quando a lista não aparece."""
    try:
        url = page.url
        title = page.title()
        snippet = ""
        try:
            snippet = (page.inner_text("body") or "")[:1200].replace("\n", " ")
        except Exception:
            pass
        _log(
            f"DEBUG lista pedidos pág.{pagina}: url={url!r} title={title!r} {extra} "
            f"body≈{snippet[:400]}…"
        )
    except Exception as e:
        _log(f"DEBUG lista pedidos (falha ao coletar): {e}")
    path = os.path.join(config.DATA_DIR, f"orders_list_fail_p{pagina}.png")
    try:
        page.screenshot(path=path, full_page=True)
        _log(f"Screenshot salvo em {path}")
    except Exception as e:
        _log(f"Screenshot falhou: {e}")


def _count_order_like_rows(page: Page) -> int:
    for sel in _ORDERS_ROW_SELECTORS:
        try:
            n = page.locator(sel).count()
            if n > 0:
                return n
        except Exception:
            continue
    return 0


def _wait_orders_table_ready(page: Page, pagina: int) -> None:
    """
    Aguarda linhas da lista de pedidos. Usa state=attached (às vezes a UI não marca como visible).
    Com reload e várias tentativas se a SPA demorar ou falhar rede.
    """
    last_err: str | None = None
    combined = ", ".join(_ORDERS_ROW_SELECTORS)
    for attempt in range(1, ORDERS_PAGE_LOAD_RETRIES + 1):
        try:
            if _is_auth_or_2fa(page):
                _raise_session_expired(page, f"lista pedidos pág.{pagina}, tent.{attempt}")
            try:
                page.wait_for_load_state("load", timeout=min(90000, ORDERS_SEL_TIMEOUT))
            except Exception as e:
                _log(f"Aviso: wait load após lista (tent.{attempt}): {e!s}")
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            if ORDERS_SETTLE_MS > 0:
                time.sleep(max(0.2, ORDERS_SETTLE_MS / 1000.0))
            page.wait_for_selector(combined, state="attached", timeout=ORDERS_SEL_TIMEOUT)
            n = _count_order_like_rows(page)
            if n > 0:
                if attempt > 1:
                    _log(f"Lista de pedidos OK na tentativa {attempt} (pág.{pagina}, ~{n} linhas).")
                return
            last_err = f"seletores anexados mas nenhuma linha contável (count=0)"
        except Exception as e:
            last_err = str(e)
            _log(f"Espera lista pedidos pág.{pagina} tent.{attempt}/{ORDERS_PAGE_LOAD_RETRIES}: {e!s}")
        if attempt < ORDERS_PAGE_LOAD_RETRIES:
            time.sleep(2.0 * attempt)
            url = f"{BASE_URL}/admin/orders?page={pagina}&pageSize={ORDERS_PAGE_SIZE}"
            _log(f"Nova navegação para lista (sem reload F5) pág.{pagina}…")
            _goto_with_retry(page, url, label=f"retry lista pág.{pagina}")
            _require_orders_session(page, f"após retry lista pág.{pagina}")
    _log_orders_page_debug(page, pagina, extra=last_err or "")
    raise RuntimeError(
        f"Timeout aguardando tabela de pedidos (página {pagina}). "
        f"Último erro: {last_err}. Confira sessão, screenshot em data/orders_list_fail_p{pagina}.png e APPLYFY_HEADED=1."
    )


def _open_orders_page(page: Page, pagina: int) -> None:
    url = f"{BASE_URL}/admin/orders?page={pagina}&pageSize={ORDERS_PAGE_SIZE}"
    _goto_with_retry(page, url, label=f"lista pedidos pág.{pagina}")
    _require_orders_session(page, f"logo após abrir /admin/orders pág.{pagina}")
    _wait_orders_table_ready(page, pagina)


def _get_order_rows(page: Page):
    if page.locator("table tbody tr").count() > 0:
        return page.locator("table tbody tr"), "table tbody tr"
    if page.locator("tbody tr").count() > 0:
        return page.locator("tbody tr"), "tbody tr"
    n_role = page.locator("[role=row]").count()
    if n_role > 0:
        return page.locator("[role=row]"), "[role=row]"
    n_tr = page.locator("tr:has(a[href*='/admin/orders/'])").count()
    if n_tr > 0:
        return page.locator("tr:has(a[href*='/admin/orders/'])"), "tr order link"
    return page.locator("[role=row]"), "[role=row]"


def _extract_order_link_from_row(row) -> str | None:
    href = row.locator("a[href*='/admin/orders/']").first.get_attribute("href")
    if href:
        return href if href.startswith("http") else f"{BASE_URL}{href}"
    return None


def _extract_code_from_row(row) -> str | None:
    try:
        txt = row.inner_text()
        for token in txt.split():
            if len(token) > 18 and token.startswith("cm"):
                return token
        return None
    except Exception:
        return None


def _open_order_detail(page: Page, row, fallback_code: str | None) -> str:
    href = None
    try:
        href = _extract_order_link_from_row(row)
    except Exception:
        href = None
    if href:
        _goto_with_retry(page, href, label="detalhe venda (href)")
        return page.url

    row.locator("button").last.click(timeout=DETAIL_CLICK_MS)
    page.wait_for_load_state("domcontentloaded", timeout=60000)
    if "/admin/orders/" in page.url:
        return page.url
    if fallback_code:
        detail_url = f"{BASE_URL}/admin/orders/{fallback_code}"
        _goto_with_retry(page, detail_url, label=f"detalhe {fallback_code}")
        return page.url
    raise RuntimeError("Não foi possível abrir o detalhe da venda.")


def run_export_vendas() -> ImportStats:
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    except ImportError:
        pass
    config.ensure_data_dir()
    init_applyfy_vendas_db()

    start_page, start_row = _resolve_export_start()
    run_at = datetime.now()
    stats = ImportStats()
    vendas_snapshot: list[VendaConsolidada] = []
    log_rows: list[dict[str, Any]] = []

    headed = os.environ.get("APPLYFY_HEADED", "").lower() in ("1", "true", "yes")
    use_headed = headed and config.has_display_server()
    if headed and not use_headed:
        _log("Sem DISPLAY; forçando headless.")

    _log(f"INÍCIO export vendas | página inicial={start_page} linha inicial={start_row + 1}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not use_headed,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            storage_state=config.SESSION_FILE,
            locale="pt-BR",
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        page.set_default_timeout(SEL_TIMEOUT)
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        pagina = start_page
        while True:
            _open_orders_page(page, pagina)
            if _is_auth_or_2fa(page):
                _raise_session_expired(page, "loop principal /admin/orders")

            rows, _ = _get_order_rows(page)
            total_linhas = rows.count()
            if total_linhas == 0:
                break

            stats.paginas += 1
            linha_inicio = start_row if pagina == start_page else 0
            _log(f"Página {pagina}: {total_linhas} vendas (iniciando linha {linha_inicio + 1}).")

            for i in range(linha_inicio, total_linhas):
                inicio = time.perf_counter()
                status = "OK"
                mensagem = ""
                source_strategy: str | None = None
                venda: VendaConsolidada | None = None
                codigo_venda_row = None
                tx_id: str | None = None
                try:
                    _open_orders_page(page, pagina)
                    rows, _ = _get_order_rows(page)
                    row = rows.nth(i)
                    codigo_venda_row = _extract_code_from_row(row)
                    _open_order_detail(page, row, codigo_venda_row)
                    if _is_auth_or_2fa(page):
                        _raise_session_expired(page, "detalhe da venda")

                    bundles, source_strategy = parse_order_detail(page)
                    if not bundles:
                        raise ValueError("Parse não retornou vendas (detalhe vazio).")
                    total_mov = len(bundles)
                    for mov_i, (venda, fees, attempts, webhooks) in enumerate(bundles, start=1):
                        if not venda.codigo_venda:
                            venda.codigo_venda = codigo_venda_row
                        if not venda.order_id:
                            venda.order_id = venda.codigo_venda or codigo_venda_row
                        result = upsert_venda(venda, fees, attempts, webhooks)
                        if result == "inserted":
                            stats.inseridas += 1
                        elif result == "updated":
                            stats.atualizadas += 1
                        tx_id = venda.transaction_id
                        vendas_snapshot.append(venda)
                        stats.processadas += 1
                        dur = round(time.perf_counter() - inicio, 3)
                        log_row = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pagina": pagina,
                            "linha": i + 1,
                            "movimento": mov_i,
                            "total_movimentos": total_mov,
                            "codigo_venda": venda.codigo_venda,
                            "transaction_id": tx_id,
                            "status": status,
                            "source_strategy": source_strategy,
                            "duracao_segundos": dur,
                            "mensagem": mensagem,
                        }
                        log_rows.append(log_row)
                        _write_log_csv(log_rows)
                        log_import_event(
                            run_at=run_at,
                            pagina=pagina,
                            linha=i + 1,
                            codigo_venda=log_row["codigo_venda"],
                            transaction_id=tx_id,
                            source_strategy=source_strategy,
                            status=status,
                            duracao_segundos=dur,
                            mensagem=mensagem or None,
                        )
                        _log(
                            f"{status} | página={pagina} linha={i + 1}/{total_linhas} "
                            f"mov={mov_i}/{total_mov} codigo={log_row['codigo_venda']} "
                            f"tx={tx_id} strategy={source_strategy} dur={dur}s"
                        )
                    _save_json_snapshot(vendas_snapshot)
                    _save_checkpoint(pagina, i + 1)
                except PWTimeout as e:
                    status = "TIMEOUT"
                    mensagem = str(e)[:500]
                    stats.erros += 1
                    dur = round(time.perf_counter() - inicio, 3)
                    log_row = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "pagina": pagina,
                        "linha": i + 1,
                        "movimento": 0,
                        "total_movimentos": 0,
                        "codigo_venda": codigo_venda_row,
                        "transaction_id": tx_id,
                        "status": status,
                        "source_strategy": source_strategy,
                        "duracao_segundos": dur,
                        "mensagem": mensagem,
                    }
                    log_rows.append(log_row)
                    _write_log_csv(log_rows)
                    _save_json_snapshot(vendas_snapshot)
                    _save_checkpoint(pagina, i + 1)
                    log_import_event(
                        run_at=run_at,
                        pagina=pagina,
                        linha=i + 1,
                        codigo_venda=log_row["codigo_venda"],
                        transaction_id=tx_id,
                        source_strategy=source_strategy,
                        status=status,
                        duracao_segundos=dur,
                        mensagem=mensagem or None,
                    )
                    _log(
                        f"{status} | página={pagina} linha={i + 1}/{total_linhas} "
                        f"codigo={log_row['codigo_venda']} strategy={source_strategy} dur={dur}s"
                    )
                except Exception as e:
                    status = "ERRO"
                    mensagem = str(e)[:500]
                    stats.erros += 1
                    dur = round(time.perf_counter() - inicio, 3)
                    log_row = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "pagina": pagina,
                        "linha": i + 1,
                        "movimento": 0,
                        "total_movimentos": 0,
                        "codigo_venda": codigo_venda_row,
                        "transaction_id": tx_id,
                        "status": status,
                        "source_strategy": source_strategy,
                        "duracao_segundos": dur,
                        "mensagem": mensagem,
                    }
                    log_rows.append(log_row)
                    _write_log_csv(log_rows)
                    _save_json_snapshot(vendas_snapshot)
                    _save_checkpoint(pagina, i + 1)
                    log_import_event(
                        run_at=run_at,
                        pagina=pagina,
                        linha=i + 1,
                        codigo_venda=log_row["codigo_venda"],
                        transaction_id=tx_id,
                        source_strategy=source_strategy,
                        status=status,
                        duracao_segundos=dur,
                        mensagem=mensagem or None,
                    )
                    _log(
                        f"{status} | página={pagina} linha={i + 1}/{total_linhas} "
                        f"codigo={log_row['codigo_venda']} strategy={source_strategy} dur={dur}s"
                    )

            pagina += 1
            start_row = 0

        browser.close()

    _clear_checkpoint()
    _log(
        f"FIM | páginas={stats.paginas} processadas={stats.processadas} "
        f"inseridas={stats.inseridas} atualizadas={stats.atualizadas} erros={stats.erros}"
    )
    return stats
