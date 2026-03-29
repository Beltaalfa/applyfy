# -*- coding: utf-8 -*-
"""Cliente HTTP mínimo para WAHA (POST /api/sendText). Sem dependência extra (urllib)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

# Cloudflare (erro 1010) bloqueia muitos clientes sem User-Agent de browser.
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _request_headers() -> dict[str, str]:
    h = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "User-Agent": (os.environ.get("WAHA_HTTP_USER_AGENT") or "").strip() or _DEFAULT_UA,
    }
    return h


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def notify_chat_ids() -> list[str]:
    """
    Lista de destinos (número@c.us ou grupo@g.us).
    Usa WAHA_NOTIFY_CHAT_IDS (vários, separados por vírgula ou quebra de linha);
    se vazio, usa só WAHA_NOTIFY_CHAT_ID.
    """
    raw = (os.environ.get("WAHA_NOTIFY_CHAT_IDS") or "").strip()
    if raw:
        out: list[str] = []
        for part in raw.replace("\n", ",").split(","):
            p = part.strip()
            if p:
                out.append(p)
        if out:
            return out
    one = (os.environ.get("WAHA_NOTIFY_CHAT_ID") or "").strip()
    return [one] if one else []


def is_waha_configured() -> bool:
    if not _truthy("WAHA_NOTIFY_ENABLED"):
        return False
    base = (os.environ.get("WAHA_BASE_URL") or "").strip().rstrip("/")
    return bool(base and notify_chat_ids())


def _send_text_one(
    base: str,
    session: str,
    chat_id: str,
    text: str,
    api_key: str,
    timeout_sec: float,
) -> tuple[bool, str]:
    url = f"{base}/api/sendText"
    body = json.dumps(
        {"session": session, "chatId": chat_id, "text": text},
        ensure_ascii=False,
    ).encode("utf-8")
    hdrs = _request_headers()
    req = urllib.request.Request(url, data=body, method="POST", headers=hdrs)
    if api_key:
        req.add_header("X-Api-Key", api_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            _ = resp.read()
        return True, ""
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            detail = str(e)
        return False, f"HTTP {e.code}: {detail}"
    except urllib.error.URLError as e:
        return False, str(e.reason if hasattr(e, "reason") else e)
    except Exception as e:
        return False, str(e)


def send_text(text: str, timeout_sec: float = 15.0) -> tuple[bool, str]:
    """
    Envia o mesmo texto a todos os destinos em notify_chat_ids().
    Retorna (True, "") só se todos tiverem sucesso; senão (False, erros concatenados).
    Documentação: https://waha.devlike.pro/docs/how-to/send-messages/
    """
    if not _truthy("WAHA_NOTIFY_ENABLED"):
        return False, "WAHA_NOTIFY_ENABLED não está ativo"
    base = (os.environ.get("WAHA_BASE_URL") or "").strip().rstrip("/")
    session = (os.environ.get("WAHA_SESSION") or "default").strip() or "default"
    api_key = (os.environ.get("WAHA_API_KEY") or "").strip()
    chat_ids = notify_chat_ids()

    if not base or not chat_ids:
        return False, "WAHA_BASE_URL ou WAHA_NOTIFY_CHAT_ID(S) ausente"

    try:
        delay = float((os.environ.get("WAHA_SEND_DELAY_SEC") or "1.2").replace(",", "."))
    except ValueError:
        delay = 1.2
    if delay < 0:
        delay = 0.0

    errs: list[str] = []
    for i, chat_id in enumerate(chat_ids):
        if i > 0 and delay > 0:
            time.sleep(delay)
        ok, err = _send_text_one(base, session, chat_id, text, api_key, timeout_sec)
        if not ok:
            errs.append(f"{chat_id}: {err}")
    if errs:
        return False, " | ".join(errs)
    return True, ""
