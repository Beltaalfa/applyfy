# -*- coding: utf-8 -*-
"""Parser de detalhe de vendas ApplyFy: payload Next.js primeiro, DOM como fallback."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from playwright.sync_api import Page

from applyfy_models import FeeTransaction, TransactionAttempt, VendaConsolidada, WebhookLog


RE_NEXT_PUSH = re.compile(r"self\.__next_f\.push\(\[1,\"(.*?)\"\]\);?", re.DOTALL)
RE_MONEY = re.compile(r"R\$\s*([\d\.\,]+)")
RE_DATE_BR = re.compile(r"(\d{2}/\d{2}/\d{4})\s*[- ]\s*(\d{2}:\d{2})")


def parse_order_detail(
    page: Page,
) -> tuple[list[tuple[VendaConsolidada, list[FeeTransaction], list[TransactionAttempt], list[WebhookLog]]], str]:
    """Tenta payload Next.js; se falhar, usa fallback por DOM (uma linha)."""
    html = page.content()
    bundles = parse_payload_order(html)
    if bundles:
        return bundles, "payload"
    dom_v = parse_dom_order(page)
    return [(dom_v, [], [], [])], "dom"


def parse_payload_order(
    html: str,
) -> list[tuple[VendaConsolidada, list[FeeTransaction], list[TransactionAttempt], list[WebhookLog]]]:
    """
    Extrai o pedido do HTML e devolve **uma linha por transação** em order.transactions.
    Se não houver transações, devolve uma única linha agregando dados do pedido.
    """
    payload_order = _extract_order_from_next_payload(html)
    if not isinstance(payload_order, dict):
        return []

    txs = payload_order.get("transactions")
    if txs is None:
        txs = []
    if not txs:
        txs = [{}]

    n_tx = len(txs)
    out: list[tuple[VendaConsolidada, list[FeeTransaction], list[TransactionAttempt], list[WebhookLog]]] = []
    for idx, tx in enumerate(txs):
        if not isinstance(tx, dict):
            tx = {}
        bundle = _build_sale_bundle_from_transaction(payload_order, tx, tx_index=idx, n_transactions=n_tx)
        if bundle:
            out.append(bundle)
    return out


def _build_sale_bundle_from_transaction(
    payload_order: dict[str, Any],
    tx0: dict[str, Any],
    *,
    tx_index: int = 0,
    n_transactions: int = 1,
) -> tuple[VendaConsolidada, list[FeeTransaction], list[TransactionAttempt], list[WebhookLog]] | None:
    fee_rows = tx0.get("feeTransactions") or []
    attempt_rows = tx0.get("transactionAttempts") or []
    webhook_rows = tx0.get("webhookLogs") or tx0.get("webhooks") or []
    item0 = (payload_order.get("items") or [{}])[0] or {}
    product = item0.get("product") or {}
    client = payload_order.get("client") or {}
    producer = payload_order.get("producer") or {}
    address = payload_order.get("address") or {}
    affiliate_rows = tx0.get("affiliateCommissions") or []

    taxa_processamento = _sum_fee_type(fee_rows, "OPERATION")
    taxa_adquirente = _sum_fee_type(fee_rows, "ACQUIRER")
    retencao = _sum_fee_type(fee_rows, "FUND_LOCK")
    valor_total = _as_float(payload_order.get("totalAmount"))
    valor_cobrado = _as_float(tx0.get("chargeAmount") or payload_order.get("chargeAmount"))
    comissao_produtor = _as_float(tx0.get("producerCommission"))
    if comissao_produtor is None and valor_total is not None:
        comissao_produtor = (valor_total or 0.0) - (taxa_processamento or 0.0) - (taxa_adquirente or 0.0) - (retencao or 0.0)
    valor_liquido = _as_float(tx0.get("netAmount"))
    if valor_liquido is None:
        valor_liquido = comissao_produtor

    acquirer_raw = tx0.get("acquirer")
    tentativa0 = attempt_rows[0] if attempt_rows else {}

    codigo = str(payload_order.get("code") or payload_order.get("id") or "").strip() or None
    order_id_str = str(payload_order.get("id") or "").strip() or None
    tx_id_str = str(tx0.get("id") or "").strip() or None
    if not tx_id_str:
        base = order_id_str or codigo
        if n_transactions <= 1:
            tx_id_str = base
        else:
            tx_id_str = f"{base or 'order'}:tx{tx_index + 1}" if base else f"synthetic:tx{tx_index + 1}"
    if not tx_id_str:
        tx_id_str = f"synthetic:tx{tx_index + 1}"

    raw_json = {"order": payload_order, "transaction": tx0}

    venda = VendaConsolidada(
        codigo_venda=codigo,
        order_id=order_id_str,
        transaction_id=str(tx_id_str),
        valor_total=valor_total,
        valor_cobrado=valor_cobrado,
        taxa_processamento=taxa_processamento,
        taxa_adquirente=taxa_adquirente,
        retencao=retencao,
        comissao_produtor=comissao_produtor,
        valor_liquido_produtor=valor_liquido,
        data_venda=_parse_datetime(payload_order.get("createdAt")),
        data_liberacao=_parse_datetime(tx0.get("availableAt")),
        data_pagamento=_parse_datetime(tx0.get("payedAt")),
        data_atualizacao=_parse_datetime(tx0.get("updatedAt") or payload_order.get("updatedAt")),
        metodo_pagamento=(tx0.get("paymentMethod") or payload_order.get("paymentMethod") or "").upper() or None,
        status_pagamento=tx0.get("status") or payload_order.get("status"),
        adquirente=_normalize_acquirer(acquirer_raw),
        adquirente_bruto=acquirer_raw,
        id_adquirente=tx0.get("acquirerExternalId"),
        substatus=tx0.get("subStatus"),
        parcelas=_as_int(tx0.get("installments")),
        produtor_nome=producer.get("name"),
        produtor_email=producer.get("email"),
        comprador_nome=client.get("name"),
        comprador_email=client.get("email"),
        comprador_telefone=client.get("phone"),
        comprador_cpf=client.get("cpf"),
        comprador_cnpj=client.get("cnpj"),
        afiliado_nome=(affiliate_rows[0] or {}).get("name") if affiliate_rows else None,
        afiliado_email=(affiliate_rows[0] or {}).get("email") if affiliate_rows else None,
        affiliate_code=tx0.get("affiliateCode"),
        produto_nome=product.get("name"),
        produto_id=str(product.get("id") or "") or None,
        offer_code=item0.get("offerCode") or payload_order.get("offerCode"),
        quantidade=_as_int(item0.get("quantity")),
        valor_unitario=_as_float(item0.get("price")),
        pais=address.get("country"),
        cep=address.get("zipCode"),
        estado=address.get("state"),
        cidade=address.get("city"),
        bairro=address.get("neighborhood"),
        rua=address.get("street"),
        numero=str(address.get("number") or "") or None,
        complemento=address.get("complement"),
        response_time_ms=_as_int(tentativa0.get("responseTimeMs")),
        tentativa_status=tentativa0.get("status"),
        tentativa_substatus=tentativa0.get("subStatus"),
        tentativa_mensagem=tentativa0.get("message"),
        webhook_logs_json=webhook_rows,
        tracking_props_json=payload_order.get("trackingProps") or tx0.get("trackingProps"),
        fee_transactions_json=fee_rows,
        affiliate_commissions_json=affiliate_rows,
        raw_json=raw_json,
        source_strategy="payload",
    )

    tid = venda.transaction_id or venda.codigo_venda or venda.order_id or ""

    fees = [
        FeeTransaction(
            transaction_id=tid,
            fee_type=row.get("type"),
            amount=_as_float(row.get("amount")) or 0.0,
            description=row.get("description"),
            raw_json=row,
        )
        for row in fee_rows
    ]
    attempts = [
        TransactionAttempt(
            transaction_id=tid,
            acquirer=row.get("acquirer"),
            status=row.get("status"),
            substatus=row.get("subStatus"),
            response_time_ms=_as_int(row.get("responseTimeMs")),
            message=row.get("message"),
            created_at=_parse_datetime(row.get("createdAt")),
            raw_json=row,
        )
        for row in attempt_rows
    ]
    webhooks = [
        WebhookLog(
            transaction_id=tid,
            status=row.get("status"),
            response=row.get("response"),
            created_at=_parse_datetime(row.get("createdAt")),
            raw_json=row,
        )
        for row in webhook_rows
    ]
    return venda, fees, attempts, webhooks


def parse_dom_order(page: Page) -> VendaConsolidada:
    """Fallback de DOM/texto visível para quando payload não for parseável."""
    body = page.inner_text("body")
    order_id = _extract_order_id_from_url(page.url)
    valores = [float(v.replace(".", "").replace(",", ".")) for v in RE_MONEY.findall(body)[:8]]
    data_venda, data_liberacao = _extract_dates_from_text(body)
    status_pagamento = _extract_after_label(body, "Status")
    metodo_pagamento = _extract_after_label(body, "Método de pagamento")
    adquirente = _extract_after_label(body, "Adquirente")
    id_adquirente = _extract_after_label(body, "ID da adquirente")

    return VendaConsolidada(
        codigo_venda=order_id,
        order_id=order_id,
        transaction_id=order_id,
        valor_total=valores[0] if len(valores) > 0 else None,
        valor_cobrado=valores[1] if len(valores) > 1 else None,
        taxa_processamento=valores[2] if len(valores) > 2 else None,
        taxa_adquirente=valores[3] if len(valores) > 3 else None,
        retencao=valores[4] if len(valores) > 4 else None,
        comissao_produtor=valores[5] if len(valores) > 5 else None,
        valor_liquido_produtor=valores[6] if len(valores) > 6 else None,
        data_venda=data_venda,
        data_liberacao=data_liberacao,
        metodo_pagamento=metodo_pagamento,
        status_pagamento=status_pagamento,
        adquirente=_normalize_acquirer(adquirente),
        adquirente_bruto=adquirente,
        id_adquirente=id_adquirente,
        raw_json={"dom_excerpt": body[:2500]},
        source_strategy="dom",
    )


def _extract_order_from_next_payload(html: str) -> dict[str, Any] | None:
    chunks = RE_NEXT_PUSH.findall(html)
    if not chunks:
        return None

    decoded_parts: list[str] = []
    for raw in chunks:
        txt = raw.encode("utf-8", "ignore").decode("unicode_escape", "ignore")
        txt = txt.replace('\\"', '"')
        decoded_parts.append(txt)
    merged = "\n".join(decoded_parts)
    idx = merged.find('"order":{')
    if idx < 0:
        idx = merged.find('"order":{"id"')
    if idx < 0:
        return None
    start = merged.find("{", idx)
    order_obj_str = _extract_json_object(merged, start)
    if not order_obj_str:
        return None
    try:
        return json.loads(order_obj_str)
    except Exception:
        return None


def _extract_json_object(text: str, start_idx: int) -> str | None:
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != "{":
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start_idx, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]
    return None


def _sum_fee_type(rows: list[dict[str, Any]], fee_type: str) -> float:
    total = 0.0
    for row in rows:
        if str(row.get("type") or "").upper() == fee_type:
            total += _as_float(row.get("amount")) or 0.0
    return total


def _normalize_acquirer(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().lower()
    mapa = {
        "pagar_me": "Pagar.me",
        "mercado_pago": "Mercado Pago",
        "mercadopago": "Mercado Pago",
        "infinitepay": "InfinitePay",
        "stripe": "Stripe",
    }
    return mapa.get(raw, value)


def _extract_order_id_from_url(url: str) -> str | None:
    m = re.search(r"/admin/orders/([a-zA-Z0-9_-]+)", url)
    return m.group(1) if m else None


def _extract_dates_from_text(text: str) -> tuple[datetime | None, datetime | None]:
    values = RE_DATE_BR.findall(text)
    parsed = []
    for date_part, time_part in values[:2]:
        try:
            parsed.append(datetime.strptime(f"{date_part} {time_part}", "%d/%m/%Y %H:%M"))
        except Exception:
            parsed.append(None)
    while len(parsed) < 2:
        parsed.append(None)
    return parsed[0], parsed[1]


def _extract_after_label(text: str, label: str) -> str | None:
    pattern = rf"{re.escape(label)}\s*[:\-]?\s*([^\n\r]+)"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except Exception:
        pass
    try:
        return datetime.strptime(text, "%d/%m/%Y %H:%M")
    except Exception:
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        text = str(value).replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            return float(text)
        except Exception:
            return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None
