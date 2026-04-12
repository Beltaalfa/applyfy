# -*- coding: utf-8 -*-
"""
Autenticação via Hub (hub.northempresarial.com): JWT em cookie HttpOnly (fluxo B).

Contrato alinhado com o Hub (HS256, sem iss/aud):
- sub: id do user (cuid) ou email
- exp / iat: standard JWT
- permissions: array de strings; scope: join com espaço (redundante)
- hub_role: "admin" | "client" (informativo na API /api/me)
- applyfy_screens: opcional; lista de paths de ecrã (ex. /vendas). Se presente, o gate usa só esta lista + applyfy.admin.
- email, name: opcionais (perfil Hub no JWT).
- applyfy.comercial / applyfy.comercial.gerente: flags de carteira comercial (Hub UserClientPermission).

Segredo: no Applyfy use HUB_JWT_SECRET (ou HUB_APPLYFY_JWT_SECRET com o mesmo valor que HUB_APPLYFY_JWT_SECRET no Hub).
Cookie: HUB_JWT_COOKIE_NAME = nome no Hub HUB_APPLYFY_COOKIE_NAME (default access_token).

Troca authorization_code (HUB_TOKEN_URL): opcional; o Hub atual não usa — ver docs/HUB_INTEGRACAO_APPLYFY.md.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode, urlparse
from functools import wraps
from typing import Any

from flask import Request, g, jsonify, redirect, request, session

from applyfy_screens import normalize_applyfy_path, path_to_screen_id

try:
    import jwt
    from jwt import PyJWKClient
except ImportError:  # pragma: no cover
    jwt = None
    PyJWKClient = None


def auth_enabled() -> bool:
    raw = (os.environ.get("APPLYFY_AUTH_ENABLED") or os.environ.get("HUB_AUTH_ENABLED") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def hub_jwt_cookie_name() -> str:
    return (os.environ.get("HUB_JWT_COOKIE_NAME") or "access_token").strip() or "access_token"


def effective_return_url() -> str:
    """
    URL absoluta do Applyfy para onde o Hub deve redirecionar após o login.
    Usa APPLYFY_PUBLIC_URL + path atual, ou request.url (com ProxyFix atrás do Nginx).
    """
    base = (os.environ.get("APPLYFY_PUBLIC_URL") or "").strip().rstrip("/")
    fp = request.full_path
    if not fp.startswith("/"):
        fp = "/" + fp
    if base:
        return base + fp
    return request.url


def _hub_origin_from_applyfy_public_url() -> str | None:
    """
    URL base do Hub (https://hub.apex) quando HUB_LOGIN_URL não está no .env.
    Substitui o primeiro rótulo do hostname de APPLYFY_PUBLIC_URL por HUB_LOGIN_SUBDOMAIN (default hub).
    """
    raw = (os.environ.get("APPLYFY_PUBLIC_URL") or "").strip()
    if not raw:
        return None
    try:
        u = urlparse(raw if "://" in raw else f"https://{raw}")
        host = (u.hostname or "").lower()
        if not host or "." not in host:
            return None
        _first, rest = host.split(".", 1)
        hub_sub = (os.environ.get("HUB_LOGIN_SUBDOMAIN") or os.environ.get("HUB_SUBDOMAIN") or "hub").strip().lower() or "hub"
        hub_host = f"{hub_sub}.{rest}"
        scheme = u.scheme if u.scheme in ("http", "https") else "https"
        return f"{scheme}://{hub_host}"
    except Exception:
        return None


def hub_login_url(return_to: str | None = None) -> str:
    """
    Redireciona para o login do Hub com o destino pós-login.
    Por defeito usa callbackUrl (NextAuth); defina HUB_LOGIN_RETURN_PARAM=next se o Hub só ler ?next=.
    """
    base = (os.environ.get("HUB_LOGIN_URL") or "").strip().rstrip("/")
    if not base:
        return "/"
    if not return_to:
        return base
    sep = "&" if "?" in base else "?"
    param = (os.environ.get("HUB_LOGIN_RETURN_PARAM") or "callbackUrl").strip() or "callbackUrl"
    parts = [f"{param}={quote(return_to, safe='')}"]
    if (os.environ.get("HUB_LOGIN_APPEND_NEXT") or "").strip().lower() in ("1", "true", "yes"):
        parts.append(f"next={quote(return_to, safe='')}")
    return f"{base}{sep}{'&'.join(parts)}"


# Parâmetros de query alinhados ao Hub (safe-post-login-redirect / middleware) — primeiro valor não vazio ganha.
CALLBACK_URL_QUERY_KEYS: tuple[str, ...] = (
    "callbackUrl",
    "next",
    "returnUrl",
    "return_to",
    "redirect",
    "return",
    "continue",
    "goto",
    "destination",
)


def redirect_target_from_request_args(req: Request) -> str | None:
    """Primeiro argumento de query não vazio entre as chaves reconhecidas pelo Hub."""
    for key in CALLBACK_URL_QUERY_KEYS:
        v = (req.args.get(key) or "").strip()
        if v:
            return v
    return None


def sanitize_redirect_target(next_raw: str | None) -> str:
    """Evita open redirect: só path relativo ou URL do próprio Applyfy."""
    default = effective_return_url()
    if not next_raw or not str(next_raw).strip():
        return default
    n = str(next_raw).strip()
    if n.startswith("/") and not n.startswith("//"):
        return n
    pub = (os.environ.get("APPLYFY_PUBLIC_URL") or "").strip().rstrip("/")
    if pub and (n == pub or n.startswith(pub + "/") or n.startswith(pub + "?")):
        return n
    try:
        p = urlparse(n)
        if p.scheme in ("http", "https") and p.netloc and p.netloc == request.host:
            return n
    except Exception:
        pass
    return default


def jwt_project_allowed(payload: dict[str, Any]) -> bool:
    """
    Se APPLYFY_HUB_ALLOWED_PROJECT_IDS estiver definido (lista separada por vírgulas),
    o JWT tem de trazer project_id, tenant_id ou client_id contido nessa lista.
    """
    raw = (os.environ.get("APPLYFY_HUB_ALLOWED_PROJECT_IDS") or "").strip()
    if not raw:
        return True
    allowed = {x.strip() for x in raw.split(",") if x.strip()}
    pid = str(
        payload.get("project_id") or payload.get("tenant_id") or payload.get("client_id") or ""
    ).strip()
    if not pid:
        return False
    return pid in allowed


def hub_logout_url() -> str:
    u = (os.environ.get("HUB_LOGOUT_URL") or "").strip()
    if u:
        return u
    # Sem isto, o default era `hub_login_url()` — não chama `/logout` do Hub e a sessão NextAuth não termina.
    base = (os.environ.get("HUB_LOGIN_URL") or "").strip().rstrip("/")
    if base:
        try:
            p = urlparse(base)
            if p.scheme in ("http", "https") and p.netloc:
                return f"{p.scheme}://{p.netloc}/logout"
        except Exception:
            pass
    derived = _hub_origin_from_applyfy_public_url()
    if derived:
        return f"{derived}/logout"
    login_fb = hub_login_url()
    if login_fb.startswith("http://") or login_fb.startswith("https://"):
        try:
            p = urlparse(login_fb)
            return f"{p.scheme}://{p.netloc}/logout"
        except Exception:
            pass
    return login_fb


def is_public_path(path: str) -> bool:
    if path.startswith("/static/"):
        return True
    exact = {
        "/health",
        "/api/health",
        "/api/gateway/ping",
        "/api/_debug/client-log",
        "/api/me",
        "/api/webhooks/applyfy",
        "/favicon.ico",
        "/manifest.json",
        "/robots.txt",
        "/sitemap.xml",
        "/sw.js",
        "/auth/callback",
        "/auth/logout",
    }
    if path in exact:
        return True
    return False


def _permissions_from_payload(payload: dict[str, Any]) -> list[str]:
    perms = payload.get("permissions")
    if isinstance(perms, list):
        return [str(p).strip() for p in perms if str(p).strip()]
    if isinstance(perms, str) and perms.strip():
        return [p.strip() for p in perms.replace(",", " ").split() if p.strip()]
    scope = payload.get("scope")
    if isinstance(scope, str) and scope.strip():
        return [p.strip() for p in scope.split() if p.strip()]
    return []


def _jwt_decode_options() -> dict[str, Any]:
    """Hub não envia iss nem aud; PyJWT não deve exigir."""
    return {"verify_aud": False, "verify_iss": False}


def _decode_jwt(token: str) -> dict[str, Any] | None:
    if not jwt or not token:
        return None
    secret = (os.environ.get("HUB_JWT_SECRET") or os.environ.get("HUB_APPLYFY_JWT_SECRET") or "").strip()
    jwks_url = (os.environ.get("HUB_JWKS_URL") or "").strip()
    algorithms_env = (os.environ.get("HUB_JWT_ALGORITHMS") or "HS256,RS256").strip()
    algorithms = [a.strip() for a in algorithms_env.split(",") if a.strip()]
    opts = _jwt_decode_options()
    try:
        if jwks_url and PyJWKClient:
            jwks_client = PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            data = jwt.decode(
                token,
                signing_key.key,
                algorithms=algorithms,
                options=opts,
            )
            return data if isinstance(data, dict) else None
        if secret:
            # Hub em produção: só HS256 (jose SignJWT); não misturar algs sem JWKS
            data = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options=opts,
            )
            return data if isinstance(data, dict) else None
    except Exception:
        return None
    return None


def payload_to_session(payload: dict[str, Any]) -> None:
    session["hub_sub"] = str(payload.get("sub") or payload.get("user_id") or "").strip() or None
    session["hub_project_id"] = str(
        payload.get("project_id") or payload.get("tenant_id") or payload.get("client_id") or ""
    ).strip() or None
    role = payload.get("hub_role")
    session["hub_role"] = str(role).strip() if role is not None else None
    perms = _permissions_from_payload(payload)
    session["hub_permissions"] = perms
    session["hub_authenticated"] = bool(session.get("hub_sub"))
    em = payload.get("email")
    session["hub_user_email"] = str(em).strip() if em is not None and str(em).strip() else None
    nm = payload.get("name")
    session["hub_user_name"] = str(nm).strip() if nm is not None and str(nm).strip() else None
    if "applyfy_screens" in payload:
        raw = payload.get("applyfy_screens")
        if isinstance(raw, list):
            session["hub_allowed_screens"] = [str(x).strip() for x in raw if str(x).strip()]
        else:
            session["hub_allowed_screens"] = []
    else:
        session.pop("hub_allowed_screens", None)


def clear_hub_session() -> None:
    for k in (
        "hub_sub",
        "hub_project_id",
        "hub_role",
        "hub_permissions",
        "hub_authenticated",
        "hub_allowed_screens",
        "hub_user_email",
        "hub_user_name",
        "oauth_state",
    ):
        session.pop(k, None)


def try_cookie_jwt(req: Request) -> bool:
    g.hub_auth_reject = None
    token = (req.cookies.get(hub_jwt_cookie_name()) or "").strip()
    if not token:
        return bool(session.get("hub_authenticated") and session.get("hub_sub"))
    payload = _decode_jwt(token)
    if not payload or not (payload.get("sub") or payload.get("user_id")):
        clear_hub_session()
        return False
    if not jwt_project_allowed(payload):
        clear_hub_session()
        g.hub_auth_reject = "project"
        return False
    payload_to_session(payload)
    return True


def exchange_code_for_token(code: str) -> str | None:
    token_url = (os.environ.get("HUB_TOKEN_URL") or "").strip()
    client_id = (os.environ.get("HUB_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("HUB_CLIENT_SECRET") or "").strip()
    redirect_uri = (os.environ.get("HUB_REDIRECT_URI") or "").strip()
    if not all([token_url, client_id, code]):
        return None
    if not redirect_uri:
        redirect_uri = request.url_root.rstrip("/") + "/auth/callback"
    body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    )
    try:
        req = urllib.request.Request(
            token_url,
            data=body.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        return (data.get("access_token") or data.get("accessToken") or "").strip() or None
    except (urllib.error.URLError, json.JSONDecodeError, OSError, ValueError):
        return None


def session_has_full_access() -> bool:
    perms = session.get("hub_permissions")
    if not perms:
        return True
    return "applyfy.admin" in perms


APPLYFY_PERM_COMERCIAL = "applyfy.comercial"
APPLYFY_PERM_COMERCIAL_GERENTE = "applyfy.comercial.gerente"


def session_can_edit_carteira_comercial() -> bool:
    """Gerente comercial ou admin Applyfy podem alterar atribuições vendedor → produtor."""
    if not auth_enabled():
        return True
    return session_has_full_access() or session_has_permission(APPLYFY_PERM_COMERCIAL_GERENTE)


def session_is_somente_vendedor_comercial() -> bool:
    """Vendedor comercial (vê só a própria carteira), sem gerente nem admin."""
    if not auth_enabled():
        return False
    if session_has_full_access():
        return False
    if session_has_permission(APPLYFY_PERM_COMERCIAL_GERENTE):
        return False
    return session_has_permission(APPLYFY_PERM_COMERCIAL)


def session_has_permission(*required: str) -> bool:
    if not auth_enabled():
        return True
    if not session.get("hub_authenticated"):
        return False
    if session_has_full_access():
        return True
    have = set(session.get("hub_permissions") or [])
    if not have:
        return True
    return any(r in have for r in required)


def hub_uses_granular_screens() -> bool:
    """JWT trouxe applyfy_screens — o gate por ecrã substitui a verificação coarse por path."""
    return "hub_allowed_screens" in session


def session_can_access_path(path: str) -> bool:
    """Quando hub_allowed_screens está na sessão, verifica se o path (HTML ou API) está coberto."""
    if not auth_enabled():
        return True
    if not session.get("hub_authenticated"):
        return False
    if session_has_full_access():
        return True
    perms = session.get("hub_permissions") or []
    if path.startswith("/api/admin"):
        return "applyfy.admin" in perms
    if path.startswith("/api/hub/applyfy-screen-grants"):
        return "applyfy.admin" in perms
    if path.startswith("/api/hub/applyfy-commercial-users"):
        return "applyfy.admin" in perms or APPLYFY_PERM_COMERCIAL_GERENTE in perms
    if path.startswith("/api/hub/applyfy-user-commercial-config") or path.startswith(
        "/api/hub/applyfy_user_commercial_config"
    ):
        return "applyfy.admin" in perms
    if normalize_applyfy_path(path) == "/permissoes":
        return True
    if normalize_applyfy_path(path) == "/config-comercial":
        return "applyfy.admin" in perms
    if "hub_allowed_screens" not in session:
        return True
    allowed = set(session.get("hub_allowed_screens") or [])
    ap = normalize_applyfy_path(path)
    # Mesma API que listagem de produtores — ecrãs Saldo / Taxas também.
    if ap.startswith("/api/gateway/producer"):
        if "/produtores" in allowed or "/saldo" in allowed or "/taxas" in allowed:
            return True
    sid = path_to_screen_id(path)
    if sid is None:
        return False
    return sid in allowed


def require_hub_permission(*permissions: str):
    """Exige pelo menos uma das permissões (ou applyfy.admin / lista vazia no JWT = tudo)."""

    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not auth_enabled():
                return fn(*args, **kwargs)
            if not session.get("hub_authenticated"):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "unauthorized", "message": "Sessão necessária"}), 401
                return redirect(hub_login_url(request.path))
            if not session_has_permission(*permissions):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "forbidden", "message": "Permissão insuficiente"}), 403
                return redirect(hub_login_url(request.path))
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def apply_access_token(token: str) -> bool:
    payload = _decode_jwt(token)
    if not payload:
        return False
    if not jwt_project_allowed(payload):
        return False
    payload_to_session(payload)
    return True


def required_permissions_for_path(path: str) -> tuple[str, ...] | None:
    """
    Permissões necessárias para o path; None = só autenticação (ou rotas admin tratadas no handler).
    """
    if is_public_path(path):
        return None
    if path.startswith("/api/"):
        if path.startswith("/api/integracao-status"):
            return None
        if path.startswith("/api/financeiro"):
            return ("applyfy.financeiro",)
        if path.startswith("/api/job-vendas") or path.startswith("/api/job"):
            return ("applyfy.jobs",)
        if path.startswith("/api/hub/applyfy-screen-grants"):
            return ("applyfy.admin",)
        if path.startswith("/api/hub/applyfy-commercial-users"):
            return ("applyfy.admin", APPLYFY_PERM_COMERCIAL_GERENTE)
        if path.startswith("/api/hub/applyfy-user-commercial-config") or path.startswith(
            "/api/hub/applyfy_user_commercial_config"
        ):
            return ("applyfy.admin",)
        if path.startswith("/api/admin"):
            return None
        return ("applyfy.painel",)
    p = path.rstrip("/") or "/"
    if p in ("/financeiro",) or path.startswith("/financeiro/"):
        return ("applyfy.financeiro",)
    if p in ("/integracoes",):
        return ("applyfy.jobs",)
    if path in (
        "/health",
        "/favicon.ico",
        "/sw.js",
        "/auth/callback",
        "/auth/logout",
    ):
        return None
    if path.startswith("/auth/"):
        return None
    if path.startswith("/static/"):
        return None
    if normalize_applyfy_path(path) == "/config-comercial":
        return ("applyfy.admin",)
    return ("applyfy.painel",)


def hub_me_payload() -> dict[str, Any]:
    if not auth_enabled():
        return {"auth_enabled": False, "nav": {h: True for h in NAV_PERMISSIONS}}
    if not session.get("hub_authenticated"):
        return {"auth_enabled": True, "authenticated": False, "nav": {}}
    perms = list(session.get("hub_permissions") or [])
    if hub_uses_granular_screens():
        allowed = set(session.get("hub_allowed_screens") or [])
        nav = {}
        for href in NAV_PERMISSIONS.keys():
            if href == "/permissoes":
                nav[href] = True
            else:
                nav[href] = href in allowed
    else:
        nav = {href: session_has_permission(perm) for href, perm in NAV_PERMISSIONS.items()}
    out: dict[str, Any] = {
        "auth_enabled": True,
        "authenticated": True,
        "hub_logout_url": hub_logout_url(),
        "user": {
            "sub": session.get("hub_sub"),
            "project_id": session.get("hub_project_id"),
            "hub_role": session.get("hub_role"),
            "email": session.get("hub_user_email"),
            "name": session.get("hub_user_name"),
        },
        "permissions": perms,
        "nav": nav,
        "applyfy_granular": hub_uses_granular_screens(),
        "can_edit_carteira_comercial": session_can_edit_carteira_comercial(),
        "is_somente_vendedor_comercial": session_is_somente_vendedor_comercial(),
    }
    if hub_uses_granular_screens():
        out["applyfy_screens"] = list(session.get("hub_allowed_screens") or [])
    return out


# Mapa href do menu -> permissão necessária (painel-shell.js)
NAV_PERMISSIONS: dict[str, str] = {
    "/": "applyfy.painel",
    "/historico": "applyfy.painel",
    "/evolucao": "applyfy.painel",
    "/transacoes": "applyfy.painel",
    "/integracoes": "applyfy.jobs",
    "/meta": "applyfy.painel",
    "/comercial": "applyfy.painel",
    "/produtores": "applyfy.painel",
    "/saldo": "applyfy.painel",
    "/taxas": "applyfy.painel",
    "/financeiro": "applyfy.financeiro",
    "/log": "applyfy.painel",
    "/permissoes": "applyfy.painel",
}
