"""Desenho das legendas e da faixa do topo, com animações (pop, subir, aparecer) quadro a quadro.

O render monta um "stream" de imagens PNG via concat do ffmpeg: quadros animados só nas janelas de
transição (~0,25 s) e uma imagem parada no resto do tempo. Os quadros são desenhados em paralelo.
"""
from __future__ import annotations

import math
import os
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from styles import FONTS, resolve_style, resolve_title

_FONTDIR = Path(__file__).parent / "fonts"
EMOJI_FONTS = [  # (arquivo, tamanho nativo do bitmap)
    ("/System/Library/Fonts/Apple Color Emoji.ttc", 160),
    ("C:/Windows/Fonts/seguiemj.ttf", 109),
    ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109),
    ("/usr/share/fonts/noto/NotoColorEmoji.ttf", 109),
    ("/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf", 109),
]
PAGE_IN = 0.24      # duração da entrada da legenda (s)
WORD_IN = 0.18      # "soco" da palavra falada (s)
TITLE_IN = 0.32
TITLE_OUT = 0.22


# ----------------------------------------------------------------------------- utilidades

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def even(x: float) -> int:
    return max(2, int(round(x / 2)) * 2)


@lru_cache(maxsize=128)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(6, size))


@lru_cache(maxsize=128)
def _emoji_base(ch: str) -> Image.Image | None:
    for path, native in EMOJI_FONTS:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, native)
            except OSError:
                continue
            im = Image.new("RGBA", (native + 60, native + 60), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
            bbox = im.getbbox()
            return im.crop(bbox) if bbox else None
    return None


def emoji_img(ch: str, size: int) -> Image.Image | None:
    im = _emoji_base(ch)
    if im is None or size < 2:
        return None
    r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def hex_rgba(h: str, a: int = 255) -> tuple:
    h = (h or "#FFFFFF").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def is_emoji_char(ch: str) -> bool:
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0xFE0F, 0x200D) or unicodedata.category(ch) == "So"


def add_shadow(layer: Image.Image, strength=150, radius=10, dy=6) -> Image.Image:
    """Sombra suave; o desfoque é feito em meia resolução (bem mais rápido)."""
    a = layer.getchannel("A").point(lambda v: v * strength // 255)
    small = a.resize((max(1, a.width // 2), max(1, a.height // 2)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(max(1, radius / 2)))
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(small.resize(a.size, Image.BILINEAR))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, dy))
    out.alpha_composite(layer)
    return out


def _transform(img: Image.Image, scale: float, cx: float, cy: float, dy: float, alpha: float) -> Image.Image:
    if abs(scale - 1) < 1e-3 and abs(dy) < 0.5 and alpha >= 0.999:
        return img
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    if abs(scale - 1) >= 1e-3:
        w, h = max(1, int(img.width * scale)), max(1, int(img.height * scale))
        sc = img.resize((w, h), Image.BILINEAR)
        out.alpha_composite(sc, (int(round(cx - cx * scale)), int(round(cy - cy * scale + dy))))
    else:
        out.alpha_composite(img, (0, int(round(dy))))
    if alpha < 0.999:
        out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    return out


# ----------------------------------------------------------------------------- legenda

class CaptionPainter:
    def __init__(self, settings: dict, W: int, H: int):
        self.st = settings
        self.s = resolve_style(settings)
        self.W, self.H = W, H
        unit = min(W, H) / 1080
        self.base = self.s["size"] * unit * float(settings.get("caption_scale") or 1.0)
        self.band_h = even(min(H, max(600, self.base * 6.6)))
        cy = settings.get("caption_y")
        cy = self.s["y"] if cy is None else float(cy)
        text_center = cy * H
        self.band_y = int(min(max(0, text_center - self.band_h * 0.64), H - self.band_h))
        self.text_y = text_center - self.band_y
        self._layout_cache: dict = {}

    def word_text(self, w):
        return w["text"].upper() if self.s.get("upper") else w["text"]

    def _layout(self, key, page):
        if key in self._layout_cache:
            return self._layout_cache[key]
        s, W = self.s, self.W
        items = []
        for i, w in enumerate(page):
            size = int(self.base * (s["kw_scale"] if w.get("kw") else 1.0))
            ffile = s["kw_font_file"] if w.get("kw") else s["font_file"]
            f = font(ffile, size)
            txt = self.word_text(w)
            items.append({"w": w, "i": i, "txt": txt, "size": size, "f": f, "file": ffile, "tw": f.getlength(txt)})
        max_w, space = W * 0.84, self.base * 0.34
        lines, cur, cw = [], [], 0.0
        for it in items:
            add = it["tw"] + (space if cur else 0)
            if cur and cw + add > max_w:
                lines.append(cur)
                cur, cw, add = [], 0.0, it["tw"]
            cur.append(it)
            cw += add
        if cur:
            lines.append(cur)
        if len(lines) == 2:
            flat = lines[0] + lines[1]
            best = None
            for k in range(1, len(flat)):
                w1 = sum(x["tw"] for x in flat[:k]) + space * (k - 1)
                w2 = sum(x["tw"] for x in flat[k:]) + space * (len(flat) - k - 1)
                if max(w1, w2) <= max_w and (best is None or max(w1, w2) < best[0]):
                    best = (max(w1, w2), k)
            if best:
                lines = [flat[:best[1]], flat[best[1]:]]
        line_h = self.base * 1.2
        top = self.text_y - line_h * len(lines) / 2
        for li, line in enumerate(lines):
            lw = sum(x["tw"] for x in line) + space * (len(line) - 1)
            x = (W - lw) / 2
            base_y = top + line_h * (li + 0.8)
            for it in line:
                it["x"], it["y"] = x, base_y
                x += it["tw"] + space
        res = (items, top)
        self._layout_cache[key] = res
        return res

    def render(self, key, page: list[dict], active: int, page_t: float, word_t: float) -> Image.Image:
        s, W = self.s, self.W
        items, top = self._layout(key, page)
        anim = s.get("anim", "pop")
        layer = Image.new("RGBA", (W, self.band_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        stroke = int(round(s.get("stroke", 0) * self.base / s["size"])) if s.get("stroke") else 0
        stroke_fill = hex_rgba(s.get("stroke_color", "#000000"))
        mode = s.get("active_mode", "color")
        punch = 1.0
        if anim != "none" and 0 <= active < len(items):
            punch = 1 + 0.10 * (1 - ease_out_cubic(clamp(word_t / WORD_IN)))
        for it in items:
            w, i = it["w"], it["i"]
            is_act = i == active and mode != "none"
            color = s["text"]
            if w.get("kw"):
                color = s["kw"]
            if is_act and mode == "color" and not w.get("kw"):
                color = s["active"]
            sc = punch if i == active else 1.0
            f = it["f"] if sc == 1.0 else font(it["file"], int(it["size"] * sc))
            cx = it["x"] + it["tw"] / 2
            if is_act and mode == "box":
                tw = it["tw"] * sc
                asc, desc = f.getmetrics()
                pad = self.base * 0.17
                d.rounded_rectangle([cx - tw / 2 - pad, it["y"] - asc * 0.80 - pad * 0.7,
                                     cx + tw / 2 + pad, it["y"] + desc * 0.40 + pad * 0.7],
                                    radius=int(self.base * 0.2), fill=hex_rgba(s.get("box", "#7B2FF7")))
                color = "#FFFFFF"
            d.text((cx, it["y"]), it["txt"], font=f, fill=hex_rgba(color), anchor="ms",
                   stroke_width=stroke, stroke_fill=stroke_fill)
        if s.get("shadow", True):
            layer = add_shadow(layer, strength=160 if stroke else 210,
                               radius=max(6, int(self.base * 0.16)), dy=int(self.base * 0.06))
        # emoji acima do bloco (entra com elástico quando a palavra-chave é falada)
        if self.st.get("emojis", True):
            em, em_idx = None, -1
            for i, w in enumerate(page):
                if w.get("kw") and w.get("emoji") and (i <= active or anim == "none"):
                    em, em_idx = w["emoji"], i
            if em:
                grow = ease_out_back(clamp(word_t / 0.26)) if (em_idx == active and anim != "none") else 1.0
                size = int(self.base * 1.45 * max(0.05, grow))
                img = emoji_img(em, size)
                if img:
                    ey = int(top - self.base * 0.2 - self.base * 1.45 / 2 - img.height / 2)
                    if ey >= 0:
                        layer.alpha_composite(img, ((W - img.width) // 2, ey))
        # entrada da página
        p = clamp(page_t / PAGE_IN)
        if anim == "pop":
            return _transform(layer, 0.8 + 0.2 * ease_out_back(p), W / 2, self.text_y, 0, clamp(page_t / 0.07))
        if anim == "slide":
            return _transform(layer, 1.0, W / 2, self.text_y, (1 - ease_out_cubic(p)) * self.base * 0.55, ease_out_cubic(p))
        if anim == "fade":
            return _transform(layer, 1.0, W / 2, self.text_y, 0, ease_out_cubic(p))
        return layer


# ----------------------------------------------------------------------------- título / tópicos

class TitlePainter:
    """Gancho/títulos de tópico (topo) e frases de destaque (y própria)."""

    def __init__(self, settings: dict, W: int, H: int, y: float | None = None, scale_mul: float = 1.0):
        self.W, self.H = W, H
        t = resolve_title(settings)
        self.font_file = t["font_file"]
        self.size = int((66 if H > W else 58) * min(W, H) / 1080 * float(t["scale"] or 1.0) * scale_mul)
        self.color = t["color"] or "#FFFFFF"
        self.bg = t["bg"] or "none"
        ty = y if y is not None else t["y"]
        self.center_y = (float(ty) if ty is not None else (0.13 if H > W else 0.09)) * H
        self.band_h = even(min(H * 0.34, self.size * 6.5))
        self.band_y = int(min(max(0, self.center_y - self.band_h / 2), H - self.band_h))

    def _static(self, text: str) -> Image.Image:
        size, W = self.size, self.W
        f = font(self.font_file, size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if cur and f.getlength(t) > W * 0.82:
                lines.append(cur)
                cur = w
            else:
                cur = t
        if cur:
            lines.append(cur)
        line_h = int(size * 1.28)
        layer = Image.new("RGBA", (W, self.band_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        top = self.band_h / 2 - line_h * len(lines) / 2
        for li, line in enumerate(lines):
            runs, buf, emo = [], "", False
            for ch in line:
                e = is_emoji_char(ch)
                if buf and e != emo:
                    runs.append((buf, emo))
                    buf = ""
                buf += ch
                emo = e
            if buf:
                runs.append((buf, emo))
            widths = [sum(size * 1.05 for c in r if ord(c) not in (0xFE0F, 0x200D)) if e else f.getlength(r)
                      for r, e in runs]
            lw = sum(widths)
            x = (W - lw) / 2
            y = top + line_h * li + size * 0.98
            if self.bg == "box":
                pad = size * 0.32
                d.rounded_rectangle([x - pad, y - size * 0.95 - pad * 0.45, x + lw + pad, y + size * 0.28 + pad * 0.45],
                                    radius=int(size * 0.35), fill=(255, 255, 255, 240) if self.color.upper() != "#FFFFFF" else (0, 0, 0, 150))
            for (r, e), wd in zip(runs, widths):
                if e:
                    for c in r:
                        if ord(c) in (0xFE0F, 0x200D):
                            continue
                        img = emoji_img(c, int(size * 0.95))
                        if img:
                            layer.alpha_composite(img, (int(x), int(y - size * 0.85)))
                        x += size * 1.05
                else:
                    d.text((x, y), r, font=f, fill=hex_rgba(self.color), anchor="ls")
                    x += wd
        if self.bg == "box":
            return layer
        return add_shadow(layer, strength=200, radius=9, dy=3)

    @lru_cache(maxsize=64)
    def static(self, text: str) -> Image.Image:
        return self._static(text)

    def render(self, text: str, t_in: float, t_out: float) -> Image.Image:
        img = self.static(text)
        a_in = ease_out_cubic(clamp(t_in / TITLE_IN))
        a_out = clamp(t_out / TITLE_OUT)
        dy = -(1 - a_in) * self.size * 0.5
        return _transform(img, 1.0, self.W / 2, self.band_h / 2, dy, min(a_in, a_out))


# ----------------------------------------------------------------------------- montagem dos streams

_WORKER: dict = {}


def _init_worker(settings, W, H, pages):
    _WORKER["cap"] = CaptionPainter(settings, W, H)
    _WORKER["top"] = TitlePainter(settings, W, H)
    _WORKER["call"] = TitlePainter(settings, W, H, y=float(settings.get("callout_y") or 0.78), scale_mul=0.92)
    _WORKER["pages"] = pages


def _job(args):
    kind, path, a = args
    if kind == "cap":
        pi, k, pt, wt = a
        img = _WORKER["cap"].render(pi, _WORKER["pages"][pi], k, pt, wt)
    else:
        text, ti, to = a
        img = _WORKER[kind].render(text, ti, to)
    img.save(path, compress_level=1)
    return path


def build_streams(project: dict, tl, W: int, H: int, fps: float, rdir: Path, pages_timed, top_items,
                  progress, callout_items=()) -> dict:
    """Gera os PNGs (em paralelo) e as listas concat. Retorna caminhos e posições."""
    st = project["settings"]
    cap = CaptionPainter(st, W, H)
    top = TitlePainter(st, W, H)
    D = tl.duration
    step = 1.0 / fps
    jobs, files = [], {}

    def frame_file(kind, key):
        if key not in files:
            files[key] = rdir / f"{kind}{len(files):05d}.png"
            jobs.append((kind, str(files[key]), key[1:]))
        return files[key]

    out = {}
    anim = cap.s.get("anim", "pop")
    if pages_timed:
        lines, t = [], 0.0
        blank = rdir / "blank_cap.png"
        Image.new("RGBA", (W, cap.band_h), (0, 0, 0, 0)).save(blank, compress_level=1)

        def put(path, t0, t1):
            nonlocal t
            if t0 > t + 1e-3:
                lines.extend([f"file {q(blank)}", f"duration {t0 - t:.4f}"])
                t = t0
            if t1 > t + 1e-4:
                lines.extend([f"file {q(path)}", f"duration {t1 - t:.4f}"])
                t = t1

        mode_static = cap.s.get("active_mode") == "none" and anim == "none"
        for pi, (p, tw) in enumerate(pages_timed):
            start = tw[0][0]
            nxt = pages_timed[pi + 1][1][0][0] if pi + 1 < len(pages_timed) else D
            end = min(nxt, tw[-1][1] + 0.6)
            if nxt - end < 0.25:
                end = nxt
            ks = [(len(p), start, end)] if mode_static else [
                (k, start if k == 0 else tw[k][0], tw[k + 1][0] if k + 1 < len(p) else end) for k in range(len(p))]
            for k, t0, t1 in ks:
                if t1 <= t0:
                    continue
                win = 0 if anim == "none" else (PAGE_IN if k == 0 else WORD_IN)
                if k == 0 and anim != "none":
                    win = max(PAGE_IN, 0.26)  # emoji também anima
                ft = t0
                while ft < min(t1, t0 + win) - 1e-6:
                    pt, wt = ft - start, ft - t0
                    key = ("cap", pi, k, round(pt * fps), round(wt * fps))
                    put(frame_file("cap", key), ft, min(t1, ft + step))
                    ft += step
                if ft < t1:
                    put(frame_file("cap", ("cap", pi, k, 999, 999)), ft, t1)
        lines += [f"file {q(blank)}", f"duration {max(0.1, D - t + 0.5):.4f}", f"file {q(blank)}"]
        (rdir / "captions.txt").write_text("\n".join(lines))
        out["captions"] = rdir / "captions.txt"
        out["cap_y"] = cap.band_y

    call = TitlePainter(st, W, H, y=float(st.get("callout_y") or 0.78), scale_mul=0.92)
    for kind, items, painter in (("top", top_items, top), ("call", callout_items, call)):
        if not items:
            continue
        lines, t = [], 0.0
        blank = rdir / f"blank_{kind}.png"
        Image.new("RGBA", (W, painter.band_h), (0, 0, 0, 0)).save(blank, compress_level=1)
        for t0, t1, text in items:
            if t0 > t + 1e-3:
                lines += [f"file {q(blank)}", f"duration {t0 - t:.4f}"]
                t = t0
            ft = max(t0, t)
            while ft < t1 - 1e-6:
                ti, to = ft - t0, t1 - ft
                if ti < TITLE_IN or to < TITLE_OUT:
                    key = (kind, text, round(ti * fps) if ti < TITLE_IN else 999, round(to * fps) if to < TITLE_OUT else 999)
                    nxt = min(t1, ft + step)
                else:
                    key = (kind, text, 999, 999)
                    nxt = max(ft + step, t1 - TITLE_OUT)
                lines += [f"file {q(frame_file(kind, key))}", f"duration {nxt - ft:.4f}"]
                t = ft = nxt
        lines += [f"file {q(blank)}", f"duration {max(0.1, D - t + 0.5):.4f}", f"file {q(blank)}"]
        (rdir / f"{kind}.txt").write_text("\n".join(lines))
        out[kind] = rdir / f"{kind}.txt"
        out[kind + "_y"] = painter.band_y

    # reescreve as chaves dos jobs de título para o formato do worker (texto, t_in, t_out)
    fixed = []
    for kind, path, a in jobs:
        if kind in ("top", "call"):
            text, ti, to = a
            fixed.append((kind, path, (text, 999 if ti == 999 else ti / fps, 999 if to == 999 else to / fps)))
        else:
            pi, k, pt, wt = a
            fixed.append((kind, path, (pi, k, 999 if pt == 999 else pt / fps, 999 if wt == 999 else wt / fps)))
    n = len(fixed)
    if n:
        pages = [p for p, _ in pages_timed]
        workers = max(1, min(8, (os.cpu_count() or 2) - 1))
        done = 0
        if workers == 1 or n < 40:
            _init_worker(st, W, H, pages)
            for j in fixed:
                _job(j)
                done += 1
                if done % 25 == 0:
                    progress("captions", 0.02 + 0.2 * done / n, "Desenhando legendas e animações")
        else:
            with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(st, W, H, pages)) as ex:
                for _ in ex.map(_job, fixed, chunksize=16):
                    done += 1
                    if done % 25 == 0:
                        progress("captions", 0.02 + 0.2 * done / n, "Desenhando legendas e animações")
    out["frames"] = n
    return out


def q(path) -> str:
    return "'" + str(path).replace("'", "'\\''") + "'"
