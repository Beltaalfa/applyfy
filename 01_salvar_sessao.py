# -*- coding: utf-8 -*-
"""
Login automático na Applyfy (admin): email, senha e 2FA TOTP.
Salva a sessão em data/sessao_applyfy.json para uso pelo exportador.

Variáveis de ambiente obrigatórias:
  APPLYFY_USER, APPLYFY_PASSWORD, APPLYFY_TOTP_SECRET
Opcional: APPLYFY_DATA_DIR (default: ./data), HEADLESS=0 para ver o browser.
"""
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

APPLYFY_USER = os.environ.get("APPLYFY_USER")
APPLYFY_PASSWORD = os.environ.get("APPLYFY_PASSWORD")
APPLYFY_TOTP_SECRET = os.environ.get("APPLYFY_TOTP_SECRET")

if not all([APPLYFY_USER, APPLYFY_PASSWORD, APPLYFY_TOTP_SECRET]):
    print("Erro: defina APPLYFY_USER, APPLYFY_PASSWORD e APPLYFY_TOTP_SECRET no .env ou no ambiente.")
    sys.exit(1)

import pyotp
from playwright.sync_api import sync_playwright

import config
from export_saldos import PAGE_SIZE, _esta_em_2fa, preenche_e_submete_2fa_estilo_login

config.ensure_data_dir()

LOGIN_URL = "https://app.applyfy.com.br/auth/admin"
REPORT_URL = "https://app.applyfy.com.br/admin/reports/producers?page=1&pageSize=50"
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
TIMEOUT_MS = 30000


def main():
    totp = pyotp.TOTP(APPLYFY_TOTP_SECRET.strip().replace(" ", ""))
    code_2fa = totp.now()
    headless = HEADLESS
    if not headless and not config.has_display_server():
        print("Sem DISPLAY no servidor; forçando headless no login.", flush=True)
        headless = True

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        context.set_default_timeout(TIMEOUT_MS)
        page = context.new_page()

        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

            # Email: tenta name, type=email, placeholder
            email_sel = 'input[name="email"], input[type="email"], input[placeholder*="mail" i], input[placeholder*="e-mail" i], input[id="email"]'
            page.wait_for_selector(email_sel, timeout=15000)
            page.fill(email_sel, APPLYFY_USER)

            # Senha
            pwd_sel = 'input[name="password"], input[type="password"], input[id="password"]'
            page.fill(pwd_sel, APPLYFY_PASSWORD)

            # Submit: Enter no campo senha costuma enviar o form
            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)  # ~2s para a tela de 2FA aparecer

            def _submit_login():
                try:
                    page.locator("form button[type='submit'], form input[type='submit']").first.click(timeout=5000)
                except Exception:
                    page.get_by_role("button", name=re.compile(r"^Entrar$")).first.click(timeout=5000)

            def _save_debug():
                for folder in [config.DATA_DIR, "/tmp", os.path.dirname(config.SESSION_FILE)]:
                    try:
                        path = os.path.join(folder, "login_debug.png")
                        page.screenshot(path=path)
                        print("Screenshot salvo em", path, "| URL:", page.url)
                        return
                    except (OSError, PermissionError) as e:
                        continue
                print("URL da página:", page.url)

            # Tenta vários jeitos de achar o campo do código 2FA
            code_filled = False
            otp_sel = 'input[data-input-otp="true"], input[autocomplete="one-time-code"]'
            try:
                page.wait_for_selector(otp_sel, timeout=20000)
                page.locator(otp_sel).first.fill(code_2fa)
                code_filled = True
            except Exception:
                pass
            # 1) Por label ou placeholder (Playwright)
            if not code_filled:
                for label in ["Código", "Código de verificação", "Code", "Digite o código", "Token", "2FA"]:
                    try:
                        inp = page.get_by_label(label, exact=False)
                        if inp.count() > 0:
                            inp.first.fill(code_2fa)
                            code_filled = True
                            break
                    except Exception:
                        pass
                    try:
                        inp = page.get_by_placeholder(label, exact=False)
                        if inp.count() > 0:
                            inp.first.fill(code_2fa)
                            code_filled = True
                            break
                    except Exception:
                        pass
            if not code_filled:
                # 2) Selectors clássicos
                code_sel = 'input[name="code"], input[name="token"], input[placeholder*="código" i], input[type="text"][maxlength="6"], input[inputmode="numeric"], input[type="tel"][maxlength="6"]'
                code_boxes = page.locator('input[maxlength="1"][type="text"], input[maxlength="1"][type="tel"], input[inputmode="numeric"][maxlength="1"]')
                try:
                    page.wait_for_selector(code_sel, timeout=25000)
                    page.fill(code_sel, code_2fa)
                    code_filled = True
                except Exception:
                    if code_boxes.count() >= 6:
                        for i, digit in enumerate(code_2fa[:6]):
                            code_boxes.nth(i).fill(digit)
                            page.wait_for_timeout(100)
                        code_filled = True
            if not code_filled:
                _submit_login()
                page.wait_for_timeout(5000)
                for label in ["Código", "Código de verificação", "Code", "Digite o código", "Token", "2FA"]:
                    try:
                        inp = page.get_by_placeholder(label, exact=False)
                        if inp.count() > 0:
                            inp.first.fill(code_2fa)
                            code_filled = True
                            break
                    except Exception:
                        pass
                if not code_filled:
                    try:
                        page.wait_for_selector('input[name="code"], input[name="token"], input[type="text"][maxlength="6"], input[type="tel"][maxlength="6"]', timeout=15000)
                        page.fill('input[name="code"], input[name="token"], input[type="text"][maxlength="6"], input[type="tel"][maxlength="6"]', code_2fa)
                        code_filled = True
                    except Exception:
                        pass
            if not code_filled:
                _save_debug()
                raise RuntimeError("Campo do código 2FA não encontrado. Veja login_debug.png na pasta data/.")
            page.wait_for_timeout(1500)

            # Submete 2FA: tenta Enter (muitos formulários enviam assim) ou clica no botão
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            try:
                page.locator('button[type="submit"], input[type="submit"], button:has-text("Confirmar"), button:has-text("Verificar"), button:has-text("Enviar"), button:has-text("Continuar"), button:has-text("Validar")').first.click(timeout=8000)
                page.wait_for_timeout(3000)
            except Exception:
                pass

            # Garante que estamos logados: navega para o relatório
            # domcontentloaded evita timeout (networkidle exige rede parada e costuma estourar)
            page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            # Se ainda estiver na página de login, algo falhou
            if "auth" in page.url.lower():
                print("Aviso: ainda na página de auth. Verifique usuário/senha/TOTP e selectors da página.")
                browser.close()
                sys.exit(2)

            # Export usa /admin/producers; o login só abria /admin/reports/producers — rotas diferentes.
            # Sem visitar /admin/producers aqui, o Applyfy costuma pedir 2FA de novo no export.
            producers_url = f"https://app.applyfy.com.br/admin/producers?page=1&pageSize={PAGE_SIZE}"
            try:
                page.goto(producers_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(6000)
            except Exception:
                pass
            if "auth" in page.url.lower():
                print("Aviso: /admin/producers redirecionou para auth.")
                _save_debug()
                browser.close()
                sys.exit(4)
            if _esta_em_2fa(page):
                print("2FA em /admin/producers; validando com o mesmo fluxo do login...", flush=True)
                ok_2fa = False
                for tentativa in range(2):
                    codigo = totp.now()
                    if preenche_e_submete_2fa_estilo_login(page, codigo, _submit_login):
                        ok_2fa = True
                        break
                    page.wait_for_timeout(2000)
                if not ok_2fa:
                    print(
                        "Aviso: 2FA automático em /admin/producers falhou. Voltando ao relatório e salvando sessão mesmo assim — "
                        "rode o export (03 ou run_daily); ele tentará 2FA outra vez com o TOTP do .env.",
                        flush=True,
                    )
                    try:
                        page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(4000)
                    except Exception:
                        pass
                    if "auth" in page.url.lower():
                        print("Sessão perdeu login ao voltar do 2FA. Veja login_debug.png")
                        _save_debug()
                        browser.close()
                        sys.exit(4)

            context.storage_state(path=config.SESSION_FILE)
            print("OK! Sessão salva em", config.SESSION_FILE, flush=True)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
