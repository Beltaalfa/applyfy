# -*- coding: utf-8 -*-
"""
Cliente da API Admin ApplyFy (taxas e detalhes do produtor).
Base: https://app.applyfy.com.br/api/v1/gateway/admin
Autenticação: headers x-public-key e x-secret-key.
"""
import os
import urllib.request
import urllib.error
import json

BASE_URL = os.environ.get("APPLYFY_API_BASE", "https://app.applyfy.com.br/api/v1/gateway/admin")
PUBLIC_KEY = os.environ.get("APPLYFY_PUBLIC_KEY", "")
SECRET_KEY = os.environ.get("APPLYFY_SECRET_KEY", "")
TIMEOUT = int(os.environ.get("APPLYFY_API_TIMEOUT", "10"))
TIMEOUT_LIST = int(os.environ.get("APPLYFY_API_TIMEOUT_LIST", "30"))

# Chaves permitidas (query) — alinhado com a documentação API Admin
_TRANSACTION_QUERY_KEYS = frozenset(
    {
        "page",
        "pageSize",
        "transactionId",
        "orderOrTransactionId",
        "acquirerExternalId",
        "clientEmail",
        "clientDocument",
        "producerEmail",
        "paymentMethod",
        "acquirer",
        "status",
        "subStatus",
        "period",
        "start",
        "end",
    }
)
_PRODUCERS_QUERY_KEYS = frozenset(
    {
        "page",
        "pageSize",
        "nameOrEmail",
        "phone",
        "status",
        "kycStatus",
        "bankDataStatus",
        "minDocumentsSent",
        "accountType",
        "tags",
    }
)
_PRODUCER_BY_EMAIL_KEYS = frozenset(
    {
        "email",
        "includeKyc",
        "includePayoutAccount",
        "includeTaxes",
        "includeDocuments",
    }
)
# Cloudflare pode bloquear requests sem User-Agent de browser (Error 1010).
_DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-public-key": PUBLIC_KEY or "",
        "x-secret-key": SECRET_KEY or "",
        "User-Agent": (os.environ.get("APPLYFY_API_USER_AGENT") or "").strip() or _DEFAULT_UA,
    }


def _filter_query(allowed: frozenset, raw: dict) -> dict:
    """Só inclui chaves permitidas; valores None são omitidos."""
    out = {}
    for k in allowed:
        if k not in raw:
            continue
        v = raw[k]
        if v is None or v == "":
            continue
        out[k] = v
    return out


def _request(method, path, data=None, query_params=None, timeout_sec=None):
    if not PUBLIC_KEY or not SECRET_KEY:
        return None, {"message": "APPLYFY_PUBLIC_KEY e APPLYFY_SECRET_KEY não configurados"}
    to = timeout_sec if timeout_sec is not None else TIMEOUT
    url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    if query_params:
        from urllib.parse import urlencode
        q = {k: "true" if v is True else ("false" if v is False else v) for k, v in query_params.items() if v is not None}
        if q:
            url += "?" + urlencode(q)
    try:
        req = urllib.request.Request(url, method=method, headers=_headers())
        if data and method in ("POST", "PUT", "PATCH"):
            req.data = json.dumps(data).encode("utf-8")
        with urllib.request.urlopen(req, timeout=to) as resp:
            body = resp.read().decode("utf-8")
            return (json.loads(body) if body else {}, None)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
            err = json.loads(body) if body else {}
        except Exception:
            err = {}
        if not isinstance(err, dict):
            err = {"message": str(e)}
        err.setdefault("message", str(e))
        err.setdefault("statusCode", e.code)
        if e.code == 403:
            api_msg = (err.get("error") or {}).get("message") if isinstance(err.get("error"), dict) else None
            if api_msg:
                err["message"] = api_msg
            else:
                err["message"] = "403: Produtor não pertence a esta empresa (webhook e API devem usar a mesma conta ApplyFy)"
        return None, err
    except (TimeoutError, OSError) as e:
        if "timed out" in str(e).lower() or getattr(e, "errno", None) == 110:
            return None, {"message": "Timeout ao contactar API ApplyFy. Tente de novo."}
        return None, {"message": str(e)}
    except Exception as e:
        return None, {"message": str(e)}


def get_producer(producer_id, include_taxes=False, include_kyc=False, include_payout_account=False, include_documents=False):
    """
    GET /producer/{producerId}
    Documentação: includeKyc, includePayoutAccount, includeTaxes, includeDocuments.
    Resposta: { "success": true, "data": { id, name, email, ... } } ou { "success": false, "error": { message } }.
    Retorna (dict_response_completo, None) em sucesso ou (None, dict_error).
    """
    if not producer_id:
        return None, {"message": "producer_id obrigatório"}
    path = f"producer/{producer_id}"
    params = {}
    if include_taxes:
        params["includeTaxes"] = True
    if include_kyc:
        params["includeKyc"] = True
    if include_payout_account:
        params["includePayoutAccount"] = True
    if include_documents:
        params["includeDocuments"] = True
    res, err = _request("GET", path, query_params=params or None)
    if err:
        return None, err
    if res.get("success") is False and res.get("error"):
        return None, res.get("error", res)
    return res, None


def _normalize_pagination(params: dict) -> dict:
    """Garante page >= 1 e pageSize entre 5 e 50 (limites da API)."""
    out = dict(params)
    try:
        p = int(out.get("page", 1) or 1)
        out["page"] = max(1, p)
    except (TypeError, ValueError):
        out["page"] = 1
    try:
        ps = int(out.get("pageSize", 20) or 20)
        out["pageSize"] = min(50, max(5, ps))
    except (TypeError, ValueError):
        out["pageSize"] = 20
    return out


def list_transactions(raw_params: dict):
    """
    GET /transactions — listagem paginada e filtros (documentação API Admin).
    raw_params: dict com chaves camelCase; apenas _TRANSACTION_QUERY_KEYS são enviadas.
    """
    q = _filter_query(_TRANSACTION_QUERY_KEYS, raw_params)
    q = _normalize_pagination(q)
    res, err = _request("GET", "transactions", query_params=q, timeout_sec=TIMEOUT_LIST)
    if err:
        return None, err
    if res.get("success") is False and res.get("error"):
        return None, res.get("error", res)
    return res, None


def list_producers(raw_params: dict):
    """GET /producers — listagem paginada de produtores."""
    q = _filter_query(_PRODUCERS_QUERY_KEYS, raw_params)
    q = _normalize_pagination(q)
    res, err = _request("GET", "producers", query_params=q, timeout_sec=TIMEOUT_LIST)
    if err:
        return None, err
    if res.get("success") is False and res.get("error"):
        return None, res.get("error", res)
    return res, None


def get_producer_by_email(
    email: str,
    include_kyc=False,
    include_payout_account=False,
    include_taxes=False,
    include_documents=False,
):
    """GET /producer?email=..."""
    em = (email or "").strip()
    if not em:
        return None, {"message": "email obrigatório"}
    params: dict = {"email": em}
    if include_kyc:
        params["includeKyc"] = True
    if include_payout_account:
        params["includePayoutAccount"] = True
    if include_taxes:
        params["includeTaxes"] = True
    if include_documents:
        params["includeDocuments"] = True
    res, err = _request("GET", "producer", query_params=params, timeout_sec=TIMEOUT_LIST)
    if err:
        return None, err
    if res.get("success") is False and res.get("error"):
        return None, res.get("error", res)
    return res, None


def fetch_and_save_producer_taxes(producer_id, email=None):
    """
    Chama get_producer(include_taxes=True), extrai taxas de data.taxes e persiste.
    Resposta da API: { success, data: { id, name, taxes?: {... } } }.
    """
    import db
    res, err = get_producer(producer_id, include_taxes=True)
    if err:
        return None, err
    data = res.get("data") if res.get("success") else res
    data = data or {}
    taxes = data.get("taxes") or {}
    if isinstance(taxes, list):
        taxes = {"items": taxes}
    snapshot = {"raw": res, "data": data, "taxes": taxes} if taxes else {"raw": res, "data": data}
    if db.DATABASE_URL:
        db.save_producer_taxes(producer_id, email, snapshot)
    return snapshot, None


def offer_codes_from_producer_response(producer_response):
    """
    Extrai offer codes da resposta GET /producer/{id}.
    A documentação atual não mostra offerCode em data; procura em data, data.offers, etc.
    """
    if not producer_response or not isinstance(producer_response, dict):
        return []
    data = producer_response.get("data") if producer_response.get("success") else producer_response
    data = data or producer_response
    codes = []
    single = data.get("offerCode") or data.get("offer_code") or data.get("code")
    if single:
        codes.append(str(single).strip())
    for offer in data.get("offers") or []:
        if isinstance(offer, dict):
            c = offer.get("code") or offer.get("offerCode") or offer.get("offer_code")
            if c:
                codes.append(str(c).strip())
    return list(dict.fromkeys(codes))
