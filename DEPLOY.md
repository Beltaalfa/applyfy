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
# Se você roda o cron como www-data mas salva sessão manualmente como tactical:
sudo chown -R tactical:www-data /var/www/applyfy/data
sudo chmod -R 775 /var/www/applyfy/data
sudo chmod g+s /var/www/applyfy/data
# Novos arquivos herdam o grupo www-data; tactical e www-data podem ler/escrever.
# Alternativa: só um usuário usa (ex. tudo como www-data):
# sudo chown -R www-data:www-data /var/www/applyfy/data
```

## 5. PostgreSQL (opcional)

Se quiser que o último relatório seja lido do banco, use o script que cria usuário, banco e reinicia o painel:

```bash
sudo bash /var/www/applyfy/scripts/recriar_banco_postgres.sh
```

Ou manualmente:

```bash
sudo -u postgres createuser -P applyfy
sudo -u postgres createdb -O applyfy applyfy
```

No `.env` (sem espaço antes do nome da variável):

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

**Retry e checkpoint:** O job roda em loop até concluir ou atingir 6 h (`MAX_RUN_HOURS`). O progresso é salvo em `data/export_checkpoint.json`; ao retomar, a exportação continua de onde parou. Para forçar recomeço do zero: `rm -f /var/www/applyfy/data/export_checkpoint.json`.

## 9. Restauração (pós-clone ou após perda da pasta)

Se o projeto foi clonado de novo ou a pasta foi restaurada do GitHub:

1. **Recriar `.env`** (não versionado): `cp .env.example .env` e preencher `APPLYFY_USER`, `APPLYFY_PASSWORD`, `APPLYFY_TOTP_SECRET` e, se usar Postgres, `DATABASE_URL` (ou `PG_*`).
2. **Diretório de dados:** `mkdir -p /var/www/applyfy/data` e ajustar dono se necessário (ex.: `chown -R www-data:www-data /var/www/applyfy/data`).
3. **Venv e dependências:** `python3 -m venv venv`, `source venv/bin/activate`, `pip install -r requirements.txt`, `playwright install chromium`.
4. **Serviço do painel:** usar o unit em `applyfy-painel.service` com `WorkingDirectory=/var/www/applyfy` e `EnvironmentFile=/var/www/applyfy/.env`; depois `sudo systemctl daemon-reload && sudo systemctl restart applyfy-painel`.
5. **Cron:** garantir que o cron do job use o mesmo `.env` (ex.: `source /var/www/applyfy/env.sh` ou `EnvironmentFile`).
6. **Primeira sessão:** rodar uma vez o login/sessão (ex.: `python 01_salvar_sessao.py`) para gerar `data/sessao_applyfy.json`.

## 10. O que mais pode precisar

- **Primeira sessão:** na primeira vez, o login automático pode falhar se os seletores da página de login da Applyfy forem diferentes. Rode com `HEADLESS=0` para ver o browser: `HEADLESS=0 python 01_salvar_sessao.py` e ajuste os seletores em `01_salvar_sessao.py` se necessário.
- **Firewall:** libere 80 e 443 para o Nginx.
- **Troca de senha/2FA:** após testar, troque a senha e regenere o 2FA na Applyfy (as credenciais foram usadas no chat).

## 11. Exportador de vendas ApplyFy (PostgreSQL + upsert)

Arquivos principais:

- `applyfy_export_vendas.py` (orquestrador Playwright)
- `applyfy_parser.py` (payload Next.js + fallback DOM)
- `applyfy_repository.py` (DDL + persistência)
- `03_exportar_vendas.py` (executor)
- `sql/applyfy_vendas.sql` (DDL standalone)

Pré-requisitos:

- Sessão autenticada salva em `data/sessao_applyfy.json` (`python 01_salvar_sessao.py`)
- `DATABASE_URL` configurada para habilitar persistência em Postgres

Execução:

```bash
cd /var/www/applyfy
source venv/bin/activate
python 03_exportar_vendas.py
```

Variáveis úteis:

- `ORDERS_PAGE_SIZE` (default `50`)
- `APPLYFY_HEADED=1` para abrir browser visível (se houver DISPLAY)
- `EXPORT_VENDAS_GOTO_RETRIES` (default `5`) — repetições em `page.goto` se aparecer `net::ERR_NETWORK_CHANGED` ou timeout
- `EXPORT_VENDAS_GOTO_RETRY_SEC` (default `2`) — base de espera entre tentativas (multiplicada pelo número da tentativa)
- `EXPORT_VENDAS_START_PAGINA` — ex.: `29` para **voltar a uma página** e ignorar o checkpoint em disco; a **linha inicial** vem do Postgres: `COALESCE(MAX(linha),0)` em `applyfy_import_log` com `pagina` e `status='OK'` (próxima linha da lista após o último OK naquela página). O checkpoint em disco é atualizado ao iniciar.
- `EXPORT_VENDAS_ORDERS_SEL_TIMEOUT_MS` — timeout só da lista `/admin/orders` (default = `EXPORT_VENDAS_SEL_TIMEOUT_MS` ou 120000).
- `EXPORT_VENDAS_ORDERS_LOAD_RETRIES` (default `3`) — tentativas com `reload` se a tabela não aparecer.
- `EXPORT_VENDAS_ORDERS_SETTLE_MS` (default `2500`) — pausa após `load` para a SPA hidratar.

Arquivos de saída em `data/`:

- `applyfy_orders_log.txt`
- `applyfy_orders_log.csv`
- `applyfy_orders_log.json`
- `orders_export_checkpoint.json` (retomada)

**Painel web — log e job de vendas**

- URL: **`/log-vendas.html`** ou **`/log-vendas`** (ambas servidas pelo Flask após deploy).
- APIs: `GET /api/vendas/log` ou `GET /api/vendas-log`, `GET /api/vendas/import-log` ou `GET /api/vendas-import-log`, `POST /api/job-vendas/start`, `POST /api/job-vendas/stop`.
- Se o HTML carregar mas as APIs retornarem erro em JSON: o `app.py` em produção está desatualizado — faça **git pull** e **`sudo systemctl restart applyfy-painel`** (ou o nome do seu unit).
- **Iniciar export** no painel executa `03_exportar_vendas.py` como o mesmo usuário do gunicorn; exige `venv`, Playwright/Chromium instalados e `data/sessao_applyfy.json` válida.

Comportamento de robustez:

- Estratégia primária: parse do payload Next.js (`source_strategy=payload`)
- Fallback: extração por DOM (`source_strategy=dom`)
- Upsert com chave primária lógica em `transaction_id`
- Retomada automática por checkpoint em falhas/interrupções

Para recriar estrutura do banco manualmente:

```bash
psql "$DATABASE_URL" -f /var/www/applyfy/sql/applyfy_vendas.sql
```
