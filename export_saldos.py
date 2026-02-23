# -*- coding: utf-8 -*-
"""
Lógica de exportação de saldos dos produtores Applyfy.
Usa sessao_applyfy.json em config.DATA_DIR.
Retorna lista de dicts e grava CSV/XLSX em config.
"""
import time
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import config
import db

config.ensure_data_dir()

BASE_URL = "https://app.applyfy.com.br"
PAGE_SIZE = 20
ESPERA_CARREGAR_LISTA = 7
ESPERA_PROXIMA_DISPONIVEL = 7
NAV_TIMEOUT = 120000
SEL_TIMEOUT = 60000
CLICK_TIMEOUT = 30000


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


def _wait_lista(page):
    page.wait_for_selector("table tbody tr", timeout=SEL_TIMEOUT)
    time.sleep(ESPERA_CARREGAR_LISTA)


def _get_primeiro_nome_da_lista(page) -> str:
    try:
        row0 = page.locator("table tbody tr").first
        cell_text = row0.locator("td").first.inner_text(timeout=SEL_TIMEOUT)
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


def _clicar_proxima(page, nome_antes: str) -> bool:
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
            if get_primeiro_nome_da_lista(page) != nome_antes:
                return True
        except Exception:
            pass
    return True


# alias para compat
get_primeiro_nome_da_lista = _get_primeiro_nome_da_lista


def run_export(session_path=None, save_to_disk=True):
    """
    Executa a exportação. session_path default: config.SESSION_FILE.
    Retorna (resultados: list[dict], log_rows: list[dict], run_at: datetime).
    Alimenta o Postgres a cada produtor processado (run_at fixo no início).
    """
    session_path = session_path or config.SESSION_FILE
    run_at = datetime.now()
    resultados = []
    log_rows = []
    ok_count = timeout_count = erro_count = 0

    _log_txt("Abrindo browser para exportação (aguarde ~30s)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session_path)
        page = context.new_page()
        page.set_default_timeout(SEL_TIMEOUT)
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        pagina = 1
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
                _wait_lista(page)
                nome_antes = _get_primeiro_nome_da_lista(page)
                rows = page.locator("table tbody tr")
                total_linhas = rows.count()

                if total_linhas == 0:
                    _log_txt("ℹ Nenhuma linha na tabela. Encerrando.")
                    break

                for i in range(total_linhas):
                    row = page.locator("table tbody tr").nth(i)
                    produtor_inicio = time.perf_counter()
                    nome = ""
                    email = ""

                    try:
                        cell_text = row.locator("td").first.inner_text(timeout=SEL_TIMEOUT)
                        lines = [l.strip() for l in cell_text.split("\n") if l.strip()]
                        if not lines:
                            continue
                        nome = lines[0]
                        email = lines[1] if len(lines) > 1 else ""

                        row.locator("button").last.click(timeout=CLICK_TIMEOUT)
                        page.wait_for_load_state("domcontentloaded")
                        time.sleep(ESPERA_CARREGAR_LISTA)

                        page.locator("text=Saldo").first.click(timeout=CLICK_TIMEOUT)
                        page.wait_for_load_state("domcontentloaded")
                        time.sleep(ESPERA_CARREGAR_LISTA)

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
                        resultados.append(data)
                        ok_count += 1
                        if db.DATABASE_URL:
                            db.insert_saldo_row(run_at, data)
                        dur = round(time.perf_counter() - produtor_inicio, 2)
                        _log_txt(f"✔ {nome} ({email}) | {dur}s | Página {pagina} | Linha {i+1}/{total_linhas}")
                        log_rows.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pagina": pagina, "linha": i + 1, "nome": nome, "email": email,
                            "status": "OK", "segundos": dur, "mensagem": "",
                        })
                    except PWTimeout:
                        timeout_count += 1
                        dur = round(time.perf_counter() - produtor_inicio, 2)
                        _log_txt(f"⏱ TIMEOUT | {nome} ({email}) | {dur}s | Página {pagina} | Linha {i+1}/{total_linhas}")
                        log_rows.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pagina": pagina, "linha": i + 1, "nome": nome, "email": email,
                            "status": "TIMEOUT", "segundos": dur, "mensagem": "Timeout",
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

                    if save_to_disk:
                        df = pd.DataFrame(resultados)
                        df.to_csv(config.OUT_CSV, index=False, sep=";", encoding="utf-8-sig")
                        df.to_excel(config.OUT_XLSX, index=False)
                        pd.DataFrame(log_rows).to_csv(config.LOG_CSV, index=False, sep=";", encoding="utf-8-sig")

                    try:
                        _goto_with_retry(page, lista_url)
                        _wait_lista(page)
                    except Exception as e:
                        _log_txt(f"❌ Falha ao voltar pra lista: {e}")
                        raise
                    time.sleep(0.5)

                ok = _clicar_proxima(page, nome_antes)
                if not ok:
                    _log_txt("ℹ Botão Próxima indisponível (fim).")
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
