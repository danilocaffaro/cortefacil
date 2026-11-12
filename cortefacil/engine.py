"""Motor de edição: análise (transcrição, silêncios), montagem da linha do tempo e render final."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import unicodedata
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from nlp import emoji_for, is_filler, pick_keywords
from styles import DEFAULT_SETTINGS, FORMATS, PACES, STYLES

import platform
import sys

FONTS = Path(__file__).parent / "fonts"
TITLE_FONT = (str(FONTS / "Montserrat-Bold.ttf"), 0)
EMOJI_FONTS = [  # (arquivo, tamanho nativo do bitmap)
    ("/System/Library/Fonts/Apple Color Emoji.ttc", 160),
    ("C:/Windows/Fonts/seguiemj.ttf", 109),
    ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109),
    ("/usr/share/fonts/noto/NotoColorEmoji.ttf", 109),
    ("/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf", 109),
]
IS_APPLE_SILICON = sys.platform == "darwin" and platform.machine() == "arm64"
WHISPER_MLX = "mlx-community/whisper-large-v3-turbo"
WHISPER_CPU = "small"   # faster-whisper (Windows/Linux/Mac Intel)


def ffmpeg_bin() -> str:
    env = os.environ.get("CORTEFACIL_FFMPEG")
    if env:
        return env
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        import shutil
        return shutil.which("ffmpeg") or "ffmpeg"


FF = ffmpeg_bin()


@lru_cache(maxsize=1)
def video_encoder() -> list[str]:
    """Usa o encoder de hardware do Mac quando existe; senão libx264."""
    try:
        enc = subprocess.run([FF, "-hide_banner", "-encoders"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
    except OSError:
        enc = ""
    if sys.platform == "darwin" and "h264_videotoolbox" in enc:
        return ["-c:v", "h264_videotoolbox", "-b:v", "14M", "-maxrate", "20M", "-profile:v", "high"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-profile:v", "high"]


def proxy_encoder() -> list[str]:
    if video_encoder()[1] == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", "4M"]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"]


# ----------------------------------------------------------------------------- utilidades

def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    if cmd and cmd[0] == "ffmpeg":
        cmd = [FF, *cmd[1:]]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          check=True, **kw)


def probe(path: str) -> dict:
    """Lê dimensões, rotação, fps e duração usando só o ffmpeg (sem ffprobe)."""
    p = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    err = p.stderr
    vline = next((l for l in err.splitlines() if re.search(r"Stream #.*Video:", l)), None)
    if vline is None:
        raise ValueError("O arquivo não tem trilha de vídeo.")
    m = re.search(r"\b(\d{2,5})x(\d{2,5})\b", vline)
    w, h = int(m.group(1)), int(m.group(2))
    rot = 0
    m = re.search(r"rotation of (-?[\d.]+) degrees", err) or re.search(r"rotate\s*:\s*(-?\d+)", err)
    if m:
        rot = int(float(m.group(1)))
    if abs(rot) % 180 == 90:
        w, h = h, w
    m = re.search(r"([\d.]+) fps", vline) or re.search(r"([\d.]+) tbr", vline)
    fps = float(m.group(1)) if m else 30.0
    if not (10 <= fps <= 120):
        fps = 30.0
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    return {"width": w, "height": h, "fps": round(fps, 3), "duration": dur,
            "has_audio": bool(re.search(r"Stream #.*Audio:", err))}



def q(path) -> str:
    """Aspas para o demuxer concat do ffmpeg."""
    return "'" + str(path).replace("'", "'\\''") + "'"


def even(x: float) -> int:
    return max(2, int(round(x / 2)) * 2)


# ----------------------------------------------------------------------------- análise

def whisper_backend() -> str:
    if IS_APPLE_SILICON:
        try:
            import mlx_whisper  # noqa: F401
            return "mlx"
        except ImportError:
            pass
    return "faster"


def transcribe(wav: str, language: str | None = "pt") -> list[dict]:
    raw: list[tuple[str, float, float, float]] = []
    if whisper_backend() == "mlx":
        import mlx_whisper
        res = mlx_whisper.transcribe(wav, path_or_hf_repo=WHISPER_MLX, word_timestamps=True,
                                     language=language, condition_on_previous_text=False)
        for s in res["segments"]:
            for w in s.get("words", []):
                raw.append((w["word"], float(w["start"]), float(w["end"]), float(w.get("probability", 1))))
    else:
        from faster_whisper import WhisperModel
        model = WhisperModel(WHISPER_CPU, device="cpu", compute_type="int8")
        segs, _ = model.transcribe(wav, word_timestamps=True, language=language, vad_filter=False)
        for s in segs:
            for w in s.words or []:
                raw.append((w.word, float(w.start), float(w.end), float(w.probability)))
    words: list[dict] = []
    for txt, st, en, pr in raw:
        # tokens sem espaço inicial que são só pontuação/símbolo ("%", "?") grudam na anterior
        if words and not txt.startswith(" ") and re.fullmatch(r"[^\wÀ-ÿ]+", txt.strip() or "x"):
            words[-1]["text"] += txt.strip()
            words[-1]["e"] = en
            continue
        if txt.strip():
            words.append({"text": txt.strip(), "s": st, "e": en, "p": pr})
    for i, w in enumerate(words):
        w["id"] = i
    return words


def detect_silences(wav: str, noise_db: int = -38, min_dur: float = 0.25) -> list[list[float]]:
    p = subprocess.run([FF, "-hide_banner", "-nostats", "-i", wav, "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    sil, start = [], None
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            sil.append([start, float(m.group(1))])
            start = None
    return sil


def analyze(src: str, work: Path, progress) -> dict:
    progress("probe", 0.03, "Lendo o vídeo")
    meta = probe(src)
    progress("proxy", 0.08, "Preparando a pré-visualização")
    sw, sh = meta["width"], meta["height"]
    scale = 720 / min(sw, sh) if min(sw, sh) > 720 else 1
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
         "-vf", f"scale={even(sw * scale)}:{even(sh * scale)},format=yuv420p",
         *proxy_encoder(), "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", str(work / "proxy.mp4")])
    words: list[dict] = []
    silences: list = []
    if meta["has_audio"]:
        progress("audio", 0.2, "Extraindo o áudio")
        wav = str(work / "audio.wav")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav])
        progress("transcribe", 0.3, "Transcrevendo a fala (IA)")
        words = transcribe(wav)
        progress("silence", 0.85, "Detectando silêncios")
        silences = detect_silences(wav)
    progress("keywords", 0.93, "Escolhendo palavras-chave")
    for w in words:
        w["filler"] = is_filler(w["text"])
        w["removed"] = False
        w["kw"] = False
        w["emoji"] = emoji_for(w["text"])
    pick_keywords(words)
    project = {"meta": meta, "words": words, "silences": silences,
               "settings": dict(DEFAULT_SETTINGS)}
    progress("ready", 1.0, "Pronto")
    return project


# ----------------------------------------------------------------------------- linha do tempo

def active_words(project: dict) -> list[dict]:
    st = project["settings"]
    return [w for w in project["words"]
            if not w.get("removed") and not (st.get("remove_fillers") and w.get("filler"))]


def subtract(intervals: list[list[float]], cut: list[float]) -> list[list[float]]:
    a, b = cut
    out = []
    for s, e in intervals:
        if b <= s or a >= e:
            out.append([s, e])
            continue
        if a > s:
            out.append([s, a])
        if b < e:
            out.append([b, e])
    return out


def build_segments(project: dict) -> list[list[float]]:
    st = project["settings"]
    dur = project["meta"]["duration"]
    words = project["words"]
    act_ids = {w["id"] for w in active_words(project)}
    max_gap, pre, post = PACES.get(st.get("pace", "normal"), PACES["normal"])

    if not words:
        return [[0.0, dur]]

    if st.get("cut_silence", True):
        groups, cur = [], []
        for w in words:
            if w["id"] not in act_ids:          # palavra removida quebra o grupo
                if cur:
                    groups.append(cur)
                cur = []
                continue
            if cur and w["s"] - cur[-1]["e"] > max_gap:
                groups.append(cur)
                cur = []
            cur.append(w)
        if cur:
            groups.append(cur)
        segs = [[max(0.0, g[0]["s"] - pre), min(dur, g[-1]["e"] + post)] for g in groups]
        # O Whisper às vezes "estica" palavras por cima do silêncio: corta silêncios reais.
        for a, b in project.get("silences", []):
            if b - a > max_gap + pre + post:
                segs = subtract(segs, [a + post, b - pre])
    else:
        segs = [[0.0, dur]]
        for w in words:
            if w["id"] not in act_ids:
                segs = subtract(segs, [w["s"], w["e"]])

    segs = sorted(s for s in segs if s[1] - s[0] >= 0.12)
    merged: list[list[float]] = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 0.04:
            merged[-1][1] = max(merged[-1][1], s[1])
        else:
            merged.append(list(s))
    return merged or [[0.0, dur]]


def segment_zooms(project: dict, segs: list[list[float]]) -> list[float]:
    if not project["settings"].get("zoom", True):
        return [1.0] * len(segs)
    kw_times = [w["s"] for w in active_words(project) if w.get("kw")]
    zooms, flip = [], False
    for s, e in segs:
        if e - s < 0.5:          # trechos muito curtos herdam o zoom anterior
            zooms.append(zooms[-1] if zooms else 1.0)
            continue
        flip = not flip
        z = 1.0 if flip else 1.12
        if any(s <= t <= min(e, s + 0.8) for t in kw_times):
            z = 1.22             # "punch-in" quando o trecho abre com palavra-chave
        zooms.append(z)
    return zooms


def build_pages(project: dict) -> list[list[dict]]:
    st = project["settings"]
    style = STYLES.get(st.get("style"), STYLES["viral"])
    pages, cur, chars = [], [], 0
    for w in active_words(project):
        t = w["text"]
        if cur and (len(cur) >= style["max_words"] or chars + len(t) > style["max_chars"]
                    or w["s"] - cur[-1]["e"] > 0.9):
            pages.append(cur)
            cur, chars = [], 0
        cur.append(w)
        chars += len(t) + 1
        if re.search(r"[.!?…]$", t) or (re.search(r"[,;:]$", t) and len(cur) >= 2):
            pages.append(cur)
            cur, chars = [], 0
    if cur:
        pages.append(cur)
    return pages


class Timeline:
    """Mapeia tempo do vídeo original → tempo do vídeo editado."""

    def __init__(self, segs):
        self.segs = segs
        self.offsets, acc = [], 0.0
        for s, e in segs:
            self.offsets.append(acc)
            acc += e - s
        self.duration = acc

    def map(self, t: float) -> float | None:
        for (s, e), off in zip(self.segs, self.offsets):
            if s - 1e-3 <= t <= e + 1e-3:
                return off + min(max(t, s), e) - s
        return None

    def map_word(self, w) -> tuple[float, float] | None:
        for (s, e), off in zip(self.segs, self.offsets):
            if w["s"] < e and w["e"] > s:  # sobrepõe o trecho mantido
                return off + max(w["s"], s) - s, off + min(w["e"], e) - s
        # palavra caiu num silêncio aparado (desalinhamento do Whisper): ancora no próximo trecho
        for (s, e), off in zip(self.segs, self.offsets):
            if s >= w["s"] and s - w["e"] < 0.8:
                return off, off + min(0.25, e - s)
        return None


def top_items(project: dict, tl: "Timeline") -> list[tuple[float, float, str]]:
    """Itens do topo em tempo do vídeo EDITADO: gancho (início) + títulos de tópico."""
    st = project["settings"]
    D = tl.duration
    items: list[list] = []
    title = (st.get("title") or "").strip()
    if title:
        items.append([0.0, min(D, float(st.get("title_secs") or 5)), title])
    act = active_words(project)
    for tp in st.get("topics") or []:
        text = (tp.get("text") or "").strip()
        w = next((w for w in act if w["id"] >= tp.get("word_id", -1)), None)
        if not text or not w:
            continue
        m = tl.map_word(w)
        if m:
            items.append([m[0], D, text])
    items.sort(key=lambda x: x[0])
    for i in range(len(items) - 1):
        items[i][1] = min(items[i][1], items[i + 1][0])
    return [(a, b, t) for a, b, t in items if b - a >= 0.3]


def layout(project: dict) -> dict:
    """Resumo para a pré-visualização (em tempo do vídeo ORIGINAL)."""
    segs = build_segments(project)
    zooms = segment_zooms(project, segs)
    pages = build_pages(project)
    tl = Timeline(segs)
    return {
        "segments": [[s, e, z] for (s, e), z in zip(segs, zooms)],
        "pages": [[w["id"] for w in p] for p in pages],
        "duration_in": project["meta"]["duration"],
        "duration_out": tl.duration,
        "top": top_items(project, tl),
    }


# ----------------------------------------------------------------------------- desenho das legendas

@lru_cache(maxsize=64)
def font(path: str, index: int, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=index)


@lru_cache(maxsize=64)
def emoji_img(ch: str, size: int) -> Image.Image | None:
    f = None
    for path, native in EMOJI_FONTS:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, native)
                break
            except OSError:
                continue
    if f is None:
        return None
    im = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    bbox = im.getbbox()
    if not bbox:
        return None
    im = im.crop(bbox)
    r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def hex_rgba(h: str, a: int = 255) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def is_emoji_char(ch: str) -> bool:
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0xFE0F, 0x200D) or \
        unicodedata.category(ch) == "So"


def add_shadow(layer: Image.Image, strength: int = 150, radius: int = 10, dy: int = 6) -> Image.Image:
    alpha = layer.getchannel("A")
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(alpha.point(lambda v: v * strength // 255).filter(ImageFilter.GaussianBlur(radius)))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, dy))
    out.alpha_composite(layer)
    return out


class CaptionPainter:
    def __init__(self, settings: dict, W: int, H: int):
        self.st = settings
        self.style = STYLES.get(settings.get("style"), STYLES["viral"])
        self.W, self.H = W, H
        unit = min(W, H) / 1080
        self.base = self.style["size"] * unit * float(settings.get("caption_scale") or 1.0)
        self.band_h = even(min(H, max(560, self.base * 6.2)))
        cy = settings.get("caption_y")
        cy = self.style["y"] if cy is None else float(cy)
        text_center = cy * H
        self.text_y_in_band = self.band_h * 0.66        # espaço em cima para o emoji
        self.band_y = int(min(max(0, text_center - self.text_y_in_band), H - self.band_h))
        self.text_y_in_band = text_center - self.band_y
        acc = settings.get("accent")
        self.active_color = acc if (acc and self.style["active_mode"] == "color") else self.style["active"]
        self.box_color = acc if (acc and self.style["active_mode"] == "box") else self.style.get("box", "#7B2FF7")
        self.kw_color = acc if (acc and self.style["active_mode"] == "none") else self.style["kw"]

    def word_text(self, w):
        t = w["text"]
        return t.upper() if self.style["upper"] else t

    def render(self, page: list[dict], active: int, pop: bool) -> Image.Image:
        s, W = self.style, self.W
        ff, idx = s["font"]
        canvas = Image.new("RGBA", (W, self.band_h), (0, 0, 0, 0))
        layer = Image.new("RGBA", (W, self.band_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        items = []
        for i, w in enumerate(page):
            size = self.base * (s["kw_scale"] if w.get("kw") else 1.0)
            if pop and i == active:
                size *= 1.14
            f = font(ff, idx, int(size))
            txt = self.word_text(w)
            items.append((w, txt, f, f.getlength(txt), i))
        # quebra de linhas
        max_w = W * 0.86
        space = self.base * 0.26
        lines, cur, cw = [], [], 0.0
        for it in items:
            add = it[3] + (space if cur else 0)
            if cur and cw + add > max_w:
                lines.append(cur)
                cur, cw = [], 0.0
                add = it[3]
            cur.append(it)
            cw += add
        if cur:
            lines.append(cur)
        if len(lines) == 2:  # equilibra as duas linhas (evita palavra órfã)
            flat = lines[0] + lines[1]
            best = None
            for k in range(1, len(flat)):
                w1 = sum(it[3] for it in flat[:k]) + space * (k - 1)
                w2 = sum(it[3] for it in flat[k:]) + space * (len(flat) - k - 1)
                if max(w1, w2) <= max_w and (best is None or max(w1, w2) < best[0]):
                    best = (max(w1, w2), k)
            if best:
                lines = [flat[:best[1]], flat[best[1]:]]
        line_h = self.base * 1.22
        total_h = line_h * len(lines)
        top = self.text_y_in_band - total_h / 2
        stroke = int(s["stroke"] * self.base / s["size"]) if s["stroke"] else 0
        for li, line in enumerate(lines):
            lw = sum(it[3] for it in line) + space * (len(line) - 1)
            x = (W - lw) / 2
            baseline = top + line_h * (li + 0.8)
            for w, txt, f, tw, i in line:
                is_active = i == active and s["active_mode"] != "none"
                color = s["text"]
                if w.get("kw"):
                    color = self.kw_color
                if is_active and s["active_mode"] == "color" and not w.get("kw"):
                    color = self.active_color
                if is_active and s["active_mode"] == "box":
                    asc, desc = f.getmetrics()
                    pad = self.base * 0.16
                    d.rounded_rectangle([x - pad, baseline - asc * 0.78 - pad,
                                         x + tw + pad, baseline + desc * 0.35 + pad],
                                        radius=int(self.base * 0.18), fill=hex_rgba(self.box_color))
                    color = "#FFFFFF"
                d.text((x, baseline), txt, font=f, fill=hex_rgba(color), anchor="ls",
                       stroke_width=stroke, stroke_fill=hex_rgba(s["stroke_color"]))
                x += tw + space
        if s["shadow"]:
            layer = add_shadow(layer, strength=170 if stroke else 200,
                               radius=max(4, int(self.base * 0.12)), dy=int(self.base * 0.06))
        canvas.alpha_composite(layer)
        # emoji acima do bloco de texto
        if self.st.get("emojis", True):
            em = None
            for i, w in enumerate(page):
                if w.get("kw") and w.get("emoji") and (i <= active or not s["pop"]):
                    em = w["emoji"]
            if em:
                size = int(self.base * (1.55 if pop else 1.4))
                img = emoji_img(em, size)
                if img:
                    ex = (W - img.width) // 2
                    ey = int(top - img.height - self.base * 0.25)
                    if ey >= 0:
                        canvas.alpha_composite(img, (ex, ey))
        return canvas


def render_title(text: str, W: int) -> Image.Image:
    """Título/gancho no topo (suporta emoji)."""
    size = int(66 * min(W, 1920) / 1080) if W <= 1080 else 70
    f = font(TITLE_FONT[0], TITLE_FONT[1], size)
    max_w = W * 0.84
    # quebra por palavras
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if cur and f.getlength(test) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    line_h = int(size * 1.3)
    h = line_h * len(lines) + 40
    layer = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
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
        widths = []
        for r, e in runs:
            if e:
                widths.append(sum(size * 1.05 for c in r if ord(c) not in (0xFE0F, 0x200D)))
            else:
                widths.append(f.getlength(r))
        x = (W - sum(widths)) / 2
        y = 20 + line_h * li + size
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
                d.text((x, y), r, font=f, fill=(255, 255, 255, 255), anchor="ls")
                x += wd
    return add_shadow(layer, strength=210, radius=8, dy=3)


# ----------------------------------------------------------------------------- render final

def render(project: dict, src: str, work: Path, out_path: str, progress) -> None:
    st = project["settings"]
    meta = project["meta"]
    W, H = FORMATS.get(st.get("format", "9:16"), FORMATS["9:16"])
    fps = min(60.0, meta["fps"] or 30.0)
    sw, sh = meta["width"], meta["height"]
    segs = build_segments(project)
    zooms = segment_zooms(project, segs)
    tl = Timeline(segs)
    D = tl.duration
    work = Path(work).resolve()
    rdir = work / "render"
    rdir.mkdir(exist_ok=True)
    for f in rdir.glob("*.png"):
        f.unlink()

    # ---- legendas: renderiza só os "estados" únicos e monta um stream via concat
    cap_list = None
    painter = CaptionPainter(st, W, H)
    if st.get("captions", True) and project["words"]:
        progress("captions", 0.02, "Desenhando legendas")
        pages = build_pages(project)
        states = []  # (t0, t1, page_idx, active, pop)
        timed_pages = []
        for p in pages:
            tw = [tl.map_word(w) for w in p]
            if any(t is None for t in tw):
                keep = [(w, t) for w, t in zip(p, tw) if t is not None]
                if not keep:
                    continue
                p, tw = [k[0] for k in keep], [k[1] for k in keep]
            timed_pages.append((p, tw))
        for pi, (p, tw) in enumerate(timed_pages):
            start = tw[0][0]
            nxt = timed_pages[pi + 1][1][0][0] if pi + 1 < len(timed_pages) else D
            end = min(nxt, tw[-1][1] + 0.6)
            if nxt - end < 0.25:
                end = nxt
            pop_style = STYLES[st.get("style", "viral")]["pop"] if st.get("style") in STYLES else True
            mode_none = STYLES.get(st.get("style"), STYLES["viral"])["active_mode"] == "none"
            if mode_none and not pop_style:
                states.append((start, end, pi, len(p), False))
                continue
            for k in range(len(p)):
                t0 = start if k == 0 else tw[k][0]
                t1 = tw[k + 1][0] if k + 1 < len(p) else end
                if t1 <= t0:
                    continue
                if pop_style and t1 - t0 > 0.12:
                    states.append((t0, t0 + 0.07, pi, k, True))
                    states.append((t0 + 0.07, t1, pi, k, False))
                else:
                    states.append((t0, t1, pi, k, False))
        blank = rdir / "blank.png"
        Image.new("RGBA", (W, painter.band_h), (0, 0, 0, 0)).save(blank, compress_level=1)
        lines, t, cache = [], 0.0, {}
        n = max(1, len(states))
        for si, (t0, t1, pi, k, pop) in enumerate(states):
            if t0 > t + 0.001:
                lines += [f"file {q(blank)}", f"duration {t0 - t:.4f}"]
            key = (pi, k, pop)
            if key not in cache:
                img = painter.render(timed_pages[pi][0], k, pop)
                fp = rdir / f"c{len(cache):05d}.png"
                img.save(fp, compress_level=1)
                cache[key] = fp
            lines += [f"file {q(cache[key])}", f"duration {t1 - max(t0, t):.4f}"]
            t = t1
            if si % 20 == 0:
                progress("captions", 0.02 + 0.18 * si / n, "Desenhando legendas")
        lines += [f"file {q(blank)}", f"duration {max(0.1, D - t + 0.5):.4f}", f"file {q(blank)}"]
        cap_list = rdir / "captions.txt"
        cap_list.write_text("\n".join(lines))

    # ---- faixa do topo: gancho + títulos de tópico (estilo "capítulos")
    top_list = None
    items = top_items(project, tl)
    if items:
        top_h = even(min(H * 0.3, 420))
        blank_t = rdir / "blank_top.png"
        Image.new("RGBA", (W, top_h), (0, 0, 0, 0)).save(blank_t, compress_level=1)
        lines, t, cache = [], 0.0, {}
        for t0, t1, text in items:
            if t0 > t + 0.001:
                lines += [f"file {q(blank_t)}", f"duration {t0 - t:.4f}"]
            if text not in cache:
                canvas = Image.new("RGBA", (W, top_h), (0, 0, 0, 0))
                img = render_title(text, W)
                canvas.alpha_composite(img.crop((0, 0, W, min(img.height, top_h))))
                fp = rdir / f"t{len(cache):03d}.png"
                canvas.save(fp, compress_level=1)
                cache[text] = fp
            lines += [f"file {q(cache[text])}", f"duration {t1 - max(t0, t):.4f}"]
            t = t1
        lines += [f"file {q(blank_t)}", f"duration {max(0.1, D - t + 0.5):.4f}", f"file {q(blank_t)}"]
        top_list = rdir / "top.txt"
        top_list.write_text("\n".join(lines))

    # ---- filtro principal
    progress("encode", 0.2, "Montando cortes e efeitos")
    inputs = ["-i", src]
    idx = 1
    cap_idx = title_idx = music_idx = None
    if cap_list:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(cap_list)]
        cap_idx, idx = idx, idx + 1
    if top_list:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(top_list)]
        title_idx, idx = idx, idx + 1
    music = st.get("music")
    if music and Path(work / music).exists():
        inputs += ["-stream_loop", "-1", "-i", str(work / music)]
        music_idx, idx = idx, idx + 1

    fit = st.get("fit", "crop")
    ta = W / H
    f = []
    for i, ((s, e), z) in enumerate(zip(segs, zooms)):
        if fit == "crop":
            if sw / sh > ta:
                cw0, ch0 = sh * ta, sh
            else:
                cw0, ch0 = sw, sw / ta
            cw, ch = cw0 / z, ch0 / z
            x = (sw - cw) / 2
            y = (sh - ch) * (0.38 if z > 1 else 0.5)
            vf = (f"crop={even(cw)}:{even(ch)}:{int(x)}:{int(y)},"
                  f"scale={W}:{H}:flags=lanczos,setsar=1")
        else:
            cw, ch = sw / z, sh / z
            x, y = (sw - cw) / 2, (sh - ch) * (0.38 if z > 1 else 0.5)
            r = min(W / sw, H / sh)
            vf = (f"crop={even(cw)}:{even(ch)}:{int(x)}:{int(y)},"
                  f"scale={even(sw * r)}:{even(sh * r)}:flags=lanczos,setsar=1")
        f.append(f"[0:v]trim=start={s:.4f}:end={e:.4f},setpts=PTS-STARTPTS,{vf}[v{i}]")
        if meta["has_audio"]:
            dd = e - s
            f.append(f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.012,afade=t=out:st={max(0, dd - 0.018):.4f}:d=0.018[a{i}]")
    n = len(segs)
    if meta["has_audio"]:
        f.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    else:
        f.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vc]")
    last = "vc"
    if fit != "crop":
        f.append(f"[vc]split[fg][bgs];[bgs]scale={W}:{H}:force_original_aspect_ratio=increase,"
                 f"crop={W}:{H},boxblur=40:6,eq=brightness=-0.06[bg];"
                 f"[bg][fg]overlay=(W-w)/2:(H-h)/2[vfit]")
        last = "vfit"
    post = [f"fps={fps}"]
    if st.get("enhance", True):
        post.append("eq=contrast=1.05:saturation=1.12,unsharp=5:5:0.45")
    f.append(f"[{last}]{','.join(post)}[vp]")
    last = "vp"
    if cap_idx is not None:
        f.append(f"[{cap_idx}:v]format=rgba[cap];[{last}][cap]overlay=0:{painter.band_y}:eof_action=pass[vcap]")
        last = "vcap"
    if title_idx is not None:
        ty = int(H * (0.11 if H > W else 0.06))
        f.append(f"[{title_idx}:v]format=rgba[tt];[{last}][tt]overlay=0:{ty}:eof_action=pass[vt]")
        last = "vt"
    if st.get("progress_bar", True):
        bh = max(8, H // 160)
        color = (st.get("accent") or STYLES.get(st.get("style"), STYLES["viral"])["active"]).lstrip("#")
        if color.upper() == "FFFFFF":
            color = "FFE600"
        f.append(f"color=c=0x{color}:s={W}x{bh}:r={fps}:d={D + 1:.3f}[bar];"
                 f"[{last}][bar]overlay=x='-w+w*t/{D:.4f}':y={H - bh}:shortest=1[vb]")
        last = "vb"
    f.append(f"[{last}]format=yuv420p[vout]")
    if meta["has_audio"]:
        f.append("[ac]highpass=f=70,acompressor=threshold=0.1:ratio=3:attack=5:release=120,"
                 "loudnorm=I=-14:TP=-1.5:LRA=11[an]")
        if music_idx is not None:
            vol = float(st.get("music_volume") or 0.12)
            f.append(f"[an]asplit[vo1][vo2];[{music_idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                     f"volume={vol:.3f},atrim=0:{D:.3f}[m];"
                     f"[m][vo1]sidechaincompress=threshold=0.04:ratio=5:attack=30:release=350[md];"
                     f"[vo2][md]amix=inputs=2:duration=first:normalize=0[aout]")
        else:
            f.append("[an]anull[aout]")
    graph = rdir / "graph.txt"
    graph.write_text(";\n".join(f))
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", *inputs,
           "-/filter_complex", str(graph), "-map", "[vout]"]
    if meta["has_audio"]:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += [*video_encoder(),
            "-t", f"{D:.3f}", "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", out_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace")
    for line in proc.stdout:
        if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
            try:
                us = int(line.split("=")[1])
                progress("encode", 0.2 + 0.79 * min(1.0, us / 1e6 / max(D, 0.1)), "Renderizando o vídeo")
            except ValueError:
                pass
    err = proc.stderr.read()
    if proc.wait() != 0:
        raise RuntimeError("Falha no ffmpeg: " + err[-1500:])
    progress("done", 1.0, "Vídeo pronto!")
