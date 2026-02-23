#!/bin/bash
# Inicia o job de exportação em background. Saída vai para data/cron.log.
# Uso: ./rodar_job.sh   (ou: bash rodar_job.sh)
# Acompanhe pelo painel: https://applyfy.northempresarial.com/log
cd /var/www/applyfy
. env.sh
# PYTHONUNBUFFERED=1: log aparece na hora no cron.log (não fica “preso” após Login OK)
PYTHONUNBUFFERED=1 nohup /var/www/applyfy/venv/bin/python run_daily.py >> data/cron.log 2>&1 &
echo "Job iniciado. Acompanhe em https://applyfy.northempresarial.com/log"
