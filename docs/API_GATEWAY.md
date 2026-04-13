# API Admin Applyfy (proxy no painel)

O painel Flask expõe rotas **autenticadas** (Hub + JWT granular por ecrã) que fazem proxy para `https://app.applyfy.com.br/api/v1/gateway/admin`. O browser **nunca** recebe `x-public-key` / `x-secret-key`; só o servidor as envia.

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `APPLYFY_PUBLIC_KEY` | Chave pública da API Admin (painel Applyfy: Integrações). |
| `APPLYFY_SECRET_KEY` | Chave secreta (mesmo sítio). **Não commite** valores reais. |
| `APPLYFY_API_BASE` | Opcional. Default: `https://app.applyfy.com.br/api/v1/gateway/admin`. |
| `APPLYFY_API_TIMEOUT` | Timeout em segundos para pedidos “normais” (ex.: detalhe produtor). Default: `10`. |
| `APPLYFY_API_TIMEOUT_LIST` | Timeout para listagens (`transactions`, `producers`). Default: `30`. |
| `APPLYFY_API_USER_AGENT` | Opcional. Se vazio, usa um User-Agent de browser (evita bloqueios tipo Cloudflare 1010). |

Após alterar chaves ou timeouts: reinicie o processo da app (ex.: Gunicorn).

## Rotas internas (proxy)

Todas são `GET` e reutilizam a query string **filtrada** no servidor (só parâmetros permitidos).

| Rota | Destino API | Notas |
|------|-------------|--------|
| `/api/gateway/transactions` | `GET …/transactions` | `page`, `pageSize` (5–50), filtros documentados em `applyfy_api._TRANSACTION_QUERY_KEYS`. |
| `/api/gateway/producers` | `GET https://app.applyfy.com.br/api/v1/gateway/admin/producers` | Headers no servidor: `x-public-key`, `x-secret-key`. Query (ver `applyfy_api._PRODUCERS_QUERY_KEYS`): `page` (default 1), `pageSize` (default 20, **5–50**), `nameOrEmail`, `phone`, `status` (vários separados por vírgula), `kycStatus`, `bankDataStatus`, `minDocumentsSent`, `accountType`, `tags` (IDs separados por vírgula). Resposta 200: `success`, `data.pagination` (`page`, `pageSize`, `totalPages`, `count`, `take`, `skip`), `data.items[]` (produtor com `balances`, `totals`, `taxes`, `bankAccounts`, `tags`, etc.). |
| `/api/gateway/producer` | `GET …/producer?email=…` | **Obrigatório:** `email`. Opcionais: `includeKyc`, `includePayoutAccount`, `includeTaxes`, `includeDocuments` (`true`/`1`). |

Detalhe por ID (já existente): `/api/produtor/<id>/detalhes` com os mesmos `include*`.

## Permissões Hub (JWT granular)

Prefixos mapeados para ecrãs (ver `applyfy_screens.py` e `north/hub/src/lib/applyfy-screens.ts`):

- `/api/gateway/transactions` → ecrã **Transações** (`/transacoes`)
- `/api/gateway/producers` e `/api/gateway/producer` → ecrã **Produtores** (`/produtores`)

Alterou `applyfy-screens.ts`? Faça **rebuild** do Hub para os JWT refletirem os novos prefixos.

## Rotação de chaves

1. Gere novas chaves no painel Applyfy.
2. Atualize `APPLYFY_PUBLIC_KEY` e `APPLYFY_SECRET_KEY` no `.env` do servidor (ficheiro fora do git; permissões restritas).
3. Reinicie a app.
4. Trate chaves antigas como **comprometidas** se tiverem sido expostas (chat, logs públicos, etc.).

## UI

- **Transações:** secção “API cloud” em `static/transacoes.html`.
- **Produtores:** lista API em `static/produtores.html` (além da lista webhook).
- **Saldo:** `static/saldo.html` — tabela só com `balances` + `totals` e filtro `nameOrEmail`; mesmo proxy `/api/gateway/producers`. Ecrã JWT `/saldo` (ou `/produtores`) para a API.
- **Taxas:** `static/taxas.html` — colunas a partir de `items[].taxes` e **Total vendas (API)** = `totals.sold`; proxy `/api/gateway/producers`. Ecrã JWT `/taxas` (ou `/produtores` / `/saldo`) para a API.

## Problemas (404 em `/api/gateway/producers`)

1. **Teste sem login:** abra `GET /api/gateway/ping` — deve devolver JSON `{"ok": true, "gateway": "admin-proxy", ...}`.
   - **404 também aqui:** o processo HTTP (Gunicorn) não está a usar o `app.py` atual. No servidor: `cd /var/www/applyfy`, atualize o código, depois `sudo systemctl restart applyfy-painel` (ou o nome do unit em `applyfy-painel.service`).
   - **`/api/gateway/ping` OK mas `/api/gateway/producers` 404:** situação anómala; confira se não há typo no path e se não há outro vhost Nginx a responder por `applyfy.northempresarial.com`.
2. **502 / timeout:** confira `APPLYFY_PUBLIC_KEY`, `APPLYFY_SECRET_KEY` e `APPLYFY_API_TIMEOUT_LIST` no `.env`.
3. **401 / 403:** sessão Hub ou JWT sem permissão ao ecrã **Consultar produtores** (`/produtores` / prefixos API em `applyfy_screens.py`).
