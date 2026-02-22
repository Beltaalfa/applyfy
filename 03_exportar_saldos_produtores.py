from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import time
import pandas as pd
from datetime import datetime

import config
config.ensure_data_dir()

BASE_URL = "https://app.applyfy.com.br"
PAGE_SIZE = 20
ESPERA_CARREGAR_LISTA = 7
ESPERA_PROXIMA_DISPONIVEL = 7
NAV_TIMEOUT = 120000
SEL_TIMEOUT = 60000
CLICK_TIMEOUT = 30000

OUT_CSV = config.OUT_CSV
OUT_XLSX = config.OUT_XLSX
LOG_TXT = config.LOG_TXT
LOG_CSV = config.LOG_CSV


# =============================
# LOG
# =============================
def log_txt(msg: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line)
    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def salvar_log_csv(log_rows):
    df = pd.DataFrame(log_rows)
    df.to_csv(LOG_CSV, index=False, sep=";", encoding="utf-8-sig")


# =============================
# Utilidades
# =============================
def money_to_float(txt: str) -> float:
    if not txt:
        return 0.0
    txt = txt.replace("R$", "").strip()
    txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except:
        return 0.0


def get_total_from_card(page, title: str) -> float:
    try:
        card = page.locator(f"text={title}").first.locator("..").locator("..")
        total_locator = card.locator("text=Total").first.locator("xpath=following::p[1]")

        if total_locator.count() == 0:
            return 0.0

        total_text = total_locator.first.inner_text(timeout=SEL_TIMEOUT)
        return money_to_float(total_text)
    except:
        return 0.0


def salvar_parcial(resultados):
    df = pd.DataFrame(resultados)
    df.to_csv(OUT_CSV, index=False, sep=";", encoding="utf-8-sig")
    df.to_excel(OUT_XLSX, index=False)


def wait_lista(page):
    page.wait_for_selector("table tbody tr", timeout=SEL_TIMEOUT)
    time.sleep(ESPERA_CARREGAR_LISTA)


def get_primeiro_nome_da_lista(page) -> str:
    try:
        row0 = page.locator("table tbody tr").first
        cell_text = row0.locator("td").first.inner_text(timeout=SEL_TIMEOUT)
        lines = [l.strip() for l in cell_text.split("\n") if l.strip()]
        return lines[0] if lines else ""
    except:
        return ""


def clicar_proxima(page, nome_antes: str) -> bool:
    time.sleep(ESPERA_PROXIMA_DISPONIVEL)

    next_btn = page.get_by_role("button", name="Próxima")
    if next_btn.count() == 0:
        return False

    try:
        if next_btn.is_disabled():
            return False
    except:
        pass

    try:
        next_btn.scroll_into_view_if_needed(timeout=SEL_TIMEOUT)
    except:
        pass

    try:
        next_btn.click(timeout=CLICK_TIMEOUT)
    except:
        try:
            next_btn.click(timeout=CLICK_TIMEOUT, force=True)
        except:
            return False

    # espera mudança real
    url_antes = page.url
    for _ in range(40):  # ~20s
        time.sleep(0.5)
        try:
            if page.url != url_antes:
                return True
        except:
            pass

        nome_depois = get_primeiro_nome_da_lista(page)
        if nome_depois and nome_depois != nome_antes:
            return True

    return True


# =============================
# Execução principal
# =============================
resultados = []
log_rows = []

ok_count = 0
timeout_count = 0
erro_count = 0

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state=config.SESSION_FILE)
    page = context.new_page()
    page.set_default_timeout(SEL_TIMEOUT)
    page.set_default_navigation_timeout(NAV_TIMEOUT)

    pagina = 1
    inicio_geral = time.perf_counter()
    log_txt("INÍCIO da exportação Applyfy")

    try:
        while True:
            lista_url = f"{BASE_URL}/admin/producers?page={pagina}&pageSize={PAGE_SIZE}"
            log_txt(f"📄 Abrindo página {pagina}: {lista_url}")

            page.goto(lista_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            wait_lista(page)

            nome_antes = get_primeiro_nome_da_lista(page)

            rows = page.locator("table tbody tr")
            total_linhas = rows.count()

            if total_linhas == 0:
                log_txt("ℹ Nenhuma linha na tabela. Encerrando.")
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

                    # abrir produtor (olho)
                    row.locator("button").last.click(timeout=CLICK_TIMEOUT)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(ESPERA_CARREGAR_LISTA)

                    # aba Saldo
                    page.locator("text=Saldo").first.click(timeout=CLICK_TIMEOUT)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(ESPERA_CARREGAR_LISTA)

                    data = {
                        "Nome": nome,
                        "Email": email,
                        "Saldo pendente": get_total_from_card(page, "Saldo pendente"),
                        "Saldo retido": get_total_from_card(page, "Saldo retido"),
                        "Saldo disponível": get_total_from_card(page, "Saldo disponível"),
                        "Total sacado": get_total_from_card(page, "Total sacado"),
                        "Vendas líquidas": get_total_from_card(page, "Vendas líquidas"),
                        "Indicação": get_total_from_card(page, "Indicação"),
                        "Outros": get_total_from_card(page, "Outros"),
                    }

                    resultados.append(data)
                    ok_count += 1

                    produtor_fim = time.perf_counter()
                    dur = round(produtor_fim - produtor_inicio, 2)

                    log_txt(f"✔ {nome} ({email}) | {dur}s | Página {pagina} | Linha {i+1}/{total_linhas}")
                    print(f"  ✔ {nome} ({dur}s)")

                    log_rows.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "pagina": pagina,
                        "linha": i + 1,
                        "nome": nome,
                        "email": email,
                        "status": "OK",
                        "segundos": dur,
                        "mensagem": ""
                    })

                    # salva parcial a cada produtor
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
                        "mensagem": "Timeout em clique/carregamento/selector"
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
                        "mensagem": msg
                    })

                    salvar_parcial(resultados)
                    salvar_log_csv(log_rows)

                # volta para lista (estabilidade)
                try:
                    page.goto(lista_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                    wait_lista(page)
                except Exception as e:
                    log_txt(f"❌ Falha ao voltar pra lista. Salvando e encerrando. Motivo: {e}")
                    salvar_parcial(resultados)
                    salvar_log_csv(log_rows)
                    raise

                # pequena proteção extra
                time.sleep(0.5)

            # final da página
            salvar_parcial(resultados)
            salvar_log_csv(log_rows)

            # próxima página
            ok = clicar_proxima(page, nome_antes)
            if not ok:
                log_txt("ℹ Botão Próxima indisponível (fim).")
                break

            pagina += 1

    finally:
        # garante salvar tudo mesmo se parar no meio
        try:
            salvar_parcial(resultados)
            salvar_log_csv(log_rows)
        except:
            pass

        dur_total = round(time.perf_counter() - inicio_geral, 2)
        log_txt(f"FIM | duração total: {dur_total}s | OK={ok_count} TIMEOUT={timeout_count} ERRO={erro_count}")

        browser.close()

print("\n✅ Exportação concluída com sucesso (ou salva parcial se interromper).")
