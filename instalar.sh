#!/bin/bash
# Rode DEPOIS de: sudo apt install -y python3-venv python3-pip libpq-dev
# Uso: cd /var/www/applyfy && chmod +x instalar.sh && ./instalar.sh

set -e
cd "$(dirname "$0")"

echo "Criando venv..."
python3 -m venv venv
source venv/bin/activate

echo "Instalando dependências Python..."
pip install -r requirements.txt

echo "Instalando Chromium para o Playwright..."
playwright install chromium

echo "Pronto. Agora faça: cp .env.example .env e edite o .env com suas credenciais."
echo "Depois use os comandos do COMANDOS.md (Nginx, systemd, cron)."
