# -*- coding: utf-8 -*-
"""
Job diário: login automático + exportação + gravação em disco e Postgres.
Agendar com cron às 2h: 0 2 * * * cd /var/www/applyfy && . env.sh && python run_daily.py
"""
import os
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

import config
from export_saldos import run_export
import db

config.ensure_data_dir()
BASE = os.path.dirname(os.path.abspath(__file__))


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

    # 2) Exportar saldos (usa sessão recém-salva)
    resultados, log_rows = run_export(session_path=config.SESSION_FILE, save_to_disk=True)

    # 3) Salvar no Postgres se DATABASE_URL estiver definido
    if resultados and db.DATABASE_URL:
        db.save_export_run(resultados, log_rows)

    print("Run diário concluído. Registros:", len(resultados))


if __name__ == "__main__":
    main()
