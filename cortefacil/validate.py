"""Validação do que chega da interface: só aceita valores no formato esperado.

Tudo que vai para o ffmpeg (cores, nome da música) ou para o HTML (emoji, textos) passa por aqui,
para que um valor estranho não vire filtro injetado, caminho de arquivo ou HTML.
"""
from __future__ import annotations

import math
import re

from styles import ANIMS, CUSTOM_KEYS, FONTS, FORMATS, PACES, STYLES

HEX = re.compile(r"#?[0-9A-Fa-f]{6}")
MUSIC = re.compile(r"music\.(mp3|m4a|wav|aac|ogg)")
BAD_TXT = re.compile(r"[<>\x00-\x1f]")

BOOLS = {"cut_silence", "remove_fillers", "zoom", "emojis", "progress_bar", "captions", "push_in",
         "safe_guides", "enhance"}
CHOICES = {
    "style": set(STYLES), "format": set(FORMATS), "fit": {"crop", "blur"}, "pace": set(PACES),
    "llm": {"auto", "claude", "codex", "none"}, "sfx": {"off", "sutil", "marcante"},
}
NULLABLE_CHOICES = {"title_font": set(FONTS), "title_bg": {"none", "box"}, "zoom_mode": {"cuts", "topics", "off"}}
NUMS = {  # chave: (mín, máx, pode ser None)
    "caption_y": (0.0, 1.0, True), "title_y": (0.0, 1.0, True), "callout_y": (0.0, 1.0, False),
    "caption_scale": (0.3, 3.0, False), "title_scale": (0.3, 3.0, True), "music_volume": (0.0, 1.0, False),
    "title_secs": (0.0, 999.0, False),
}
CUSTOM_COLORS = {"text", "active", "kw", "box", "stroke_color"}
CUSTOM_NUMS = {"stroke": (0, 30), "max_words": (1, 8), "kw_scale": (0.5, 2.0)}


class Invalid(ValueError):
    pass


def color(v):
    if v is None:
        return None
    if isinstance(v, str) and HEX.fullmatch(v):
        return "#" + v.lstrip("#").upper()
    raise Invalid("cor inválida")


def num(v, lo, hi, nullable=False):
    if v is None and nullable:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise Invalid("número inválido")
    return max(lo, min(hi, v))


def text(v, limit):
    if not isinstance(v, str):
        raise Invalid("texto inválido")
    return BAD_TXT.sub("", v)[:limit]


def emoji(v):
    if not isinstance(v, str):
        raise Invalid("emoji inválido")
    v = re.sub(r"[\x00-\x7f]|\w|\s", "", v)  # só símbolos (emoji): nada de ASCII, letras ou espaços
    return v[:8]


def custom(v):
    if not isinstance(v, dict):
        raise Invalid("personalização inválida")
    out = {}
    for k, x in v.items():
        if k not in CUSTOM_KEYS or x is None:
            continue
        try:
            _custom_one(out, k, x)
        except (Invalid, TypeError, ValueError):
            continue
    return out


def _custom_one(out: dict, k, x) -> None:
    if k in CUSTOM_COLORS:
        out[k] = color(x)
    elif k in ("font", "kw_font"):
        if x in FONTS or (k == "kw_font" and x == ""):
            out[k] = x
    elif k == "anim":
        if x in ANIMS:
            out[k] = x
    elif k == "active_mode":
        if x in ("color", "box", "none"):
            out[k] = x
    elif k in ("upper", "shadow"):
        out[k] = bool(x)
    elif k in CUSTOM_NUMS:
        lo, hi = CUSTOM_NUMS[k]
        out[k] = num(x, lo, hi)
        if k == "max_words":
            out[k] = int(out[k])


def settings(body: dict) -> dict:
    """Devolve só as chaves válidas, já normalizadas. Valor malformado é descartado (fica o anterior)."""
    if not isinstance(body, dict):
        return {}
    out = {}
    for k, v in body.items():
        try:
            _one(out, k, v)
        except (Invalid, TypeError, ValueError, AttributeError):
            continue
    return out


def _one(out: dict, k, v) -> None:
    if k in BOOLS:
        out[k] = bool(v)
    elif k in CHOICES:
        if v not in CHOICES[k]:
            raise Invalid(f"valor inválido para {k}")
        out[k] = v
    elif k in NULLABLE_CHOICES:
        if v is not None and v not in NULLABLE_CHOICES[k]:
            raise Invalid(f"valor inválido para {k}")
        out[k] = v
    elif k in NUMS:
        lo, hi, nullable = NUMS[k]
        out[k] = num(v, lo, hi, nullable)
    elif k in ("accent", "title_color"):
        out[k] = color(v)
    elif k == "title":
        out[k] = text(v, 120)
    elif k == "custom":
        out[k] = custom(v)
    elif k == "music":
        if v is not None and not (isinstance(v, str) and MUSIC.fullmatch(v)):
            raise Invalid("música inválida")
        out[k] = v
    elif k == "topics":
        out[k] = [{"word_id": int(num(t.get("word_id"), 0, 10**7)), "text": text(t.get("text", ""), 60)}
                  for t in (v if isinstance(v, list) else []) if isinstance(t, dict)][:100]
    elif k == "callouts":
        out[k] = [{"start_id": int(num(c.get("start_id"), 0, 10**7)),
                   "end_id": int(num(c.get("end_id", c.get("start_id")), 0, 10**7)),
                   "text": text(c.get("text", ""), 70)}
                  for c in (v if isinstance(v, list) else []) if isinstance(c, dict)][:100]
    return out


def word(w: dict) -> dict:
    out = {}
    try:
        if "text" in w:
            out["text"] = text(w["text"], 60)
        if "kw" in w:
            out["kw"] = bool(w["kw"])
        if "removed" in w:
            out["removed"] = bool(w["removed"])
        if "emoji" in w:
            out["emoji"] = emoji(w["emoji"] or "")
    except Invalid:
        pass
    return out
