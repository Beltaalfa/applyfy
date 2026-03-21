# -*- coding: utf-8 -*-
"""Executor standalone do exportador de vendas ApplyFy."""
import os

_BASE = os.path.dirname(os.path.abspath(__file__))
from dotenv import load_dotenv

# Antes de importar módulos que carregam db.py — senão DATABASE_URL fica vazio e nada grava no Postgres.
load_dotenv(os.path.join(_BASE, ".env"), override=True)

from applyfy_export_vendas import run_export_vendas


if __name__ == "__main__":
    stats = run_export_vendas()
    print(
        (
            "Resumo export vendas | páginas={p} processadas={pr} "
            "inseridas={i} atualizadas={a} erros={e}"
        ).format(
            p=stats.paginas,
            pr=stats.processadas,
            i=stats.inseridas,
            a=stats.atualizadas,
            e=stats.erros,
        ),
        flush=True,
    )
