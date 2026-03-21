-- DDL do importador de vendas ApplyFy

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

DROP INDEX IF EXISTS uq_applyfy_vendas_transaction_id;
DROP INDEX IF EXISTS uq_applyfy_vendas_codigo_venda;

DO $$
BEGIN
  ALTER TABLE applyfy_vendas
  ADD CONSTRAINT uq_applyfy_vendas_transaction_id_c UNIQUE (transaction_id);
EXCEPTION
  WHEN duplicate_object OR duplicate_table THEN NULL;
END $$;

-- Várias transações podem compartilhar o mesmo codigo_venda (mesmo pedido).
ALTER TABLE applyfy_vendas DROP CONSTRAINT IF EXISTS uq_applyfy_vendas_codigo_venda_c;

CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_codigo_venda ON applyfy_vendas(codigo_venda);
CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_data_venda ON applyfy_vendas(data_venda);
CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_adquirente ON applyfy_vendas(adquirente);

CREATE TABLE IF NOT EXISTS applyfy_vendas_fee_transactions (
    id BIGSERIAL PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    fee_type TEXT,
    amount NUMERIC(16, 2),
    description TEXT,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_fee_tx_transaction_id
ON applyfy_vendas_fee_transactions(transaction_id);

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
CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_attempts_transaction_id
ON applyfy_vendas_transaction_attempts(transaction_id);

CREATE TABLE IF NOT EXISTS applyfy_vendas_webhook_logs (
    id BIGSERIAL PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    status TEXT,
    response TEXT,
    created_at TIMESTAMPTZ,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_applyfy_vendas_webhooks_transaction_id
ON applyfy_vendas_webhook_logs(transaction_id);

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
CREATE INDEX IF NOT EXISTS idx_applyfy_import_log_run_at ON applyfy_import_log(run_at);
