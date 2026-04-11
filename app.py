# -*- coding: utf-8 -*-
"""
API Flask do painel Applyfy: último relatório (JSON) e download XLSX/CSV.
"""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

import pandas as pd
from flask import Flask, Response, g, redirect, request, session, jsonify, send_file, send_from_directory
from dotenv import load_dotenv

import config
import db
import waha_client
from applyfy_repository import list_applyfy_vendas_import_log

import auth_hub

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

if auth_hub.auth_enabled() and not (
    (os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY") or "").strip()
):
    raise RuntimeError(
        "APPLYFY_AUTH_ENABLED=1 exige FLASK_SECRET_KEY (ou SECRET_KEY) definido e estável no .env. "
        'Gere um valor: python3 -c "import secrets; print(secrets.token_hex(32))"'
    )

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["JSON_AS_ASCII"] = False
_mb = (os.environ.get("APPLYFY_MAX_UPLOAD_MB") or "35").strip() or "35"
app.config["MAX_CONTENT_LENGTH"] = int(_mb) * 1024 * 1024
app.secret_key = (os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY") or "").strip() or os.urandom(32).hex()
_sc = (os.environ.get("SESSION_COOKIE_SECURE") or "").strip().lower() in ("1", "true", "yes", "on")
app.config["SESSION_COOKIE_SECURE"] = _sc
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = (os.environ.get("SESSION_COOKIE_SAMESITE") or "Lax").strip() or "Lax"

if (os.environ.get("APPLYFY_TRUST_PROXY") or os.environ.get("TRUST_PROXY") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
):
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


@app.before_request
def _hub_auth_gate():
    if not auth_hub.auth_enabled():
        return None
    path = request.path
    if not (os.environ.get("HUB_LOGIN_URL") or "").strip():
        if path.startswith("/api/"):
            return jsonify({"error": "HUB_LOGIN_URL não configurado (obrigatório com APPLYFY_AUTH_ENABLED)."}), 503
        return (
            "<p>Configure <code>HUB_LOGIN_URL</code> no servidor (com <code>APPLYFY_AUTH_ENABLED=1</code>).</p>",
            503,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    if auth_hub.is_public_path(path):
        return None
    if not auth_hub.try_cookie_jwt(request):
        if getattr(g, "hub_auth_reject", None) == "project":
            msg = "Sem acesso a este painel Applyfy para a empresa/projeto da sua sessão."
            if path.startswith("/api/"):
                return jsonify({"error": "forbidden", "message": msg}), 403
            return Response(
                f"<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><title>Acesso negado</title></head>"
                f"<body style=\"font-family:sans-serif;max-width:32rem;margin:3rem auto;padding:1rem;\">"
                f"<h1>Acesso negado</h1><p>{msg}</p>"
                f"<p><a href=\"{auth_hub.hub_logout_url()}\">Voltar ao Hub</a></p></body></html>",
                403,
                mimetype="text/html; charset=utf-8",
            )
        if path.startswith("/api/"):
            return jsonify(
                {"error": "unauthorized", "message": "Sessão ou cookie JWT do hub necessário"}
            ), 401
        return redirect(auth_hub.hub_login_url(auth_hub.effective_return_url()))
    if auth_hub.hub_uses_granular_screens():
        if not auth_hub.session_can_access_path(path):
            if path.startswith("/api/"):
                return jsonify({"error": "forbidden", "message": "Sem acesso a este recurso (ecrã não autorizado)"}), 403
            return Response(
                "<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><title>Acesso negado</title></head>"
                "<body style=\"font-family:sans-serif;max-width:32rem;margin:3rem auto;padding:1rem;\">"
                "<h1>Acesso negado</h1><p>Sem permissão para este ecrã.</p>"
                f"<p><a href=\"{auth_hub.hub_logout_url()}\">Voltar ao Hub</a></p></body></html>",
                403,
                mimetype="text/html; charset=utf-8",
            )
    else:
        needed = auth_hub.required_permissions_for_path(path)
        if needed and not auth_hub.session_has_permission(*needed):
            if path.startswith("/api/"):
                return jsonify({"error": "forbidden", "message": "Permissão insuficiente para este recurso"}), 403
            return redirect(auth_hub.hub_login_url(auth_hub.effective_return_url()))
    return None


@app.route("/auth/callback")
def hub_auth_callback():
    next_raw = auth_hub.redirect_target_from_request_args(request)
    target = auth_hub.sanitize_redirect_target(next_raw)
    code = (request.args.get("code") or "").strip()
    if code:
        token = auth_hub.exchange_code_for_token(code)
        if token and auth_hub.apply_access_token(token):
            return redirect(target)
    if auth_hub.try_cookie_jwt(request):
        return redirect(target)
    return redirect(auth_hub.hub_login_url(auth_hub.effective_return_url()))


@app.route("/auth/logout")
def hub_auth_logout():
    # #region agent log
    try:
        import json
        import time as _time

        with open("/var/www/.cursor/debug-422278.log", "a", encoding="utf-8") as _df:
            _df.write(
                json.dumps(
                    {
                        "sessionId": "422278",
                        "location": "app.py:hub_auth_logout",
                        "message": "flask_logout_hit",
                        "data": {"path": request.path},
                        "timestamp": int(_time.time() * 1000),
                        "hypothesisId": "H4",
                        "runId": "pre-fix",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    auth_hub.clear_hub_session()
    dest = auth_hub.hub_logout_url()
    # #region agent log
    try:
        import json
        import time as _time
        from urllib.parse import urlparse as _urlparse

        _p = _urlparse(dest) if dest else None
        with open("/var/www/.cursor/debug-422278.log", "a", encoding="utf-8") as _df:
            _df.write(
                json.dumps(
                    {
                        "sessionId": "422278",
                        "location": "app.py:hub_auth_logout_redirect",
                        "message": "redirect_after_clear",
                        "data": {
                            "dest_netloc": _p.netloc if _p else "",
                            "dest_path": _p.path if _p else "",
                        },
                        "timestamp": int(_time.time() * 1000),
                        "hypothesisId": "H5",
                        "runId": "post-env-fix",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    return redirect(dest)


@app.route("/api/_debug/client-log", methods=["POST"])
def agent_client_debug_log():
    """Debug session: browser envia NDJSON para o ficheiro do agent (sem PII)."""
    # #region agent log
    import json as _json
    import time as _time

    try:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("timestamp", int(_time.time() * 1000))
        with open("/var/www/.cursor/debug-422278.log", "a", encoding="utf-8") as _f:
            _f.write(_json.dumps(payload) + "\n")
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"ok": False}), 500
    # #endregion


@app.route("/api/me")
def api_me():
    return jsonify(auth_hub.hub_me_payload())


def _hub_public_hostname() -> str:
    """Hostname público do Hub (NextAuth associa cookies a este host)."""
    raw = (os.environ.get("HUB_INTERNAL_HOST") or "").strip()
    if raw:
        return raw.split("/")[0].split(":")[0]
    login = (os.environ.get("HUB_LOGIN_URL") or "").strip()
    if login:
        try:
            from urllib.parse import urlparse

            h = urlparse(login if "://" in login else f"https://{login}").hostname
            if h:
                return h
        except Exception:
            pass
    return "hub.northempresarial.com"


def _hub_internal_http_request(rel_path: str, method: str = "GET", body: bytes | None = None) -> tuple[int, bytes]:
    """HTTP ao Hub interno com Host público (NextAuth). rel_path ex.: /api/applyfy/commercial-users"""
    import http.client
    from urllib.parse import urlparse

    base = (os.environ.get("HUB_INTERNAL_URL") or "http://127.0.0.1:3007").rstrip("/")
    parsed = urlparse(base)
    conn_host = parsed.hostname or "127.0.0.1"
    scheme = (parsed.scheme or "http").lower()
    conn_port = parsed.port or (443 if scheme == "https" else 80)
    cookie = request.headers.get("Cookie") or ""
    public_host = _hub_public_hostname()
    _xf = (request.headers.get("X-Forwarded-Proto") or "https").split(",")[0].strip().lower()
    xf_proto = _xf if _xf in ("http", "https") else "https"
    headers = {
        "Host": public_host,
        "Cookie": cookie,
        "Accept": "application/json",
        "X-Forwarded-Host": public_host,
        "X-Forwarded-Proto": xf_proto,
        "X-Forwarded-For": request.headers.get("X-Forwarded-For") or (request.remote_addr or "127.0.0.1"),
    }
    if body is not None:
        headers["Content-Type"] = request.headers.get("Content-Type") or "application/json"
    path = rel_path if rel_path.startswith("/") else "/" + rel_path
    try:
        if scheme == "https":
            conn = http.client.HTTPSConnection(conn_host, conn_port, timeout=90)
        else:
            conn = http.client.HTTPConnection(conn_host, conn_port, timeout=90)
        conn.request(method.upper(), path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        status = resp.status
        conn.close()
        return status, data
    except Exception:
        return 0, b""


def _carteira_assign_visible(rec: dict, sub: str | None, name_lower: str) -> bool:
    vid = rec.get("vendedor_user_id")
    vnom = (rec.get("vendedor_nome") or "").strip().lower()
    if vid and sub and vid == sub:
        return True
    if not vid and name_lower and vnom == name_lower:
        return True
    return False


def _filter_relatorio_vendedor_comercial(resultados: list) -> list:
    if not resultados:
        return []
    sub = session.get("hub_sub")
    name_lower = (session.get("hub_user_name") or "").strip().lower()
    items = db.list_producer_vendedor()
    by_email: dict[str, dict] = {}
    for i in items:
        k = db._normalize_producer_email(i.get("producer_email"))
        if k:
            by_email[k] = i
    out = []
    for row in resultados:
        if not isinstance(row, dict):
            continue
        em = db._normalize_producer_email(row.get("Email"))
        if not em:
            continue
        rec = by_email.get(em)
        if not rec or not _carteira_assign_visible(rec, sub, name_lower):
            continue
        out.append(row)
    return out


def _hub_commercial_user_ids_allowed() -> set[str] | None:
    st, raw = _hub_internal_http_request("/api/applyfy/commercial-users")
    if st != 200 or not raw:
        return None
    try:
        j = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    users = j.get("users") or []
    return {str(u["id"]) for u in users if isinstance(u, dict) and u.get("id")}


@app.route("/api/hub/applyfy-screen-grants", methods=["GET", "PUT"])
def api_hub_applyfy_screen_grants_proxy():
    """
    Proxy para o Hub (Next.js) /api/admin/applyfy-screens.
    Reenvia Cookie e usa Host público do Hub — pedidos só a 127.0.0.1 com Host=hub.*
    quebram a sessão NextAuth.
    """
    import http.client
    from urllib.parse import urlparse

    base = (os.environ.get("HUB_INTERNAL_URL") or "http://127.0.0.1:3007").rstrip("/")
    parsed = urlparse(base)
    conn_host = parsed.hostname or "127.0.0.1"
    scheme = (parsed.scheme or "http").lower()
    if scheme == "https":
        conn_port = parsed.port or 443
    else:
        conn_port = parsed.port or 80
    path = "/api/admin/applyfy-screens"
    cookie = request.headers.get("Cookie") or ""
    public_host = _hub_public_hostname()
    _xf = (request.headers.get("X-Forwarded-Proto") or "https").split(",")[0].strip().lower()
    xf_proto = _xf if _xf in ("http", "https") else "https"

    headers = {
        "Host": public_host,
        "Cookie": cookie,
        "Accept": "application/json",
        "X-Forwarded-Host": public_host,
        "X-Forwarded-Proto": xf_proto,
        "X-Forwarded-For": request.headers.get("X-Forwarded-For") or (request.remote_addr or "127.0.0.1"),
    }

    try:
        body = None
        method = request.method.upper()
        if method == "PUT":
            body = request.get_data()
            headers["Content-Type"] = request.headers.get("Content-Type") or "application/json"

        if scheme == "https":
            conn = http.client.HTTPSConnection(conn_host, conn_port, timeout=90)
        else:
            conn = http.client.HTTPConnection(conn_host, conn_port, timeout=90)

        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        ct = resp.getheader("Content-Type") or "application/json"
        mimetype = (ct.split(";")[0] or "application/json").strip()
        status = resp.status
        conn.close()
        return Response(data, status=status, mimetype=mimetype)
    except Exception as ex:  # noqa: BLE001
        app.logger.exception("api_hub_applyfy_screen_grants_proxy")
        return jsonify({"error": "proxy_hub", "message": str(ex)[:300]}), 502


@app.route("/api/hub/applyfy-commercial-users", methods=["GET"])
def api_hub_applyfy_commercial_users_proxy():
    """Proxy para Hub GET /api/applyfy/commercial-users (dropdown vendedores)."""
    st, data = _hub_internal_http_request("/api/applyfy/commercial-users")
    if st == 0:
        app.logger.exception("api_hub_applyfy_commercial_users_proxy")
        return jsonify({"error": "proxy_hub"}), 502
    return Response(data, status=st, mimetype="application/json")


@app.route("/api/hub/applyfy-user-commercial-config", methods=["GET", "PUT"])
@app.route("/api/hub/applyfy_user_commercial_config", methods=["GET", "PUT"])
def api_hub_applyfy_user_commercial_config_proxy():
    """Proxy para Hub /api/applyfy/user-commercial-config (flags comercial / gerente no Hub DB)."""
    method = request.method.upper()
    body = request.get_data() if method == "PUT" else None
    st, data = _hub_internal_http_request("/api/applyfy/user-commercial-config", method, body)
    if st == 0:
        app.logger.exception("api_hub_applyfy_user_commercial_config_proxy")
        return jsonify({"error": "proxy_hub"}), 502
    return Response(data, status=st, mimetype="application/json")


def _persist_applyfy_webhook(payload: dict, request_id_header: str = "") -> tuple[str, str | None]:
    """
    Extrai ids do payload Applyfy, insere em applyfy_transactions e mapeia offers em PRODUCER_CREATED.
    Retorna o mesmo par que insert_webhook_transaction: inserted|duplicate|no_db|error.
    """
    event = payload.get("event")
    if not event:
        return "error", "Missing event"
    offer_code = payload.get("offerCode") or payload.get("offer_code")
    producer_id = None
    if event == "PRODUCER_CREATED":
        producer = payload.get("producer") or {}
        transaction_id = producer.get("id") or f"producer-{event}"
        producer_id = producer.get("id")
    else:
        trans = payload.get("transaction") or {}
        transaction_id = trans.get("id") or f"tx-{event}-{request_id_header}"
        producer_id = payload.get("producerId") or payload.get("producer_id")
    status, ins_err = db.insert_webhook_transaction(
        transaction_id=transaction_id or f"evt-{event}",
        event=event,
        offer_code=offer_code,
        producer_id=producer_id,
        payload=payload,
    )
    if status == "inserted" and event == "PRODUCER_CREATED" and producer_id:
        try:
            import applyfy_api

            producer = payload.get("producer") or {}
            producer_name = producer.get("name")
            res, err = applyfy_api.get_producer(producer_id)
            if not err and res:
                for code in applyfy_api.offer_codes_from_producer_response(res):
                    if code:
                        db.save_offer_producer(code, producer_id, producer_name)
        except Exception as e:
            app.logger.warning("Offer-producer mapping failed: %s", str(e))
    return status, ins_err


def _get_ultimo_dados():
    """Último relatório: primeiro export_runs (rápido), depois saldos_historico só se mais recente ou vazio, depois CSV."""
    try:
        run_at_export, resultados = db.get_last_export_data()
        run_at = run_at_export
        if resultados and db.DATABASE_URL:
            datas = db.get_datas_disponiveis()
            if datas:
                latest_hist = datas[0][0]
                try:
                    if latest_hist and (run_at is None or latest_hist > run_at):
                        res_hist = db.get_relatorio_por_data(latest_hist)
                        if res_hist:
                            run_at, resultados = latest_hist, res_hist
                except (TypeError, ValueError):
                    pass
        if resultados:
            run_at_str = run_at.isoformat() if hasattr(run_at, "isoformat") else str(run_at)
            return resultados, run_at_str
    except Exception:
        resultados, run_at = [], None
    if not resultados and db.DATABASE_URL:
        try:
            datas = db.get_datas_disponiveis()
            if datas:
                run_at = datas[0][0]
                resultados = db.get_relatorio_por_data(run_at)
                if resultados:
                    run_at_str = run_at.isoformat() if hasattr(run_at, "isoformat") else str(run_at)
                    return resultados, run_at_str
        except Exception:
            pass
    csv_path = config.OUT_CSV
    if os.path.isfile(csv_path):
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")
        resultados = df.to_dict(orient="records")
        try:
            mtime = os.path.getmtime(csv_path)
            run_at_str = datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            run_at_str = None
        return resultados, run_at_str
    return [], None


def _admin_token_ok() -> bool:
    expected = os.environ.get("APPLYFY_ADMIN_TOKEN", "").strip()
    if not expected:
        return False
    if request.headers.get("X-Applyfy-Admin-Token", "").strip() == expected:
        return True
    body = request.get_json(silent=True) or {}
    if isinstance(body, dict) and (body.get("token") or "").strip() == expected:
        return True
    q = (request.args.get("token") or "").strip()
    return q == expected


def _admin_or_hub_ok() -> bool:
    if _admin_token_ok():
        return True
    if auth_hub.auth_enabled() and auth_hub.session_has_permission("applyfy.admin"):
        return True
    return False


@app.route("/api/admin/waha-test", methods=["POST"])
def api_admin_waha_test():
    """Teste WAHA; requer APPLYFY_ADMIN_TOKEN no header X-Applyfy-Admin-Token ou JSON/query token."""
    if not os.environ.get("APPLYFY_ADMIN_TOKEN", "").strip() and not auth_hub.auth_enabled():
        return jsonify({"ok": False, "error": "APPLYFY_ADMIN_TOKEN não configurado no servidor."}), 503
    if not _admin_or_hub_ok():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    ok, err = waha_client.send_text("Applyfy: teste WAHA (painel / API admin)")
    if ok:
        return jsonify({"ok": True, "message": "Mensagem enviada."})
    return jsonify({"ok": False, "error": err}), 502


@app.route("/api/settings")
def api_settings():
    """Configuração pública de leitura para o painel (meta de vendas)."""
    return jsonify(
        {
            "meta_vendas_liquidas": config.get_meta_vendas_liquidas(),
        }
    )


@app.route("/api/health")
def api_health():
    """Liveness: disco gravável e Postgres (se DATABASE_URL existir)."""
    db_url = db.get_database_url()
    postgres_ok = False
    if db_url:
        try:
            db.init_db()
            with db.cursor() as cur:
                cur.execute("SELECT 1")
            postgres_ok = True
        except Exception:
            postgres_ok = False
    data_ok = False
    try:
        config.ensure_data_dir()
        probe = os.path.join(config.DATA_DIR, ".health_probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        data_ok = True
    except Exception:
        data_ok = False
    overall = data_ok and (not db_url or postgres_ok)
    return jsonify(
        {
            "ok": overall,
            "postgres": postgres_ok,
            "data_dir_writable": data_ok,
            "database_configured": bool(db_url),
        }
    ), (200 if overall else 503)


@app.route("/api/integracao-status")
def api_integracao_status():
    """Resumo para o painel: últimos timestamps e fila DLQ (sem segredos)."""
    out = {
        "last_export_run_at": None,
        "last_webhook_received_at": None,
        "export_stale": False,
        "webhook_silent": False,
        "dlq_pending_count": 0,
        "meta_vendas_liquidas": config.get_meta_vendas_liquidas(),
    }
    try:
        stale_hours = int((os.environ.get("APPLYFY_EXPORT_STALE_HOURS") or "48").strip() or "48")
    except ValueError:
        stale_hours = 48
    try:
        silence_hours = int((os.environ.get("APPLYFY_WEBHOOK_SILENCE_HOURS") or "24").strip() or "24")
    except ValueError:
        silence_hours = 24
    now = datetime.now(timezone.utc)
    try:
        le = db.get_last_export_run_at()
        if le is not None:
            out["last_export_run_at"] = le.isoformat() if hasattr(le, "isoformat") else str(le)
            if stale_hours > 0:
                le_aware = le if getattr(le, "tzinfo", None) else le.replace(tzinfo=timezone.utc)
                out["export_stale"] = (now - le_aware) > timedelta(hours=stale_hours)
        lw = db.get_last_webhook_received_at()
        if lw is not None:
            out["last_webhook_received_at"] = lw.isoformat() if hasattr(lw, "isoformat") else str(lw)
            if silence_hours > 0:
                lw_aware = lw if getattr(lw, "tzinfo", None) else lw.replace(tzinfo=timezone.utc)
                out["webhook_silent"] = (now - lw_aware) > timedelta(hours=silence_hours)
        out["dlq_pending_count"] = db.count_webhook_dlq_pending()
    except Exception as e:
        out["error"] = str(e)[:200]
    return jsonify(out)


@app.route("/api/admin/webhook-dlq", methods=["GET"])
def api_admin_webhook_dlq():
    if not os.environ.get("APPLYFY_ADMIN_TOKEN", "").strip() and not auth_hub.auth_enabled():
        return jsonify({"error": "APPLYFY_ADMIN_TOKEN não configurado."}), 503
    if not _admin_or_hub_ok():
        return jsonify({"error": "Unauthorized"}), 401
    limit = request.args.get("limit", 50, type=int) or 50
    return jsonify({"items": db.list_webhook_dlq_pending(limit=min(limit, 200))})


@app.route("/api/admin/webhook-dlq/retry", methods=["POST"])
def api_admin_webhook_dlq_retry():
    if not os.environ.get("APPLYFY_ADMIN_TOKEN", "").strip() and not auth_hub.auth_enabled():
        return jsonify({"error": "APPLYFY_ADMIN_TOKEN não configurado."}), 503
    if not _admin_or_hub_ok():
        return jsonify({"error": "Unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    dlq_id = body.get("id")
    if dlq_id is None:
        return jsonify({"error": "Informe id (corpo JSON)."}), 400
    row = db.get_webhook_dlq_row(dlq_id)
    if not row:
        return jsonify({"error": "DLQ id não encontrado."}), 404
    if row.get("processed_at"):
        return jsonify({"error": "Já processado."}), 400
    payload = row.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    status, ins_err = _persist_applyfy_webhook(payload, f"dlq-retry-{dlq_id}")
    if status in ("inserted", "duplicate"):
        db.mark_webhook_dlq_processed(dlq_id)
        return jsonify({"ok": True, "status": status})
    db.increment_webhook_dlq_retry(dlq_id)
    return jsonify({"ok": False, "status": status, "error": ins_err or "unknown"}), 502


@app.route("/api/ultimo-relatorio")
def api_ultimo_relatorio():
    dados, run_at = _get_ultimo_dados()
    if dados is None:
        dados = []
    if auth_hub.auth_enabled() and auth_hub.session_is_somente_vendedor_comercial():
        dados = _filter_relatorio_vendedor_comercial(dados)
    return jsonify({"run_at": run_at, "resultados": dados, "total": len(dados)})


@app.route("/api/exportar")
def api_exportar():
    if auth_hub.auth_enabled() and auth_hub.session_is_somente_vendedor_comercial():
        return jsonify({"error": "Exportação indisponível para o seu perfil"}), 403
    fmt = (request.args.get("formato") or "csv").lower()
    run_at_str = request.args.get("run_at")
    if run_at_str and db.DATABASE_URL:
        try:
            resultados = db.get_relatorio_por_data(run_at_str)
            if not resultados:
                return jsonify({"error": "Nenhum dado para esta data."}), 404
            df = pd.DataFrame(resultados)
            from io import BytesIO
            if fmt == "xlsx":
                buf = BytesIO()
                df.to_excel(buf, index=False)
                buf.seek(0)
                return send_file(
                    buf,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    as_attachment=True,
                    download_name="historico_saldos.xlsx",
                )
            buf = BytesIO()
            buf.write(df.to_csv(sep=";", index=False, encoding="utf-8-sig").encode("utf-8-sig"))
            buf.seek(0)
            return send_file(
                buf,
                mimetype="text/csv; charset=utf-8",
                as_attachment=True,
                download_name="historico_saldos.csv",
            )
        except Exception as e:
            return jsonify({"error": str(e)[:200]}), 500
    if fmt == "xlsx":
        path = config.OUT_XLSX
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        as_attachment = "produtores_saldos.xlsx"
    else:
        path = config.OUT_CSV
        mimetype = "text/csv; charset=utf-8"
        as_attachment = "produtores_saldos.csv"
    if not os.path.isfile(path):
        return jsonify({"error": "Nenhum export disponível ainda."}), 404
    return send_file(
        path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=as_attachment,
    )


@app.route("/api/datas")
def api_datas():
    """Lista de datas disponíveis para filtro (histórico)."""
    try:
        datas = db.get_datas_disponiveis()
        return jsonify([{"run_at": d[0].isoformat() if hasattr(d[0], "isoformat") else str(d[0]), "label": d[1]} for d in datas])
    except Exception:
        return jsonify([])


@app.route("/api/relatorio")
def api_relatorio_por_data():
    """Relatório de uma data específica (run_at em ISO)."""
    run_at_str = request.args.get("run_at") or request.args.get("data")
    if not run_at_str:
        return jsonify({"error": "Informe run_at ou data."}), 400
    try:
        resultados = db.get_relatorio_por_data(run_at_str)
        return jsonify({"run_at": run_at_str, "resultados": resultados, "total": len(resultados)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/evolucao")
def api_evolucao():
    """Evolução dos saldos de um produtor (email) ao longo do tempo."""
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Informe email."}), 400
    try:
        dados = db.get_evolucao_produtor(email.strip())
        return jsonify({"email": email, "dados": dados})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/produtores")
def api_produtores():
    """Lista de produtores (email + nome) para dropdown."""
    try:
        lista = db.get_produtores_emails()
        return jsonify(lista)
    except Exception:
        return jsonify([])


@app.route("/api/webhooks/applyfy", methods=["GET", "POST"])
def api_webhooks_applyfy():
    """Recebe webhooks da ApplyFy (TRANSACTION_*, PRODUCER_CREATED). Valida token e persiste."""
    if request.method == "GET":
        return jsonify({"ok": True, "message": "Webhook ApplyFy ativo. Envie eventos via POST."}), 200
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    token = payload.get("token") or payload.get("webhook_token")
    expected = os.environ.get("APPLYFY_WEBHOOK_TOKEN") or os.environ.get("APPLYFY_WEBHOOK_SECRET")
    if not expected or token != expected:
        return jsonify({"error": "Unauthorized"}), 401
    if not payload.get("event"):
        return jsonify({"error": "Missing event"}), 400
    try:
        status, ins_err = _persist_applyfy_webhook(payload, request.headers.get("X-Request-Id", ""))
        if status == "error" and ins_err:
            try:
                db.insert_webhook_dlq(
                    event=payload.get("event"),
                    payload=payload if isinstance(payload, dict) else {},
                    error_message=ins_err,
                )
            except Exception as ex:
                app.logger.warning("Webhook DLQ insert failed: %s", ex)
        elif status == "no_db":
            app.logger.warning("Webhook: sem DATABASE_URL; evento não persistido.")
    except Exception as e:
        app.logger.warning("Webhook persist failed: %s", str(e))
    return "", 200


@app.route("/api/transacoes")
def api_transacoes():
    """Lista transações com todas as colunas do payload do webhook."""
    try:
        date_from = request.args.get("date_from") or request.args.get("dateFrom")
        date_to = request.args.get("date_to") or request.args.get("dateTo")
        event = request.args.get("event")
        offer_code = request.args.get("offer_code") or request.args.get("offerCode")
        limit = request.args.get("limit", 500, type=int)
        rows = db.list_transactions(date_from=date_from, date_to=date_to, event=event, offer_code=offer_code, limit=limit)
        # Ordem das colunas (todas que o webhook pode retornar)
        col_order = [
            "received_at", "event", "token", "offer_code",
            "producer_id", "producer_name", "producer_email", "producer_phone", "producer_document", "producer_status", "producer_created_at",
            "transaction_id", "transaction_status", "payment_method", "original_currency", "original_amount", "currency", "amount", "exchange_rate", "installments",
            "transaction_create_at", "transaction_payed_at", "pix_end_to_end_id",
            "client_id", "client_name", "client_email", "client_phone", "client_cpf", "client_cnpj",
            "client_address",
            "subscription_id",
            "order_items_summary",
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "track_ip", "track_country", "track_user_agent", "track_zip_code", "track_city", "track_state",
        ]
        out = []
        for r in rows:
            p = r.get("payload") or {}
            trans = p.get("transaction") or {}
            client = p.get("client") or {}
            producer = p.get("producer") or {}
            addr = client.get("address") or {}
            track = p.get("trackProps") or {}
            subs = p.get("subscription")
            items = p.get("orderItems") or []

            def _fmt(v):
                if v is None or v == "":
                    return "–"
                if isinstance(v, dict):
                    return str(v)[:200]
                if isinstance(v, list):
                    return ", ".join(str(x) for x in v[:5]) if v else "–"
                return str(v)

            # Lookup offer_code -> produtor
            if not r.get("producer_id") and producer.get("id"):
                r["producer_id"] = producer.get("id")
            if not r.get("producer_id") and r.get("offer_code"):
                lookup = db.get_producer_by_offer_code(r["offer_code"])
                if lookup:
                    r["producer_id"] = lookup.get("producer_id")
                    r["producer_name"] = r.get("producer_name") or lookup.get("producer_name")

            row = {}
            row["received_at"] = r.get("received_at")
            row["event"] = r.get("event")
            row["token"] = p.get("token")
            row["offer_code"] = r.get("offer_code") or p.get("offerCode")
            row["producer_id"] = r.get("producer_id")
            row["producer_name"] = producer.get("name") or r.get("producer_name") or p.get("producerName")
            row["producer_email"] = producer.get("email")
            row["producer_phone"] = producer.get("phone")
            row["producer_document"] = producer.get("document")
            row["producer_status"] = producer.get("status")
            row["producer_created_at"] = producer.get("createdAt")
            row["transaction_id"] = trans.get("id") or r.get("transaction_id")
            row["transaction_status"] = trans.get("status")
            row["payment_method"] = trans.get("paymentMethod") or trans.get("payment_method")
            row["original_currency"] = trans.get("originalCurrency")
            row["original_amount"] = trans.get("originalAmount")
            row["currency"] = trans.get("currency")
            row["amount"] = trans.get("amount")
            row["exchange_rate"] = trans.get("exchangeRate")
            row["installments"] = trans.get("installments")
            row["transaction_create_at"] = trans.get("createAt") or trans.get("create_at")
            row["transaction_payed_at"] = trans.get("payedAt") or trans.get("payed_at")
            pix = trans.get("pixInformation") or {}
            row["pix_end_to_end_id"] = pix.get("endToEndId") or pix.get("end_to_end_id") if isinstance(pix, dict) else None
            row["client_id"] = client.get("id")
            row["client_name"] = client.get("name")
            row["client_email"] = client.get("email")
            row["client_phone"] = client.get("phone")
            row["client_cpf"] = client.get("cpf")
            row["client_cnpj"] = client.get("cnpj")
            row["client_address"] = ", ".join(filter(None, [addr.get("street"), addr.get("number"), addr.get("neighborhood"), addr.get("city"), addr.get("state"), addr.get("zipCode"), addr.get("country")])) if addr else None
            row["subscription_id"] = subs.get("id") if isinstance(subs, dict) else (subs if subs else None)
            row["order_items_summary"] = "; ".join([(it.get("product") or {}).get("name") or it.get("product", {}).get("externalId") or str(it.get("id", "")) for it in items[:5]]) if items else None
            row["utm_source"] = track.get("utm_source")
            row["utm_medium"] = track.get("utm_medium")
            row["utm_campaign"] = track.get("utm_campaign")
            row["utm_content"] = track.get("utm_content")
            row["utm_term"] = track.get("utm_term")
            row["track_ip"] = track.get("ip")
            row["track_country"] = track.get("country")
            row["track_user_agent"] = (track.get("user_agent") or "")[:80]
            row["track_zip_code"] = track.get("zip_code")
            row["track_city"] = track.get("city")
            row["track_state"] = track.get("state")
            out.append({k: row.get(k) for k in col_order})
        return jsonify({"columns": col_order, "transacoes": out, "total": len(out)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/vendas")
def api_vendas():
    """Lista vendas consolidadas (applyfy_vendas) com filtros e paginação."""
    try:
        date_from = request.args.get("date_from") or request.args.get("dateFrom")
        date_to = request.args.get("date_to") or request.args.get("dateTo")
        adquirente = request.args.get("adquirente")
        status_pagamento = request.args.get("status_pagamento") or request.args.get("status")
        produtor_email = request.args.get("produtor_email")
        comprador_email = request.args.get("comprador_email")
        busca = request.args.get("q") or request.args.get("busca")
        limit = request.args.get("limit", 200, type=int)
        offset = request.args.get("offset", 0, type=int)
        data = db.list_applyfy_vendas(
            date_from=date_from,
            date_to=date_to,
            adquirente=adquirente,
            status_pagamento=status_pagamento,
            produtor_email=produtor_email,
            comprador_email=comprador_email,
            busca=busca,
            limit=limit,
            offset=offset,
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _vendas_log_payload():
    """Corpo JSON do tail de applyfy_orders_log.txt."""
    lines = min(int(request.args.get("lines", 500)), 2000)
    path = config.ORDERS_LOG_TXT
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                out = f.readlines()
            out = out[-lines:] if len(out) > lines else out
            log_content = "".join(out)
        else:
            log_content = "(Arquivo de log ainda não existe — rode o export de vendas ou Iniciar processo abaixo.)\n"
    except Exception as e:
        log_content = f"[Erro ao ler log: {e}]\n"
    return jsonify({"log": log_content})


@app.route("/api/vendas/log")
@app.route("/api/vendas-log")
def api_vendas_log():
    """Últimas linhas do arquivo de texto do export de vendas (rota alternativa sem barra extra)."""
    return _vendas_log_payload()


@app.route("/api/vendas/log/clear", methods=["POST"])
@app.route("/api/vendas-log/clear", methods=["POST"])
def api_vendas_log_clear():
    """Limpa txt/csv/json de sessão do export de vendas (não apaga dados no Postgres)."""
    try:
        config.ensure_data_dir()
        cleared = []
        for path in (config.ORDERS_LOG_TXT, config.ORDERS_LOG_CSV, config.ORDERS_LOG_JSON):
            if os.path.isfile(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("")
                cleared.append(os.path.basename(path))
        return jsonify({"ok": True, "message": "Log de vendas limpo." if cleared else "Nenhum arquivo para limpar."})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


def _vendas_import_log_payload():
    limit = request.args.get("limit", 200, type=int)
    offset = request.args.get("offset", 0, type=int)
    status = request.args.get("status")
    data = list_applyfy_vendas_import_log(limit=limit, offset=offset, status=status)
    return jsonify(data)


@app.route("/api/vendas/import-log")
@app.route("/api/vendas-import-log")
def api_vendas_import_log():
    """Histórico em applyfy_import_log (rota alternativa)."""
    try:
        return _vendas_import_log_payload()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/transacoes/sync-offer-producers")
def api_sync_offer_producers():
    """Preenche mapeamento offer_code -> produtor a partir dos PRODUCER_CREATED já salvos (chama API ApplyFy)."""
    try:
        import applyfy_api
        producers = db.list_producer_created_events(limit=100)
        saved = 0
        errors = []
        for producer_id, producer_name in producers:
            res, err = applyfy_api.get_producer(producer_id)
            if err:
                err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                errors.append({"producer_id": producer_id, "error": err_msg})
                continue
            codes = applyfy_api.offer_codes_from_producer_response(res or {})
            if not codes:
                errors.append({"producer_id": producer_id, "error": "API não retornou offer code na resposta"})
            for code in codes:
                if code:
                    db.save_offer_producer(code, producer_id, producer_name)
                    saved += 1
        return jsonify({"ok": True, "saved_mappings": saved, "errors": errors[:15]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/produtor/<producer_id>/taxas")
def api_produtor_taxas(producer_id):
    """Retorna taxas do produtor (cache ou busca na API Admin)."""
    try:
        import applyfy_api
        refresh = request.args.get("refresh", "").lower() in ("1", "true", "yes")
        cached = db.get_producer_taxes(producer_id=producer_id)
        if refresh or not cached:
            snapshot, err = applyfy_api.fetch_and_save_producer_taxes(producer_id)
            if err and not cached:
                return jsonify({"error": err.get("message", str(err))}), 502
            if snapshot is not None:
                cached = {"taxes_snapshot": snapshot, "fetched_at": datetime.utcnow().isoformat() + "Z"}
        if not cached:
            return jsonify({"error": "Taxas não encontradas"}), 404
        return jsonify(cached)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/produtor/taxas")
def api_produtor_taxas_by_email():
    """Retorna taxas do produtor por email (apenas cache)."""
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Informe email."}), 400
    try:
        cached = db.get_producer_taxes(email=email.strip())
        if not cached:
            return jsonify({"taxes_snapshot": None, "fetched_at": None, "message": "Nenhum cache de taxas para este email. Use a API por producer_id para buscar."})
        out = dict(cached)
        if hasattr(out.get("fetched_at"), "isoformat"):
            out["fetched_at"] = out["fetched_at"].isoformat()
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/produtores-webhook")
def api_produtores_webhook():
    """Lista produtores únicos do webhook (PRODUCER_CREATED + offer_producer)."""
    try:
        limit = request.args.get("limit", 500, type=int)
        lista = db.list_webhook_producers(limit=min(limit, 1000))
        return jsonify({"produtores": lista, "total": len(lista)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/produtor/<producer_id>/detalhes")
def api_produtor_detalhes(producer_id):
    """Busca dados completos do produtor na API ApplyFy (GET /producer/{id} com includeTaxes)."""
    try:
        import applyfy_api
        res, err = applyfy_api.get_producer(
            producer_id,
            include_taxes=True,
            include_kyc=False,
            include_payout_account=False,
            include_documents=False,
        )
        if err:
            return jsonify({"error": err.get("message", str(err)), "success": False}), 502
        return jsonify(res or {"success": False})
    except Exception as e:
        app.logger.exception("api_produtor_detalhes failed")
        return jsonify({"error": str(e), "success": False}), 500


@app.route("/api/financeiro/categorias", methods=["GET"])
def api_financeiro_categorias_list():
    return jsonify({"categorias": db.list_categorias(tipo=request.args.get("tipo"))})


@app.route("/api/financeiro/categorias", methods=["POST"])
def api_financeiro_categorias_create():
    data = request.get_json() or {}
    nome = (data.get("nome") or "").strip()
    tipo = (data.get("tipo") or "").strip().lower()
    if not nome or tipo not in ("receita", "despesa"):
        return jsonify({"error": "nome e tipo (receita/despesa) obrigatórios"}), 400
    cat = db.create_categoria(nome, tipo)
    if not cat:
        return jsonify({"error": "Erro ao criar categoria"}), 500
    return jsonify(cat), 201


@app.route("/api/financeiro/categorias/<int:id>", methods=["GET"])
def api_financeiro_categoria_get(id):
    cat = db.get_categoria(id)
    if not cat:
        return jsonify({"error": "Categoria não encontrada"}), 404
    return jsonify(cat)


@app.route("/api/financeiro/categorias/<int:id>", methods=["PUT"])
def api_financeiro_categoria_update(id):
    if not db.get_categoria(id):
        return jsonify({"error": "Categoria não encontrada"}), 404
    data = request.get_json() or {}
    nome = data.get("nome")
    nome = nome.strip()[:200] if nome is not None else None
    tipo = data.get("tipo")
    if tipo is not None and isinstance(tipo, str):
        t = tipo.strip().lower()
        tipo = t if t in ("receita", "despesa") else None
    else:
        tipo = None
    db.update_categoria(id, nome=nome, tipo=tipo, ativa=data.get("ativa"))
    return jsonify(db.get_categoria(id))


@app.route("/api/financeiro/categorias/<int:id>", methods=["DELETE"])
def api_financeiro_categoria_delete(id):
    if not db.get_categoria(id):
        return jsonify({"error": "Categoria não encontrada"}), 404
    db.delete_categoria(id)
    return "", 204


@app.route("/api/financeiro/lancamentos", methods=["GET"])
def api_financeiro_lancamentos_list():
    date_from = request.args.get("date_from") or request.args.get("dateFrom")
    date_to = request.args.get("date_to") or request.args.get("dateTo")
    mes = request.args.get("mes") or request.args.get("month")
    ano = request.args.get("ano") or request.args.get("year")
    tipo = request.args.get("tipo")
    categoria_id = request.args.get("categoria_id")
    limit = request.args.get("limit", 2000, type=int)
    lista = db.list_lancamentos(date_from=date_from, date_to=date_to, mes=mes, ano=ano, tipo=tipo, categoria_id=categoria_id, limit=limit)
    return jsonify({"lancamentos": lista, "total": len(lista)})


@app.route("/api/financeiro/lancamentos", methods=["POST"])
def api_financeiro_lancamentos_create():
    data = request.get_json() or {}
    data_la = data.get("data")
    valor = data.get("valor")
    tipo = (data.get("tipo") or "").strip().lower()
    if not data_la or tipo not in ("receita", "despesa"):
        return jsonify({"error": "data e tipo (receita/despesa) obrigatórios"}), 400
    try:
        float(valor)
    except (TypeError, ValueError):
        return jsonify({"error": "valor inválido"}), 400
    lanc = db.create_lancamento(data_la, valor, tipo, categoria_id=data.get("categoria_id"), descricao=data.get("descricao"), naturaleza_dfc=data.get("natureza_dfc"))
    if not lanc:
        return jsonify({"error": "Erro ao criar lançamento"}), 500
    return jsonify(lanc), 201


@app.route("/api/financeiro/lancamentos/<int:id>", methods=["GET"])
def api_financeiro_lancamento_get(id):
    lanc = db.get_lancamento(id)
    if not lanc:
        return jsonify({"error": "Lançamento não encontrado"}), 404
    return jsonify(lanc)


@app.route("/api/financeiro/lancamentos/<int:id>", methods=["PUT"])
def api_financeiro_lancamento_update(id):
    if not db.get_lancamento(id):
        return jsonify({"error": "Lançamento não encontrado"}), 404
    d = request.get_json() or {}
    db.update_lancamento(id, data=d.get("data"), valor=d.get("valor"), tipo=d.get("tipo"), categoria_id=d.get("categoria_id"), descricao=d.get("descricao"), naturaleza_dfc=d.get("natureza_dfc"))
    return jsonify(db.get_lancamento(id))


@app.route("/api/financeiro/lancamentos/<int:id>", methods=["DELETE"])
def api_financeiro_lancamento_delete(id):
    if not db.get_lancamento(id):
        return jsonify({"error": "Lançamento não encontrado"}), 404
    db.delete_lancamento(id)
    return "", 204


@app.route("/api/financeiro/relatorios/fluxo-caixa", methods=["GET"])
def api_financeiro_relatorio_fluxo_caixa():
    date_from = request.args.get("date_from") or request.args.get("dateFrom")
    date_to = request.args.get("date_to") or request.args.get("dateTo")
    mes = request.args.get("mes") or request.args.get("month")
    ano = request.args.get("ano") or request.args.get("year")
    return jsonify(db.relatorio_fluxo_caixa(date_from=date_from, date_to=date_to, mes=mes, ano=ano))


@app.route("/api/financeiro/relatorios/dre", methods=["GET"])
def api_financeiro_relatorio_dre():
    date_from = request.args.get("date_from") or request.args.get("dateFrom")
    date_to = request.args.get("date_to") or request.args.get("dateTo")
    mes = request.args.get("mes") or request.args.get("month")
    ano = request.args.get("ano") or request.args.get("year")
    return jsonify(db.relatorio_dre(date_from=date_from, date_to=date_to, mes=mes, ano=ano))


@app.route("/api/financeiro/relatorios/dfc", methods=["GET"])
def api_financeiro_relatorio_dfc():
    date_from = request.args.get("date_from") or request.args.get("dateFrom")
    date_to = request.args.get("date_to") or request.args.get("dateTo")
    mes = request.args.get("mes") or request.args.get("month")
    ano = request.args.get("ano") or request.args.get("year")
    return jsonify(db.relatorio_dfc(date_from=date_from, date_to=date_to, mes=mes, ano=ano))


@app.route("/api/financeiro/ofx/upload", methods=["POST"])
def api_financeiro_ofx_upload():
    if "file" not in request.files:
        return jsonify({"error": "Envie o ficheiro no campo multipart «file»."}), 400
    f = request.files["file"]
    raw = f.read()
    if not raw:
        return jsonify({"error": "Ficheiro vazio."}), 400
    name = (f.filename or "").lower()
    try:
        if name.endswith(".csv"):
            out = db.import_extrato_nubank_csv_bytes(raw, f.filename or "extrato.csv")
            return jsonify(out)
        if name.endswith(".ofx") or name.endswith(".qfx"):
            out = db.import_ofx_bytes(raw, f.filename or "extrato.ofx")
            return jsonify(out)
        return jsonify({"error": "Use .ofx, .qfx ou CSV Nubank."}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Falha ao importar: {e!s}"}), 400


@app.route("/api/financeiro/extrato/contas", methods=["GET"])
def api_financeiro_extrato_contas():
    return jsonify({"contas": db.list_ofx_contas()})


@app.route("/api/financeiro/extrato/resumo", methods=["GET"])
def api_financeiro_extrato_resumo():
    conta = request.args.get("conta_ref") or request.args.get("conta")
    return jsonify(db.resumo_conciliacao_extrato(conta_ref=conta))


@app.route("/api/financeiro/extrato", methods=["GET"])
def api_financeiro_extrato_list():
    conta = request.args.get("conta_ref") or request.args.get("conta")
    date_from = request.args.get("date_from") or request.args.get("data_de")
    date_to = request.args.get("date_to") or request.args.get("data_ate")
    pend = request.args.get("pendente")
    pendente = None
    if pend and str(pend).lower() in ("1", "true", "sim", "s"):
        pendente = True
    elif pend and str(pend).lower() in ("0", "false", "nao", "n"):
        pendente = False
    limit = request.args.get("limit", 500, type=int) or 500
    return jsonify(
        {
            "linhas": db.list_extrato_linhas(
                conta_ref=conta,
                date_from=date_from,
                date_to=date_to,
                pendente=pendente,
                limit=limit,
            )
        }
    )


@app.route("/api/financeiro/extrato/<int:id>/sugestoes", methods=["GET"])
def api_financeiro_extrato_sugestoes(id):
    janela = request.args.get("janela_dias", 7, type=int) or 7
    lim = request.args.get("limit", 10, type=int) or 10
    return jsonify({"sugestoes": db.sugestoes_conciliacao_extrato(id, janela_dias=janela, limit=lim)})


@app.route("/api/financeiro/extrato/<int:id>/conciliar", methods=["POST"])
def api_financeiro_extrato_conciliar(id):
    d = request.get_json() or {}
    lid = d.get("lancamento_id")
    if lid is None:
        return jsonify({"error": "lancamento_id obrigatório"}), 400
    if not db.conciliar_extrato_linha(id, int(lid)):
        return jsonify({"error": "Não foi possível conciliar."}), 400
    return jsonify({"ok": True})


@app.route("/api/financeiro/extrato/<int:id>/desconciliar", methods=["POST"])
def api_financeiro_extrato_desconciliar(id):
    if not db.desconciliar_extrato_linha(id):
        return jsonify({"error": "Linha não encontrada."}), 404
    return jsonify({"ok": True})


@app.route("/health")
def health():
    return "ok", 200


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/static/<path:path>")
def static_file(path):
    """Serve arquivos estáticos em /static/ para compatibilidade com links do HTML."""
    return send_from_directory(app.static_folder, path)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/historico")
def historico():
    return send_from_directory(app.static_folder, "historico.html")


@app.route("/evolucao")
def evolucao():
    return send_from_directory(
        app.static_folder,
        "evolucao.html",
        mimetype="text/html; charset=utf-8",
        max_age=0,
    )


@app.route("/evolucao/")
def evolucao_slash():
    return send_from_directory(
        app.static_folder,
        "evolucao.html",
        mimetype="text/html; charset=utf-8",
        max_age=0,
    )


@app.route("/evolucao.html")
def evolucao_html():
    return send_from_directory(
        app.static_folder,
        "evolucao.html",
        mimetype="text/html; charset=utf-8",
        max_age=0,
    )


@app.route("/evolucao-ok")
def evolucao_ok():
    """Rota de teste: HTML mínimo para confirmar que o servidor entrega conteúdo."""
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Teste Evolução</title></head>"
        "<body style='background:#1a1a2e;color:#eee;font-family:sans-serif;padding:2rem;'>"
        "<h1>Teste Evolução</h1><p>Se você vê esta página, o servidor está respondendo.</p>"
        "<p><a href='/evolucao' style='color:#c9a227'>/evolucao</a> | "
        "<a href='/evolucao.html' style='color:#c9a227'>/evolucao.html</a> | "
        "<a href='/' style='color:#c9a227'>Painel</a></p></body></html>"
    )
    return html, 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}


@app.route("/log")
def log_page():
    return send_from_directory(app.static_folder, "log.html")


@app.route("/log-vendas")
@app.route("/log-vendas.html")
def log_vendas_page():
    """HTML do painel de log de vendas (duas URLs para nginx/proxy e links diretos)."""
    return send_from_directory(app.static_folder, "log-vendas.html")


@app.route("/transacoes")
def transacoes_page():
    return send_from_directory(app.static_folder, "transacoes.html")


@app.route("/vendas")
def vendas_page():
    return send_from_directory(app.static_folder, "vendas.html")


@app.route("/produtores")
def produtores_page():
    return send_from_directory(app.static_folder, "produtores.html")


@app.route("/integracoes")
def integracoes_page():
    return send_from_directory(app.static_folder, "integracoes.html")


@app.route("/meta")
def meta_page():
    return send_from_directory(app.static_folder, "meta.html")


@app.route("/permissoes")
def permissoes_page():
    return send_from_directory(app.static_folder, "permissoes.html")


@app.route("/config-comercial")
@app.route("/config-comercial/")
def config_comercial_page():
    """Gestão de flags comercial / gerente (UserClientPermission no Hub); requer applyfy.admin."""
    return send_from_directory(app.static_folder, "config-comercial.html")


@app.route("/comercial")
@app.route("/comercial/")
def comercial_page():
    return send_from_directory(app.static_folder, "comercial.html")


@app.route("/api/comercial/carteira", methods=["GET"])
def api_comercial_carteira_get():
    """Mapa produtor (email) → vendedor para a tela Comercial."""
    if not db.get_database_url():
        return jsonify({"assignments": {}, "items": [], "db": False})
    try:
        items = db.list_producer_vendedor()
        if auth_hub.auth_enabled() and auth_hub.session_is_somente_vendedor_comercial():
            sub = session.get("hub_sub")
            name_lower = (session.get("hub_user_name") or "").strip().lower()
            items = [i for i in items if _carteira_assign_visible(i, sub, name_lower)]
        assignments = {i["producer_email"]: i["vendedor_nome"] for i in items}
        assignment_user_ids = {i["producer_email"]: i.get("vendedor_user_id") for i in items}
        return jsonify(
            {
                "assignments": assignments,
                "assignment_user_ids": assignment_user_ids,
                "items": items,
                "db": True,
                "can_edit_carteira_comercial": auth_hub.session_can_edit_carteira_comercial(),
            }
        )
    except Exception as e:
        app.logger.exception("api_comercial_carteira_get")
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/api/comercial/carteira", methods=["PUT"])
def api_comercial_carteira_put():
    """Atribui ou remove vendedor (nome vazio remove). Requer gerente comercial ou admin."""
    if not auth_hub.session_can_edit_carteira_comercial():
        return jsonify({"error": "Sem permissão para editar a carteira comercial"}), 403
    if not db.get_database_url():
        return jsonify({"error": "DATABASE_URL não configurado"}), 503
    data = request.get_json(silent=True) or {}
    email = data.get("producer_email")
    if email is None or (isinstance(email, str) and not email.strip()):
        return jsonify({"error": "producer_email obrigatório"}), 400
    nome = data.get("vendedor_nome")
    if nome is not None and not isinstance(nome, str):
        nome = str(nome)
    raw_vid = data.get("vendedor_user_id")
    if raw_vid is not None and not isinstance(raw_vid, str):
        raw_vid = str(raw_vid)
    vendedor_user_id = (raw_vid or "").strip() or None
    try:
        trimmed = (nome or "").strip()[:200]
        if not trimmed:
            ok = db.upsert_producer_vendedor(email, "", None)
        else:
            if not vendedor_user_id:
                return jsonify({"error": "vendedor_user_id obrigatório ao atribuir vendedor"}), 400
            allowed = _hub_commercial_user_ids_allowed()
            if allowed is None:
                return jsonify({"error": "Não foi possível validar vendedores no Hub"}), 502
            if vendedor_user_id not in allowed:
                return jsonify({"error": "Vendedor não permitido (exige flag comercial no Hub)"}), 400
            ok = db.upsert_producer_vendedor(email, trimmed, vendedor_user_id)
        if not ok:
            return jsonify({"error": "Email de produtor inválido"}), 400
        key = (email or "").strip().lower()
        return jsonify(
            {
                "ok": True,
                "producer_email": key,
                "vendedor_nome": trimmed,
                "vendedor_user_id": vendedor_user_id if trimmed else None,
            }
        )
    except Exception as e:
        app.logger.exception("api_comercial_carteira_put")
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/financeiro")
@app.route("/financeiro/")
def financeiro_page():
    return send_from_directory(
        os.path.join(BASE_DIR, "static"),
        "financeiro.html",
        mimetype="text/html; charset=utf-8",
        max_age=0,
        conditional=True,
    )


@app.route("/sw.js")
def sw():
    return send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")


@app.route("/api/job/start", methods=["POST"])
def api_job_start():
    """Inicia o job de exportação em background (mesmo que rodar_job.sh)."""
    try:
        config.ensure_data_dir()
        if not config.data_dir_writable():
            dd = config.DATA_DIR
            return jsonify(
                {
                    "ok": False,
                    "message": (
                        f"Sem permissão de escrita em {dd} (ex.: cron.log). "
                        "O serviço Gunicorn usa o utilizador www-data: "
                        f"sudo chown -R www-data:www-data {dd}"
                    ),
                }
            ), 500
        log_path = os.path.join(config.DATA_DIR, "cron.log")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env.setdefault("APPLYFY_DATA_DIR", config.DATA_DIR)
        py = os.path.join(BASE_DIR, "venv", "bin", "python")
        if not os.path.isfile(py):
            py = "python3"
        script = os.path.join(BASE_DIR, "run_daily.py")
        with open(log_path, "a", encoding="utf-8") as log_file:
            subprocess.Popen(
                [py, script],
                cwd=BASE_DIR,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return jsonify({"ok": True, "message": "Processo iniciado. Acompanhe o log abaixo."})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/job/stop", methods=["POST"])
def api_job_stop():
    """Interrompe o job em execução (run_daily.py e Chromium)."""
    pkill_bin = "/usr/bin/pkill" if os.path.isfile("/usr/bin/pkill") else "pkill"
    try:
        for pattern in ["run_daily.py", "01_salvar_sessao.py", "chromium"]:
            subprocess.run(
                [pkill_bin, "-f", pattern],
                capture_output=True,
                timeout=5,
                env={**os.environ, "PATH": "/usr/bin:/bin"},
            )
        return jsonify({"ok": True, "message": "Comando de parada enviado. O processo pode levar alguns segundos para encerrar."})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "message": "Timeout ao tentar parar."}), 500
    except FileNotFoundError:
        return jsonify({"ok": False, "message": "pkill não encontrado. Instale o pacote procps (apt install procps)."}), 500
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/job-vendas/start", methods=["POST"])
def api_job_vendas_start():
    """Inicia em background o export de vendas (03_exportar_vendas.py → Playwright + Postgres)."""
    try:
        config.ensure_data_dir()
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env.setdefault("APPLYFY_DATA_DIR", config.DATA_DIR)
        py = os.path.join(BASE_DIR, "venv", "bin", "python")
        if not os.path.isfile(py):
            py = "python3"
        script = os.path.join(BASE_DIR, "03_exportar_vendas.py")
        if not os.path.isfile(script):
            return jsonify({"ok": False, "message": f"Script não encontrado: {script}"}), 500
        banner = (
            f"\n{'=' * 60}\n"
            f"[{datetime.now().isoformat()}] Export vendas iniciado pelo painel (PID em background)\n"
            f"{'=' * 60}\n"
        )
        with open(config.ORDERS_LOG_TXT, "a", encoding="utf-8") as log_file:
            log_file.write(banner)
            subprocess.Popen(
                [py, script],
                cwd=BASE_DIR,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return jsonify(
            {
                "ok": True,
                "message": "Export de vendas iniciado. Acompanhe o texto abaixo (e reinicie a tabela após alguns registros).",
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/job-vendas/stop", methods=["POST"])
def api_job_vendas_stop():
    """Interrompe o processo do export de vendas (script + Chromium do Playwright)."""
    pkill_bin = "/usr/bin/pkill" if os.path.isfile("/usr/bin/pkill") else "pkill"
    # Encerra o Python do export; o Chromium filho costuma encerrar junto.
    patterns = ["03_exportar_vendas.py"]
    try:
        for pattern in patterns:
            subprocess.run(
                [pkill_bin, "-f", pattern],
                capture_output=True,
                timeout=8,
                env={**os.environ, "PATH": "/usr/bin:/bin:/usr/local/bin"},
            )
        return jsonify(
            {
                "ok": True,
                "message": "Parada enviada ao export de vendas (e Chromium do Playwright). Pode levar alguns segundos.",
            }
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "message": "Timeout ao tentar parar o export de vendas."}), 500
    except FileNotFoundError:
        return jsonify({"ok": False, "message": "pkill não encontrado (apt install procps)."}), 500
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/log")
def api_log():
    """Últimas linhas do log da exportação (para a tela de acompanhamento)."""
    lines = min(int(request.args.get("lines", 500)), 2000)
    log_path = config.LOG_TXT
    cron_path = os.path.join(config.DATA_DIR, "cron.log")
    out = []
    try:
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.readlines()
        out = out[-lines:] if len(out) > lines else out
        log_content = "".join(out)
    except Exception as e:
        log_content = f"[Erro ao ler log: {e}]\n"
    try:
        if os.path.isfile(cron_path):
            with open(cron_path, "r", encoding="utf-8", errors="replace") as f:
                cron = f.readlines()[-100:]
            log_content += "\n\n--- cron.log (últimas 100 linhas) ---\n\n" + "".join(cron)
    except Exception:
        pass
    return jsonify({"log": log_content})


@app.route("/api/log/clear", methods=["POST"])
def api_log_clear():
    """Limpa os arquivos de log (applyfy_log.txt e cron.log)."""
    try:
        log_path = config.LOG_TXT
        cron_path = os.path.join(config.DATA_DIR, "cron.log")
        cleared = []
        for path in [log_path, cron_path]:
            if os.path.isfile(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("")
                cleared.append(os.path.basename(path))
        return jsonify({"ok": True, "message": "Log limpo." if cleared else "Nenhum arquivo de log para limpar."})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


if __name__ == "__main__":
    config.ensure_data_dir()
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
