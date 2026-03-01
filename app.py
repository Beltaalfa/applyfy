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


@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/historico")
def historico():
    return send_from_directory(app.static_folder, "historico.html")


@app.route("/evolucao")
def evolucao():
    return send_from_directory(app.static_folder, "evolucao.html")


@app.route("/log")
def log_page():
    return send_from_directory(app.static_folder, "log.html")


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
