"""Apoio e patrocínio: base para monetizar o CorteFácil sem trair a privacidade de quem usa.

O conteúdo vem de um arquivo JSON publicado no site (promo.json), lido no máximo 1x por dia.
Assim dá para ligar, trocar ou desligar patrocinadores e links de apoio SEM lançar versão nova.

Princípios (não quebre):
- Nenhum dado do usuário é enviado. O pedido leva só o user-agent `cortefacil/<versão>`, e o
  número de pedidos por dia é a única métrica de uso do projeto. Não há contagem de visualizações
  nem de cliques. Para medir resultado, o patrocinador usa cupom ou UTM no próprio link.
- Dá para desligar em Preferências › "Avisos do CorteFácil" (aí o app não faz nenhum pedido ao site).
- Imagens só do domínio do CorteFácil (uma imagem de terceiros revelaria o IP de quem abre o app).
- Links só https. Todo texto é validado e limitado. Patrocínio é sempre rotulado como tal.
- Cada aviso pode ser fechado; fechado, não volta.
- Sem internet ou com o arquivo inválido, nada aparece e nada quebra.

Formato do promo.json (tudo opcional):
{
  "version": 1,
  "support": {"title": "...", "text": "...",
              "links": [{"label": "GitHub Sponsors", "url": "https://..."}], "pix": "chave-pix"},
  "campaigns": [{"id": "marca-2027-01", "slot": "home" | "export", "kind": "sponsor" | "house" | "affiliate",
                 "title": "...", "text": "...", "cta": "Conhecer", "url": "https://...",
                 "image": "https://cortefacil.melhor.dev/promo/marca.png",
                 "start": "2027-01-01", "end": "2027-01-31"}]
}
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

URL = os.environ.get("CORTEFACIL_PROMO_URL", "https://cortefacil.melhor.dev/promo.json")
IMAGE_HOSTS = {"cortefacil.melhor.dev"}
HOME = Path(__file__).resolve().parent.parent
CACHE = HOME / "logs" / "promo.json"
EVERY = 24 * 3600
SLOTS = {"home", "export"}
KINDS = {"sponsor": "Patrocinado", "affiliate": "Indicação (link de parceiro)", "house": "CorteFácil"}
ID = re.compile(r"[a-z0-9][a-z0-9\-_.]{0,63}")


def _txt(v, limit: int) -> str:
    if not isinstance(v, str):
        return ""
    return re.sub(r"[<>\x00-\x1f]", "", v).strip()[:limit]


def _https(v, hosts: set[str] | None = None) -> str:
    if not isinstance(v, str) or len(v) > 600:
        return ""
    u = urlsplit(v.strip())
    if u.scheme != "https" or not u.hostname:
        return ""
    if hosts is not None and u.hostname.lower() not in hosts:
        return ""
    return v.strip()


def _day(v) -> date | None:
    try:
        return date.fromisoformat(v) if isinstance(v, str) else None
    except ValueError:
        return None


def sanitize(raw: dict, today: date | None = None) -> dict:
    """Só passa o que está no formato esperado; o resto é descartado em silêncio."""
    today = today or date.today()
    out: dict = {"support": None, "campaigns": []}
    if not isinstance(raw, dict):
        return out
    sup = raw.get("support")
    if isinstance(sup, dict):
        links = []
        for lk in (sup.get("links") or [])[:4]:
            if isinstance(lk, dict) and _https(lk.get("url")) and _txt(lk.get("label"), 30):
                links.append({"label": _txt(lk["label"], 30), "url": _https(lk["url"])})
        pix = _txt(sup.get("pix"), 80)
        if links or pix:
            out["support"] = {"title": _txt(sup.get("title"), 60) or "Apoie o CorteFácil",
                              "text": _txt(sup.get("text"), 240), "links": links, "pix": pix}
    for c in (raw.get("campaigns") or [])[:20]:
        if not isinstance(c, dict):
            continue
        cid, slot, kind = c.get("id"), c.get("slot"), c.get("kind", "sponsor")
        url, title = _https(c.get("url")), _txt(c.get("title"), 70)
        if not (isinstance(cid, str) and ID.fullmatch(cid) and slot in SLOTS and kind in KINDS and url and title):
            continue
        start, end = _day(c.get("start")), _day(c.get("end"))
        if (start and today < start) or (end and today > end):
            continue
        out["campaigns"].append({"id": cid, "slot": slot, "kind": kind, "label": KINDS[kind], "title": title,
                                 "text": _txt(c.get("text"), 180), "cta": _txt(c.get("cta"), 24) or "Saiba mais",
                                 "url": url, "image": _https(c.get("image"), IMAGE_HOSTS)})
    return out


def version() -> str:
    try:
        v = (HOME / "VERSION").read_text().strip()
    except OSError:
        return "0"
    return v if re.fullmatch(r"[0-9][0-9A-Za-z.\-]{0,20}", v) else "0"


def fetch(force: bool = False) -> dict:
    """Config crua (do cache se tiver menos de 1 dia). Nunca levanta erro."""
    try:
        cached = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cached = {}
    if not force and cached and time.time() - cached.get("_at", 0) < EVERY:
        return cached.get("data") or {}
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": f"cortefacil/{version()}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            if r.length and r.length > 200_000:
                raise ValueError("grande demais")
            data = json.loads(r.read(200_001)[:200_000])
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps({"_at": time.time(), "data": data}, ensure_ascii=False))
        return data
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return cached.get("data") or {}


def visible(dismissed: list[str], enabled: bool = True) -> dict:
    if not enabled:
        return {"support": None, "campaigns": [], "enabled": False}
    cfg = sanitize(fetch())
    cfg["enabled"] = True
    cfg["campaigns"] = [c for c in cfg["campaigns"] if c["id"] not in set(dismissed or [])]
    return cfg
