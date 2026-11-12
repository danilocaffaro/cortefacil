"""Abre o CorteFácil: se já estiver rodando, só abre o navegador; senão sobe o servidor."""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# download HTTP comum: grava direto no cache e permite mostrar o progresso real no onboarding
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
PORT = int(os.environ.get("CORTEFACIL_PORT", "8765"))
URL = f"http://localhost:{PORT}"
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def running() -> bool:
    try:
        with urllib.request.urlopen(URL + "/api/config", timeout=1.5) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def port_busy() -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def load_saved_path():
    """O instalador salva o PATH do Terminal (onde estão claude/codex/node)."""
    f = ROOT.parent / ".path"
    if f.exists():
        extra = f.read_text().strip()
        if extra:
            os.environ["PATH"] = extra + os.pathsep + os.environ.get("PATH", "")


def main():
    no_browser = "--no-browser" in sys.argv
    if "--wait-port" in sys.argv:  # reinício após atualizar: espera a versão anterior liberar a porta
        for _ in range(60):
            if not port_busy():
                break
            time.sleep(0.5)
    if running():
        if not no_browser:
            webbrowser.open(URL)
        return
    if port_busy():
        print(f"A porta {PORT} está ocupada por outro programa. Feche-o ou defina CORTEFACIL_PORT.")
        sys.exit(1)
    # sem console (atalho/app): manda a saída para um log
    logs = ROOT.parent / "logs"
    if sys.stdout is None or "--background" in sys.argv:
        logs.mkdir(exist_ok=True)
        fh = open(logs / "servidor.log", "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stderr = fh
    load_saved_path()
    os.chdir(ROOT)

    def open_when_ready():
        for _ in range(120):
            if running():
                if not no_browser:
                    webbrowser.open(URL)
                return
            time.sleep(0.5)

    threading.Thread(target=open_when_ready, daemon=True).start()
    import uvicorn
    from app import app
    print(f"\n  ✂️  CorteFácil rodando em {URL}  (feche esta janela para desligar)\n", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning", log_config=None)


if __name__ == "__main__":
    main()
