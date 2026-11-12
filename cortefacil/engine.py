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
import captions
from styles import DEFAULT_SETTINGS, FORMATS, PACES, STYLES, resolve_style, resolve_title, zoom_mode

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


def transcribe(wav: str, language: str | None = "pt", progress=None, info: dict | None = None) -> list[dict]:
    """Transcreve com tempo por palavra. Usa a nuvem (Groq) se o usuário escolheu; senão/se falhar, a IA local."""
    import cloud_stt
    raw: list[tuple[str, float, float, float]] = []
    info = info if info is not None else {}
    cfg = cloud_stt.load()
    if cloud_stt.cloud_enabled(cfg):
        try:
            if progress:
                progress("transcribe", 0.3, "Transcrevendo na nuvem (Groq)")
            raw = cloud_stt.transcribe(wav, FF, cfg["groq_key"], language)
            info["stt"] = "groq"
        except Exception as e:  # noqa: BLE001
            info["stt_note"] = f"{e} Usei a IA do computador."
            if progress:
                progress("transcribe", 0.32, "Nuvem indisponível — transcrevendo no computador")
            raw = []
    if not raw:
        raw = _transcribe_local(wav, language)
        info.setdefault("stt", "local")
    return _clean_words(raw)


def _transcribe_local(wav: str, language: str | None) -> list[tuple[str, float, float, float]]:
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
    return raw


def _clean_words(raw) -> list[dict]:
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
        stt_info: dict = {}
        words = transcribe(wav, progress=progress, info=stt_info)
        meta.update(stt_info)
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


def push_amount(settings: dict, dur: float) -> float:
    """Quanto aproximar ao longo do trecho (sutil: ~1,2% por segundo, no máximo 6%)."""
    if not settings.get("push_in", True) or dur < 0.8:
        return 0.0
    return min(0.06, 0.012 * dur)


def topic_times(project: dict) -> list[float]:
    """Instantes (vídeo original) em que cada tópico começa."""
    act = active_words(project)
    out = []
    for tp in project["settings"].get("topics") or []:
        w = next((w for w in act if w["id"] >= tp.get("word_id", -1)), None)
        if w:
            out.append(w["s"])
    return sorted(out)


def segment_zooms(project: dict, segs: list[list[float]]) -> list[float]:
    mode = zoom_mode(project["settings"])
    if mode == "off":
        return [1.0] * len(segs)
    tts = topic_times(project)
    if mode == "topics" and tts:
        # como na referência: o enquadramento muda só quando muda o assunto
        out = []
        for s, e in segs:
            sec = sum(1 for t in tts if t <= s + 0.3)
            out.append(1.0 if sec % 2 == 0 else 1.1)
        return out
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
    style = resolve_style(st)
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


def callout_items(project: dict, tl: "Timeline") -> list[tuple[float, float, str]]:
    """Frases de destaque: aparecem com a fala do trecho e ficam ~1,2 s depois."""
    by_id = {w["id"]: w for w in project["words"]}
    act = active_words(project)
    items = []
    for c in project["settings"].get("callouts") or []:
        text = (c.get("text") or "").strip()
        a = next((w for w in act if w["id"] >= c.get("start_id", -1)), None)
        b = next((w for w in reversed(act) if w["id"] <= c.get("end_id", c.get("start_id", -1))), None)
        if not text or not a or not b:
            continue
        ma, mb = tl.map_word(a), tl.map_word(b)
        if ma and mb and mb[1] >= ma[0]:
            items.append([ma[0], min(tl.duration, max(mb[1] + 1.2, ma[0] + 2.0)), text])
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
        "segments": [[s, e, z, push_amount(project["settings"], e - s) if project["settings"].get("fit", "crop") == "crop" else 0]
                     for (s, e), z in zip(segs, zooms)],
        "pages": [[w["id"] for w in p] for p in pages],
        "duration_in": project["meta"]["duration"],
        "duration_out": tl.duration,
        "top": top_items(project, tl),
        "callouts": callout_items(project, tl),
        "style": resolve_style(project["settings"]),
        "title": resolve_title(project["settings"]),
    }


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
    for old in rdir.glob("*.png"):
        old.unlink()

    # ---- legendas + faixa do topo (quadros animados, desenhados em paralelo)
    pages_timed = []
    calls = callout_items(project, tl)
    if st.get("captions", True) and project["words"]:
        progress("captions", 0.02, "Desenhando legendas e animações")
        for p in build_pages(project):
            tw = [tl.map_word(w) for w in p]
            keep = [(w, t) for w, t in zip(p, tw) if t is not None]
            # durante uma frase de destaque, a legenda dá lugar a ela (como na referência)
            keep = [(w, t) for w, t in keep if not any(c0 - 0.05 <= t[0] < c1 for c0, c1, _ in calls)]
            if keep:
                pages_timed.append(([k[0] for k in keep], [k[1] for k in keep]))
    streams = captions.build_streams(project, tl, W, H, fps, rdir, pages_timed, top_items(project, tl), progress,
                                     calls)
    cap_list, top_list = streams.get("captions"), streams.get("top")

    # ---- filtro principal
    progress("encode", 0.2, "Montando cortes e efeitos")
    inputs = ["-i", src]
    idx = 1
    cap_idx = title_idx = music_idx = call_idx = None
    if cap_list:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(cap_list)]
        cap_idx, idx = idx, idx + 1
    if top_list:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(top_list)]
        title_idx, idx = idx, idx + 1
    if streams.get("call"):
        inputs += ["-f", "concat", "-safe", "0", "-i", str(streams["call"])]
        call_idx, idx = idx, idx + 1
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
            amt = push_amount(st, e - s)
            if amt > 0:
                nf = max(1, int(round((e - s) * fps)))
                vf += (f",fps={fps},scale={even(W * 1.5)}:{even(H * 1.5)}:flags=bicubic,"
                       f"zoompan=z='1+{amt:.4f}*on/{nf}':x='iw/2-(iw/zoom/2)':y='ih*0.4-(ih*0.4/zoom)'"
                       f":d=1:s={W}x{H}:fps={fps},setsar=1,setpts=PTS-STARTPTS")
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
        f.append(f"[{cap_idx}:v]format=rgba[cap];[{last}][cap]overlay=0:{streams['cap_y']}:eof_action=pass[vcap]")
        last = "vcap"
    if title_idx is not None:
        f.append(f"[{title_idx}:v]format=rgba[tt];[{last}][tt]overlay=0:{streams['top_y']}:eof_action=pass[vt]")
        last = "vt"
    if call_idx is not None:
        f.append(f"[{call_idx}:v]format=rgba[cl];[{last}][cl]overlay=0:{streams['call_y']}:eof_action=pass[vcl]")
        last = "vcl"
    if st.get("progress_bar", True):
        bh = max(8, H // 160)
        rs = resolve_style(st)
        color = (rs["active"] if rs["active_mode"] == "color" else rs.get("box") if rs["active_mode"] == "box" else rs["kw"]).lstrip("#")
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
