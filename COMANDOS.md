# Comandos para colar no terminal (passo a passo)

Siga **na ordem**. Cada bloco é um comando (ou vários) que você pode **copiar e colar** no terminal do servidor (SSH).

**Resumo:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Depois que o site abrir, use o passo 9 para HTTPS.

**Atalho do passo 2:** depois do passo 1, você pode rodar um script que faz o passo 2 sozinho:
```bash
cd /var/www/applyfy && ./instalar.sh
```

---

## 1) Instalar dependências do sistema (só uma vez) — OBRIGATÓRIO

*(Sem isso o passo 2 não funciona.)*

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libpq-dev
```

**Dependências do Chromium (Playwright)** – se ao rodar o job der erro `libatk-1.0.so.0` ou “cannot open shared object”:

```bash
sudo apt install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 libnss3
```

Se der erro com python3-venv, tente (troque 3.10 pela sua versão do Python, ex.: 3.11):

```bash
sudo apt install -y python3.10-venv python3-pip libpq-dev
```

---

## 2) Entrar na pasta do projeto e criar o ambiente Python (só uma vez)

**Opção A – script automático (recomendado):**

```bash
cd /var/www/applyfy
./instalar.sh
```

**Opção B – comando por comando:**

```bash
cd /var/www/applyfy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

*(Se der erro em algum comando, anote a mensagem e peça ajuda.)*

---

## 3) Criar o arquivo .env com suas credenciais (só uma vez)

```bash
cd /var/www/applyfy
cp .env.example .env
```

Depois **abra o arquivo .env para editar** (troque pelo seu editor se preferir):

```bash
nano .env
```

Preencha estas três linhas com **seus** dados da Applyfy (email, senha e chave do 2FA):

- `APPLYFY_USER=seu_email@exemplo.com`
- `APPLYFY_PASSWORD='sua_senha'`   ← use **aspas simples** se a senha tiver $ # ( ) *
- `APPLYFY_TOTP_SECRET=SUA_CHAVE_2FA`

Salve: no nano é **Ctrl+O**, Enter, depois **Ctrl+X** para sair.

---

## 4) Criar pasta de dados e permissões (só uma vez)

```bash
mkdir -p /var/www/applyfy/data
sudo chown -R www-data:www-data /var/www/applyfy/data
```

*(Se você rodar o painel com outro usuário, troque `www-data` por esse usuário.)*

---

## 5) Configurar o Nginx (só uma vez)

```bash
sudo cp /var/www/applyfy/nginx-applyfy.conf /etc/nginx/sites-available/applyfy
sudo ln -sf /etc/nginx/sites-available/applyfy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

*(Antes disso, no seu provedor de domínio, aponte **applyfy.northempresarial.com** para o IP deste servidor.)*

---

## 6) Ativar o painel para ficar sempre rodando (systemd) (só uma vez)

```bash
sudo cp /var/www/applyfy/applyfy-painel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable applyfy-painel
sudo systemctl start applyfy-painel
```

Para ver se está rodando:

```bash
sudo systemctl status applyfy-painel
```

*(Se aparecer "active (running)", está ok.)*

---

## 7) Criar o env.sh para o cron (só uma vez)

O arquivo `env.sh` já está no projeto. Só confira se o caminho do `.env` está certo:

```bash
cat /var/www/applyfy/env.sh
```

Se estiver tudo certo, deixe o arquivo executável:

```bash
chmod +x /var/www/applyfy/env.sh
```

---

## 8) Agendar atualização todo dia às 2h da manhã (cron) (só uma vez)

Abra o cron do usuário www-data:

```bash
sudo crontab -u www-data -e
```

*(Se pedir para escolher editor, escolha nano: digite o número do nano e Enter.)*

No final do arquivo que abrir, **adicione esta linha** (uma linha só):

```
0 2 * * * cd /var/www/applyfy && . env.sh && /var/www/applyfy/venv/bin/python run_daily.py >> /var/www/applyfy/data/cron.log 2>&1
```

Salve (nano: **Ctrl+O**, Enter, **Ctrl+X**).

---

## 9) SSL (HTTPS) – depois que o site estiver abrindo em http

Quando **applyfy.northempresarial.com** já estiver abrindo em HTTP, rode:

```bash
sudo certbot --nginx -d applyfy.northempresarial.com
```

Siga as perguntas na tela. Depois o site passará a abrir em HTTPS.

---

## Comandos úteis depois que tudo estiver pronto

- **Ver se o painel está rodando:**  
  `sudo systemctl status applyfy-painel`

- **Reiniciar o painel:**  
  `sudo systemctl restart applyfy-painel`

- **Ver o log do job das 2h:**  
  `cat /var/www/applyfy/data/cron.log`

- **Rodar o job manualmente (login + exportação):**  
  `cd /var/www/applyfy && . env.sh && /var/www/applyfy/venv/bin/python run_daily.py`

- **Testar só o login (com browser visível, para debug):**  
  `cd /var/www/applyfy && . env.sh && HEADLESS=0 /var/www/applyfy/venv/bin/python 01_salvar_sessao.py`
