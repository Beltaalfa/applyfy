# Deploy – Painel Applyfy (applyfy.northempresarial.com)

## 1. Servidor e dependências

- Python 3.10+
- Node não é necessário (backend é 100% Python).
- PostgreSQL (opcional): se quiser guardar histórico de exports no banco.

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3-venv python3-pip libpq-dev
# Playwright precisa do Chromium (instalado pelo playwright install)
```

## 2. Projeto e venv

```bash
cd /var/www/applyfy
python3 -m venv venv
source venv/bin/activate  # ou no Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## 3. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha (nunca commite o `.env`):

```bash
cp .env.example .env
# Edite .env com: APPLYFY_USER, APPLYFY_PASSWORD, APPLYFY_TOTP_SECRET
```

**API Admin e Webhooks (opcional):** para receber vendas/transações em tempo real e consultar taxas dos produtores:

- No painel ApplyFy, em Integrações/API, obtenha as chaves e defina no `.env`:
  - `APPLYFY_PUBLIC_KEY`
  - `APPLYFY_SECRET_KEY`
- Em Integrações > Webhooks, cadastre a URL do webhook e use o mesmo valor no `.env`:
  - `APPLYFY_WEBHOOK_TOKEN=...`

**URL do webhook** (HTTPS obrigatório):

- `https://applyfy.northempresarial.com/api/webhooks/applyfy`

O Nginx deve permitir POST nessa rota; certificado SSL deve estar ativo.

Para o cron, crie um script que carrega o `.env` antes de rodar, por exemplo `env.sh`:

```bash
# env.sh (não commitar com valores reais)
set -a
source /var/www/applyfy/.env
set +a
export APPLYFY_DATA_DIR=/var/www/applyfy/data
```

## 4. Diretório de dados

```bash
mkdir -p /var/www/applyfy/data
# Permissões: o usuário que roda o app e o cron deve poder escrever
chown -R www-data:www-data /var/www/applyfy/data   # se rodar como www-data
```

## 5. PostgreSQL (opcional)

Se quiser que o último relatório seja lido do banco:

```bash
sudo -u postgres createuser -P applyfy
sudo -u postgres createdb -O applyfy applyfy
```

No `.env`:

```
DATABASE_URL=postgresql://applyfy:SUA_SENHA@localhost:5432/applyfy
```

As tabelas são criadas automaticamente na primeira gravação (`export_runs`).

## 6. Rodar a API com Gunicorn atrás do Nginx

```bash
cd /var/www/applyfy
source venv/bin/activate
gunicorn -w 1 -b 127.0.0.1:5000 --timeout 120 app:app
```

Recomendado: usar systemd para manter o Gunicorn rodando.

Arquivo `/etc/systemd/system/applyfy-painel.service`:

```ini
[Unit]
Description=Applyfy Painel API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/applyfy
Environment="PATH=/var/www/applyfy/venv/bin"
EnvironmentFile=/var/www/applyfy/.env
ExecStart=/var/www/applyfy/venv/bin/gunicorn -w 1 -b 127.0.0.1:5000 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable applyfy-painel
sudo systemctl start applyfy-painel
```

## 7. Nginx

Copie o exemplo e ative:

```bash
sudo cp /var/www/applyfy/nginx-applyfy.conf /etc/nginx/sites-available/applyfy
sudo ln -s /etc/nginx/sites-available/applyfy /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

DNS: aponte `applyfy.northempresarial.com` para o IP deste servidor.

SSL com Let's Encrypt:

```bash
sudo certbot --nginx -d applyfy.northempresarial.com
```

Depois descomente no config do Nginx o bloco `listen 443` e o `return 301` no bloco 80.

## 8. Job diário às 2h (cron)

```bash
crontab -u www-data -e
```

Adicione (ajuste o path do `env.sh` se necessário):

```
0 2 * * * cd /var/www/applyfy && . env.sh && /var/www/applyfy/venv/bin/python run_daily.py >> /var/www/applyfy/data/cron.log 2>&1
```

**Retry e checkpoint:** Se a exportação cair (timeout, falha de rede, etc.), o job é reiniciado automaticamente (até 10 tentativas, 45 s entre cada). O progresso é salvo em `data/export_checkpoint.json`; ao retomar, a exportação continua de onde parou em vez de recomeçar a lista. Para forçar recomeço do zero: `rm -f /var/www/applyfy/data/export_checkpoint.json`.

## 9. O que mais pode precisar

- **Primeira sessão:** na primeira vez, o login automático pode falhar se os selectors da página de login da Applyfy forem diferentes. Rode com `HEADLESS=0` para ver o browser: `HEADLESS=0 python 01_salvar_sessao.py` e ajuste os seletores em `01_salvar_sessao.py` se necessário.
- **Firewall:** libere 80 e 443 para o Nginx.
- **Troca de senha/2FA:** após testar, troque a senha e regenere o 2FA na Applyfy (as credenciais foram usadas no chat).
