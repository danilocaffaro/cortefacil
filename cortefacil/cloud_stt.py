"""Transcrição na nuvem (opcional): Groq, com o Whisper large-v3-turbo e cota grátis.

A chave fica só neste computador (config.json com permissão 600) e nunca volta para a interface.
Se a nuvem falhar (sem internet, limite atingido, chave inválida), o CorteFácil usa a IA local.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

GROQ_BASE = os.environ.get("CORTEFACIL_GROQ_BASE", "https://api.groq.com/openai/v1")  # trocável só para testes
GROQ_URL = GROQ_BASE + "/audio/transcriptions"
GROQ_MODELS = GROQ_BASE + "/models"
GROQ_MODEL = "whisper-large-v3-turbo"
CHUNK_S = 600  # 10 min por envio (~2,4 MB em MP3 32 kbps, bem abaixo do limite de 25 MB)
CONFIG = Path(os.environ.get("CORTEFACIL_CONFIG", Path(__file__).resolve().parent.parent / "config.json"))


# ----------------------------------------------------------------------------- preferências

def load() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {}


def save(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False))
    try:
        os.chmod(CONFIG, 0o600)
    except OSError:
        pass


def public(cfg: dict | None = None) -> dict:
    """O que a interface pode ver: nunca a chave em si."""
    cfg = cfg if cfg is not None else load()
    key = cfg.get("groq_key") or ""
    return {"stt": cfg.get("stt", "local"), "has_key": bool(key), "key_hint": ("…" + key[-4:]) if key else ""}


def cloud_enabled(cfg: dict | None = None) -> bool:
    cfg = cfg if cfg is not None else load()
    return cfg.get("stt") == "groq" and bool(cfg.get("groq_key"))


# ----------------------------------------------------------------------------- API

def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "User-Agent": "cortefacil"}


def test_key(key: str) -> tuple[bool, str]:
    key = (key or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-]{20,200}", key):
        return False, "Essa chave não parece válida. Copie de novo em console.groq.com › API Keys."
    req = urllib.request.Request(GROQ_MODELS, headers=_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return (True, "Chave verificada") if r.status == 200 else (False, f"A Groq respondeu {r.status}.")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, "A Groq recusou essa chave. Confira se copiou inteira."
        return False, f"A Groq respondeu com erro {e.code}. Tente de novo em instantes."
    except (urllib.error.URLError, TimeoutError):
        return False, "Sem conexão com a Groq. Verifique a internet."


def _multipart(fields: list[tuple[str, str]], file_field: str, filename: str, data: bytes, mime: str):
    b = "----cortefacil" + uuid.uuid4().hex
    out = bytearray()
    for k, v in fields:
        out += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n").encode()
    out += data + f"\r\n--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


def _post(key: str, mp3: bytes, language: str | None, url: str = GROQ_URL) -> dict:
    fields = [("model", GROQ_MODEL), ("response_format", "verbose_json"), ("temperature", "0"),
              ("timestamp_granularities[]", "word"), ("timestamp_granularities[]", "segment")]
    if language:
        fields.append(("language", language))
    body, ctype = _multipart(fields, "file", "audio.mp3", mp3, "audio/mpeg")
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={**_headers(key), "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = float(e.headers.get("retry-after") or 20)
                time.sleep(min(wait, 60))
                continue
            if e.code in (401, 403):
                raise RuntimeError("A chave da Groq foi recusada.") from None
            if e.code == 429:
                raise RuntimeError("Limite grátis da Groq atingido por agora.") from None
            raise RuntimeError(f"A Groq respondeu com erro {e.code}.") from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError("Sem conexão com a Groq.") from None
    raise RuntimeError("A Groq não respondeu.")


def _words_from(resp: dict, offset: float) -> list[tuple[str, float, float, float]]:
    """Aceita 'words' no topo ou dentro dos segmentos; sem palavras, distribui o tempo do segmento."""
    out = []
    words = resp.get("words")
    if not words:
        words = [w for s in resp.get("segments") or [] for w in (s.get("words") or [])]
    if words:
        for w in words:
            txt = w.get("word") or w.get("text") or ""
            out.append((txt if txt.startswith(" ") else " " + txt, offset + float(w["start"]), offset + float(w["end"]), 1.0))
        return out
    for s in resp.get("segments") or []:
        toks = (s.get("text") or "").split()
        if not toks:
            continue
        a, b = float(s["start"]), float(s["end"])
        total = sum(len(t) for t in toks) or 1
        t = a
        for tok in toks:
            d = (b - a) * len(tok) / total
            out.append((" " + tok, offset + t, offset + t + d, 0.5))
            t += d
    return out


def transcribe(wav: str, ffmpeg: str, key: str, language: str | None = "pt", duration: float | None = None,
               url: str = GROQ_URL, progress=None) -> list[tuple[str, float, float, float]]:
    """Retorna [(texto_com_espaço, início, fim, prob)] no mesmo formato da transcrição local."""
    if duration is None:
        p = subprocess.run([ffmpeg, "-hide_banner", "-i", wav], capture_output=True, text=True, errors="replace")
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
        duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    out: list = []
    n = max(1, int((duration + CHUNK_S - 1) // CHUNK_S))
    with tempfile.TemporaryDirectory(prefix="cortefacil-stt-") as tmp:
        for i in range(n):
            start = i * CHUNK_S
            mp3 = Path(tmp) / f"c{i}.mp3"
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", str(start), "-t", str(CHUNK_S), "-i", wav,
                            "-ac", "1", "-ar", "16000", "-b:a", "32k", str(mp3)], check=True)
            if progress:
                progress(i, n)
            out += _words_from(_post(key, mp3.read_bytes(), language, url), start)
    return out
