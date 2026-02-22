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


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
