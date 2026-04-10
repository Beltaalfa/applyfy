# -*- coding: utf-8 -*-
"""
Lógica de exportação de saldos dos produtores Applyfy.
Usa sessao_applyfy.json em config.DATA_DIR.
Retorna lista de dicts e grava CSV/XLSX em config.
"""
import json
import os
import re
import time
from datetime import datetime

import pandas as pd
import pyotp
from playwright.sync_api import Error as PWError, sync_playwright, TimeoutError as PWTimeout
from playwright._impl._errors import TargetClosedError

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
PRODUCERS_LIST_SELECTORS = "table, [role=grid], [role=row]"


def _get_applyfy_login_env() -> tuple[str, str, str]:
    user = (os.environ.get("APPLYFY_USER") or "").strip()
    password = os.environ.get("APPLYFY_PASSWORD") or ""
    totp_secret = (os.environ.get("APPLYFY_TOTP_SECRET") or "").strip().replace(" ", "")
    if not all([user, password, totp_secret]):
        raise RuntimeError("Defina APPLYFY_USER, APPLYFY_PASSWORD e APPLYFY_TOTP_SECRET para resolver 2FA no export.")
    return user, password, totp_secret


def _esta_em_2fa(page) -> bool:
    try:
        if page.get_by_text("Autenticação de 2 fatores", exact=False).count() > 0:
            return True
        if page.locator("[data-input-otp-container]").count() > 0:
            return True
    except Exception:
        pass
    return False


def _preencher_otp_data_input_otp(page, codigo: str) -> bool:
    """
    Campo input[data-input-otp] (HeroUI/React): .fill() coloca value no DOM mas muitas vezes
    NÃO dispara onChange por dígito — a tela /admin/producers não tem botão enviar, só auto-submit
    ao completar 6 dígitos com teclas reais.
    """
    codigo = (codigo or "").strip().replace(" ", "")[:6]
    if len(codigo) != 6:
        return False
    sel = 'input[data-input-otp="true"]'
    try:
        if page.locator(sel).count() == 0:
            return False
        page.wait_for_selector(sel, state="visible", timeout=15000)
        inp = page.locator(sel).first
        inp.scroll_into_view_if_needed(timeout=5000)
        inp.click(timeout=5000)
        page.wait_for_timeout(200)
        try:
            inp.press("Control+a")
        except Exception:
            pass
        inp.press("Backspace")
        page.wait_for_timeout(100)
        inp.press_sequentially(codigo, delay=120)
        return True
    except Exception:
        return False


def preenche_e_submete_2fa_estilo_login(page, codigo: str, submit_fn) -> bool:
    """
    Mesmo fluxo do 01_salvar_sessao após email/senha (OTP + Enter + botões).
    submit_fn: chamado só se precisar re-disparar formulário (no export costuma ser no-op).
    Retorna True se saiu da tela de 2FA.
    """
    otp_sel = 'input[data-input-otp="true"], input[autocomplete="one-time-code"]'
    code_filled = False
    # Primeiro: digitação real no componente input-otp (obrigatório em /admin/producers).
    if _preencher_otp_data_input_otp(page, codigo):
        code_filled = True
    if not code_filled:
        try:
            page.wait_for_selector(otp_sel, timeout=15000)
            page.locator(otp_sel).first.fill(codigo)
            code_filled = True
        except Exception:
            pass
    if not code_filled:
        for label in ["Código", "Código de verificação", "Code", "Digite o código", "Token", "2FA"]:
            try:
                inp = page.get_by_label(label, exact=False)
                if inp.count() > 0:
                    inp.first.fill(codigo)
                    code_filled = True
                    break
            except Exception:
                pass
            try:
                inp = page.get_by_placeholder(label, exact=False)
                if inp.count() > 0:
                    inp.first.fill(codigo)
                    code_filled = True
                    break
            except Exception:
                pass
    if not code_filled:
        code_sel = 'input[name="code"], input[name="token"], input[placeholder*="código" i], input[type="text"][maxlength="6"], input[inputmode="numeric"], input[type="tel"][maxlength="6"]'
        code_boxes = page.locator('input[maxlength="1"][type="text"], input[maxlength="1"][type="tel"], input[inputmode="numeric"][maxlength="1"]')
        try:
            page.wait_for_selector(code_sel, timeout=12000)
            page.fill(code_sel, codigo)
            code_filled = True
        except Exception:
            if code_boxes.count() >= 6:
                for i, digit in enumerate(codigo[:6]):
                    code_boxes.nth(i).fill(digit)
                    page.wait_for_timeout(100)
                code_filled = True
    if not code_filled:
        submit_fn()
        page.wait_for_timeout(4000)
        if _preencher_otp_data_input_otp(page, codigo):
            code_filled = True
        else:
            try:
                page.wait_for_selector(otp_sel, timeout=8000)
                page.locator(otp_sel).first.fill(codigo)
                code_filled = True
            except Exception:
                pass
    if not code_filled:
        return False

    # input-otp pode submeter sozinho ao 6º dígito; dar tempo antes de Enter extra.
    page.wait_for_timeout(2500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(3000)
    try:
        page.locator(
            'button[type="submit"], input[type="submit"], button:has-text("Confirmar"), button:has-text("Verificar"), button:has-text("Enviar"), button:has-text("Continuar"), button:has-text("Validar")'
        ).first.click(timeout=8000)
        page.wait_for_timeout(3000)
    except Exception:
        pass
    if _esta_em_2fa(page):
        page.wait_for_timeout(2000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    if not _esta_em_2fa(page):
        return True
    if page.locator(PRODUCERS_LIST_SELECTORS).count() > 0:
        return True
    return False


def _resolver_2fa_painel(page) -> bool:
    """2FA em rota admin (ex.: /admin/producers) — usa o mesmo fluxo simples do login."""
    try:
        _get_applyfy_login_env()
    except Exception:
        return False

    totp = pyotp.TOTP((os.environ.get("APPLYFY_TOTP_SECRET") or "").strip().replace(" ", ""))
    otp_code = totp.now()

    _log_txt("2FA no painel; tentando validar automaticamente (TOTP, fluxo igual ao login)...")

    def _submit_vazio():
        try:
            page.locator("form button[type='submit'], form input[type='submit']").first.click(timeout=3000)
        except Exception:
            try:
                page.get_by_role("button", name=re.compile(r"^Entrar$")).first.click(timeout=3000)
            except Exception:
                pass

    return preenche_e_submete_2fa_estilo_login(page, otp_code, _submit_vazio)


def _debug_producers_fail(page):
    p = os.path.join(config.DATA_DIR, "debug_producers_fail.png")
    h = os.path.join(config.DATA_DIR, "debug_producers_fail.html")
    try:
        page.screenshot(path=p)
        with open(h, "w", encoding="utf-8") as f:
            f.write(page.content())
        _log_txt(f"Debug: {p} e {h} | URL: {page.url}")
    except Exception:
        pass


def _wait_lista(page):
    """Espera a lista carregar. Aceita <table> ou grid com [role=row]. Retorna seletor de linhas."""
    page.wait_for_timeout(2000)
    if _esta_em_2fa(page):
        if not _resolver_2fa_painel(page):
            _log_txt("Segunda tentativa de 2FA...")
            if not _resolver_2fa_painel(page):
                _debug_producers_fail(page)
                raise RuntimeError(
                    "Autenticação de 2 fatores na lista de produtores: validação automática falhou. "
                    "Confira APPLYFY_TOTP_SECRET no .env."
                )
    if "auth" in page.url.lower():
        _debug_producers_fail(page)
        raise RuntimeError(
            "Redirecionou para login (auth). Rode 01_salvar_sessao.py de novo ou verifique sessao_applyfy.json."
        )
    try:
        page.wait_for_selector(PRODUCERS_LIST_SELECTORS, state="visible", timeout=LIST_WAIT)
    except PWTimeout:
        _debug_producers_fail(page)
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


def _pagina_fingerprint(page, row_selector: str) -> str:
    """Assinatura simples da página para detectar repetição de paginação."""
    try:
        rows = page.locator(row_selector)
        total = rows.count()
        if total == 0:
            return "empty"
        first = _cell_locator(rows.first, row_selector).inner_text(timeout=SEL_TIMEOUT)
        last = _cell_locator(rows.nth(total - 1), row_selector).inner_text(timeout=SEL_TIMEOUT)
        first_line = (first.split("\n")[0] if first else "").strip()
        last_line = (last.split("\n")[0] if last else "").strip()
        return f"{total}|{first_line}|{last_line}"
    except Exception:
        return "unknown"


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
    Retorna (run_at, pagina, linha) se o checkpoint existir e for recente o suficiente; senão (None, 1, 0).
    linha é 0-based, próxima a processar.

    Idade máxima do run_at no checkpoint: APPLYFY_EXPORT_CHECKPOINT_MAX_AGE_DAYS (default 1).
    Ex.: default 1 = aceita hoje e ontem; use 0 só para o mesmo dia civil; use 7 para até uma semana.
    """
    path = getattr(config, "EXPORT_CHECKPOINT", None)
    if not path or not os.path.isfile(path):
        return None, 1, 0
    try:
        raw_max = (os.environ.get("APPLYFY_EXPORT_CHECKPOINT_MAX_AGE_DAYS") or "1").strip() or "1"
        max_age_days = max(0, int(raw_max))
    except ValueError:
        max_age_days = 1
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
        cp_date = run_at.date()
        age_days = (today - cp_date).days
        if age_days < 0:
            _log_txt("ℹ Checkpoint ignorado (run_at no futuro).")
            return None, 1, 0
        if age_days > max_age_days:
            _log_txt(
                f"ℹ Checkpoint ignorado (export de {cp_date.isoformat()}, há {age_days}d; "
                f"máx permitido {max_age_days}d — ajuste APPLYFY_EXPORT_CHECKPOINT_MAX_AGE_DAYS ou apague export_checkpoint.json)."
            )
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


def _playwright_teardown(pw_cm, browser, context, page):
    """
    Fecha page → context → browser → driver. Erros são engolidos: EPIPE no driver Node
    ao encerrar o pipe não deve derrubar o processo Python após export concluído.
    """
    if page:
        try:
            page.close()
        except (PWError, TargetClosedError, Exception):
            pass
    if context:
        try:
            context.close()
        except (PWError, TargetClosedError, Exception):
            pass
    if browser:
        try:
            browser.close()
        except (PWError, TargetClosedError, Exception):
            pass
    if pw_cm is not None:
        try:
            pw_cm.__exit__(None, None, None)
        except (PWError, TargetClosedError, Exception) as ex:
            _log_txt(f"ℹ Encerramento do driver Playwright (avisos comuns após export longo): {ex!s}")


def run_export(session_path=None, save_to_disk=True):
    """
    Executa a exportação. session_path default: config.SESSION_FILE.
    Retorna (resultados: list[dict], log_rows: list[dict], run_at: datetime).
    Alimenta o Postgres a cada produtor processado (run_at fixo no início).
    Se existir checkpoint recente (ver APPLYFY_EXPORT_CHECKPOINT_MAX_AGE_DAYS), retoma de (pagina, linha).
    """
    session_path = session_path or config.SESSION_FILE
    cp_run_at, start_pagina, start_linha = _load_checkpoint()
    resultados = []
    log_rows = []
    ok_count = timeout_count = erro_count = 0
    if cp_run_at is not None:
        run_at = cp_run_at
        _log_txt(f"▶ Retomando exportação de página {start_pagina}, linha {start_linha + 1} (run_at={run_at.isoformat()})")
        if save_to_disk:
            if os.path.isfile(config.OUT_CSV):
                try:
                    df_prev = pd.read_csv(config.OUT_CSV, sep=";", encoding="utf-8-sig")
                    resultados = df_prev.to_dict("records")
                    _log_txt(f"▶ CSV anterior carregado: {len(resultados)} linhas ({config.OUT_CSV})")
                except Exception as e:
                    _log_txt(f"⚠ Não foi possível carregar CSV anterior: {e}")
            if os.path.isfile(config.LOG_CSV):
                try:
                    df_log = pd.read_csv(config.LOG_CSV, sep=";", encoding="utf-8-sig")
                    log_rows = df_log.to_dict("records")
                    ok_count = sum(1 for r in log_rows if str(r.get("status", "")).strip().upper() == "OK")
                    timeout_count = sum(1 for r in log_rows if "TIMEOUT" in str(r.get("status", "")).upper())
                    erro_count = sum(1 for r in log_rows if str(r.get("status", "")).strip().upper() == "ERRO")
                    _log_txt(f"▶ Log CSV anterior carregado: {len(log_rows)} linhas")
                except Exception as e:
                    _log_txt(f"⚠ Não foi possível carregar log CSV anterior: {e}")
    else:
        run_at = datetime.now()
        start_pagina, start_linha = 1, 0

    _log_txt("Abrindo browser para exportação (aguarde ~30s)...")
    headed = os.environ.get("APPLYFY_HEADED", "").strip().lower() in ("1", "true", "yes")
    use_headed = headed and config.has_display_server()
    if headed and not use_headed:
        _log_txt("Sem DISPLAY; usando headless no export (igual ao servidor).")
    pw_cm = sync_playwright()
    p = pw_cm.__enter__()
    browser = None
    context = None
    page = None
    try:
        browser = p.chromium.launch(
            headless=not use_headed,
            args=[
                "--disable-application-cache",
                "--disable-cache",
                "--disk-cache-size=0",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            storage_state=session_path,
            ignore_https_errors=False,
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.set_default_timeout(SEL_TIMEOUT)
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        pagina = start_pagina
        inicio_geral = time.perf_counter()
        pagina_anterior_fp = None
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
                fp_atual = _pagina_fingerprint(page, row_selector)
                if pagina_anterior_fp is not None and fp_atual == pagina_anterior_fp:
                    _log_txt(f"ℹ Página {pagina} repetida ({fp_atual}). Encerrando para evitar loop.")
                    _clear_checkpoint()
                    break

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
                    except (PWError, TargetClosedError) as e:
                        erro_count += 1
                        dur = round(time.perf_counter() - produtor_inicio, 2)
                        msg = str(e)[:200]
                        _log_txt(f"⚠ PLAYWRIGHT | {nome} ({email}) | {dur}s | {msg}")
                        log_rows.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "pagina": pagina, "linha": i + 1, "nome": nome, "email": email,
                            "status": "ERRO", "segundos": dur, "mensagem": msg,
                        })
                        if isinstance(e, TargetClosedError) or "Target closed" in msg or "Browser closed" in msg:
                            _log_txt("❌ Browser/contexto encerrado — interrompendo export (retome com run_daily).")
                            raise
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
                    _log_txt("ℹ Botão Próxima indisponível; tentando avançar por parâmetro page.")
                pagina_anterior_fp = fp_atual
                pagina += 1

        finally:
            if save_to_disk and resultados:
                pd.DataFrame(resultados).to_csv(config.OUT_CSV, index=False, sep=";", encoding="utf-8-sig")
                pd.DataFrame(resultados).to_excel(config.OUT_XLSX, index=False)
                pd.DataFrame(log_rows).to_csv(config.LOG_CSV, index=False, sep=";", encoding="utf-8-sig")
            dur_total = round(time.perf_counter() - inicio_geral, 2)
            _log_txt(f"FIM | duração total: {dur_total}s | OK={ok_count} TIMEOUT={timeout_count} ERRO={erro_count}")
    finally:
        _playwright_teardown(pw_cm, browser, context, page)

    return resultados, log_rows, run_at
