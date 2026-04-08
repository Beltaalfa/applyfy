# -*- coding: utf-8 -*-
"""
Exportação standalone de saldos (mesma lógica de lista/2FA que export_saldos.run_export).
Use após: ./venv/bin/python 01_salvar_sessao.py
"""
import os
import time
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import config
import export_saldos as es

config.ensure_data_dir()

OUT_CSV = config.OUT_CSV
OUT_XLSX = config.OUT_XLSX
LOG_TXT = config.LOG_TXT
LOG_CSV = config.LOG_CSV


def log_txt(msg: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def salvar_log_csv(log_rows):
    df = pd.DataFrame(log_rows)
    df.to_csv(LOG_CSV, index=False, sep=";", encoding="utf-8-sig")


def salvar_parcial(resultados):
    df = pd.DataFrame(resultados)
    df.to_csv(OUT_CSV, index=False, sep=";", encoding="utf-8-sig")
    df.to_excel(OUT_XLSX, index=False)


# =============================
# Execução principal
# =============================
resultados = []
log_rows = []

ok_count = 0
timeout_count = 0
erro_count = 0

headed = os.environ.get("APPLYFY_HEADED", "").strip().lower() in ("1", "true", "yes")
use_headed = headed and config.has_display_server()
if headed and not use_headed:
    log_txt("Sem DISPLAY; usando headless (igual ao servidor).")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=not use_headed,
        args=[
            "--disable-application-cache", "--disable-cache", "--disk-cache-size=0",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = browser.new_context(
        storage_state=config.SESSION_FILE,
        ignore_https_errors=False,
        locale="pt-BR",
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()
    page.set_default_timeout(es.SEL_TIMEOUT)
    page.set_default_navigation_timeout(es.NAV_TIMEOUT)

    pagina = 1
    inicio_geral = time.perf_counter()
    pagina_anterior_fp = None
    log_txt("INÍCIO da exportação Applyfy")

    try:
        while True:
            lista_url = f"{es.BASE_URL}/admin/producers?page={pagina}&pageSize={es.PAGE_SIZE}"
            log_txt(f"📄 Abrindo página {pagina}: {lista_url}")

            es._goto_with_retry(page, lista_url)
            try:
                page.wait_for_load_state("networkidle", timeout=60000)
            except Exception:
                pass
            row_selector = es._wait_lista(page)

            nome_antes = es._get_primeiro_nome_da_lista(page, row_selector)
            rows = page.locator(row_selector)
            total_linhas = rows.count()
            try:
                if total_linhas > 0:
                    first = es._cell_locator(rows.first, row_selector).inner_text(timeout=es.SEL_TIMEOUT)
                    last = es._cell_locator(rows.nth(total_linhas - 1), row_selector).inner_text(timeout=es.SEL_TIMEOUT)
                    fp_atual = f"{total_linhas}|{(first.splitlines()[0] if first else '').strip()}|{(last.splitlines()[0] if last else '').strip()}"
                else:
                    fp_atual = "empty"
            except Exception:
                fp_atual = "unknown"

            if pagina_anterior_fp is not None and fp_atual == pagina_anterior_fp:
                log_txt(f"ℹ Página {pagina} repetida ({fp_atual}). Encerrando para evitar loop.")
                break

            if total_linhas == 0:
                log_txt("ℹ Nenhuma linha na tabela. Encerrando.")
                break

            for i in range(total_linhas):
                row = page.locator(row_selector).nth(i)
                produtor_inicio = time.perf_counter()
                nome = ""
                email = ""

                try:
                    cell_text = es._cell_locator(row, row_selector).inner_text(timeout=es.SEL_TIMEOUT)
                    lines = [l.strip() for l in cell_text.split("\n") if l.strip()]
                    if not lines:
                        continue

                    nome = lines[0]
                    email = lines[1] if len(lines) > 1 else ""

                    row.locator("button").last.click(timeout=es.CLICK_TIMEOUT)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(es.ESPERA_CARREGAR_LISTA)

                    page.locator("text=Saldo").first.click(timeout=es.CLICK_TIMEOUT)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(es.ESPERA_CARREGAR_LISTA)

                    data = {
                        "Nome": nome,
                        "Email": email,
                        "Saldo pendente": es._get_total_from_card(page, "Saldo pendente"),
                        "Saldo retido": es._get_total_from_card(page, "Saldo retido"),
                        "Saldo disponível": es._get_total_from_card(page, "Saldo disponível"),
                        "Total sacado": es._get_total_from_card(page, "Total sacado"),
                        "Vendas líquidas": es._get_total_from_card(page, "Vendas líquidas"),
                        "Indicação": es._get_total_from_card(page, "Indicação"),
                        "Outros": es._get_total_from_card(page, "Outros"),
                    }

                    resultados.append(data)
                    ok_count += 1
                    produtor_fim = time.perf_counter()
                    dur = round(produtor_fim - produtor_inicio, 2)

                    log_txt(f"✔ {nome} ({email}) | {dur}s | Página {pagina} | Linha {i+1}/{total_linhas}")
                    print(f"  ✔ {nome} ({dur}s)", flush=True)

                    log_rows.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "pagina": pagina,
                        "linha": i + 1,
                        "nome": nome,
                        "email": email,
                        "status": "OK",
                        "segundos": dur,
                        "mensagem": "",
                    })

                    salvar_parcial(resultados)
                    salvar_log_csv(log_rows)

                except PWTimeout:
                    timeout_count += 1
                    produtor_fim = time.perf_counter()
                    dur = round(produtor_fim - produtor_inicio, 2)
                    log_txt(f"⏱ TIMEOUT | {nome} ({email}) | {dur}s | Página {pagina} | Linha {i+1}/{total_linhas}")
                    log_rows.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "pagina": pagina,
                        "linha": i + 1,
                        "nome": nome,
                        "email": email,
                        "status": "TIMEOUT",
                        "segundos": dur,
                        "mensagem": "Timeout em clique/carregamento/selector",
                    })
                    salvar_parcial(resultados)
                    salvar_log_csv(log_rows)

                except Exception as e:
                    erro_count += 1
                    produtor_fim = time.perf_counter()
                    dur = round(produtor_fim - produtor_inicio, 2)
                    msg = str(e)
                    if len(msg) > 200:
                        msg = msg[:200] + "..."
                    log_txt(f"⚠ ERRO | {nome} ({email}) | {dur}s | Página {pagina} | Linha {i+1}/{total_linhas} | {msg}")
                    log_rows.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "pagina": pagina,
                        "linha": i + 1,
                        "nome": nome,
                        "email": email,
                        "status": "ERRO",
                        "segundos": dur,
                        "mensagem": msg,
                    })
                    salvar_parcial(resultados)
                    salvar_log_csv(log_rows)

                try:
                    es._goto_with_retry(page, lista_url)
                    try:
                        page.wait_for_load_state("networkidle", timeout=60000)
                    except Exception:
                        pass
                    row_selector = es._wait_lista(page)
                except Exception as e:
                    log_txt(f"❌ Falha ao voltar pra lista. Salvando e encerrando. Motivo: {e}")
                    salvar_parcial(resultados)
                    salvar_log_csv(log_rows)
                    raise

                time.sleep(0.5)

            salvar_parcial(resultados)
            salvar_log_csv(log_rows)

            ok = es._clicar_proxima(page, nome_antes, row_selector)
            if not ok:
                log_txt("ℹ Botão Próxima indisponível; tentando avançar por parâmetro page.")

            pagina_anterior_fp = fp_atual
            pagina += 1

    finally:
        try:
            salvar_parcial(resultados)
            salvar_log_csv(log_rows)
        except Exception:
            pass

        dur_total = round(time.perf_counter() - inicio_geral, 2)
        log_txt(f"FIM | duração total: {dur_total}s | OK={ok_count} TIMEOUT={timeout_count} ERRO={erro_count}")

        browser.close()

print("\n✅ Exportação concluída com sucesso (ou salva parcial se interromper).")
