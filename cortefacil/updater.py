"""Atualizações: avisa quando há versão nova publicada no GitHub e atualiza com um clique.

- Consulta só a última *release* publicada (nunca o código em desenvolvimento), no máximo 1x por dia.
  Não envia nenhum dado do usuário: é um GET público em api.github.com.
- Ao atualizar: baixa o pacote da versão, guarda a versão atual em `.update-backup/`, troca o código,
  instala os componentes (`uv sync --frozen`) e reinicia. Se algo falhar, volta a versão anterior.
- Projetos, logs, preferências (config.json), o ambiente Python (.venv) e o .path nunca são tocados.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "danilocaffaro/cortefacil"
API = os.environ.get("CORTEFACIL_UPDATE_API", f"https://api.github.com/repos/{REPO}/releases/latest")
DOWNLOAD = os.environ.get("CORTEFACIL_UPDATE_DOWNLOAD", f"https://codeload.github.com/{REPO}/tar.gz/refs/tags/{{tag}}")
HOME = Path(__file__).resolve().parent.parent
CACHE = HOME / "logs" / "update-check.json"
BACKUP = HOME / ".update-backup"
KEEP = {"projetos", "logs", ".venv", "config.json", ".path", ".update-backup", ".claude", ".git", ".ref"}
CHECK_EVERY = 24 * 3600

STATE: dict = {"state": "idle", "message": ""}
_lock = threading.Lock()


def current() -> str:
    f = HOME / "VERSION"
    return f.read_text().strip() if f.exists() else "0.0.0"


def vtuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def is_dev_checkout() -> bool:
    """Quem clonou com git atualiza com `git pull`, não por aqui."""
    return (HOME / ".git").exists()


def _get(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "cortefacil-updater",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def check(force: bool = False) -> dict:
    """{"current","latest","available","notes","url","checked_at","dev"} — nunca levanta erro."""
    cur = current()
    info = {"current": cur, "dev": is_dev_checkout(), "available": False}
    cached = {}
    try:
        cached = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        pass
    if not force and cached and time.time() - cached.get("checked_at", 0) < CHECK_EVERY:
        rel = cached
    else:
        try:
            data = json.loads(_get(API))
            rel = {"tag": data.get("tag_name") or "", "notes": (data.get("body") or "").strip()[:4000],
                   "url": data.get("html_url") or "", "published": data.get("published_at") or "",
                   "checked_at": time.time()}
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(rel, ensure_ascii=False))
        except urllib.error.HTTPError as e:
            rel = cached or {}
            if e.code != 404:  # 404 = ainda não há versão publicada
                info["error"] = "O GitHub não respondeu agora. Tente mais tarde."
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            info["error"] = "Sem conexão para procurar atualizações." if isinstance(e, (urllib.error.URLError, TimeoutError)) else str(e)
            rel = cached or {}
    tag = rel.get("tag") or ""
    if tag:
        info.update(latest=tag.lstrip("v"), tag=tag, notes=rel.get("notes", ""), url=rel.get("url", ""),
                    checked_at=rel.get("checked_at"))
        info["available"] = vtuple(tag) > vtuple(cur)
    return info


# ----------------------------------------------------------------------------- aplicar

def find_uv() -> str | None:
    exe = shutil.which("uv")
    if exe:
        return exe
    for p in (Path.home() / ".local/bin/uv", Path.home() / ".local/bin/uv.exe", Path.home() / ".cargo/bin/uv"):
        if p.exists():
            return str(p)
    return None


def _set(state: str, message: str, **kw):
    STATE.clear()
    STATE.update(state=state, message=message, **kw)


def _extract(blob: bytes, dest: Path) -> Path:
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        for m in tf.getmembers():  # nada fora da pasta, nada de links
            p = (dest / m.name).resolve()
            if not str(p).startswith(str(dest.resolve())) or m.issym() or m.islnk() or m.isdev():
                raise RuntimeError("Pacote de atualização inválido.")
        if hasattr(tarfile, "data_filter"):
            tf.extractall(dest, filter="data")
        else:
            tf.extractall(dest)  # noqa: S202 — conferido acima
    roots = [p for p in dest.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("Pacote de atualização inválido.")
    src = roots[0]
    py = src / "pyproject.toml"
    if not py.exists() or 'name = "cortefacil"' not in py.read_text():
        raise RuntimeError("O pacote baixado não é do CorteFácil.")
    return src


def _swap(src: Path) -> list[str]:
    """Troca o código: a versão atual vai para .update-backup/. Devolve os itens trocados."""
    if BACKUP.exists():
        shutil.rmtree(BACKUP, ignore_errors=True)
    BACKUP.mkdir()
    moved = []
    for item in sorted(src.iterdir()):
        if item.name in KEEP:
            continue
        target = HOME / item.name
        if target.exists():
            shutil.move(str(target), str(BACKUP / item.name))
        moved.append(item.name)
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    return moved


def _rollback(moved: list[str]) -> None:
    for name in moved:
        target = HOME / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()
        if (BACKUP / name).exists():
            shutil.move(str(BACKUP / name), str(target))


def _sync(uv: str) -> tuple[bool, str]:
    flags = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
    p = subprocess.run([uv, "sync", "--frozen", "--quiet"], cwd=HOME, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800, **flags)
    return p.returncode == 0, (p.stderr or p.stdout or "")[-400:]


def apply(tag: str, busy=lambda: False) -> None:
    """Roda numa thread. Atualiza e reinicia; em qualquer falha, mantém a versão atual."""
    if not _lock.acquire(blocking=False):
        return
    moved: list[str] = []
    try:
        if is_dev_checkout():
            raise RuntimeError("Esta cópia veio do git: atualize com `git pull` e `uv sync`.")
        if busy():
            raise RuntimeError("Espere terminar a análise ou a exportação em andamento.")
        uv = find_uv()
        if not uv:
            raise RuntimeError("Não encontrei o uv. Rode de novo o comando de instalação do site.")
        _set("running", "Baixando a nova versão", progress=0.1)
        blob = _get(DOWNLOAD.format(tag=tag), timeout=120)
        with tempfile.TemporaryDirectory(prefix="cortefacil-update-") as tmp:
            src = _extract(blob, Path(tmp))
            _set("running", "Instalando a nova versão", progress=0.4)
            moved = _swap(src)
        _set("running", "Atualizando componentes (pode levar alguns minutos)", progress=0.6)
        ok, err = _sync(uv)
        if not ok:
            _rollback(moved)
            moved = []
            _sync(uv)  # deixa os componentes como estavam
            raise RuntimeError("Não consegui instalar os componentes da nova versão. Seguimos na versão atual. " + err[-160:])
        _set("restarting", f"Atualizado para {tag.lstrip('v')}. Reiniciando…", progress=1.0, version=tag.lstrip("v"))
        threading.Timer(0.8, restart).start()
    except Exception as e:  # noqa: BLE001
        if moved:
            _rollback(moved)
        _set("error", str(e) or "Falha ao atualizar.")
    finally:
        _lock.release()


def restart() -> None:
    """Sobe um novo processo (que espera esta porta liberar) e encerra este."""
    launcher = HOME / "cortefacil" / "launcher.py"
    py = HOME / ".venv" / ("Scripts/pythonw.exe" if sys.platform == "win32" else "bin/python")
    exe = str(py if py.exists() else sys.executable)
    kw: dict = {"cwd": str(HOME), "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL, "close_fds": True}
    if sys.platform == "win32":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen([exe, str(launcher), "--background", "--no-browser", "--wait-port"], **kw)
    os._exit(0)
