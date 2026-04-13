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

**Export em paralelo (saldos + vendas):** por defeito cada tipo já usa checkpoint e logs diferentes (`export_checkpoint.json` vs `orders_export_checkpoint.json`, etc.), pelo que pode correr **ao mesmo tempo** sem variável extra. Para **dois jobs do mesmo tipo** ou para nomes explícitos no mesmo `data/`:

- `APPLYFY_EXPORT_ISOLATION` — etiqueta curta (ex.: `saldos`, `vendas`, `worker2`); os ficheiros passam a ter sufixo no nome (ex.: `applyfy_orders_log_vendas.txt`, `orders_export_checkpoint_vendas.json`). Caracteres estranhos são sanitizados.
- `APPLYFY_ISOLATED_SESSION=1` — sessão Playwright **por etiqueta** (`sessao_applyfy_vendas.json`, …). Sem isto, todos os exports partilham `sessao_applyfy.json` (recomendado para um único login).

**Painel web:** o Flask lê `config.ORDERS_LOG_*` ao arrancar. Se o export de vendas usar `APPLYFY_EXPORT_ISOLATION` no cron/CLI, o Gunicorn precisa da **mesma** variável no `.env`/systemd para o log de vendas no painel bater certo — ou deixe a variável vazia se só existir um export de vendas.

**Parar job de saldos (`/api/job/stop`):** envia `pkill` a processos que correspondam a `chromium`, o que pode **encerar também** o browser do export de vendas se estiver na mesma máquina. Use com cuidado se os dois estiverem a correr.

**API Admin e Webhooks (opcional):** para receber vendas/transações em tempo real e consultar taxas dos produtores:

- No painel ApplyFy, em Integrações/API, obtenha as chaves e defina no `.env`:
  - `APPLYFY_PUBLIC_KEY`
  - `APPLYFY_SECRET_KEY`
- Em Integrações > Webhooks, cadastre a URL do webhook e use o mesmo valor no `.env`:
  - `APPLYFY_WEBHOOK_TOKEN=...`

**URL do webhook** (HTTPS obrigatório):

- `https://applyfy.northempresarial.com/api/webhooks/applyfy`

O Nginx deve permitir POST nessa rota; certificado SSL deve estar ativo.

**WAHA (WhatsApp) e notificações:** após cada export bem-sucedido (`run_daily.py`), o sistema pode enviar mensagens pela API [WAHA](https://waha.devlike.pro/) (`POST /api/sendText`). Variáveis típicas no `.env`:

- `WAHA_NOTIFY_ENABLED=1` — liga o envio.
- `WAHA_BASE_URL` — URL base do servidor WAHA (sem barra final).
- `WAHA_NOTIFY_CHAT_ID` — um destino, ex. `5511999999999@c.us` (sem `+`) ou ID de grupo.
- `WAHA_NOTIFY_CHAT_IDS` — opcional: vários destinos com a **mesma** notificação, separados por vírgula (ex.: dois números + um grupo). Se estiver preenchido, esta lista tem prioridade sobre `WAHA_NOTIFY_CHAT_ID`.
- `WAHA_SESSION` — nome da sessão WAHA (muitas instalações usam `default`).
- `WAHA_API_KEY` — se o WAHA exigir autenticação (cabeçalho `X-Api-Key`).
- `APPLYFY_META_VENDAS_LIQUIDAS` — meta em reais para a página `/meta` e para a segunda mensagem (“metas batidas”); default `10000`.

Alertas opcionais:

- `WAHA_ALERT_ON_FAILURE=1` — avisa no WhatsApp em falha de login (`01_salvar_sessao`) ou limite de horas do export.
- `WAHA_ALERT_WEBHOOK_SILENCE=1` — use com o script `scripts/alert_webhook_silence.py` no cron; envia aviso se não houver webhooks há `APPLYFY_WEBHOOK_SILENCE_HOURS` (default 24).

**Privacidade (PII):** mensagens podem incluir nomes, emails e valores financeiros. Limite `WAHA_NOTIFY_CHAT_ID` / `WAHA_NOTIFY_CHAT_IDS` a números/grupos autorizados e proteja `WAHA_API_KEY` e `APPLYFY_ADMIN_TOKEN`.

**Teste manual:** com venv e `.env` carregado, `python scripts/waha_ping.py`. No painel, com `APPLYFY_ADMIN_TOKEN` definido: `POST /api/admin/waha-test` com header `X-Applyfy-Admin-Token`.

**Troubleshooting WAHA:** `401` — API key ou sessão; mensagem não entrega — confirme `chatId` e que a sessão WAHA está `WORKING`; timeouts — firewall entre este servidor e o WAHA.

**Estado e DLQ (operacional):** `GET /api/health` e `GET /api/integracao-status` expõem health, últimos timestamps de export/webhook, fila DLQ e flags (`APPLYFY_EXPORT_STALE_HOURS`, `APPLYFY_WEBHOOK_SILENCE_HOURS`) — uso interno / monitorização, sem página dedicada no painel.

**Fila DLQ (webhooks):** falhas ao gravar em `applyfy_transactions` são guardadas em `applyfy_webhook_dlq`. Listagem e reprocessamento: `GET /api/admin/webhook-dlq` e `POST /api/admin/webhook-dlq/retry` com JSON `{"id": <id>}` e o mesmo token admin.

**Cópia local de transações (evolução diária):** os webhooks alimentam `applyfy_transactions`; o painel grava factos agregáveis em `applyfy_tx_facts` e usa-os em `/api/evolucao` para não paginar a API Admin em cada abertura. A sincronização **não corre sozinha dentro do Flask** — use **cron** (ou systemd timer) no servidor.

**Recomendado — a cada hora** (utilizador `www-data` ou o que corre o painel). Com janela curta reduz-se carga na API em cada execução:

```cron
# A cada hora, no minuto 0 (ajuste o path do venv e do env.sh)
0 * * * * cd /var/www/applyfy && . ./env.sh && APPLYFY_SYNC_WINDOW_DAYS=2 /var/www/applyfy/venv/bin/python scripts/sync_transactions.py >> /var/www/applyfy/data/cron-sync-tx.log 2>&1
```

Exemplo ficheiro: [deploy/cron-sync-transactions-hourly.example](deploy/cron-sync-transactions-hourly.example) (`crontab -e` e colar a linha).

Sincronização **diária** (alternativa mais leve na API):

```bash
cd /var/www/applyfy && . env.sh && /var/www/applyfy/venv/bin/python scripts/sync_transactions.py >> /var/www/applyfy/data/cron.log 2>&1
```

Variáveis opcionais: `APPLYFY_SYNC_WINDOW_DAYS` (default 14; use **2–7** se correr **horária**), `APPLYFY_SYNC_MAX_PAGES`. Chamadas `POST /api/internal/sync-transactions` com `{"quick":true}` (primeiros N produtores, ver `APPLYFY_SYNC_QUICK_*`) são para uso controlado (não expostas como botão no painel público). Sync **completa** via cron não deve usar `quick`. **HTTP 504** no painel: aumente `proxy_read_timeout` no Nginx para `/api/internal/sync-transactions` (ex.: 600s, ver `nginx-applyfy.conf`) e `--timeout` do Gunicorn (≥600); depois `sudo systemctl daemon-reload && sudo systemctl restart applyfy-painel && sudo nginx -t && sudo systemctl reload nginx`.

Na primeira vez, pode executar `scripts/sync_transactions.py --backfill-webhooks` para derivar factos dos webhooks já guardados. Sincronização HTTP alternativa: `POST /api/internal/sync-transactions` com corpo vazio (janela rolling) ou JSON `{"email","from","to"}`; autenticação: header `X-Applyfy-Sync-Secret` se `APPLYFY_SYNC_SECRET` estiver definido, senão token admin (`X-Applyfy-Admin-Token`) ou sessão Hub (`applyfy.jobs` / `applyfy.admin`).

**Documentação interna:** [docs/RECONCILIACAO.md](docs/RECONCILIACAO.md), [docs/API_VS_PLAYWRIGHT.md](docs/API_VS_PLAYWRIGHT.md).

Para o cron, crie um script que carrega o `.env` antes de rodar, por exemplo `env.sh`:

```bash
# env.sh (não commitar com valores reais)
set -a
source /var/www/applyfy/.env
set +a
export APPLYFY_DATA_DIR=/var/www/applyfy/data
# Recomendado se o Chromium do Playwright estiver em path partilhado (ex.: cron como www-data):
export PLAYWRIGHT_BROWSERS_PATH=/var/www/applyfy/.playwright-browsers
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

## 5b. Ficheiros estáticos do painel (`static/`)

O Flask serve `/`, `/historico`, `/vendas`, etc. a partir de **`static/*.html`**. Se esses ficheiros **não existirem**, o browser mostra **Not Found** (404 do Flask).

- Garanta que a pasta `static/` no servidor contém os HTML referidos em `app.py` (ex.: `index.html`, `historico.html`, `vendas.html`, …). O tema e o layout estão sobretudo em **`<style>` inline** nesses HTML (não há ficheiros `.css` separados obrigatórios no repositório atual).
- Após deploy, valide o tema em **`/design-system`** (card, badges, modal de exemplo) e o painel em **`/`**.
- Após `git pull` ou cópia incompleta do projeto, volte a colocar os HTML ou faça deploy a partir do repositório completo.
- Reinicie o Gunicorn: `sudo systemctl restart applyfy-painel` (ou o nome do seu unit).

Teste rápido: `curl -sI https://applyfy.northempresarial.com/health` → `200`; `curl -s https://applyfy.northempresarial.com/api/health` → JSON com `ok`; `curl -sI https://applyfy.northempresarial.com/` → `200` com `text/html`.

## 5c. Usabilidade e validação do painel

| Página | URL | Função |
|--------|-----|--------|
| Início | `/` | Links para módulos + último relatório de saldos |
| Referência UI | `/design-system` | Cards, badges, modal (tema Applyfy) |
| Histórico | `/historico` | Datas e relatório por `run_at` |
| Vendas | `/vendas` | Lista em cards (API `/api/vendas`) |
| Transações | `/transacoes` | Webhook em cards (API `/api/transacoes`) |
| Meta | `/meta` | Progresso vs meta de vendas líquidas (`/api/settings`) |
| Log saldos | `/log` | Texto `applyfy_log.txt` + excerto `cron.log` (`/api/log`) |
| Financeiro | `/financeiro` | Categorias (API) |
| Produtores | `/produtores` | Lista para dropdown |
| Evolução | `/evolucao` | Gráfico/dados por email |

Validação automática (com venv ativo, na raiz do projeto):

```bash
python scripts/validate_painel.py
```

Deve imprimir `OK`. Ver também [USABILIDADE.md](USABILIDADE.md) no repositório.

## 6. Rodar a API com Gunicorn atrás do Nginx

```bash
cd /var/www/applyfy
source venv/bin/activate
gunicorn --no-control-socket -w 1 -b 127.0.0.1:5000 --timeout 600 app:app
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
# O prefixo "-" faz o systemd NÃO falhar se o ficheiro não existir (evita Result=resources).
EnvironmentFile=-/var/www/applyfy/.env
ExecStart=/var/www/applyfy/venv/bin/gunicorn --no-control-socket -w 1 -b 127.0.0.1:5000 --timeout 600 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**Ficheiro `.env`:** crie a partir do exemplo (`cp .env.example .env`) e preencha credenciais. Sem `.env`, o serviço ainda arranca se usar `EnvironmentFile=-/...` acima; com `EnvironmentFile=/...` (sem hífen), **falta de `.env` quebra o `systemctl start`** com `Failed to load environment files` e `result 'resources'`.

**Produção (segredo):** com login Hub (`APPLYFY_AUTH_ENABLED=1`), defina `FLASK_SECRET_KEY` estável (ver [`docs/env-bloco-hub-exemplo.env`](docs/env-bloco-hub-exemplo.env)). Restringir leitura: `sudo chown root:www-data /var/www/applyfy/.env && sudo chmod 640 /var/www/applyfy/.env` — o Gunicorn lê como `www-data`; edite o `.env` com `sudo`.

**Permissões para `www-data`:** o processo do Gunicorn corre como `www-data` e precisa de **ler** o código e o `venv`:

```bash
sudo chgrp -R www-data /var/www/applyfy
sudo chmod -R g+rX /var/www/applyfy
sudo chmod g+w /var/www/applyfy/data   # se o painel/export gravar em data/
```

Com **Gunicorn 25+**, o socket de controlo por defeito tenta escrever num caminho inacessível ao `www-data` (ex. `/var/www/.gunicorn`). O unit em [`applyfy-painel.service`](applyfy-painel.service) usa **`--no-control-socket`** para evitar esse erro; mantenha-o no `ExecStart` ao copiar da documentação.

**Após falhas em cadeia:** `sudo systemctl reset-failed applyfy-painel && sudo systemctl start applyfy-painel`

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

**Retry e checkpoint:** O job roda em loop até concluir ou atingir 6 h (`MAX_RUN_HOURS`). O progresso é salvo em `data/export_checkpoint.json` (ou `export_checkpoint_<etiqueta>.json` se `APPLYFY_EXPORT_ISOLATION` estiver definido); ao retomar, a exportação continua de onde parou. Para forçar recomeço do zero, apague o ficheiro de checkpoint correspondente em `data/`.

**Exemplo — saldos e vendas em simultâneo (dois terminais ou dois cron):**

```bash
# Terminal A (saldos) — opcional: etiqueta só para não misturar com outro job de saldos
export APPLYFY_EXPORT_ISOLATION=saldos
python run_daily.py   # ou o script que chama export_saldos

# Terminal B (vendas)
export APPLYFY_EXPORT_ISOLATION=vendas
python 03_exportar_vendas.py
```

Sem etiquetas, também funciona em paralelo (checkpoints já são distintos por tipo de export).

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

**Importante:** o ficheiro `applyfy_parser.py` precisa da **implementação completa** (payload Next.js + fallback DOM) que lê o detalhe do pedido na ApplyFy. Se estiver uma versão mínima que devolve lista vazia, o export **não extrai vendas** (erro tipo “Parse não retornou vendas”). Recupere o `applyfy_parser.py` (e, se necessário, `applyfy_models.py`) do backup ou repositório original do projeto.

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

Arquivos de saída em `data/` (com `APPLYFY_EXPORT_ISOLATION=vendas`, os nomes ganham sufixo `_vendas` antes da extensão):

- `applyfy_orders_log.txt`
- `applyfy_orders_log.csv`
- `applyfy_orders_log.json`
- `orders_export_checkpoint.json` (retomada)

**Painel web — job e APIs de vendas**

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
