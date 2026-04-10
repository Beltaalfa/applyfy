# Checklist — deploy North Hub (integração Applyfy)

Use este guia **no repositório / servidor do Hub** (não no Applyfy). Cruza com [`HUB_INTEGRACAO_APPLYFY.md`](HUB_INTEGRACAO_APPLYFY.md) e o espelho [`referencia-hub-INTEGRACAO-APPLYFY.md`](referencia-hub-INTEGRACAO-APPLYFY.md).

**Debug login Applyfy (instruções para Cursor no Hub):** [`CURSOR_HUB_DEBUG_LOGIN.md`](CURSOR_HUB_DEBUG_LOGIN.md).

## Variáveis obrigatórias / críticas

- [ ] `HUB_APPLYFY_JWT_SECRET` — **igual** a `HUB_JWT_SECRET` (ou `HUB_APPLYFY_JWT_SECRET`) no `.env` do Applyfy.
- [ ] `HUB_APPLYFY_COOKIE_DOMAIN` — domínio pai (ex. `.northempresarial.com`) para o browser enviar o cookie também a `applyfy.*`. Em local pode ficar vazio.
- [ ] `HUB_APPLYFY_COOKIE_NAME` — alinhado com o Applyfy (default `access_token` nos dois lados).
- [ ] `NEXT_PUBLIC_APPLYFY_URL` — mesma URL que `APPLYFY_PUBLIC_URL` no Applyfy (ex. `https://applyfy.northempresarial.com`).
- [ ] `NEXTAUTH_URL` — URL real do Hub em produção.
- [ ] `NEXT_PUBLIC_POST_LOGIN_TRUSTED_HOST_SUFFIX` — sufixo do domínio para redirects seguros (ex. `northempresarial.com`).

## Build

- [ ] Após alterar qualquer `NEXT_PUBLIC_*`, executar **`npm run build`** (ou o pipeline de deploy) e reiniciar o processo Node (ex. PM2 **`north-hub`**).

## Opcional multi-empresa

- [ ] `HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID=1` no Hub e `APPLYFY_HUB_ALLOWED_PROJECT_IDS` no Applyfy com os ids permitidos.

## Verificação

- [ ] Login no Hub → nas DevTools, no domínio do painel Applyfy, o pedido à raiz inclui o cookie JWT (`access_token` ou o nome configurado).
- [ ] Logout no Hub remove o cookie Applyfy (name/domain/path coerentes).
