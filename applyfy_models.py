# -*- coding: utf-8 -*-
"""Modelos de dados do exportador de vendas ApplyFy."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FeeTransaction:
    transaction_id: str
    fee_type: str | None
    amount: float
    description: str | None = None
    raw_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionAttempt:
    transaction_id: str
    acquirer: str | None = None
    status: str | None = None
    substatus: str | None = None
    response_time_ms: int | None = None
    message: str | None = None
    created_at: datetime | None = None
    raw_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookLog:
    transaction_id: str
    status: str | None = None
    response: str | None = None
    created_at: datetime | None = None
    raw_json: dict[str, Any] = field(default_factory=dict)


@dataclass
class VendaConsolidada:
    codigo_venda: str | None = None
    order_id: str | None = None
    transaction_id: str | None = None
    valor_total: float | None = None
    valor_cobrado: float | None = None
    taxa_processamento: float | None = None
    taxa_adquirente: float | None = None
    retencao: float | None = None
    comissao_produtor: float | None = None
    valor_liquido_produtor: float | None = None
    data_venda: datetime | None = None
    data_liberacao: datetime | None = None
    data_pagamento: datetime | None = None
    data_atualizacao: datetime | None = None
    metodo_pagamento: str | None = None
    status_pagamento: str | None = None
    adquirente: str | None = None
    adquirente_bruto: str | None = None
    id_adquirente: str | None = None
    substatus: str | None = None
    parcelas: int | None = None
    produtor_nome: str | None = None
    produtor_email: str | None = None
    comprador_nome: str | None = None
    comprador_email: str | None = None
    comprador_telefone: str | None = None
    comprador_cpf: str | None = None
    comprador_cnpj: str | None = None
    afiliado_nome: str | None = None
    afiliado_email: str | None = None
    affiliate_code: str | None = None
    produto_nome: str | None = None
    produto_id: str | None = None
    offer_code: str | None = None
    quantidade: int | None = None
    valor_unitario: float | None = None
    pais: str | None = None
    cep: str | None = None
    estado: str | None = None
    cidade: str | None = None
    bairro: str | None = None
    rua: str | None = None
    numero: str | None = None
    complemento: str | None = None
    response_time_ms: int | None = None
    tentativa_status: str | None = None
    tentativa_substatus: str | None = None
    tentativa_mensagem: str | None = None
    webhook_logs_json: dict[str, Any] | list[Any] | None = None
    tracking_props_json: dict[str, Any] | list[Any] | None = None
    fee_transactions_json: list[dict[str, Any]] = field(default_factory=list)
    affiliate_commissions_json: list[dict[str, Any]] = field(default_factory=list)
    raw_json: dict[str, Any] = field(default_factory=dict)
    source_strategy: str = "payload"


@dataclass
class ImportStats:
    paginas: int = 0
    processadas: int = 0
    inseridas: int = 0
    atualizadas: int = 0
    erros: int = 0
