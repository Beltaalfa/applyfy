# Inventário: API Admin vs Playwright

## API já integrada (`applyfy_api.py`)

- Credenciais: `APPLYFY_PUBLIC_KEY`, `APPLYFY_SECRET_KEY`, `APPLYFY_API_BASE`.
- Uso atual inclui consultas a produtor/ofertas (ex.: mapeamento pós-webhook `PRODUCER_CREATED`), taxas por produtor onde aplicável, e mensagens de erro 403 documentadas no código.

## Automação Playwright (export)

- `export_saldos.py` / `run_daily.py`: lista de produtores e saldos como na interface autenticada (inclui 2FA quando necessário).
- `applyfy_export_vendas.py`: fluxo de vendas na UI quando não há paridade completa via API para o mesmo conjunto de campos.

## Onde a API pode substituir ou complementar o browser

| Necessidade | Tendência |
|-------------|-----------|
| Dados já expostos em endpoint estável e documentado pela Applyfy | Preferir API + cache em Postgres |
| Campos só na UI ou sem endpoint equivalente | Manter Playwright |
| Volume alto / rate limit | Paginação API + backoff; export UI como fallback |

## Próximos passos sugeridos

1. Listar na documentação oficial da Applyfy todos os endpoints disponíveis para a conta (ambiente homologação).
2. Para cada coluna do CSV/XLSX de saldos, marcar origem “API” ou “só UI”.
3. Prototipar um modo `EXPORT_SALDOS_SOURCE=api` atrás de feature flag, comparando uma amostra com o export UI antes de trocar o job em produção.
