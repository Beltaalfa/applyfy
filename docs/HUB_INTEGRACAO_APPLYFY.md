# Integração Hub ↔ Applyfy

Documento de contrato entre **Hub** (`hub.northempresarial.com`) e **Applyfy** (`applyfy.northempresarial.com`). O código consumidor está em `auth_hub.py` e `app.py`.

**Espelho do doc no repo North Hub (para o Cursor comparar):** [`docs/referencia-hub-INTEGRACAO-APPLYFY.md`](referencia-hub-INTEGRACAO-APPLYFY.md)

**Checklist para quem faz deploy do Hub (variáveis e build):** [`docs/HUB_OPERADORES_CHECKLIST.md`](HUB_OPERADORES_CHECKLIST.md)

**Para o Cursor no repo Hub (login Applyfy ainda não funciona):** [`docs/CURSOR_HUB_DEBUG_LOGIN.md`](CURSOR_HUB_DEBUG_LOGIN.md)

---

## Resumo Applyfy (o que configurar aqui)

| Variável Applyfy | Deve coincidir com |
|------------------|-------------------|
| `HUB_JWT_SECRET` ou `HUB_APPLYFY_JWT_SECRET` | `HUB_APPLYFY_JWT_SECRET` no Hub (mesmo segredo HS256) |
| `HUB_JWT_COOKIE_NAME` | `HUB_APPLYFY_COOKIE_NAME` no Hub (default: `access_token`) |
| `HUB_LOGIN_URL` | URL real de login (ex. `https://hub.northempresarial.com/login`) |
| `HUB_LOGOUT_URL` | URL após logout no Applyfy (ex. login do Hub). Se o Hub **não** expuser `/logout`, usar `https://hub.northempresarial.com/login` até existir rota de logout |
| `APPLYFY_AUTH_ENABLED=1` | Liga o gate |
| `FLASK_SECRET_KEY` | Obrigatório (sessão Flask) |
| `SESSION_COOKIE_SECURE=1` | Em produção HTTPS |
| `APPLYFY_PUBLIC_URL` | URL absoluta do painel (ex. `https://applyfy.northempresarial.com`) — usada no redirect para o Hub (`callbackUrl`) e na validação de `next`/`callbackUrl` |
| `APPLYFY_TRUST_PROXY=1` | Recomendado atrás de Nginx: `ProxyFix` para `X-Forwarded-*` e URLs corretas em redirects |
| `APPLYFY_HUB_ALLOWED_PROJECT_IDS` | Opcional: lista CSV de `project_id` / `tenant_id` / `client_id` permitidos no JWT; se definida, quem não estiver na lista recebe 403 |
| `HUB_LOGIN_RETURN_PARAM` | Default `callbackUrl` (NextAuth); use `next` se o Hub só ler esse parâmetro |
| `HUB_LOGIN_APPEND_NEXT=1` | Opcional: além de `callbackUrl`, envia também `next=` com o mesmo valor |

**O Hub atual não usa RS256/JWKS** nem troca `authorization_code` — só **cookie JWT HS256** (fluxo B). `HUB_JWKS_URL` / `HUB_TOKEN_URL` no Applyfy são opcionais para cenários futuros.

Bloco pronto para colar: [env-bloco-hub-exemplo.env](env-bloco-hub-exemplo.env)

---

## Handoff: o que o Hub (`hub.northempresarial.com`) implementa

### Objectivo

Login e gestão de utilizadores no **Hub** (Next.js + NextAuth). O **Applyfy** só valida um JWT em cookie **HttpOnly** e aplica permissões por claims (`auth_hub.py`).

- **Fluxo B (actual):** cookie JWT HS256 partilhado no domínio pai (`.northempresarial.com`).
- **Fluxo A:** `authorization_code` + `HUB_TOKEN_URL` — **não** está implementado no Hub.

### Cookie que o Applyfy deve ler

| Campo | Valor típico (produção Hub) |
|--------|------------------------------|
| Nome | `access_token` — configurável no Hub com `HUB_APPLYFY_COOKIE_NAME` (deve coincidir com `HUB_JWT_COOKIE_NAME` no Applyfy). |
| Domain | `.northempresarial.com` via `HUB_APPLYFY_COOKIE_DOMAIN` — o cookie é enviado a `hub.` e `applyfy.`. |
| Path | `/` |
| HttpOnly | sim |
| Secure | sim com `NODE_ENV=production` |
| SameSite | Lax |

**Importante:** o cookie `__Secure-authjs.session-token` (sessão NextAuth do Hub) **não** é o token do Applyfy. O Applyfy deve usar **`access_token`** (ou o nome configurado em ambos os lados).

**Logout / sessão inválida (Hub):** middleware limpa o cookie Applyfy (`value ""`, `maxAge: 0`, mesmos name/domain/path/secure/sameSite).

### JWT (HS256)

- Segredo partilhado: Hub `HUB_APPLYFY_JWT_SECRET` = Applyfy `HUB_JWT_SECRET` (ou alias `HUB_APPLYFY_JWT_SECRET` aqui).
- **Claims:** `sub` (id do user no Hub), `exp`, `iat`, `permissions` (array), `scope` (mesmas permissões separadas por espaço), `hub_role` (`admin` \| `client`).
- **Opcional:** `client_id` se no Hub estiver `HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID=1` (primeiro `UserClientPermission` do cliente).

O Hub **não** define `iss` nem `aud`. O Applyfy valida com `verify_aud` e `verify_iss` desligados.

### Permissões (strings exatas)

`applyfy.painel`, `applyfy.financeiro`, `applyfy.jobs`, `applyfy.admin`.

| Role Hub | JWT `permissions` |
|----------|-------------------|
| `admin` | As quatro |
| `client` | Só `applyfy.painel` (lógica em `applyfy-permissions.ts`) |

### Implementação no código Hub

| Área | Ficheiros |
|------|-----------|
| Assinatura e cookie JWT (`jose`, HS256, refresh perto do expiry) | `src/lib/applyfy-cookie.ts` |
| Middleware: set / renova / remove cookie; redirects | `src/app/middleware.ts` |
| Redirects pós-login **seguros** (hosts permitidos) | `src/lib/safe-post-login-redirect.ts` |
| Auth.js: callback de redirect que aceita URL externa para o Applyfy | `src/lib/auth.ts` |
| Login: `signIn` com `redirect: false`, refresh, destino seguro, flush do cookie antes de sair | `src/app/login/page.tsx` |
| Sincronização do cookie em **Node** (segredo disponível em runtime; Edge/middleware pode não ter env) | `GET /api/hub/applyfy-cookie-sync`, `src/components/ApplyfyCookieSync.tsx` (providers), `src/lib/applyfy-cookie-flush.ts` |
| Menu Applyfy | `src/components/layout/ApplyfyNavLink.tsx` |
| Permissões | `src/lib/applyfy-permissions.ts` |
| Testes | `safe-post-login-redirect.test.ts`, `applyfy-permissions.test.ts`, `applyfy-cookie.test.ts` |
| Documentação Hub | `docs/INTEGRACAO-APPLYFY.md`, `.env.example` (raiz do repo Hub) |

### Redirects pós-login e query params

`safe-post-login-redirect.ts` só permite paths no Hub ou URLs cujo **origin** seja: Hub, Applyfy (`NEXT_PUBLIC_APPLYFY_URL`), `NEXTAUTH_URL`, ou hostname sob `NEXT_PUBLIC_POST_LOGIN_TRUSTED_HOST_SUFFIX`.

**Nomes de query suportados:** `callbackUrl`, `next`, `returnUrl`, `return_to`, `redirect`, `return`. Fallback com Referer quando confiável.

**Modo entrada Applyfy:** `?from=applyfy` (e variantes `source` / `entry` / `post_login_source=applyfy`) redireciona para a **raiz** de `NEXT_PUBLIC_APPLYFY_URL` se não houver outro destino.

Middleware: utilizador autenticado em `/login` vai para destino seguro ou default admin/dashboard; rotas protegidas sem sessão → `/login?callbackUrl=...`.

### Variáveis de ambiente no Hub (cruzar com o Applyfy)

| Hub | Applyfy / notas |
|-----|-----------------|
| `HUB_APPLYFY_JWT_SECRET` | = `HUB_JWT_SECRET` |
| `HUB_APPLYFY_COOKIE_DOMAIN` | ex. `.northempresarial.com` |
| `HUB_APPLYFY_COOKIE_NAME` | = `HUB_JWT_COOKIE_NAME` (default `access_token`) |
| `NEXT_PUBLIC_APPLYFY_URL` | = `APPLYFY_PUBLIC_URL` (URL pública do painel) |
| `NEXT_PUBLIC_POST_LOGIN_TRUSTED_HOST_SUFFIX` | ex. `northempresarial.com` |
| `NEXTAUTH_URL` | URL real do Hub |
| `HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID=1` | Opcional; allowlist no Applyfy: `APPLYFY_HUB_ALLOWED_PROJECT_IDS` |

**Deploy Hub:** alterações em `NEXT_PUBLIC_*` exigem **`npm run build`**. Processo PM2 típico: **`north-hub`** (não `hub`).

### O que o Applyfy deve garantir

1. `HUB_JWT_SECRET` igual a `HUB_APPLYFY_JWT_SECRET` do Hub.
2. Ler o cookie **`access_token`** (ou o nome alinhado em ambos).
3. Validar JWT HS256 e claims conforme este doc e `auth_hub.py`.
4. `HUB_LOGIN_URL` com query quando quiserem voltar ao painel após login, por exemplo:  
   `.../login?callbackUrl=<URL encode do Applyfy>` ou `.../login?from=applyfy`.
5. `HUB_LOGOUT_URL`: se o Hub não tiver rota `/logout`, usar por exemplo `https://hub.northempresarial.com/login` até existir logout dedicado.
6. `APPLYFY_PUBLIC_URL` e `APPLYFY_TRUST_PROXY=1` atrás de Nginx; reiniciar o serviço Applyfy após alterar `.env`.

---

## Endpoints Applyfy

| Rota | Uso |
|------|-----|
| `GET /auth/callback` | Se cookie já veio do Hub, segue para o primeiro query param não vazio entre: `callbackUrl`, `next`, `returnUrl`, `return_to`, `redirect`, `return`, `continue`, `goto`, `destination` (sanitizado; alinhado ao Hub); código OAuth só se existir `HUB_TOKEN_URL` (não usado pelo Hub atual). |
| `GET /auth/logout` | Limpa sessão Flask; redireciona para `HUB_LOGOUT_URL`. |
| `GET /api/me` | `auth_enabled`, `authenticated`, `user` (`sub`, `project_id`, `hub_role`), `permissions`, `nav` (menu). |

Rotas públicas (sem JWT de utilizador): `/health`, `/api/health`, `/api/webhooks/applyfy`, `/api/me`, `/manifest.json`, `/favicon.ico`, `/sw.js`, prefixo `/static/`, `/auth/callback`, `/auth/logout`, etc. (`/manifest.json` evita redirect ao Hub quando o browser pede o manifest na raiz; o ficheiro real está em `static/manifest.json` com `static_url_path=""`.)

---

## Permissões no Applyfy (efeito)

| Permissão | Acesso |
|-----------|--------|
| `applyfy.painel` | Painel geral, relatórios, vendas, transações, meta, comercial, produtores, logs de saldo, APIs correspondentes |
| `applyfy.financeiro` | `/financeiro` e `/api/financeiro/*` |
| `applyfy.jobs` | `/integracoes` e `/api/job*`, `/api/job-vendas*` |
| `applyfy.admin` | Rotas `/api/admin/*` (alternativa ao header `APPLYFY_ADMIN_TOKEN`) + bypass de checks quando em conjunto com as outras |

Utilizador com `applyfy.admin` na lista é tratado como acesso amplo às permissões (atalho no código).

---

## Checklist Applyfy (servidor)

- [ ] `HUB_JWT_SECRET` = valor de `HUB_APPLYFY_JWT_SECRET` do Hub
- [ ] `HUB_JWT_COOKIE_NAME` = `HUB_APPLYFY_COOKIE_NAME` do Hub (se não for `access_token`)
- [ ] `HUB_LOGIN_URL` aponta para o login real
- [ ] `FLASK_SECRET_KEY` definido e estável
- [ ] `SESSION_COOKIE_SECURE=1` em HTTPS
- [ ] `APPLYFY_AUTH_ENABLED=1` após testar cookie no subdomínio Applyfy
- [ ] `APPLYFY_PUBLIC_URL` = URL pública do painel (redirects e validação de retorno)
- [ ] `APPLYFY_TRUST_PROXY=1` se estiver atrás de Nginx com `X-Forwarded-*`
- [ ] (Opcional) `APPLYFY_HUB_ALLOWED_PROJECT_IDS` alinhado com `client_id` / `project_id` / `tenant_id` do JWT; no Hub ligar **`HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID=1`** se usarem `client_id`
- [ ] Reiniciar Gunicorn/systemd após alterar `.env`

**Verificação sem browser:** `./venv/bin/python scripts/hub_auth_smoke.py` (com `APPLYFY_AUTH_ENABLED=1`, confirma redirects e `/api/me` sem cookie).

---

## Evolução futura

- **RS256 / JWKS:** hoje não emitido pelo Hub; o Applyfy já suporta `HUB_JWKS_URL` se no futuro o Hub mudar.
- **Fluxo authorization_code:** código em `auth_hub.exchange_code_for_token` + `/auth/callback`; exige `HUB_TOKEN_URL` e credenciais — não necessário com o Hub descrito acima.
