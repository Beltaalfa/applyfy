# -*- coding: utf-8 -*-
"""
Job diário: login automático + exportação + gravação em disco e Postgres.
Agendar com cron às 2h: 0 2 * * * cd /var/www/applyfy && . env.sh && python run_daily.py
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
from dotenv import load_dotenv

# .env do projeto sempre prevalece (evita DATABASE_URL do shell, ex. tactical)
load_dotenv(os.path.join(BASE, ".env"), override=True)

import config
from export_saldos import run_export
import db

config.ensure_data_dir()


def main():
    # 1) Login e salvar sessão (subprocess para isolar Playwright)
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "01_salvar_sessao.py")],
        cwd=BASE,
        env=os.environ,
    )
    if r.returncode != 0:
        print("Falha no login. Abortando run diário.")
        sys.exit(r.returncode)

    print("Login OK. Iniciando exportação de saldos (pode levar 1–2 min até a primeira linha)...", flush=True)
    # 2) Exportar saldos (usa sessão recém-salva; Postgres é alimentado a cada produtor)
    resultados, log_rows, run_at = run_export(session_path=config.SESSION_FILE, save_to_disk=True)

    # 3) Registrar run no Postgres (saldos_historico já foi preenchido durante o export)
    if resultados and db.DATABASE_URL:
        db.save_export_run(resultados, log_rows, run_at=run_at)

    print("Run diário concluído. Registros:", len(resultados))


if __name__ == "__main__":
    main()
