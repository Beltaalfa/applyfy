# Espelho: documento do repositório North Hub

**Origem:** `north/hub/docs/INTEGRACAO-APPLYFY.md` (vista do lado Hub).

**Para quê:** no Cursor, abre também `docs/HUB_INTEGRACAO_APPLYFY.md` (contrato do lado Applyfy) e compara — o espelho descreve ficheiros e variáveis no Hub; o outro doc descreve `auth_hub.py`, `.env` e checklist aqui. **Checklist operacional Hub (deploy):** `docs/HUB_OPERADORES_CHECKLIST.md`. **Debug login Applyfy (texto para Cursor no Hub):** `docs/CURSOR_HUB_DEBUG_LOGIN.md`.

---

# Integração Hub ↔ Applyfy

Contrato implementado no **Hub** para o painel **Applyfy** validar utilizadores com JWT em cookie HttpOnly (Fluxo B).

**Documento de referência no repositório Applyfy:** `docs/HUB_INTEGRACAO_APPLYFY.md` (contrato cookie, claims, checklist, pós-login).

## O que o Hub faz

1. Após **login** bem-sucedido, define cookie com JWT **HS256** (`sub`, `exp`, `permissions`, `scope`, `hub_role`; opcionalmente `client_id`).
2. Nos pedidos seguintes (autenticado), **renova** o cookie quando está ausente ou perto de expirar.
3. Em **logout** ou sessão inválida, **remove** o cookie (mesmo `name` + `Domain` + `Path`).
4. **Redirect pós-login:** resolvido no **middleware** em `/login` (uma única fonte de verdade). Clientes North vão para o **subdomínio do portal**; se o origin de `NEXT_PUBLIC_APPLYFY_URL` for o mesmo que `{subdomínio}.{HUB_ROOT_DOMAIN}` do cliente (ex. ApplyFy), o destino passa a ser essa URL (raiz ou path configurado), em vez de `/dashboard`. Admins mantêm redirects seguros por query (`callbackUrl`, etc.).
5. Menu lateral / quick nav **Applyfy:** apenas utilizadores com `role === admin` no host `hub.*` (clientes usam o portal no subdomínio). Requer `NEXT_PUBLIC_APPLYFY_URL`; entradas em `applyfy-hub-nav.ts`. Opcional: `NEXT_PUBLIC_APPLYFY_NAV_JSON`.

## Redirect pós-login (segurança)

- **Paths relativos** permitidos: só no mesmo origin do Hub (pathname começa com `/`, não `//`).
- **URLs absolutas** permitidas: `https:` / `http:` com origin igual a `NEXT_PUBLIC_APPLYFY_URL`, ao origin do pedido (Hub), ou a `NEXTAUTH_URL`.
- **Rejeitado:** outros hosts, `javascript:`, `data:`, paths com `\`.
- Pedidos a páginas protegidas sem sessão redirecionam para `/login?callbackUrl=<url codificada>` para, após login, voltar ao sítio pretendido.

**Parâmetros de query reconhecidos** (primeiro valor válido ganha): `callbackUrl`, `next`, `returnUrl`, `return_to`, `redirect`, `return`, `continue`, `goto`, `destination`.

**Sem `callbackUrl` na URL:** o Hub tenta ainda `document.referrer` / header `Referer` (se for origin confiável, ex. Applyfy). Se o Applyfy não puder enviar URL completo, configure **`HUB_LOGIN_URL`** com query mínima:

- `https://hub.northempresarial.com/login?from=applyfy` — após login, o utilizador vai para `NEXT_PUBLIC_APPLYFY_URL` (raiz do painel).

Ou, com destino exacto:

- `https://hub.northempresarial.com/login?callbackUrl=` + URL do Applyfy codificada (path específico após login).

Implementação: `src/lib/safe-post-login-redirect.ts`, `src/lib/post-login-destination.ts` e `middleware.ts`.

**Loop login Hub ↔ Applyfy:** o cookie `access_token` **não** é o cookie de sessão NextAuth. O **login** no formulário faz navegação completa para `/login` para o middleware aplicar o redirect e definir o JWT Applyfy no **302** quando o destino é externo. A rota **GET `/hub/bridge?to=…`** (fora do `matcher` do middleware, Node + `getToken`) continua disponível para links explícitos; sem `to` válido redirecciona com a mesma lógica de `post-login-destination`. `applyfy-cookie-sync` corre **só para admin**. `post-login-external` é alternativa programática.

**SSO entre subdomínios:** opcional `HUB_AUTH_COOKIE_DOMAIN` (ex.: `.northempresarial.com`) para o cookie de sessão NextAuth ser enviado em `hub.*` e nos portais `*.northempresarial.com`.

## Variáveis de ambiente (Hub)

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `HUB_APPLYFY_JWT_SECRET` | Para ativar | Mesmo segredo que o Applyfy usa para validar (`HUB_JWT_SECRET` no lado Applyfy). |
| `HUB_APPLYFY_COOKIE_DOMAIN` | Produção | Ex.: `.northempresarial.com` para o cookie ir também ao Applyfy. Em local deixe vazio (cookie só no host atual). |
| `HUB_APPLYFY_COOKIE_NAME` | Não | Default `access_token`. |
| `HUB_APPLYFY_COOKIE_ENABLED` | Não | `0` desliga mesmo com segredo. |
| `HUB_APPLYFY_JWT_EXPIRES_SEC` | Não | Default `86400`. |
| `HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID` | Não | `1` inclui no JWT o `client_id` do Hub (primeiro `UserClientPermission` do user cliente). Para allowlist no Applyfy (`APPLYFY_HUB_ALLOWED_PROJECT_IDS`). |
| `HUB_APPLYFY_CLIENT_ID` | Não | Id do `Client` ApplyFy no Hub; se vazio, resolve por `subdomain=applyfy`. Usado nas permissões por tela. |
| `NEXT_PUBLIC_APPLYFY_URL` | Recomendado | URL do painel (menu + validação de redirects externos). |
| `NEXT_PUBLIC_APPLYFY_NAV_JSON` | Não | JSON opcional: array `{ "label", "path", "required" }` com `required` ∈ `painel` \| `financeiro` \| `jobs` \| `admin`. |
| `NEXT_PUBLIC_POST_LOGIN_TRUSTED_HOST_SUFFIX` | Recomendado | Ex.: `northempresarial.com` — aceita `callbackUrl`/`next` para qualquer subdomínio (ex. Applyfy) mesmo que o URL exacto não estivesse no build. Se omitir, o Hub deriva um sufixo a partir do *hostname* de `NEXTAUTH_URL` (ex. `hub.x.com` → `x.com`). |
| `NEXTAUTH_URL` | Sim | Usado no middleware e no callback `redirect` do Auth.js para o Hub. |

## JWT (claims)

- `sub`: id do utilizador no Hub (cuid).
- `exp` / `iat`: standard JWT.
- `permissions`: array de strings, ex. `applyfy.painel`, `applyfy.financeiro`, `applyfy.jobs`, `applyfy.admin`.
- `scope`: mesmas permissões separadas por espaço.
- `hub_role`: `admin` \| `client` (informativo).
- `client_id` (opcional): id do modelo `Client` no Hub, só com `HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID=1` e utilizadores com role `client` e permissão associada.
- `applyfy_screens` (opcional): array de paths de ecrã do painel; quando presente, o Applyfy restringe por tela. Gestão: Admin Hub → **ApplyFy — telas**; modelo `UserApplyfyScreenGrant`; lista canónica em `src/lib/applyfy-screens.ts`.

**Mapeamento actual (permissions coarse)**

- **admin** Hub → todas as permissões Applyfy (`applyfy.painel`, `applyfy.financeiro`, `applyfy.jobs`, `applyfy.admin`).
- **client** Hub → `applyfy.painel`, `applyfy.financeiro`, `applyfy.jobs` (ver `src/lib/applyfy-permissions.ts`). O acesso fino por tela usa `applyfy_screens` quando configurado.

## Fluxo A (código + token URL)

Não implementado neste repositório. Exige endpoints `POST` no Hub conforme especificação partilhada com o time Applyfy.

## Checklist Applyfy (servidor)

Alinhar com o `.env.example` do Applyfy: `APPLYFY_AUTH_ENABLED`, `HUB_LOGIN_URL`, `HUB_JWT_SECRET` (= `HUB_APPLYFY_JWT_SECRET` no Hub), `SESSION_COOKIE_SECURE`, etc.

## Ficheiros relevantes no Hub

- `src/lib/applyfy-cookie.ts` — assinatura JWT e cookie.
- `src/lib/applyfy-permissions.ts` — permissões Applyfy e regra do menu.
- `src/lib/applyfy-screens.ts` — lista de ecrãs e mapeamento API → ecrã (sincronizar com `applyfy/applyfy_screens.py`).
- `src/app/api/admin/applyfy-screens/route.ts` — API admin para `UserApplyfyScreenGrant`.
- `src/app/admin/config/applyfy-permissoes/` — UI de checkboxes por utilizador.
- `src/lib/safe-post-login-redirect.ts` — redirects seguros pós-login.
- `src/app/middleware.ts` — cookie, redirect login, `callbackUrl` em rotas protegidas; **não** cobre `/hub/bridge`.
- `src/app/login/LoginForm.tsx` — após credentials, redirect externo via GET `/hub/bridge?to=...` (middleware).
- `src/app/hub/bridge/route.ts` — GET Node + `getToken` + cookie Applyfy + redirect externo.
- `src/app/api/hub/post-login-external/route.ts` — alternativa Node (validação de `to`); o fluxo principal do formulário usa o middleware.
- `src/app/login/page.tsx` — props ao `LoginForm` + query.
- `src/lib/applyfy-hub-nav.ts` — entradas do menu Applyfy no Hub (paths editáveis).
- `src/components/layout/ApplyfySidebarSection.tsx` — secção Applyfy no menu lateral.
- `src/components/layout/ApplyfyQuickNav.tsx` — menu compacto (ex.: cabeçalho Helpdesk).

## Uma frase para o agente Applyfy

Implementar consumo de `callbackUrl` / `next` no Hub já está feito com validação de host; manter cookie JWT no domínio partilhado; link Applyfy no menu só com permissão equivalente a `applyfy.painel`; opcionalmente claim `client_id` no JWT com `HUB_APPLYFY_JWT_INCLUDE_CLIENT_ID=1` para allowlist no Applyfy.
