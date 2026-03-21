# -*- coding: utf-8 -*-
"""Persistência de vendas ApplyFy em PostgreSQL."""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable

import db
from applyfy_models import FeeTransaction, TransactionAttempt, VendaConsolidada, WebhookLog


DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS applyfy_vendas (
        id BIGSERIAL PRIMARY KEY,
        codigo_venda TEXT,
        order_id TEXT,
        transaction_id TEXT,
        valor_total NUMERIC(16, 2),
        valor_cobrado NUMERIC(16, 2),
        taxa_processamento NUMERIC(16, 2),
        taxa_adquirente NUMERIC(16, 2),
        retencao NUMERIC(16, 2),
        comissao_produtor NUMERIC(16, 2),
        valor_liquido_produtor NUMERIC(16, 2),
        data_venda TIMESTAMPTZ,
        data_liberacao TIMESTAMPTZ,
        data_pagamento TIMESTAMPTZ,
        data_atualizacao TIMESTAMPTZ,
        metodo_pagamento TEXT,
        status_pagamento TEXT,
        adquirente TEXT,
        adquirente_bruto TEXT,
        id_adquirente TEXT,
        substatus TEXT,
        parcelas INT,
        produtor_nome TEXT,
        produtor_email TEXT,
        comprador_nome TEXT,
        comprador_email TEXT,
        comprador_telefone TEXT,
        comprador_cpf TEXT,
        comprador_cnpj TEXT,
        afiliado_nome TEXT,
        afiliado_email TEXT,
        affiliate_code TEXT,
        produto_nome TEXT,
        produto_id TEXT,
        offer_code TEXT,
        quantidade INT,
        valor_unitario NUMERIC(16, 2),
        pais TEXT,
        cep TEXT,
        estado TEXT,
        cidade TEXT,
        bairro TEXT,
        rua TEXT,
        numero TEXT,
        complemento TEXT,
        response_time_ms INT,
        tentativa_status TEXT,
        tentativa_substatus TEXT,
        tentativa_mensagem TEXT,
        webhook_logs_json JSONB,
        tracking_props_json JSONB,
        fee_transactions_json JSONB,
        affiliate_commissions_json JSONB,
        raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        source_strategy TEXT NOT NULL,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "DROP INDEX IF EXISTS uq_applyfy_vendas_transaction_id;",
    "DROP INDEX IF EXISTS uq_applyfy_vendas_codigo_venda;",
    """
    DO $$
    BEGIN
        ALTER TABLE applyfy_vendas
        ADD CONSTRAINT uq_applyfy_vendas_transaction_id_c UNIQUE (transaction_id);
    EXCEPTION
        WHEN duplicate_object OR duplicate_table THEN NULL;
    END $$;
    """,
    "ALTER TABLE applyfy_vendas DROP CONSTRAINT IF EXISTS uq_applyfy_vendas_codigo_venda_c;",
    "CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_codigo_venda ON applyfy_vendas(codigo_venda);",
    "CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_data_venda ON applyfy_vendas(data_venda);",
    "CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_adquirente ON applyfy_vendas(adquirente);",
    """
    CREATE TABLE IF NOT EXISTS applyfy_vendas_fee_transactions (
        id BIGSERIAL PRIMARY KEY,
        transaction_id TEXT NOT NULL,
        fee_type TEXT,
        amount NUMERIC(16, 2),
        description TEXT,
        raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_fee_tx_transaction_id ON applyfy_vendas_fee_transactions(transaction_id);",
    """
    CREATE TABLE IF NOT EXISTS applyfy_vendas_transaction_attempts (
        id BIGSERIAL PRIMARY KEY,
        transaction_id TEXT NOT NULL,
        acquirer TEXT,
        status TEXT,
        substatus TEXT,
        response_time_ms INT,
        message TEXT,
        created_at TIMESTAMPTZ,
        raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_attempts_transaction_id ON applyfy_vendas_transaction_attempts(transaction_id);",
    """
    CREATE TABLE IF NOT EXISTS applyfy_vendas_webhook_logs (
        id BIGSERIAL PRIMARY KEY,
        transaction_id TEXT NOT NULL,
        status TEXT,
        response TEXT,
        created_at TIMESTAMPTZ,
        raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_webhooks_transaction_id ON applyfy_vendas_webhook_logs(transaction_id);",
    """
    CREATE TABLE IF NOT EXISTS applyfy_import_log (
        id BIGSERIAL PRIMARY KEY,
        run_at TIMESTAMPTZ NOT NULL,
        pagina INT NOT NULL,
        linha INT NOT NULL,
        codigo_venda TEXT,
        transaction_id TEXT,
        source_strategy TEXT,
        status TEXT NOT NULL,
        duracao_segundos NUMERIC(10, 3),
        mensagem TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_applyfy_import_log_run_at ON applyfy_import_log(run_at);",
]


@contextmanager
def _conn_cursor():
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        try:
            yield conn, cur
        finally:
            cur.close()
    finally:
        conn.close()


def init_applyfy_vendas_db() -> None:
    if not db.DATABASE_URL:
        return
    with _conn_cursor() as (conn, cur):
        for stmt in DDL_STATEMENTS:
            cur.execute(stmt)
        conn.commit()


def get_next_row_index_for_export_resume(pagina: int) -> int:
    """
    Próximo índice 0-based da linha na tabela /admin/orders para retomar o export.

    Usa applyfy_import_log: em cada linha da lista o log grava ``linha`` = i+1 (1-based).
    O último OK com MAX(linha) na página indica até qual linha já foi processada; o próximo
    índice na lista é exatamente esse valor (índice 0-based = próximo após última concluída).
    """
    if not db.DATABASE_URL:
        return 0
    init_applyfy_vendas_db()
    with _conn_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT COALESCE(MAX(linha), 0) FROM applyfy_import_log
            WHERE pagina = %s AND status = 'OK';
            """,
            (pagina,),
        )
        row = cur.fetchone()
        n = int(row[0] or 0) if row else 0
    return n


def _jsonb(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _venda_pk(venda: VendaConsolidada) -> str:
    return venda.transaction_id or venda.codigo_venda or venda.order_id or ""


def upsert_venda(
    venda: VendaConsolidada,
    fees: Iterable[FeeTransaction],
    attempts: Iterable[TransactionAttempt],
    webhooks: Iterable[WebhookLog],
) -> str:
    if not db.DATABASE_URL:
        return "skipped"
    if not _venda_pk(venda):
        raise ValueError("Venda sem chave identificadora (transaction_id/codigo_venda/order_id).")
    init_applyfy_vendas_db()
    with _conn_cursor() as (conn, cur):
        cur.execute(
            """
            INSERT INTO applyfy_vendas (
                codigo_venda, order_id, transaction_id, valor_total, valor_cobrado, taxa_processamento, taxa_adquirente,
                retencao, comissao_produtor, valor_liquido_produtor, data_venda, data_liberacao, data_pagamento, data_atualizacao,
                metodo_pagamento, status_pagamento, adquirente, adquirente_bruto, id_adquirente, substatus, parcelas,
                produtor_nome, produtor_email, comprador_nome, comprador_email, comprador_telefone, comprador_cpf, comprador_cnpj,
                afiliado_nome, afiliado_email, affiliate_code, produto_nome, produto_id, offer_code, quantidade, valor_unitario,
                pais, cep, estado, cidade, bairro, rua, numero, complemento, response_time_ms, tentativa_status, tentativa_substatus,
                tentativa_mensagem, webhook_logs_json, tracking_props_json, fee_transactions_json, affiliate_commissions_json,
                raw_json, source_strategy, imported_at, last_seen_at
            ) VALUES (
                %(codigo_venda)s, %(order_id)s, %(transaction_id)s, %(valor_total)s, %(valor_cobrado)s, %(taxa_processamento)s, %(taxa_adquirente)s,
                %(retencao)s, %(comissao_produtor)s, %(valor_liquido_produtor)s, %(data_venda)s, %(data_liberacao)s, %(data_pagamento)s, %(data_atualizacao)s,
                %(metodo_pagamento)s, %(status_pagamento)s, %(adquirente)s, %(adquirente_bruto)s, %(id_adquirente)s, %(substatus)s, %(parcelas)s,
                %(produtor_nome)s, %(produtor_email)s, %(comprador_nome)s, %(comprador_email)s, %(comprador_telefone)s, %(comprador_cpf)s, %(comprador_cnpj)s,
                %(afiliado_nome)s, %(afiliado_email)s, %(affiliate_code)s, %(produto_nome)s, %(produto_id)s, %(offer_code)s, %(quantidade)s, %(valor_unitario)s,
                %(pais)s, %(cep)s, %(estado)s, %(cidade)s, %(bairro)s, %(rua)s, %(numero)s, %(complemento)s, %(response_time_ms)s, %(tentativa_status)s, %(tentativa_substatus)s,
                %(tentativa_mensagem)s, %(webhook_logs_json)s::jsonb, %(tracking_props_json)s::jsonb, %(fee_transactions_json)s::jsonb, %(affiliate_commissions_json)s::jsonb,
                %(raw_json)s::jsonb, %(source_strategy)s, NOW(), NOW()
            )
            ON CONFLICT ON CONSTRAINT uq_applyfy_vendas_transaction_id_c DO UPDATE SET
                codigo_venda = EXCLUDED.codigo_venda,
                order_id = EXCLUDED.order_id,
                valor_total = EXCLUDED.valor_total,
                valor_cobrado = EXCLUDED.valor_cobrado,
                taxa_processamento = EXCLUDED.taxa_processamento,
                taxa_adquirente = EXCLUDED.taxa_adquirente,
                retencao = EXCLUDED.retencao,
                comissao_produtor = EXCLUDED.comissao_produtor,
                valor_liquido_produtor = EXCLUDED.valor_liquido_produtor,
                data_venda = EXCLUDED.data_venda,
                data_liberacao = EXCLUDED.data_liberacao,
                data_pagamento = EXCLUDED.data_pagamento,
                data_atualizacao = EXCLUDED.data_atualizacao,
                metodo_pagamento = EXCLUDED.metodo_pagamento,
                status_pagamento = EXCLUDED.status_pagamento,
                adquirente = EXCLUDED.adquirente,
                adquirente_bruto = EXCLUDED.adquirente_bruto,
                id_adquirente = EXCLUDED.id_adquirente,
                substatus = EXCLUDED.substatus,
                parcelas = EXCLUDED.parcelas,
                produtor_nome = EXCLUDED.produtor_nome,
                produtor_email = EXCLUDED.produtor_email,
                comprador_nome = EXCLUDED.comprador_nome,
                comprador_email = EXCLUDED.comprador_email,
                comprador_telefone = EXCLUDED.comprador_telefone,
                comprador_cpf = EXCLUDED.comprador_cpf,
                comprador_cnpj = EXCLUDED.comprador_cnpj,
                afiliado_nome = EXCLUDED.afiliado_nome,
                afiliado_email = EXCLUDED.afiliado_email,
                affiliate_code = EXCLUDED.affiliate_code,
                produto_nome = EXCLUDED.produto_nome,
                produto_id = EXCLUDED.produto_id,
                offer_code = EXCLUDED.offer_code,
                quantidade = EXCLUDED.quantidade,
                valor_unitario = EXCLUDED.valor_unitario,
                pais = EXCLUDED.pais,
                cep = EXCLUDED.cep,
                estado = EXCLUDED.estado,
                cidade = EXCLUDED.cidade,
                bairro = EXCLUDED.bairro,
                rua = EXCLUDED.rua,
                numero = EXCLUDED.numero,
                complemento = EXCLUDED.complemento,
                response_time_ms = EXCLUDED.response_time_ms,
                tentativa_status = EXCLUDED.tentativa_status,
                tentativa_substatus = EXCLUDED.tentativa_substatus,
                tentativa_mensagem = EXCLUDED.tentativa_mensagem,
                webhook_logs_json = EXCLUDED.webhook_logs_json,
                tracking_props_json = EXCLUDED.tracking_props_json,
                fee_transactions_json = EXCLUDED.fee_transactions_json,
                affiliate_commissions_json = EXCLUDED.affiliate_commissions_json,
                raw_json = EXCLUDED.raw_json,
                source_strategy = EXCLUDED.source_strategy,
                last_seen_at = NOW()
            RETURNING (xmax = 0) AS inserted;
            """,
            {
                **venda.__dict__,
                "webhook_logs_json": _jsonb(venda.webhook_logs_json),
                "tracking_props_json": _jsonb(venda.tracking_props_json),
                "fee_transactions_json": _jsonb(venda.fee_transactions_json),
                "affiliate_commissions_json": _jsonb(venda.affiliate_commissions_json),
                "raw_json": _jsonb(venda.raw_json),
            },
        )
        inserted = bool(cur.fetchone()[0])

        tx_id = venda.transaction_id or venda.codigo_venda or venda.order_id
        cur.execute("DELETE FROM applyfy_vendas_fee_transactions WHERE transaction_id = %s;", (tx_id,))
        cur.execute("DELETE FROM applyfy_vendas_transaction_attempts WHERE transaction_id = %s;", (tx_id,))
        cur.execute("DELETE FROM applyfy_vendas_webhook_logs WHERE transaction_id = %s;", (tx_id,))

        for fee in fees:
            cur.execute(
                """
                INSERT INTO applyfy_vendas_fee_transactions (transaction_id, fee_type, amount, description, raw_json)
                VALUES (%s, %s, %s, %s, %s::jsonb);
                """,
                (fee.transaction_id, fee.fee_type, fee.amount, fee.description, _jsonb(fee.raw_json)),
            )
        for attempt in attempts:
            cur.execute(
                """
                INSERT INTO applyfy_vendas_transaction_attempts (
                    transaction_id, acquirer, status, substatus, response_time_ms, message, created_at, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb);
                """,
                (
                    attempt.transaction_id,
                    attempt.acquirer,
                    attempt.status,
                    attempt.substatus,
                    attempt.response_time_ms,
                    attempt.message,
                    attempt.created_at,
                    _jsonb(attempt.raw_json),
                ),
            )
        for webhook in webhooks:
            cur.execute(
                """
                INSERT INTO applyfy_vendas_webhook_logs (transaction_id, status, response, created_at, raw_json)
                VALUES (%s, %s, %s, %s, %s::jsonb);
                """,
                (webhook.transaction_id, webhook.status, webhook.response, webhook.created_at, _jsonb(webhook.raw_json)),
            )

        conn.commit()
    return "inserted" if inserted else "updated"


def list_applyfy_vendas_import_log(
    limit: int = 200,
    offset: int = 0,
    status: str | None = None,
) -> dict[str, Any]:
    """Histórico estruturado de cada linha processada no export de vendas (Postgres)."""
    if not db.DATABASE_URL:
        return {"rows": [], "total": 0}
    init_applyfy_vendas_db()
    lim = min(max(int(limit), 1), 1000)
    off = max(int(offset), 0)
    conditions: list[str] = []
    params: list[Any] = []
    if status and status.strip():
        conditions.append("status ILIKE %s")
        params.append(status.strip())
    where = " AND ".join(conditions) if conditions else "1=1"
    cols = [
        "id",
        "run_at",
        "pagina",
        "linha",
        "codigo_venda",
        "transaction_id",
        "source_strategy",
        "status",
        "duracao_segundos",
        "mensagem",
        "created_at",
    ]
    with _conn_cursor() as (conn, cur):
        cur.execute(f"SELECT COUNT(*) FROM applyfy_import_log WHERE {where};", params)
        total = int(cur.fetchone()[0] or 0)
        cur.execute(
            f"""
            SELECT id, run_at, pagina, linha, codigo_venda, transaction_id, source_strategy,
                   status, duracao_segundos, mensagem, created_at
            FROM applyfy_import_log
            WHERE {where}
            ORDER BY id DESC
            LIMIT %s OFFSET %s;
            """,
            [*params, lim, off],
        )
        raw = cur.fetchall()
    out: list[dict[str, Any]] = []
    for r in raw:
        item: dict[str, Any] = {}
        for i, c in enumerate(cols):
            v = r[i]
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            elif isinstance(v, float):
                v = v
            elif v is None:
                v = None
            else:
                v = str(v) if v is not None else None
            item[c] = v
        out.append(item)
    return {"rows": out, "total": total}


def log_import_event(
    *,
    run_at: datetime,
    pagina: int,
    linha: int,
    codigo_venda: str | None,
    transaction_id: str | None,
    source_strategy: str | None,
    status: str,
    duracao_segundos: float | None,
    mensagem: str | None,
) -> None:
    if not db.DATABASE_URL:
        return
    with _conn_cursor() as (conn, cur):
        cur.execute(
            """
            INSERT INTO applyfy_import_log (
                run_at, pagina, linha, codigo_venda, transaction_id, source_strategy,
                status, duracao_segundos, mensagem
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                run_at,
                pagina,
                linha,
                codigo_venda,
                transaction_id,
                source_strategy,
                status,
                duracao_segundos,
                mensagem,
            ),
        )
        conn.commit()
