#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testa conexão com o Postgres usando o mesmo .env do projeto.
Uso: python scripts/test_postgres.py   (com venv ativado)
Ou:  venv/bin/python scripts/test_postgres.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

env_path = os.path.join(BASE, ".env")
try:
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
except ImportError:
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip("'\"")

import db

def main():
    if not db.DATABASE_URL:
        print("ERRO: DATABASE_URL não definido. Verifique PG_HOST, PG_USER, PG_PASSWORD, PG_DATABASE no .env (sem espaço no início da linha).")
        return 1
    user = db._db_user_from_url()
    print(f"Config: usuário '{user}' (URL definida)")
    try:
        db.init_db()
        print("Conexão OK. Tabelas existentes:")
        with db.cursor() as cur:
            cur.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            for (name,) in cur.fetchall():
                print(f"  - {name}")
        print("Postgres está conectado e utilizável.")
        return 0
    except Exception as e:
        print(f"ERRO ao conectar: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
