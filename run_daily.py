# -*- coding: utf-8 -*-
"""
Job diário: login automático + exportação + gravação em disco e Postgres.
Agendar com cron às 2h: 0 2 * * * cd /var/www/applyfy && . env.sh && python run_daily.py
Em caso de falha (timeout, rede), o job é reiniciado automaticamente e retoma de onde parou (checkpoint).
"""
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
from dotenv import load_dotenv

# .env do projeto sempre prevalece (evita DATABASE_URL do shell, ex. tactical)
load_dotenv(os.path.join(BASE, ".env"), override=True)

import config
import applyfy_notify
from export_saldos import run_export, _log_txt
import db

config.ensure_data_dir()

MAX_EXPORT_RETRIES = 0
RETRY_SLEEP_SEC = 45
MAX_RUN_HOURS = 6

def main():
    # 1) Login e salvar sessão (subprocess para isolar Playwright)
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "01_salvar_sessao.py")],
        cwd=BASE,
        env=os.environ,
    )
    if r.returncode != 0:
        print("Falha no login. Abortando run diário.", flush=True)
        applyfy_notify.notify_failure("Login/sessão Applyfy falhou (01_salvar_sessao).")
        sys.exit(r.returncode)

    print("Login OK. Iniciando exportação de saldos (pode levar 1–2 min até a primeira linha)...", flush=True)

    # 2) Exportar saldos: loop até concluir com sucesso ou atingir limite de tempo (MAX_RUN_HOURS)
    resultados = []
    log_rows = []
    run_at = None
    inicio_run = time.perf_counter()
    while True:
        try:
            resultados, log_rows, run_at = run_export(session_path=config.SESSION_FILE, save_to_disk=True)
            break
        except Exception as e:
            _log_txt(f"Exportação falhou: {e}")
            print(f"Exportação falhou: {e}", flush=True)
            elapsed_h = (time.perf_counter() - inicio_run) / 3600
            if elapsed_h >= MAX_RUN_HOURS:
                print(f"Limite de {MAX_RUN_HOURS}h atingido. Encerrando.", flush=True)
                applyfy_notify.notify_failure(
                    f"Exportação de saldos: limite de {MAX_RUN_HOURS}h atingido sem concluir."
                )
                sys.exit(1)
            print(f"Aguardando {RETRY_SLEEP_SEC}s antes de retentar (retomando de onde parou)...", flush=True)
            time.sleep(RETRY_SLEEP_SEC)

    # 3) Registrar run no Postgres (saldos_historico já foi preenchido durante o export)
    if resultados and db.DATABASE_URL:
        db.save_export_run(resultados, log_rows, run_at=run_at)

    applyfy_notify.notify_export_success(resultados, log_rows, run_at)
    print("Run diário concluído. Registros:", len(resultados), flush=True)


if __name__ == "__main__":
    main()
