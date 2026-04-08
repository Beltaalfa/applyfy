# -*- coding: utf-8 -*-
"""Conexão e helpers para PostgreSQL (export runs e último relatório)."""
import hashlib
import os
import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import config


def get_database_url() -> str | None:
    """Lê a URL do Postgres no momento da chamada (funciona após load_dotenv no script)."""
    url = os.environ.get("DATABASE_URL")
    if not url and os.environ.get("PG_HOST"):
        user = os.environ.get("PG_USER", "applyfy")
        password = os.environ.get("PG_PASSWORD", "")
        host = os.environ.get("PG_HOST", "localhost")
        port = os.environ.get("PG_PORT", "5432")
        dbname = os.environ.get("PG_DATABASE", "applyfy")
        url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return url


def __getattr__(name: str):
    """Compat: ``db.DATABASE_URL`` resolve sempre do ambiente atual."""
    if name == "DATABASE_URL":
        return get_database_url()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _db_user_from_url():
    """Extrai o usuário da DATABASE_URL (só para mensagens; não expõe senha)."""
    url = get_database_url()
    if not url:
        return None
    try:
        part = url.split("@")[0]
        if "://" in part:
            part = part.split("://", 1)[1]
        if ":" in part:
            return part.split(":")[0]
        return part
    except Exception:
        return None


def get_connection():
    import psycopg2

    url = get_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL não definido (configure .env ou exporte a variável).")
    return psycopg2.connect(url, connect_timeout=5)


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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applyfy_transactions (
                id SERIAL PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                event TEXT NOT NULL,
                offer_code TEXT,
                producer_id TEXT,
                payload JSONB NOT NULL,
                received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_applyfy_transaction_event UNIQUE (transaction_id, event)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_applyfy_transactions_event ON applyfy_transactions(event);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_applyfy_transactions_offer_code ON applyfy_transactions(offer_code);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_applyfy_transactions_received_at ON applyfy_transactions(received_at);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applyfy_webhook_dlq (
                id SERIAL PRIMARY KEY,
                received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                event TEXT,
                payload JSONB NOT NULL,
                error_message TEXT NOT NULL,
                retry_count INT NOT NULL DEFAULT 0,
                processed_at TIMESTAMPTZ
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_applyfy_webhook_dlq_pending ON applyfy_webhook_dlq (processed_at) WHERE processed_at IS NULL;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applyfy_producer_taxes (
                producer_id TEXT PRIMARY KEY,
                email TEXT,
                taxes_snapshot JSONB NOT NULL DEFAULT '{}',
                fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_applyfy_producer_taxes_email ON applyfy_producer_taxes(email);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applyfy_offer_producer (
                offer_code TEXT PRIMARY KEY,
                producer_id TEXT NOT NULL,
                producer_name TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applyfy_producer_vendedor (
                producer_email TEXT PRIMARY KEY,
                vendedor_nome TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_applyfy_producer_vendedor_nome ON applyfy_producer_vendedor (vendedor_nome);"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS financeiro_categorias (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('receita','despesa')),
                ativa BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_financeiro_categorias_tipo ON financeiro_categorias(tipo);")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS financeiro_lancamentos (
                id SERIAL PRIMARY KEY,
                data DATE NOT NULL,
                valor NUMERIC(16,2) NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('receita','despesa')),
                categoria_id INT REFERENCES financeiro_categorias(id) ON DELETE SET NULL,
                descricao TEXT,
                natureza_dfc TEXT CHECK (natureza_dfc IN ('operacional','investimento','financiamento')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_financeiro_lancamentos_data ON financeiro_lancamentos(data);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_financeiro_lancamentos_tipo ON financeiro_lancamentos(tipo);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_financeiro_lancamentos_categoria ON financeiro_lancamentos(categoria_id);")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS banco_ofx_imports (
                id SERIAL PRIMARY KEY,
                imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                filename TEXT,
                conta_ref TEXT NOT NULL,
                bank_id TEXT,
                account_id TEXT,
                currency TEXT,
                balance_end NUMERIC(16,2),
                balance_date DATE,
                periodo_inicio DATE,
                periodo_fim DATE,
                movimentos_count INT NOT NULL DEFAULT 0
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_banco_ofx_imports_conta ON banco_ofx_imports (conta_ref);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS banco_extrato_linhas (
                id SERIAL PRIMARY KEY,
                import_id INT NOT NULL REFERENCES banco_ofx_imports(id) ON DELETE CASCADE,
                conta_ref TEXT NOT NULL,
                fitid TEXT,
                dedupe_key TEXT NOT NULL,
                data_mov DATE NOT NULL,
                valor NUMERIC(16,2) NOT NULL,
                memo TEXT,
                payee TEXT,
                tipo TEXT NOT NULL CHECK (tipo IN ('credito','debito')),
                conciliado_lancamento_id INT REFERENCES financeiro_lancamentos(id) ON DELETE SET NULL,
                conciliado_em TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_banco_extrato_conta_dedupe UNIQUE (conta_ref, dedupe_key)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_banco_extrato_data ON banco_extrato_linhas (data_mov);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_banco_extrato_conta ON banco_extrato_linhas (conta_ref);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_banco_extrato_pendente ON banco_extrato_linhas (conta_ref) WHERE conciliado_lancamento_id IS NULL;"
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_banco_extrato_lancamento_unico
            ON banco_extrato_linhas (conciliado_lancamento_id)
            WHERE conciliado_lancamento_id IS NOT NULL;
            """
        )

        cur.execute("SELECT 1 FROM financeiro_categorias LIMIT 1")
        if cur.fetchone() is None:
            for nome, tipo in [
                ("Vendas", "receita"), ("Serviços", "receita"),
                ("Salários", "despesa"), ("Luz", "despesa"), ("Água", "despesa"),
                ("Aluguel", "despesa"), ("Outros", "despesa"),
            ]:
                cur.execute(
                    "INSERT INTO financeiro_categorias (nome, tipo) VALUES (%s, %s)",
                    (nome, tipo),
                )


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
    if not get_database_url():
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
    if not get_database_url():
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
    if not get_database_url():
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
    if not get_database_url():
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
    if not get_database_url():
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
    if not get_database_url():
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
    if not get_database_url():
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


def insert_webhook_transaction(transaction_id, event, offer_code, producer_id, payload):
    """
    Insere evento de webhook (idempotente).
    Retorna (status, erro_opcional): inserted | duplicate | no_db | error.
    """
    if not get_database_url():
        return "no_db", None
    init_db()
    payload_val = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else payload
    with cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO applyfy_transactions (transaction_id, event, offer_code, producer_id, payload)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (transaction_id, event) DO NOTHING;
                """,
                (
                    str(transaction_id),
                    str(event),
                    offer_code and str(offer_code)[:64] or None,
                    producer_id and str(producer_id)[:64] or None,
                    payload_val,
                ),
            )
            if cur.rowcount > 0:
                return "inserted", None
            return "duplicate", None
        except Exception as e:
            return "error", str(e)[:500]


def insert_webhook_dlq(event, payload, error_message):
    """Persiste payload que não pôde ser gravado em applyfy_transactions."""
    if not get_database_url():
        return
    init_db()
    if not isinstance(payload, dict):
        payload = {}
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO applyfy_webhook_dlq (event, payload, error_message)
            VALUES (%s, %s, %s);
            """,
            (
                (event and str(event)[:128]) or None,
                json.dumps(payload, ensure_ascii=False),
                (error_message or "")[:2000],
            ),
        )


def get_webhook_dlq_row(dlq_id):
    """Uma linha da DLQ por id ou None."""
    if not get_database_url():
        return None
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT id, received_at, event, error_message, retry_count, payload, processed_at
            FROM applyfy_webhook_dlq WHERE id = %s;
            """,
            (int(dlq_id),),
        )
        r = cur.fetchone()
    if not r:
        return None
    p = r[5]
    if isinstance(p, str):
        p = json.loads(p) if p else {}
    return {
        "id": r[0],
        "received_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
        "event": r[2],
        "error_message": r[3],
        "retry_count": r[4],
        "payload": p if isinstance(p, dict) else {},
        "processed_at": r[6].isoformat() if r[6] and hasattr(r[6], "isoformat") else (str(r[6]) if r[6] else None),
    }


def list_webhook_dlq_pending(limit=50):
    """Filas com falha ainda não reprocessadas."""
    if not get_database_url():
        return []
    init_db()
    lim = min(int(limit), 200)
    with cursor() as cur:
        cur.execute(
            """
            SELECT id, received_at, event, error_message, retry_count, payload
            FROM applyfy_webhook_dlq
            WHERE processed_at IS NULL
            ORDER BY id ASC
            LIMIT %s;
            """,
            (lim,),
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        p = r[5]
        if isinstance(p, str):
            p = json.loads(p) if p else {}
        out.append(
            {
                "id": r[0],
                "received_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "event": r[2],
                "error_message": r[3],
                "retry_count": r[4],
                "payload": p if isinstance(p, dict) else {},
            }
        )
    return out


def mark_webhook_dlq_processed(dlq_id):
    if not get_database_url():
        return
    init_db()
    with cursor() as cur:
        cur.execute(
            "UPDATE applyfy_webhook_dlq SET processed_at = NOW() WHERE id = %s AND processed_at IS NULL;",
            (int(dlq_id),),
        )


def increment_webhook_dlq_retry(dlq_id):
    if not get_database_url():
        return
    init_db()
    with cursor() as cur:
        cur.execute(
            "UPDATE applyfy_webhook_dlq SET retry_count = retry_count + 1 WHERE id = %s;",
            (int(dlq_id),),
        )


def get_last_export_run_at():
    """Último run_at em export_runs ou None."""
    if not get_database_url():
        return None
    init_db()
    with cursor() as cur:
        cur.execute("SELECT MAX(run_at) FROM export_runs;")
        row = cur.fetchone()
    return row[0] if row and row[0] else None


def get_last_webhook_received_at():
    """Último received_at em applyfy_transactions ou None."""
    if not get_database_url():
        return None
    init_db()
    with cursor() as cur:
        cur.execute("SELECT MAX(received_at) FROM applyfy_transactions;")
        row = cur.fetchone()
    return row[0] if row and row[0] else None


def count_webhook_dlq_pending():
    if not get_database_url():
        return 0
    init_db()
    with cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM applyfy_webhook_dlq WHERE processed_at IS NULL;"
        )
        row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def list_transactions(date_from=None, date_to=None, event=None, offer_code=None, limit=500):
    """Lista transações com filtros. Retorna lista de dicts."""
    if not get_database_url():
        return []
    init_db()
    conditions = []
    params = []
    if date_from:
        conditions.append("received_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("received_at <= %s")
        params.append(date_to)
    if event:
        conditions.append("event = %s")
        params.append(event)
    if offer_code:
        conditions.append("offer_code = %s")
        params.append(offer_code)
    params.append(min(int(limit), 1000))
    where = " AND ".join(conditions) if conditions else "1=1"
    with cursor() as cur:
        cur.execute(
            f"""
            SELECT id, transaction_id, event, offer_code, producer_id, payload, received_at
            FROM applyfy_transactions
            WHERE {where}
            ORDER BY received_at DESC
            LIMIT %s;
            """,
            params,
        )
        rows = cur.fetchall()
    return [
        {
            "id": r[0],
            "transaction_id": r[1],
            "event": r[2],
            "offer_code": r[3],
            "producer_id": r[4],
            "payload": r[5] if isinstance(r[5], dict) else (json.loads(r[5]) if r[5] else {}),
            "received_at": r[6].isoformat() if hasattr(r[6], "isoformat") else str(r[6]),
        }
        for r in rows
    ]


def save_producer_taxes(producer_id, email, taxes_snapshot):
    """Salva ou atualiza cache de taxas do produtor."""
    if not get_database_url():
        return
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO applyfy_producer_taxes (producer_id, email, taxes_snapshot, fetched_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (producer_id) DO UPDATE SET
                email = EXCLUDED.email,
                taxes_snapshot = EXCLUDED.taxes_snapshot,
                fetched_at = NOW();
            """,
            (str(producer_id), email or None, json.dumps(taxes_snapshot, ensure_ascii=False) if isinstance(taxes_snapshot, dict) else taxes_snapshot),
        )


def get_producer_taxes(producer_id=None, email=None):
    """Retorna último taxes_snapshot e fetched_at por producer_id ou email."""
    if not get_database_url():
        return None
    init_db()
    with cursor() as cur:
        if producer_id:
            cur.execute(
                "SELECT taxes_snapshot, fetched_at FROM applyfy_producer_taxes WHERE producer_id = %s;",
                (str(producer_id),),
            )
        elif email:
            cur.execute(
                "SELECT taxes_snapshot, fetched_at FROM applyfy_producer_taxes WHERE email = %s;",
                (email,),
            )
        else:
            return None
        row = cur.fetchone()
    if not row:
        return None
    snapshot = row[0]
    if isinstance(snapshot, str):
        snapshot = json.loads(snapshot) if snapshot else {}
    return {"taxes_snapshot": snapshot, "fetched_at": row[1]}


def save_offer_producer(offer_code, producer_id, producer_name=None):
    """Salva mapeamento offer_code -> produtor (para preencher transações que não trazem produtor no payload)."""
    if not get_database_url() or not offer_code or not producer_id:
        return
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO applyfy_offer_producer (offer_code, producer_id, producer_name, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (offer_code) DO UPDATE SET
                producer_id = EXCLUDED.producer_id,
                producer_name = EXCLUDED.producer_name,
                updated_at = NOW();
            """,
            (str(offer_code).strip()[:64], str(producer_id)[:64], (producer_name or "")[:256] or None),
        )


def get_producer_by_offer_code(offer_code):
    """Retorna {producer_id, producer_name} para um offer_code, ou None."""
    if not get_database_url() or not offer_code:
        return None
    init_db()
    with cursor() as cur:
        cur.execute(
            "SELECT producer_id, producer_name FROM applyfy_offer_producer WHERE offer_code = %s;",
            (str(offer_code).strip(),),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {"producer_id": row[0], "producer_name": row[1]}


def _normalize_producer_email(email: str | None) -> str:
    return (email or "").strip().lower()


def list_producer_vendedor():
    """
    Carteira comercial: atribuição vendedor → produtor (email do export).
    Retorna lista de { producer_email, vendedor_nome, updated_at }.
    """
    if not get_database_url():
        return []
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT producer_email, vendedor_nome, updated_at
            FROM applyfy_producer_vendedor
            ORDER BY lower(vendedor_nome), producer_email;
            """
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        ts = r[2]
        out.append(
            {
                "producer_email": r[0],
                "vendedor_nome": r[1],
                "updated_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            }
        )
    return out


def upsert_producer_vendedor(producer_email, vendedor_nome):
    """
    Define o vendedor do produtor. vendedor_nome vazio remove a linha.
    Retorna True se alterou a BD, False se sem URL ou email inválido.
    """
    if not get_database_url():
        return False
    key = _normalize_producer_email(producer_email)
    if not key:
        return False
    nome = (vendedor_nome or "").strip()[:200]
    init_db()
    with cursor() as cur:
        if not nome:
            cur.execute("DELETE FROM applyfy_producer_vendedor WHERE producer_email = %s;", (key,))
            return True
        cur.execute(
            """
            INSERT INTO applyfy_producer_vendedor (producer_email, vendedor_nome, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (producer_email) DO UPDATE SET
                vendedor_nome = EXCLUDED.vendedor_nome,
                updated_at = NOW();
            """,
            (key, nome),
        )
    return True


def list_producer_created_events(limit=200):
    """Lista eventos PRODUCER_CREATED para sincronizar offer_code -> produtor."""
    if not get_database_url():
        return []
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT producer_id, payload FROM applyfy_transactions
            WHERE event = 'PRODUCER_CREATED' AND producer_id IS NOT NULL
            ORDER BY received_at DESC LIMIT %s;
            """,
            (limit,),
        )
        rows = cur.fetchall()
    seen = set()
    out = []
    for r in rows:
        pid = r[0]
        if pid in seen:
            continue
        seen.add(pid)
        p = r[1] if isinstance(r[1], dict) else (json.loads(r[1]) if r[1] else {})
        name = (p.get("producer") or {}).get("name")
        out.append((pid, name))
    return out


def list_webhook_producers(limit=500):
    """
    Lista produtores únicos: webhook (PRODUCER_CREATED) + applyfy_offer_producer + fallback saldos_historico.
    Retorna lista de dicts: { producer_id, producer_name, offer_codes[] }.
    """
    if not get_database_url():
        return []
    init_db()
    by_id = {}
    with cursor() as cur:
        cur.execute(
            """
            SELECT producer_id, payload FROM applyfy_transactions
            WHERE event = 'PRODUCER_CREATED' AND producer_id IS NOT NULL
            ORDER BY received_at DESC;
            """
        )
        for r in cur.fetchall():
            pid = r[0]
            if pid not in by_id:
                p = r[1] if isinstance(r[1], dict) else (json.loads(r[1]) if r[1] else {})
                name = (p.get("producer") or {}).get("name")
                by_id[pid] = {"producer_id": pid, "producer_name": name or None, "offer_codes": []}
        cur.execute("SELECT offer_code, producer_id, producer_name FROM applyfy_offer_producer;")
        for r in cur.fetchall():
            code, pid, name = r[0], r[1], r[2]
            if pid not in by_id:
                by_id[pid] = {"producer_id": pid, "producer_name": name, "offer_codes": []}
            if code and code not in by_id[pid]["offer_codes"]:
                by_id[pid]["offer_codes"].append(code)
            if name and not by_id[pid]["producer_name"]:
                by_id[pid]["producer_name"] = name
        # Fallback: produtores do histórico de saldos (exportação) para não ficar vazio
        cur.execute(
            """
            SELECT DISTINCT ON (email) email, nome FROM saldos_historico
            ORDER BY email, run_at DESC;
            """
        )
        for r in cur.fetchall():
            email, nome = r[0], r[1]
            if not email:
                continue
            key = "email:" + str(email)
            if key not in by_id:
                by_id[key] = {"producer_id": email, "producer_name": nome or email, "offer_codes": []}
    out = list(by_id.values())[: int(limit)]
    return sorted(out, key=lambda x: (x["producer_name"] or "").lower())


def list_categorias(tipo=None):
    if not get_database_url():
        return []
    init_db()
    with cursor() as cur:
        if tipo:
            cur.execute("SELECT id, nome, tipo, ativa, created_at FROM financeiro_categorias WHERE tipo = %s ORDER BY nome", (tipo,))
        else:
            cur.execute("SELECT id, nome, tipo, ativa, created_at FROM financeiro_categorias ORDER BY tipo, nome")
        rows = cur.fetchall()
    return [{"id": r[0], "nome": r[1], "tipo": r[2], "ativa": bool(r[3]), "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4])} for r in rows]


def get_categoria(id):
    if not get_database_url() or not id:
        return None
    init_db()
    with cursor() as cur:
        cur.execute("SELECT id, nome, tipo, ativa, created_at FROM financeiro_categorias WHERE id = %s", (int(id),))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "nome": row[1], "tipo": row[2], "ativa": bool(row[3]), "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4])}


def create_categoria(nome, tipo):
    if not get_database_url() or not nome or tipo not in ("receita", "despesa"):
        return None
    init_db()
    with cursor() as cur:
        cur.execute("INSERT INTO financeiro_categorias (nome, tipo) VALUES (%s, %s) RETURNING id, nome, tipo, ativa, created_at", (nome.strip()[:200], tipo))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "nome": row[1], "tipo": row[2], "ativa": bool(row[3]), "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4])}


def update_categoria(id, nome=None, tipo=None, ativa=None):
    if not get_database_url() or not id:
        return False
    init_db()
    updates, params = [], []
    if nome is not None:
        updates.append("nome = %s")
        params.append(nome.strip()[:200])
    if tipo is not None and tipo in ("receita", "despesa"):
        updates.append("tipo = %s")
        params.append(tipo)
    if ativa is not None:
        updates.append("ativa = %s")
        params.append(bool(ativa))
    if not updates:
        return True
    params.append(int(id))
    with cursor() as cur:
        cur.execute("UPDATE financeiro_categorias SET " + ", ".join(updates) + " WHERE id = %s", params)
        return cur.rowcount > 0


def delete_categoria(id):
    if not get_database_url() or not id:
        return False
    init_db()
    with cursor() as cur:
        cur.execute("DELETE FROM financeiro_categorias WHERE id = %s", (int(id),))
        return cur.rowcount > 0


def _parse_period(date_from=None, date_to=None, mes=None, ano=None):
    if mes is not None and ano is not None:
        try:
            from calendar import monthrange
            mes, ano = int(mes), int(ano)
            _, last = monthrange(ano, mes)
            date_from = f"{ano:04d}-{mes:02d}-01"
            date_to = f"{ano:04d}-{mes:02d}-{last:02d}"
        except (ValueError, TypeError):
            pass
    return date_from, date_to


def list_lancamentos(date_from=None, date_to=None, mes=None, ano=None, tipo=None, categoria_id=None, limit=2000):
    if not get_database_url():
        return []
    date_from, date_to = _parse_period(date_from, date_to, mes, ano)
    init_db()
    conditions, params = [], []
    if date_from:
        conditions.append("l.data >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("l.data <= %s")
        params.append(date_to)
    if tipo:
        conditions.append("l.tipo = %s")
        params.append(tipo)
    if categoria_id is not None:
        conditions.append("l.categoria_id = %s")
        params.append(int(categoria_id))
    params.append(min(int(limit), 2000))
    where = " AND ".join(conditions) if conditions else "1=1"
    with cursor() as cur:
        cur.execute(
            f"SELECT l.id, l.data, l.valor, l.tipo, l.categoria_id, c.nome, l.descricao, l.natureza_dfc, l.created_at, l.updated_at FROM financeiro_lancamentos l LEFT JOIN financeiro_categorias c ON c.id = l.categoria_id WHERE {where} ORDER BY l.data DESC, l.id DESC LIMIT %s",
            params,
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "data": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]), "valor": float(r[2]) if r[2] else 0, "tipo": r[3], "categoria_id": r[4], "categoria_nome": r[5], "descricao": r[6], "natureza_dfc": r[7], "created_at": r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8]), "updated_at": r[9].isoformat() if hasattr(r[9], "isoformat") else str(r[9])}
        for r in rows
    ]


def get_lancamento(id):
    if not get_database_url() or not id:
        return None
    init_db()
    with cursor() as cur:
        cur.execute("SELECT l.id, l.data, l.valor, l.tipo, l.categoria_id, c.nome, l.descricao, l.natureza_dfc, l.created_at, l.updated_at FROM financeiro_lancamentos l LEFT JOIN financeiro_categorias c ON c.id = l.categoria_id WHERE l.id = %s", (int(id),))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "data": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1]), "valor": float(row[2]) if row[2] else 0, "tipo": row[3], "categoria_id": row[4], "categoria_nome": row[5], "descricao": row[6], "natureza_dfc": row[7], "created_at": row[8].isoformat() if hasattr(row[8], "isoformat") else str(row[8]), "updated_at": row[9].isoformat() if hasattr(row[9], "isoformat") else str(row[9])}


def create_lancamento(data, valor, tipo, categoria_id=None, descricao=None, natureza_dfc=None):
    if not get_database_url() or tipo not in ("receita", "despesa"):
        return None
    try:
        val = abs(float(valor))
    except (TypeError, ValueError):
        return None
    init_db()
    cat_id = int(categoria_id) if categoria_id else None
    nat = natureza_dfc if natureza_dfc in ("operacional", "investimento", "financiamento") else None
    with cursor() as cur:
        cur.execute("INSERT INTO financeiro_lancamentos (data, valor, tipo, categoria_id, descricao, natureza_dfc, updated_at) VALUES (%s, %s, %s, %s, %s, %s, NOW()) RETURNING id", (data, val, tipo, cat_id, (descricao or "").strip() or None, nat))
        row = cur.fetchone()
    if not row:
        return None
    return get_lancamento(row[0])


def update_lancamento(id, data=None, valor=None, tipo=None, categoria_id=None, descricao=None, naturaleza_dfc=None):
    if not get_database_url() or not id:
        return False
    updates, params = ["updated_at = NOW()"], []
    if data is not None:
        updates.append("data = %s")
        params.append(data)
    if valor is not None:
        try:
            updates.append("valor = %s")
            params.append(abs(float(valor)))
        except (TypeError, ValueError):
            pass
    if tipo is not None and tipo in ("receita", "despesa"):
        updates.append("tipo = %s")
        params.append(tipo)
    if categoria_id is not None:
        updates.append("categoria_id = %s")
        params.append(int(categoria_id) if categoria_id else None)
    if descricao is not None:
        updates.append("descricao = %s")
        params.append((descricao or "").strip() or None)
    if naturaleza_dfc is not None:
        updates.append("natureza_dfc = %s")
        params.append(natureza_dfc if naturaleza_dfc in ("operacional", "investimento", "financiamento") else None)
    if len(params) == 0:
        return True
    params.append(int(id))
    with cursor() as cur:
        cur.execute("UPDATE financeiro_lancamentos SET " + ", ".join(updates) + " WHERE id = %s", params)
        return cur.rowcount > 0


def delete_lancamento(id):
    if not get_database_url() or not id:
        return False
    init_db()
    with cursor() as cur:
        cur.execute("DELETE FROM financeiro_lancamentos WHERE id = %s", (int(id),))
        return cur.rowcount > 0


def relatorio_fluxo_caixa(date_from=None, date_to=None, mes=None, ano=None):
    if not get_database_url():
        return {"dias": [], "total_receitas": 0, "total_despesas": 0, "saldo": 0}
    date_from, date_to = _parse_period(date_from, date_to, mes, ano)
    if not date_from or not date_to:
        return {"dias": [], "total_receitas": 0, "total_despesas": 0, "saldo": 0}
    init_db()
    with cursor() as cur:
        cur.execute("SELECT data, COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor ELSE 0 END), 0), COALESCE(SUM(CASE WHEN tipo = 'despesa' THEN valor ELSE 0 END), 0) FROM financeiro_lancamentos WHERE data >= %s AND data <= %s GROUP BY data ORDER BY data", (date_from, date_to))
        rows = cur.fetchall()
    dias = [{"data": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]), "receitas": float(r[1]), "despesas": float(r[2]), "saldo": float(r[1]) - float(r[2])} for r in rows]
    tr = sum(d["receitas"] for d in dias)
    td = sum(d["despesas"] for d in dias)
    return {"dias": dias, "total_receitas": tr, "total_despesas": td, "saldo": tr - td}


def relatorio_dre(date_from=None, date_to=None, mes=None, ano=None):
    if not get_database_url():
        return {"receitas": [], "despesas": [], "total_receitas": 0, "total_despesas": 0, "resultado": 0}
    date_from, date_to = _parse_period(date_from, date_to, mes, ano)
    if not date_from or not date_to:
        return {"receitas": [], "despesas": [], "total_receitas": 0, "total_despesas": 0, "resultado": 0}
    init_db()
    with cursor() as cur:
        cur.execute("SELECT COALESCE(c.nome, 'Sem categoria'), l.tipo, SUM(l.valor) FROM financeiro_lancamentos l LEFT JOIN financeiro_categorias c ON c.id = l.categoria_id WHERE l.data >= %s AND l.data <= %s GROUP BY c.nome, l.tipo ORDER BY l.tipo, SUM(l.valor) DESC", (date_from, date_to))
        rows = cur.fetchall()
    receitas = [{"categoria": r[0], "valor": float(r[2])} for r in rows if r[1] == "receita"]
    despesas = [{"categoria": r[0], "valor": float(r[2])} for r in rows if r[1] == "despesa"]
    tr = sum(x["valor"] for x in receitas)
    td = sum(x["valor"] for x in despesas)
    return {"receitas": receitas, "despesas": despesas, "total_receitas": tr, "total_despesas": td, "resultado": tr - td}


def relatorio_dfc(date_from=None, date_to=None, mes=None, ano=None):
    if not get_database_url():
        return {"operacional": {"entradas": 0, "saidas": 0, "saldo": 0}, "investimento": {"entradas": 0, "saidas": 0, "saldo": 0}, "financiamento": {"entradas": 0, "saidas": 0, "saldo": 0}}
    date_from, date_to = _parse_period(date_from, date_to, mes, ano)
    if not date_from or not date_to:
        return {"operacional": {"entradas": 0, "saidas": 0, "saldo": 0}, "investimento": {"entradas": 0, "saidas": 0, "saldo": 0}, "financiamento": {"entradas": 0, "saidas": 0, "saldo": 0}}
    init_db()
    with cursor() as cur:
        cur.execute("SELECT COALESCE(NULLIF(natureza_dfc, ''), 'operacional'), tipo, SUM(valor) FROM financeiro_lancamentos WHERE data >= %s AND data <= %s GROUP BY COALESCE(NULLIF(natureza_dfc, ''), 'operacional'), tipo", (date_from, date_to))
        rows = cur.fetchall()
    result = {n: {"entradas": 0.0, "saidas": 0.0, "saldo": 0.0} for n in ("operacional", "investimento", "financiamento")}
    for r in rows:
        nat = r[0] if r[0] in result else "operacional"
        v = float(r[2])
        if r[1] == "receita":
            result[nat]["entradas"] += v
        else:
            result[nat]["saidas"] += v
    for nat in result:
        result[nat]["saldo"] = result[nat]["entradas"] - result[nat]["saidas"]
    return result


def list_applyfy_vendas(
    date_from=None,
    date_to=None,
    adquirente=None,
    status_pagamento=None,
    produtor_email=None,
    comprador_email=None,
    busca=None,
    limit=200,
    offset=0,
):
    """Lista vendas consolidadas da tabela applyfy_vendas com filtros e paginação."""
    if not get_database_url():
        return {"rows": [], "total": 0}
    init_db()
    conditions = []
    params = []
    if date_from:
        conditions.append("data_venda >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("data_venda <= %s")
        params.append(date_to)
    if adquirente:
        conditions.append("adquirente ILIKE %s")
        params.append(f"%{adquirente}%")
    if status_pagamento:
        conditions.append("status_pagamento ILIKE %s")
        params.append(f"%{status_pagamento}%")
    if produtor_email:
        conditions.append("produtor_email ILIKE %s")
        params.append(f"%{produtor_email}%")
    if comprador_email:
        conditions.append("comprador_email ILIKE %s")
        params.append(f"%{comprador_email}%")
    if busca:
        conditions.append(
            "(codigo_venda ILIKE %s OR order_id ILIKE %s OR transaction_id ILIKE %s OR "
            "comprador_nome ILIKE %s OR produtor_nome ILIKE %s OR produto_nome ILIKE %s)"
        )
        like = f"%{busca}%"
        params.extend([like, like, like, like, like, like])
    where = " AND ".join(conditions) if conditions else "1=1"
    lim = min(max(int(limit), 1), 1000)
    off = max(int(offset), 0)

    with cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM applyfy_vendas WHERE {where};", params)
        total = int(cur.fetchone()[0] or 0)
        cur.execute(
            f"""
            SELECT
                codigo_venda, order_id, transaction_id, status_pagamento, valor_total, valor_cobrado,
                data_venda, data_liberacao, data_pagamento, data_atualizacao, metodo_pagamento,
                adquirente, adquirente_bruto, id_adquirente, taxa_processamento, taxa_adquirente, retencao,
                comissao_produtor, valor_liquido_produtor, produtor_nome, produtor_email, comprador_nome,
                comprador_email, comprador_telefone, comprador_cpf, comprador_cnpj, produto_nome, produto_id,
                offer_code, quantidade, valor_unitario, afiliado_nome, afiliado_email, affiliate_code,
                response_time_ms, tentativa_status, tentativa_substatus, tentativa_mensagem,
                pais, cep, estado, cidade, bairro, rua, numero, complemento,
                source_strategy, imported_at, last_seen_at
            FROM applyfy_vendas
            WHERE {where}
            ORDER BY data_venda DESC NULLS LAST, last_seen_at DESC
            LIMIT %s OFFSET %s;
            """,
            [*params, lim, off],
        )
        rows = cur.fetchall()

    cols = [
        "codigo_venda", "order_id", "transaction_id", "status_pagamento", "valor_total", "valor_cobrado",
        "data_venda", "data_liberacao", "data_pagamento", "data_atualizacao", "metodo_pagamento",
        "adquirente", "adquirente_bruto", "id_adquirente", "taxa_processamento", "taxa_adquirente", "retencao",
        "comissao_produtor", "valor_liquido_produtor", "produtor_nome", "produtor_email", "comprador_nome",
        "comprador_email", "comprador_telefone", "comprador_cpf", "comprador_cnpj", "produto_nome", "produto_id",
        "offer_code", "quantidade", "valor_unitario", "afiliado_nome", "afiliado_email", "affiliate_code",
        "response_time_ms", "tentativa_status", "tentativa_substatus", "tentativa_mensagem",
        "pais", "cep", "estado", "cidade", "bairro", "rua", "numero", "complemento",
        "source_strategy", "imported_at", "last_seen_at",
    ]
    out = []
    for r in rows:
        item = {}
        for i, c in enumerate(cols):
            v = r[i]
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            elif isinstance(v, (int, float)):
                v = v
            elif v is None:
                v = None
            else:
                v = str(v)
            item[c] = v
        out.append(item)
    return {"rows": out, "total": total}


def _extrato_dedupe_key(conta_ref: str, tx: dict) -> str:
    fid = tx.get("fitid")
    if fid:
        return ("fitid:" + str(fid))[:180]
    dm = tx["data_mov"]
    ds = dm.isoformat() if hasattr(dm, "isoformat") else str(dm)[:10]
    raw = f"{conta_ref}|{ds}|{tx['valor']}|{tx.get('memo') or ''}|{tx.get('payee') or ''}"
    return "h:" + hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:48]


def _parse_date_arg(d):
    if d is None or d == "":
        return None
    if hasattr(d, "isoformat"):
        return d if isinstance(d, date) else d.date() if hasattr(d, "date") else None
    s = str(d)[:10]
    try:
        y, m, day = int(s[0:4]), int(s[5:7]), int(s[8:10])
        return date(y, m, day)
    except (ValueError, TypeError):
        return None


def _bulk_insert_banco_extrato_linhas(imp_id: int, conta_ref: str, txs: list) -> tuple[int, int]:
    from psycopg2.extras import execute_values

    rows = []
    for tx in txs:
        dm = tx["data_mov"]
        if not hasattr(dm, "year"):
            dm = _parse_date_arg(dm) or date.today()
        dk = _extrato_dedupe_key(conta_ref, {**tx, "data_mov": dm})
        rows.append(
            (
                imp_id,
                conta_ref,
                tx.get("fitid"),
                dk,
                dm,
                tx["valor"],
                tx.get("memo"),
                tx.get("payee"),
                tx["tipo"],
            )
        )
    inserted = 0
    skipped = 0
    chunk_size = 800
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        with cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO banco_extrato_linhas (
                    import_id, conta_ref, fitid, dedupe_key, data_mov, valor, memo, payee, tipo
                ) VALUES %s
                ON CONFLICT (conta_ref, dedupe_key) DO NOTHING
                """,
                chunk,
            )
            n_ins = cur.rowcount
            inserted += n_ins
            skipped += len(chunk) - n_ins
    return inserted, skipped


def _import_one_extrato_block(
    filename: str,
    conta_ref: str,
    txs: list,
    bank_id=None,
    account_id=None,
    currency: str = "BRL",
    balance_end=None,
    balance_date=None,
    periodo_inicio=None,
    periodo_fim=None,
):
    if not get_database_url():
        raise RuntimeError("DATABASE_URL não definido.")
    conta_ref = (conta_ref or "sem_conta")[:200]
    txs = txs or []
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO banco_ofx_imports (
                filename, conta_ref, bank_id, account_id, currency,
                balance_end, balance_date, periodo_inicio, periodo_fim, movimentos_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                (filename or "")[:255] or None,
                conta_ref,
                bank_id,
                account_id,
                (currency or "BRL")[:8],
                balance_end,
                balance_date,
                periodo_inicio,
                periodo_fim,
                len(txs),
            ),
        )
        imp_id = cur.fetchone()[0]
    inserted, skipped = _bulk_insert_banco_extrato_linhas(imp_id, conta_ref, txs)
    return imp_id, inserted, skipped, len(txs)


def import_ofx_bytes(data: bytes, filename: str = "extrato.ofx"):
    if not get_database_url():
        raise RuntimeError("DATABASE_URL não definido.")
    from ofx_import import parse_ofx_bytes as _parse

    blocks = _parse(data)
    if not blocks:
        raise ValueError("OFX sem contas reconhecidas.")
    total_ins = 0
    total_skip = 0
    imports_out = []
    for b in blocks:
        txs = b.get("transacoes") or []
        conta_ref = (b.get("conta_ref") or "sem_conta")[:200]
        imp_id, ins, sk, n = _import_one_extrato_block(
            filename=filename,
            conta_ref=conta_ref,
            txs=txs,
            bank_id=b.get("bank_id"),
            account_id=b.get("account_id"),
            currency=b.get("currency") or "BRL",
            balance_end=b.get("balance_end"),
            balance_date=_parse_date_arg(b.get("balance_date")),
            periodo_inicio=_parse_date_arg(b.get("periodo_inicio")),
            periodo_fim=_parse_date_arg(b.get("periodo_fim")),
        )
        total_ins += ins
        total_skip += sk
        imports_out.append({"import_id": imp_id, "conta_ref": conta_ref, "movimentos_no_arquivo": n})
    return {
        "ok": True,
        "formato": "ofx",
        "contas": len(blocks),
        "linhas_inseridas": total_ins,
        "linhas_duplicadas_ignoradas": total_skip,
        "imports": imports_out,
    }


def import_extrato_nubank_csv_bytes(data: bytes, filename: str = "extrato.csv"):
    if not get_database_url():
        raise RuntimeError("DATABASE_URL não definido.")
    from extrato_csv_import import parse_nubank_csv_bytes

    block = parse_nubank_csv_bytes(data, filename=filename or "extrato.csv")
    if not block:
        raise ValueError("CSV não reconhecido como Nubank (Data, Valor, Identificador, Descrição).")
    conta_ref = (block.get("conta_ref") or "nubank|csv")[:200]
    txs = block.get("transacoes") or []
    imp_id, ins, sk, n = _import_one_extrato_block(
        filename=filename or "extrato.csv",
        conta_ref=conta_ref,
        txs=txs,
        bank_id="nubank",
        account_id=block.get("account_id"),
        currency="BRL",
        balance_end=None,
        balance_date=None,
        periodo_inicio=None,
        periodo_fim=None,
    )
    return {
        "ok": True,
        "formato": "nubank_csv",
        "contas": 1,
        "linhas_inseridas": ins,
        "linhas_duplicadas_ignoradas": sk,
        "imports": [{"import_id": imp_id, "conta_ref": conta_ref, "movimentos_no_arquivo": n}],
    }


def list_extrato_linhas(conta_ref=None, date_from=None, date_to=None, pendente=None, limit=500):
    if not get_database_url():
        return []
    init_db()
    cond, params = ["1=1"], []
    if conta_ref:
        cond.append("e.conta_ref = %s")
        params.append(str(conta_ref)[:200])
    df = _parse_date_arg(date_from)
    dt = _parse_date_arg(date_to)
    if df:
        cond.append("e.data_mov >= %s")
        params.append(df)
    if dt:
        cond.append("e.data_mov <= %s")
        params.append(dt)
    if pendente is True:
        cond.append("e.conciliado_lancamento_id IS NULL")
    elif pendente is False:
        cond.append("e.conciliado_lancamento_id IS NOT NULL")
    params.append(min(int(limit or 500), 25000))
    w = " AND ".join(cond)
    with cursor() as cur:
        cur.execute(
            f"""
            SELECT e.id, e.conta_ref, e.data_mov, e.valor, e.tipo, e.memo, e.payee, e.fitid,
                   e.conciliado_lancamento_id, e.conciliado_em, i.filename, i.imported_at
            FROM banco_extrato_linhas e
            JOIN banco_ofx_imports i ON i.id = e.import_id
            WHERE {w}
            ORDER BY e.data_mov DESC, e.id DESC
            LIMIT %s;
            """,
            params,
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "conta_ref": r[1],
                "data_mov": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
                "valor": float(r[3]) if r[3] is not None else 0.0,
                "tipo": r[4],
                "memo": r[5],
                "payee": r[6],
                "fitid": r[7],
                "conciliado_lancamento_id": r[8],
                "conciliado_em": r[9].isoformat() if r[9] and hasattr(r[9], "isoformat") else (str(r[9]) if r[9] else None),
                "arquivo": r[10],
                "importado_em": r[11].isoformat() if r[11] and hasattr(r[11], "isoformat") else str(r[11]),
            }
        )
    return out


def list_ofx_contas():
    if not get_database_url():
        return []
    init_db()
    with cursor() as cur:
        cur.execute("SELECT DISTINCT conta_ref FROM banco_extrato_linhas ORDER BY 1;")
        return [r[0] for r in cur.fetchall()]


def _fetch_extrato_linha(linha_id: int):
    if not get_database_url():
        return None
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT id, conta_ref, data_mov, valor, tipo, memo, payee, fitid, conciliado_lancamento_id
            FROM banco_extrato_linhas WHERE id = %s;
            """,
            (int(linha_id),),
        )
        r = cur.fetchone()
    if not r:
        return None
    dm = r[2]
    return {
        "id": r[0],
        "conta_ref": r[1],
        "data_mov": dm if hasattr(dm, "year") else _parse_date_arg(dm),
        "valor": float(r[3]) if r[3] is not None else 0.0,
        "tipo": r[4],
        "memo": r[5],
        "payee": r[6],
        "fitid": r[7],
        "conciliado_lancamento_id": r[8],
    }


def sugestoes_conciliacao_extrato(linha_id: int, janela_dias: int = 7, limit: int = 10):
    ex = _fetch_extrato_linha(linha_id)
    if not ex or ex.get("conciliado_lancamento_id"):
        return []
    tipo_l = "receita" if ex["tipo"] == "credito" else "despesa"
    absv = abs(float(ex["valor"]))
    d0 = ex["data_mov"] - timedelta(days=max(1, int(janela_dias)))
    d1 = ex["data_mov"] + timedelta(days=max(1, int(janela_dias)))
    tol = 0.02
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            SELECT l.id, l.data, l.valor, l.tipo, l.descricao, c.nome
            FROM financeiro_lancamentos l
            LEFT JOIN financeiro_categorias c ON c.id = l.categoria_id
            WHERE l.tipo = %s
              AND l.data >= %s AND l.data <= %s
              AND l.valor BETWEEN %s AND %s
              AND NOT EXISTS (
                SELECT 1 FROM banco_extrato_linhas x
                WHERE x.conciliado_lancamento_id = l.id AND x.id <> %s
              )
            ORDER BY ABS((l.data - CAST(%s AS DATE))::integer), ABS((l.valor - %s::numeric))
            LIMIT %s;
            """,
            (tipo_l, d0, d1, absv - tol, absv + tol, int(linha_id), ex["data_mov"], absv, min(int(limit), 50)),
        )
        rows = cur.fetchall()
    return [
        {
            "lancamento_id": r[0],
            "data": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
            "valor": float(r[2]) if r[2] else 0,
            "tipo": r[3],
            "descricao": r[4],
            "categoria_nome": r[5],
        }
        for r in rows
    ]


def conciliar_extrato_linha(linha_id: int, lancamento_id: int) -> bool:
    ex = _fetch_extrato_linha(linha_id)
    if not ex or ex.get("conciliado_lancamento_id"):
        return False
    tipo_l = "receita" if ex["tipo"] == "credito" else "despesa"
    init_db()
    with cursor() as cur:
        cur.execute("SELECT id, tipo FROM financeiro_lancamentos WHERE id = %s;", (int(lancamento_id),))
        lr = cur.fetchone()
        if not lr or lr[1] != tipo_l:
            return False
        cur.execute(
            "SELECT id FROM banco_extrato_linhas WHERE conciliado_lancamento_id = %s AND id <> %s;",
            (int(lancamento_id), int(linha_id)),
        )
        if cur.fetchone():
            return False
        cur.execute(
            """
            UPDATE banco_extrato_linhas
            SET conciliado_lancamento_id = %s, conciliado_em = NOW()
            WHERE id = %s AND conciliado_lancamento_id IS NULL;
            """,
            (int(lancamento_id), int(linha_id)),
        )
        return cur.rowcount > 0


def desconciliar_extrato_linha(linha_id: int) -> bool:
    if not get_database_url():
        return False
    init_db()
    with cursor() as cur:
        cur.execute(
            """
            UPDATE banco_extrato_linhas
            SET conciliado_lancamento_id = NULL, conciliado_em = NULL
            WHERE id = %s;
            """,
            (int(linha_id),),
        )
        return cur.rowcount > 0


def resumo_conciliacao_extrato(conta_ref=None):
    if not get_database_url():
        return {"pendentes": 0, "conciliadas": 0, "total": 0}
    init_db()
    cond = "1=1"
    params = []
    if conta_ref:
        cond = "conta_ref = %s"
        params.append(str(conta_ref)[:200])
    with cursor() as cur:
        cur.execute(
            f"""
            SELECT
              COUNT(*) FILTER (WHERE conciliado_lancamento_id IS NULL),
              COUNT(*) FILTER (WHERE conciliado_lancamento_id IS NOT NULL),
              COUNT(*)
            FROM banco_extrato_linhas WHERE {cond};
            """,
            params,
        )
        r = cur.fetchone()
    return {"pendentes": int(r[0] or 0), "conciliadas": int(r[1] or 0), "total": int(r[2] or 0)}
