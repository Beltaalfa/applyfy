# -*- coding: utf-8 -*-
"""Conexão e helpers para PostgreSQL (export runs e último relatório)."""
import os
import json
from contextlib import contextmanager
from datetime import datetime

import config

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL and os.environ.get("PG_HOST"):
    # Monta URL a partir de variáveis
    user = os.environ.get("PG_USER", "applyfy")
    password = os.environ.get("PG_PASSWORD", "")
    host = os.environ.get("PG_HOST", "localhost")
    port = os.environ.get("PG_PORT", "5432")
    dbname = os.environ.get("PG_DATABASE", "applyfy")
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def get_connection():
    import psycopg2
    return psycopg2.connect(DATABASE_URL, connect_timeout=5)


@contextmanager
def cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()


def init_db():
    """Cria tabelas se não existirem."""
    with cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS export_runs (
                id SERIAL PRIMARY KEY,
                run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                rows_count INT NOT NULL,
                ok_count INT NOT NULL,
                timeout_count INT NOT NULL,
                erro_count INT NOT NULL,
                data JSONB NOT NULL
            );
        """)


def save_export_run(resultados, log_rows):
    """Salva o resultado de uma exportação no Postgres."""
    if not DATABASE_URL:
        return
    init_db()
    ok_c = sum(1 for r in log_rows if r.get("status") == "OK")
    timeout_c = sum(1 for r in log_rows if r.get("status") == "TIMEOUT")
    erro_c = sum(1 for r in log_rows if r.get("status") == "ERRO")
    data = {"resultados": resultados, "log_rows": log_rows}
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO export_runs (run_at, rows_count, ok_count, timeout_count, erro_count, data)
            VALUES (NOW(), %s, %s, %s, %s, %s);
            """,
            (len(resultados), ok_c, timeout_c, erro_c, json.dumps(data, ensure_ascii=False)),
        )


def get_last_export_data():
    """Retorna (run_at, resultados) do último export ou (None, [])."""
    if not DATABASE_URL:
        return None, []
    init_db()
    with cursor() as cur:
        cur.execute(
            "SELECT run_at, data FROM export_runs ORDER BY run_at DESC LIMIT 1;"
        )
        row = cur.fetchone()
    if not row:
        return None, []
    run_at, data = row
    if isinstance(data, str):
        data = json.loads(data)
    return run_at, data.get("resultados", [])
