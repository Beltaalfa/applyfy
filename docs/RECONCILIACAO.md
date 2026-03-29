# Reconciliação de dados Applyfy

## Objetivo

Garantir consistência entre três fontes possíveis:

1. **Export Playwright** — tabela `saldos_historico` / último `export_runs` (saldos e vendas líquidas por produtor).
2. **API Admin Applyfy** — endpoints usados em `applyfy_api.py` (ex.: produtor, taxas, ofertas).
3. **Webhooks** — tabela `applyfy_transactions` (eventos de transação e `PRODUCER_CREATED`).

## O que significa “bater”

Definição depende do caso de uso:

- **Saldos**: comparar totais agregados do último export com soma esperada a partir de webhooks `TRANSACTION_PAID` (quando o modelo de negócio permitir agregação confiável).
- **Produtores**: emails no último export vs. mapa `applyfy_offer_producer` + eventos `PRODUCER_CREATED`.
- **Vendas detalhadas**: linhas em `applyfy_vendas` (export vendas) vs. API de transação por `transaction_id`.

Nenhuma dessas igualdades é automática: webhooks podem chegar atrasados, moedas e estornos alteram totais, e o export Playwright reflete um instante da UI.

## Job sugerido (evolução)

1. Rodar após o export diário ou em horário fixo.
2. Consultar último `run_at` em `export_runs` e amostra de produtores com maior divergência vs. API (se rate limit permitir).
3. Persistir achados em tabela dedicada (ex.: `reconciliation_findings`) ou apenas log estruturado na primeira versão.
4. Opcional: notificação WAHA se `WAHA_ALERT_ON_FAILURE` ou flag específica estiver ativa e houver divergência acima de limiar configurável.

## Script de referência

`scripts/reconcile_probe.py` (se presente) imprime contagens básicas para inspeção manual; não altera dados.
