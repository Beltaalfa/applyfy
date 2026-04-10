# Debug: login Applyfy não funciona (para abrir no Cursor do **North Hub**)

**Contexto:** o painel Applyfy já valida o fluxo B (JWT HS256 em cookie `access_token`). Se após login no Hub o utilizador **continua a ser mandado para o login** ou vê **401/403** no Applyfy, o problema está quase sempre na **emissão do cookie ou do redirect no Hub**, não no código Python do Applyfy.

**Cole este ficheiro (ou o seu conteúdo) no workspace do Hub** e peça ao Cursor, por exemplo:

> Segue `docs/CURSOR_HUB_DEBUG_LOGIN.md` (ou o texto anexado) e verifica `applyfy-cookie.ts`, middleware, `safe-post-login-redirect` e variáveis de ambiente em produção. O Applyfy espera o cookie no domínio partilhado e o segredo HS256 igual ao servidor Applyfy.

---

## Fluxo esperado (resumo)

1. Utilizador abre `https://applyfy…` sem cookie Applyfy → Applyfy redireciona para `HUB_LOGIN_URL?callbackUrl=…` (URL do Applyfy codificada).
2. Utilizador faz login no Hub.
3. O Hub deve **definir** `Set-Cookie` com o JWT Applyfy (**nome** configurável, default `access_token`) com **Domain** = domínio **pai** (ex. `.northempresarial.com`), **Path** `/`, **HttpOnly**, **Secure** em produção, **SameSite** compatível (ex. Lax).
4. O Hub redireciona o browser para o **destino seguro** (origin do Applyfy permitido por `NEXT_PUBLIC_APPLYFY_URL` ou sufixo confiável).
5. O browser envia o **mesmo** cookie no pedido seguinte ao host `applyfy.…` → Applyfy valida JWT com `HUB_JWT_SECRET` e deixa entrar.

Se o cookie ficar só no host `hub.…` (sem `Domain` pai), o Applyfy **nunca** recebe `access_token` → loop de login.

---

## Checklist rápido (lado Hub — produção)

| Verificação | O que deve ser |
|-------------|----------------|
| `HUB_APPLYFY_JWT_SECRET` | **Byte a byte igual** a `HUB_JWT_SECRET` (ou `HUB_APPLYFY_JWT_SECRET`) no `.env` do servidor Applyfy. Espaço extra ou aspas erradas quebram a assinatura. |
| `HUB_APPLYFY_COOKIE_DOMAIN` | Em produção com subdomínios: **`.dominio.com`** (ponto inicial). Vazio = cookie só no host actual (mau para `applyfy.`). |
| `HUB_APPLYFY_COOKIE_NAME` | Igual ao Applyfy `HUB_JWT_COOKIE_NAME` (default `access_token`). |
| `HUB_APPLYFY_COOKIE_ENABLED` | Não pode estar `0` se quiserem cookie Applyfy. |
| `NEXT_PUBLIC_APPLYFY_URL` | **Exactamente** a URL pública do painel (mesmo que `APPLYFY_PUBLIC_URL` no Applyfy), incluindo `https://` e sem barra final desnecessária que parta redirects. |
| `NEXT_PUBLIC_POST_LOGIN_TRUSTED_HOST_SUFFIX` | Deve cobrir o domínio do Applyfy (ex. `northempresarial.com`) se usarem subdomínios. |
| `NEXTAUTH_URL` | URL real do Hub em produção. |
| Build | Qualquer mudança em `NEXT_PUBLIC_*` exige **`npm run build`** + reinício (ex. PM2 **`north-hub`**). |

---

## O que pedir ao Cursor no repo Hub (ficheiros)

1. **`src/lib/applyfy-cookie.ts`** — onde se assina o JWT e se define `domain`, `name`, `secure`, `sameSite`, `path`, `maxAge`.
2. **`src/app/middleware.ts`** — onde o cookie é escrito/renovado/removido no redirect; confirmar que corre no fluxo de login que afecta redirects para o Applyfy.
3. **`src/lib/safe-post-login-redirect.ts`** (e `post-login-destination`) — se o redirect para `applyfy…` está a ser **rejeitado** (fallback para dashboard Hub).
4. **`src/app/login/LoginForm.tsx` / `login/page.tsx`** — fluxo pós-credentials (middleware vs `/hub/bridge`).
5. **`src/app/hub/bridge/route.ts`** — redirects explícitos com cookie.
6. Logs / Sentry no momento do login: erros ao assinar JWT (segredo em falta no runtime Edge vs Node).

---

## Teste no browser (sem Cursor)

1. Janela anónima → abrir o Applyfy → login no Hub.
2. **Antes** de voltar ao Applyfy: DevTools → **Application** → **Cookies** → seleccionar o domínio **`https://applyfy.…`**.
3. Deve existir cookie com o **nome** esperado (`access_token` por defeito), **Domain** típico `.northempresarial.com` (ou o vosso pai).
4. **Network**: primeiro GET ao Applyfy após redirect → **Request Headers** deve incluir `Cookie: access_token=…` (ou o nome configurado).

**Se o cookie só aparece em `hub.…` e não em `applyfy.…`:** ajustar `HUB_APPLYFY_COOKIE_DOMAIN` e o código que define o `Set-Cookie`.

---

## Lado Applyfy (só para cruzar dados — repo Applyfy)

| Applyfy `.env` | Deve alinhar com Hub |
|----------------|----------------------|
| `HUB_JWT_SECRET` | = `HUB_APPLYFY_JWT_SECRET` no Hub |
| `HUB_JWT_COOKIE_NAME` | = `HUB_APPLYFY_COOKIE_NAME` no Hub |
| `APPLYFY_PUBLIC_URL` | = `NEXT_PUBLIC_APPLYFY_URL` no Hub |
| `APPLYFY_HUB_ALLOWED_PROJECT_IDS` | Se preenchido no Applyfy, o JWT **tem** de trazer `client_id` / `project_id` / `tenant_id` na lista → no Hub `HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID=1` quando aplicável |

Contrato completo no repo Applyfy: `docs/HUB_INTEGRACAO_APPLYFY.md`.  
Checklist deploy Hub: `docs/HUB_OPERADORES_CHECKLIST.md`.

---

## Sintomas → causas prováveis

| Sintoma | Causa provável no Hub |
|---------|------------------------|
| Loop infinito Hub ↔ Applyfy | Cookie não enviado ao `applyfy.*` (`Domain` errado ou ausente). |
| 403 “empresa/projeto” no Applyfy | `APPLYFY_HUB_ALLOWED_PROJECT_IDS` no Applyfy sem `client_id` correspondente no JWT. |
| Sempre 401 / redirect login | Segredo HS256 diferente; ou nome do cookie diferente; ou JWT expirado/inválido. |
| Após login vai para dashboard Hub em vez do Applyfy | Redirect pós-login rejeitou URL do Applyfy (`NEXT_PUBLIC_APPLYFY_URL` errado ou sufixo confiável em falta). |

---

## Comando no servidor Applyfy (sanidade)

Com venv e `.env` de produção:

```bash
./venv/bin/python scripts/hub_auth_smoke.py
```

Se imprimir `OK (auth Hub ligada)…`, o Applyfy está coerente; o gargalo é **cookie/redirect no Hub** ou **browser não envia cookie** ao subdomínio Applyfy.
