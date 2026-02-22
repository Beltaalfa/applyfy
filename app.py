# -*- coding: utf-8 -*-
"""
API Flask do painel Applyfy: último relatório (JSON) e download XLSX/CSV.
"""
import os
from datetime import datetime

import pandas as pd
from flask import Flask, request, jsonify, send_file, send_from_directory

import config
import db

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["JSON_AS_ASCII"] = False


def _get_ultimo_dados():
    """Último relatório: primeiro do Postgres, senão do CSV em data/."""
    try:
        run_at, resultados = db.get_last_export_data()
    except Exception:
        resultados, run_at = [], None
    if resultados:
        run_at_str = run_at.isoformat() if hasattr(run_at, "isoformat") else str(run_at)
        return resultados, run_at_str
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


@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    config.ensure_data_dir()
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
