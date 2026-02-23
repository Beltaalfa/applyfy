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


def _db_user_from_url():
    """Extrai o usuário da DATABASE_URL (só para mensagens; não expõe senha)."""
    if not DATABASE_URL:
        return None
    try:
        part = DATABASE_URL.split("@")[0]
        if "://" in part:
            part = part.split("://", 1)[1]
        if ":" in part:
            return part.split(":")[0]
        return part
    except Exception:
        return None


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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saldos_historico (
                run_at TIMESTAMPTZ NOT NULL,
                email TEXT NOT NULL,
                nome TEXT NOT NULL,
                saldo_pendente NUMERIC(16,2) NOT NULL DEFAULT 0,
                saldo_retido NUMERIC(16,2) NOT NULL DEFAULT 0,
                saldo_disponivel NUMERIC(16,2) NOT NULL DEFAULT 0,
                total_sacado NUMERIC(16,2) NOT NULL DEFAULT 0,
                vendas_liquidas NUMERIC(16,2) NOT NULL DEFAULT 0,
                indicacao NUMERIC(16,2) NOT NULL DEFAULT 0,
                outros NUMERIC(16,2) NOT NULL DEFAULT 0,
                PRIMARY KEY (run_at, email)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_saldos_historico_run_at ON saldos_historico(run_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_saldos_historico_email ON saldos_historico(email);")


def _row_to_historico(run_at, row):
    def num(v):
        try:
            return float(v) if v is not None and v != "" else 0.0
        except (TypeError, ValueError):
            return 0.0
    return (
        run_at,
        (row.get("Email") or "").strip() or "sem-email",
        (row.get("Nome") or "").strip(),
        num(row.get("Saldo pendente")),
        num(row.get("Saldo retido")),
        num(row.get("Saldo disponível")),
        num(row.get("Total sacado")),
        num(row.get("Vendas líquidas")),
        num(row.get("Indicação")),
        num(row.get("Outros")),
    )


def insert_saldo_row(run_at, row):
    """Insere um produtor no histórico durante a exportação (alimentação em tempo real)."""
    if not DATABASE_URL:
        return
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO saldos_historico (run_at, email, nome, saldo_pendente, saldo_retido, saldo_disponivel, total_sacado, vendas_liquidas, indicacao, outros)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_at, email) DO UPDATE SET
                nome = EXCLUDED.nome,
                saldo_pendente = EXCLUDED.saldo_pendente,
                saldo_retido = EXCLUDED.saldo_retido,
                saldo_disponivel = EXCLUDED.saldo_disponivel,
                total_sacado = EXCLUDED.total_sacado,
                vendas_liquidas = EXCLUDED.vendas_liquidas,
                indicacao = EXCLUDED.indicacao,
                outros = EXCLUDED.outros;
            """,
            _row_to_historico(run_at, row),
        )


def save_export_run(resultados, log_rows, run_at=None):
    """Salva o resultado no Postgres. run_at opcional (quando já alimentou saldos_historico durante o processo)."""
    if not DATABASE_URL:
        return
    init_db()
    ok_c = sum(1 for r in log_rows if r.get("status") == "OK")
    timeout_c = sum(1 for r in log_rows if r.get("status") == "TIMEOUT")
    erro_c = sum(1 for r in log_rows if r.get("status") == "ERRO")
    data = {"resultados": resultados, "log_rows": log_rows}
    with cursor() as cur:
        if run_at is not None:
            cur.execute(
                """
                INSERT INTO export_runs (run_at, rows_count, ok_count, timeout_count, erro_count, data)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (run_at, len(resultados), ok_c, timeout_c, erro_c, json.dumps(data, ensure_ascii=False)),
            )
        else:
            cur.execute(
                """
                INSERT INTO export_runs (run_at, rows_count, ok_count, timeout_count, erro_count, data)
                VALUES (NOW(), %s, %s, %s, %s, %s)
                RETURNING run_at;
                """,
                (len(resultados), ok_c, timeout_c, erro_c, json.dumps(data, ensure_ascii=False)),
            )
            run_at = cur.fetchone()[0]
            for row in resultados:
                cur.execute(
                    """
                    INSERT INTO saldos_historico (run_at, email, nome, saldo_pendente, saldo_retido, saldo_disponivel, total_sacado, vendas_liquidas, indicacao, outros)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_at, email) DO UPDATE SET
                        nome = EXCLUDED.nome,
                        saldo_pendente = EXCLUDED.saldo_pendente,
                        saldo_retido = EXCLUDED.saldo_retido,
                        saldo_disponivel = EXCLUDED.saldo_disponivel,
                        total_sacado = EXCLUDED.total_sacado,
                        vendas_liquidas = EXCLUDED.vendas_liquidas,
                        indicacao = EXCLUDED.indicacao,
                        outros = EXCLUDED.outros;
                    """,
                    _row_to_historico(run_at, row),
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


def get_datas_disponiveis():
    """Lista de (run_at, label) de runs com histórico, mais recente primeiro."""
    if not DATABASE_URL:
        return []
    init_db()
    with cursor() as cur:
        cur.execute(
            "SELECT DISTINCT run_at FROM saldos_historico ORDER BY run_at DESC LIMIT 365;"
        )
        rows = cur.fetchall()
    return [(r[0], r[0].strftime("%d/%m/%Y %H:%M") if hasattr(r[0], "strftime") else str(r[0])) for r in rows]


def get_relatorio_por_data(run_at):
    """Retorna lista de dicts (resultados) para a data run_at. run_at pode ser ISO string ou datetime."""
    if not DATABASE_URL:
        return []
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT email, nome, saldo_pendente, saldo_retido, saldo_disponivel, total_sacado, vendas_liquidas, indicacao, outros
            FROM saldos_historico WHERE run_at = %s ORDER BY nome;
            """,
            (run_at,),
        )
        rows = cur.fetchall()
    return [
        {
            "Email": r[0],
            "Nome": r[1],
            "Saldo pendente": float(r[2]) if r[2] is not None else 0,
            "Saldo retido": float(r[3]) if r[3] is not None else 0,
            "Saldo disponível": float(r[4]) if r[4] is not None else 0,
            "Total sacado": float(r[5]) if r[5] is not None else 0,
            "Vendas líquidas": float(r[6]) if r[6] is not None else 0,
            "Indicação": float(r[7]) if r[7] is not None else 0,
            "Outros": float(r[8]) if r[8] is not None else 0,
        }
        for r in rows
    ]


def get_evolucao_produtor(email):
    """Retorna lista de { run_at, nome, saldo_pendente, ... } para o email, ordenado por run_at."""
    if not DATABASE_URL:
        return []
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT run_at, nome, saldo_pendente, saldo_retido, saldo_disponivel, total_sacado, vendas_liquidas, indicacao, outros
            FROM saldos_historico WHERE email = %s ORDER BY run_at;
            """,
            (email,),
        )
        rows = cur.fetchall()
    return [
        {
            "run_at": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "nome": r[1],
            "saldo_pendente": float(r[2]) if r[2] is not None else 0,
            "saldo_retido": float(r[3]) if r[3] is not None else 0,
            "saldo_disponivel": float(r[4]) if r[4] is not None else 0,
            "total_sacado": float(r[5]) if r[5] is not None else 0,
            "vendas_liquidas": float(r[6]) if r[6] is not None else 0,
            "indicacao": float(r[7]) if r[7] is not None else 0,
            "outros": float(r[8]) if r[8] is not None else 0,
        }
        for r in rows
    ]


def get_produtores_emails():
    """Lista de { email, nome } únicos (do último run ou histórico) para dropdown."""
    if not DATABASE_URL:
        return []
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (email) email, nome FROM saldos_historico ORDER BY email, run_at DESC;
            """
        )
        rows = cur.fetchall()
    return [{"email": r[0], "nome": r[1] or r[0]} for r in rows]
