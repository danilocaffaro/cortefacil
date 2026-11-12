"""Checagem do sistema e download do modelo de transcrição (primeiro uso)."""
from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import subprocess
import sys
import threading
from pathlib import Path

import cloud_stt
import engine
import llm

MODELS = {  # repo no Hugging Face, tamanho aproximado em bytes
    "mlx": ("mlx-community/whisper-large-v3-turbo", 1_620_000_000),
    "faster": ("Systran/faster-whisper-small", 486_000_000),
}
STATE = {"state": "idle", "error": None}
_lock = threading.Lock()


def _repo():
    return MODELS[engine.whisper_backend()]


def _cache_dir(repo: str) -> Path:
    base = Path(os.environ.get("HF_HUB_CACHE") or
                Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub")
    return base / ("models--" + repo.replace("/", "--"))


def model_ready() -> bool:
    repo, _ = _repo()
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo, local_files_only=True)
        return True
    except Exception:  # noqa: BLE001
        return False


def _downloaded_bytes(repo: str) -> int:
    d = _cache_dir(repo) / "blobs"
    if not d.exists():
        return 0
    return sum(f.stat().st_size for f in d.iterdir() if f.is_file())


def ffmpeg_ok() -> bool:
    try:
        return subprocess.run([engine.FF, "-version"], capture_output=True).returncode == 0
    except OSError:
        return False


def status() -> dict:
    repo, size = _repo()
    ready = STATE["state"] == "done" or model_ready()
    got = size if ready else _downloaded_bytes(repo)
    av = llm.available()
    return {
        "platform": sys.platform,
        "ffmpeg": ffmpeg_ok(),
        "model": {"ready": ready, "state": "done" if ready else STATE["state"], "error": STATE["error"],
                  "bytes": got, "total": size, "progress": min(1.0, got / size) if size else 0,
                  "engine": "Whisper large-v3-turbo (GPU do Mac)" if engine.whisper_backend() == "mlx"
                  else "Whisper small (CPU)"},
        "llm": {"claude": av["claude"], "codex": av["codex"]},
        "stt": cloud_stt.public(),
    }


def _download():
    repo, _ = _repo()
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo)
        STATE.update(state="done", error=None)
    except Exception as e:  # noqa: BLE001
        STATE.update(state="error", error=f"Não consegui baixar o modelo ({e}). Verifique a internet.")


def prepare():
    with _lock:
        if STATE["state"] == "downloading" or model_ready():
            return
        STATE.update(state="downloading", error=None)
        threading.Thread(target=_download, daemon=True).start()
