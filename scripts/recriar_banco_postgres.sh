#!/bin/bash
# Recria usuário e banco PostgreSQL para Applyfy (rode com: sudo bash scripts/recriar_banco_postgres.sh)
set -e
echo "Criando usuário applyfy (senha 8421)..."
sudo -u postgres psql -c "DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'applyfy') THEN
    CREATE USER applyfy WITH PASSWORD '8421';
  ELSE
    ALTER USER applyfy WITH PASSWORD '8421';
  END IF;
END \$\$;"
echo "Criando banco applyfy (owner applyfy)..."
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'applyfy'" | grep -q 1 \
  && sudo -u postgres psql -c "ALTER DATABASE applyfy OWNER TO applyfy;" \
  || sudo -u postgres psql -c "CREATE DATABASE applyfy OWNER applyfy;"
echo "Reiniciando painel..."
systemctl restart applyfy-painel || true
echo "Pronto. Teste: PGPASSWORD=8421 psql -h localhost -U applyfy -d applyfy -c '\\dt'"
