# Applyfy – painel e exports

Painel web (Flask) e scripts de exportação de dados da plataforma Applyfy.

## Arranque rápido (desenvolvimento)

```bash
cd /var/www/applyfy   # ou o path onde clonaste o repo
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env       # editar .env (não commitar)
flask run                  # ou ver DEPLOY.md para Gunicorn
```

## Onde está documentado o resto

| Ficheiro | Conteúdo |
|----------|----------|
| **[DEPLOY.md](DEPLOY.md)** | Servidor Ubuntu, venv, `.env`, `data/`, PostgreSQL opcional, **systemd** (`applyfy-painel`), **Nginx**, SSL, cron, troubleshooting. |
| **[USABILIDADE.md](USABILIDADE.md)** | Mapa de URLs do painel e usabilidade (se existir no teu clone). |

## Produção (resumo)

- Path típico no VPS: **`/var/www/applyfy`**
- Domínio de referência: **applyfy.northempresarial.com** (ajusta ao teu DNS).
- Páginas HTML: **`templates/pages/`** (Jinja); ficheiros estáticos em **`static/`**.

## Git entre PC e VPS

1. **Um repositório remoto** (GitHub/GitLab/etc.) como fonte de verdade — ou `git pull` / `git push` entre máquinas.
2. Na VPS: `git clone …` ou `git pull` em `/var/www/applyfy`.
3. Garante que **`.env` não entra no Git** (mantém só local na VPS e no teu PC).

## Cursor / assistente noutro workspace

- As regras do projeto ficam em **`.cursor/rules/`** (versionadas com o Git).
- Abres a **mesma pasta do repo** noutro PC ou via Remote SSH; depois de `git pull`, o assistente lê `DEPLOY.md` e as regras automaticamente.
