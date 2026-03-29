# -*- coding: utf-8 -*-
"""Configurações centralizadas; paths e env."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("APPLYFY_DATA_DIR", os.path.join(BASE_DIR, "data"))

# Arquivos em DATA_DIR
SESSION_FILE = os.path.join(DATA_DIR, "sessao_applyfy.json")
OUT_CSV = os.path.join(DATA_DIR, "produtores_saldos.csv")
OUT_XLSX = os.path.join(DATA_DIR, "produtores_saldos.xlsx")
LOG_TXT = os.path.join(DATA_DIR, "applyfy_log.txt")
LOG_CSV = os.path.join(DATA_DIR, "applyfy_log.csv")
# Export de vendas (Playwright → Postgres)
ORDERS_LOG_TXT = os.path.join(DATA_DIR, "applyfy_orders_log.txt")
ORDERS_LOG_CSV = os.path.join(DATA_DIR, "applyfy_orders_log.csv")
ORDERS_LOG_JSON = os.path.join(DATA_DIR, "applyfy_orders_log.json")
EXPORT_CHECKPOINT = os.path.join(DATA_DIR, "export_checkpoint.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def get_meta_vendas_liquidas() -> float:
    """Meta de vendas líquidas (painel /meta e notificações WAHA). Default 10000."""
    raw = (os.environ.get("APPLYFY_META_VENDAS_LIQUIDAS") or "10000").strip()
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return 10000.0


def has_display_server() -> bool:
    """True quando há DISPLAY/WAYLAND (browser headed)."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
