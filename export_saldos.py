# -*- coding: utf-8 -*-
"""
Lógica de exportação de saldos dos produtores Applyfy.
Usa sessao_applyfy.json em config.DATA_DIR.
Retorna lista de dicts e grava CSV/XLSX em config.
"""
import json
import os
import time
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import config
import db

config.ensure_data_dir()

BASE_URL = "https://app.applyfy.com.br"
PAGE_SIZE = 20
ESPERA_CARREGAR_LISTA = 10  # segundos após clicar (site pode demorar)
ESPERA_PROXIMA_DISPONIVEL = 7
NAV_TIMEOUT = 180000
SEL_TIMEOUT = 120000   # 90s para seletores (página pode demorar)
CLICK_TIMEOUT = 120000  # 60s para cliques (tela de saldo pode ser lenta)


def _log_txt(msg: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    with open(config.LOG_TXT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _money_to_float(txt: str) -> float:
    if not txt:
        return 0.0
    txt = txt.replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return 0.0


def _get_total_from_card(page, title: str) -> float:
    try:
        card = page.locator(f"text={title}").first.locator("..").locator("..")
        total_locator = card.locator("text=Total").first.locator("xpath=following::p[1]")
        if total_locator.count() == 0:
            return 0.0
        return _money_to_float(total_locator.first.inner_text(timeout=SEL_TIMEOUT))
    except Exception:
        return 0.0


LIST_WAIT = 120000   # 120s para aparecer table OU [role=row] (um único wait longo para API lenta)
ROWS_WAIT = 90000   # 90s para linhas (depois segue com 0 linhas se timeout)

def _wait_lista(page):
    """Espera a lista carregar. Aceita <table> ou grid com [role=row]. Retorna seletor de linhas."""
    try:
        page.wait_for_selector("table, [role=row]", timeout=LIST_WAIT)
    except PWTimeout:
        try:
            page.screenshot(path=os.path.join(config.DATA_DIR, "debug_producers_fail.png"))
            with open(os.path.join(config.DATA_DIR, "debug_producers_fail.html"), "w", encoding="utf-8") as f:
                f.write(page.content())
        except Exception:
            pass
        raise
    time.sleep(ESPERA_CARREGAR_LISTA)
    if page.locator("table").count() > 0:
        try:
            page.wait_for_selector("table tbody tr", timeout=ROWS_WAIT)
        except PWTimeout:
            pass
        return "table tbody tr"
    return "[role=row]"


def _cell_locator(row, row_selector: str):
    """Locator da primeira célula da linha (td para table, role=cell para grid)."""
    if row_selector == "table tbody tr":
        return row.locator("td").first
    return row.locator("[role=cell], [role=gridcell], td").first

def _get_primeiro_nome_da_lista(page, row_selector: str = "table tbody tr") -> str:
    try:
        row0 = page.locator(row_selector).first
        cell_text = _cell_locator(row0, row_selector).inner_text(timeout=SEL_TIMEOUT)
        lines = [l.strip() for l in cell_text.split("\n") if l.strip()]
        return lines[0] if lines else ""
    except Exception:
        return ""


def _goto_with_retry(page, url, max_retries=3):
    """Faz page.goto com retry em caso de erro de rede (ex.: ERR_NETWORK_CHANGED)."""
    last_err = None
    for tentativa in range(max_retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            return
        except Exception as e:
            last_err = e
            if "ERR_NETWORK" in str(e) or "net::" in str(e):
                _log_txt(f"⚠ Rede falhou (tentativa {tentativa + 1}/{max_retries}), aguardando 5s…")
                time.sleep(5)
            else:
                raise
    if last_err:
        raise last_err


def _clicar_proxima(page, nome_antes: str, row_selector: str = "table tbody tr") -> bool:
    time.sleep(ESPERA_PROXIMA_DISPONIVEL)
    next_btn = page.get_by_role("button", name="Próxima")
    if next_btn.count() == 0:
        return False
    try:
        if next_btn.is_disabled():
            return False
    except Exception:
        pass
    try:
        next_btn.scroll_into_view_if_needed(timeout=SEL_TIMEOUT)
        next_btn.click(timeout=CLICK_TIMEOUT)
    except Exception:
        try:
            next_btn.click(timeout=CLICK_TIMEOUT, force=True)
        except Exception:
            return False
    for _ in range(40):
        time.sleep(0.5)
        try:
            if _get_primeiro_nome_da_lista(page, row_selector) != nome_antes:
                return True
        except Exception:
            pass
    return True


# alias para compat
get_primeiro_nome_da_lista = _get_primeiro_nome_da_lista


def _load_checkpoint():
    """
    Retorna (run_at, pagina, linha) se checkpoint válido para hoje; senão (None, 1, 0).
    linha é 0-based, próxima a processar.
    """
    path = getattr(config, "EXPORT_CHECKPOINT", None)
    if not path or not os.path.isfile(path):
        return None, 1, 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        run_at_str = data.get("run_at")
        pagina = int(data.get("pagina", 1))
        linha = int(data.get("linha", 0))
        if not run_at_str:
            return None, 1, 0
        run_at = datetime.fromisoformat(run_at_str.replace("Z", "+00:00"))
        if run_at.tzinfo:
            run_at = run_at.replace(tzinfo=None)
        today = datetime.now().date()
        if run_at.date() != today:
            return None, 1, 0
        return run_at, pagina, linha
    except Exception:
        return None, 1, 0


def _save_checkpoint(run_at, pagina, linha):
    """Persiste checkpoint: próxima posição a processar (pagina 1-based, linha 0-based)."""
    path = getattr(config, "EXPORT_CHECKPOINT", None)
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"run_at": run_at.isoformat(), "pagina": pagina, "linha": linha}, f, ensure_ascii=False)
    except Exception:
        pass


def _clear_checkpoint():
    """Remove o arquivo de checkpoint (exportação concluída)."""
    path = getattr(config, "EXPORT_CHECKPOINT", None)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except Exception:
            pass


def run_export(session_path=None, save_to_disk=True):
    """
    Executa a exportação. session_path default: config.SESSION_FILE.
    Retorna (resultados: list[dict], log_rows: list[dict], run_at: datetime).
    Alimenta o Postgres a cada produtor processado (run_at fixo no início).
    Se existir checkpoint do mesmo dia, retoma de (pagina, linha).
    """
    session_path = session_path or config.SESSION_FILE
    cp_run_at, start_pagina, start_linha = _load_checkpoint()
    today = datetime.now().date()
    if cp_run_at is not None and cp_run_at.date() == today:
        run_at = cp_run_at
        _log_txt(f"▶ Retomando exportação de página {start_pagina}, linha {start_linha + 1} (run_at={run_at.isoformat()})")
    else:
        run_at = datetime.now()
        start_pagina, start_linha = 1, 0
    resultados = []
    log_rows = []
    ok_count = timeout_count = erro_count = 0

    _log_txt("Abrindo browser para exportação (aguarde ~30s)...")
    headed = os.environ.get("APPLYFY_HEADED", "").strip().lower() in ("1", "true", "yes")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            args=["--disable-application-cache", "--disable-cache", "--disk-cache-size=0"],
        )
        context = browser.new_context(
            storage_state=session_path,
            ignore_https_errors=False,
        )
        page = context.new_page()
        page.set_default_timeout(SEL_TIMEOUT)
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        pagina = start_pagina
        inicio_geral = time.perf_counter()
        _log_txt("INÍCIO da exportação Applyfy")
        if db.DATABASE_URL:
            u = db._db_user_from_url()
            if u:
                _log_txt(f"Postgres: usuário '{u}' (se der erro de senha, corrija DATABASE_URL ou PG_USER no .env para o usuário do banco, ex: applyfy)")

        try:
            while True:
                lista_url = f"{BASE_URL}/admin/producers?page={pagina}&pageSize={PAGE_SIZE}"
                _log_txt(f"📄 Abrindo página {pagina}: {lista_url}")
                _goto_with_retry(page, lista_url)
                try:
                    page.wait_for_load_state("networkidle", timeout=60000)
                except Exception:
                    pass
                try:
                    row_selector = _wait_lista(page)
                except Exception as wait_err:
                    raise
                nome_antes = _get_primeiro_nome_da_lista(page, row_selector)
                rows = page.locator(row_selector)
                total_linhas = rows.count()

                if total_linhas == 0:
                    _log_txt("ℹ Nenhuma linha na tabela. Encerrando.")
                    _clear_checkpoint()
                    break

                first_row = start_linha if pagina == start_pagina else 0
                for i in range(first_row, total_linhas):
                    row = page.locator(row_selector).nth(i)
                    produtor_inicio = time.perf_counter()
                    nome = ""
                    email = ""

                    try:
                        etapa = "lista"
                        cell_text = _cell_locator(row, row_selector).inner_text(timeout=SEL_TIMEOUT)
                        lines = [l.strip() for l in cell_text.split("\n") if l.strip()]
                        if not lines:
                            continue
                        nome = lines[0]
                        email = lines[1] if len(lines) > 1 else ""

                        t_abrir = t_saldo = t_cards = 0.0
                        _t0 = time.perf_counter()

                        row.locator("button").last.click(timeout=CLICK_TIMEOUT)
                        page.wait_for_load_state("domcontentloaded")
                        time.sleep(ESPERA_CARREGAR_LISTA)
                        t_abrir = round(time.perf_counter() - _t0, 1)

                        etapa = "saldo"
                        page.locator("text=Saldo").first.click(timeout=CLICK_TIMEOUT)
                        page.wait_for_load_state("domcontentloaded")
                        time.sleep(ESPERA_CARREGAR_LISTA)
                        t_saldo = round(time.perf_counter() - _t0 - t_abrir, 1)

                        etapa = "cards"
                        data = {
                            "Nome": nome,
                            "Email": email,
                            "Saldo pendente": _get_total_from_card(page, "Saldo pendente"),
                            "Saldo retido": _get_total_from_card(page, "Saldo retido"),
                            "Saldo disponível": _get_total_from_card(page, "Saldo disponível"),
                            "Total sacado": _get_total_from_card(page, "Total sacado"),
                            "Vendas líquidas": _get_total_from_card(page, "Vendas líquidas"),
                            "Indicação": _get_total_from_card(page, "Indicação"),
                            "Outros": _get_total_from_card(page, "Outros"),
                        }
                        t_cards = round(time.perf_counter() - _t0 - t_abrir - t_saldo, 1)
                        resultados.append(data)
                        ok_count += 1
                        if db.DATABASE_URL:
                            db.insert_saldo_row(run_at, data)
                        dur = round(time.perf_counter() - produtor_inicio, 2)
                        _log_txt(f"✔ {nome} ({email}) | {dur}s | [latência] abrir:{t_abrir}s saldo:{t_saldo}s cards:{t_cards}s | Página {pagina} | Linha {i+1}/{total_linhas}")
                        log_rows.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pagina": pagina, "linha": i + 1, "nome": nome, "email": email,
                            "status": "OK", "segundos": dur, "mensagem": "",
                        })
                    except PWTimeout:
                        timeout_count += 1
                        dur = round(time.perf_counter() - produtor_inicio, 2)
                        _log_txt(f"⏱ TIMEOUT | {nome} ({email}) | {dur}s | parou em: {etapa} | Página {pagina} | Linha {i+1}/{total_linhas}")
                        log_rows.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pagina": pagina, "linha": i + 1, "nome": nome, "email": email,
                            "status": "TIMEOUT", "segundos": dur, "mensagem": f"Timeout (parou em: {etapa})",
                        })
                    except Exception as e:
                        erro_count += 1
                        dur = round(time.perf_counter() - produtor_inicio, 2)
                        msg = str(e)[:200]
                        _log_txt(f"⚠ ERRO | {nome} ({email}) | {dur}s | {msg}")
                        log_rows.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pagina": pagina, "linha": i + 1, "nome": nome, "email": email,
                            "status": "ERRO", "segundos": dur, "mensagem": msg,
                        })

                    next_linha = i + 1
                    next_pagina = pagina if next_linha < total_linhas else pagina + 1
                    next_linha = next_linha if next_linha < total_linhas else 0
                    _save_checkpoint(run_at, next_pagina, next_linha)

                    if save_to_disk:
                        df = pd.DataFrame(resultados)
                        df.to_csv(config.OUT_CSV, index=False, sep=";", encoding="utf-8-sig")
                        df.to_excel(config.OUT_XLSX, index=False)
                        pd.DataFrame(log_rows).to_csv(config.LOG_CSV, index=False, sep=";", encoding="utf-8-sig")

                    try:
                        _goto_with_retry(page, lista_url)
                        row_selector = _wait_lista(page)
                    except Exception as e:
                        _log_txt(f"❌ Falha ao voltar pra lista: {e}")
                        raise
                    time.sleep(0.5)

                ok = _clicar_proxima(page, nome_antes, row_selector)
                if not ok:
                    _log_txt("ℹ Botão Próxima indisponível (fim).")
                    _clear_checkpoint()
                    break
                pagina += 1

        finally:
            if save_to_disk and resultados:
                pd.DataFrame(resultados).to_csv(config.OUT_CSV, index=False, sep=";", encoding="utf-8-sig")
                pd.DataFrame(resultados).to_excel(config.OUT_XLSX, index=False)
                pd.DataFrame(log_rows).to_csv(config.LOG_CSV, index=False, sep=";", encoding="utf-8-sig")
            dur_total = round(time.perf_counter() - inicio_geral, 2)
            _log_txt(f"FIM | duração total: {dur_total}s | OK={ok_count} TIMEOUT={timeout_count} ERRO={erro_count}")
            browser.close()

    return resultados, log_rows, run_at
