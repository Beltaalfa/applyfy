# -*- coding: utf-8 -*-
"""
API Flask do painel Applyfy: último relatório (JSON) e download XLSX/CSV.
"""
import os
import subprocess
from datetime import datetime

import pandas as pd
from flask import Flask, request, jsonify, send_file, send_from_directory
from dotenv import load_dotenv

import config
import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["JSON_AS_ASCII"] = False


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


@app.route("/api/ultimo-relatorio")
def api_ultimo_relatorio():
    dados, run_at = _get_ultimo_dados()
    return jsonify({"run_at": run_at, "resultados": dados, "total": len(dados)})


@app.route("/api/exportar")
def api_exportar():
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
    event = payload.get("event")
    if not event:
        return jsonify({"error": "Missing event"}), 400
    transaction_id = None
    offer_code = payload.get("offerCode") or payload.get("offer_code")
    producer_id = None
    if event == "PRODUCER_CREATED":
        producer = payload.get("producer") or {}
        transaction_id = producer.get("id") or f"producer-{event}"
        producer_id = producer.get("id")
    else:
        trans = payload.get("transaction") or {}
        transaction_id = trans.get("id") or f"tx-{event}-{request.headers.get('X-Request-Id', '')}"
        producer_id = payload.get("producerId") or payload.get("producer_id")
    try:
        db.insert_webhook_transaction(
            transaction_id=transaction_id or f"evt-{event}",
            event=event,
            offer_code=offer_code,
            producer_id=producer_id,
            payload=payload,
        )
        if event == "PRODUCER_CREATED" and producer_id:
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
    except Exception as e:
        app.logger.warning("Webhook insert failed: %s", str(e))
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


@app.route("/transacoes")
def transacoes_page():
    return send_from_directory(app.static_folder, "transacoes.html")


@app.route("/produtores")
def produtores_page():
    return send_from_directory(app.static_folder, "produtores.html")


@app.route("/meta")
def meta_page():
    return send_from_directory(app.static_folder, "meta.html")


@app.route("/financeiro")
@app.route("/financeiro/")
def financeiro_page():
    return send_from_directory(
        os.path.join(BASE_DIR, "static"),
        "financeiro.html",
        mimetype="text/html; charset=utf-8",
    )


@app.route("/sw.js")
def sw():
    return send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")


@app.route("/api/job/start", methods=["POST"])
def api_job_start():
    """Inicia o job de exportação em background (mesmo que rodar_job.sh)."""
    try:
        config.ensure_data_dir()
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
