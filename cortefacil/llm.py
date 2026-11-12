"""IA de edição usando o "harness" que o usuário já tem instalado: Claude Code ou Codex.

Não pedimos chave de API: chamamos o CLI em modo não-interativo, com a conta do próprio usuário.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
EXTRA_DIRS = [
    HOME / ".local/bin", HOME / ".claude/local", HOME / ".npm-global/bin", HOME / ".bun/bin",
    HOME / ".volta/bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin"),
    HOME / "AppData/Roaming/npm", HOME / ".cargo/bin",
] + [Path(p) for p in sorted(glob.glob(str(HOME / ".nvm/versions/node/*/bin")), reverse=True)]

NAMES = {"claude": "Claude Code", "codex": "Codex"}


def find(cmd: str) -> str | None:
    exe = shutil.which(cmd)
    if exe:
        return exe
    for d in EXTRA_DIRS:
        for name in (cmd, cmd + ".cmd", cmd + ".exe"):
            p = d / name
            if p.exists():
                return str(p)
    return None


def available() -> dict:
    return {k: find(k) is not None for k in NAMES}


def pick(pref: str = "auto") -> str | None:
    av = available()
    if pref in NAMES and av.get(pref):
        return pref
    if pref == "none":
        return None
    return next((k for k in ("claude", "codex") if av[k]), None)


def _env_for(exe: str) -> dict:
    env = dict(os.environ)
    # CLIs instalados via npm precisam do "node" no PATH (ex.: nvm)
    dirs = [str(Path(exe).parent)] + [str(d) for d in EXTRA_DIRS if d.exists()]
    env["PATH"] = os.pathsep.join(dirs + [env.get("PATH", "")])
    return env


SYSTEM = ("Você é um editor sênior de vídeos curtos para Instagram Reels e TikTok, em português do "
          "Brasil. Responda SEMPRE e SOMENTE com um objeto JSON válido, sem texto antes ou depois.")


def ask(prompt: str, provider: str, timeout: int = 240) -> str:
    exe = find(provider)
    if not exe:
        raise RuntimeError(f"{NAMES.get(provider, provider)} não encontrado neste computador.")
    workdir = tempfile.mkdtemp(prefix="cortefacil-")  # pasta neutra: sem CLAUDE.md/AGENTS.md alheios
    flags = {"creationflags": 0x08000000} if sys.platform == "win32" else {}  # sem janela no Windows
    if provider == "claude":
        cmd = [exe, "-p", "--output-format", "json", "--system-prompt", SYSTEM, "--tools", "",
               "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence"]
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=workdir, env=_env_for(exe), **flags)
        if p.returncode != 0:
            raise RuntimeError(_friendly(p.stderr or p.stdout, provider))
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            return p.stdout
        if data.get("is_error"):
            raise RuntimeError(_friendly(str(data.get("result")), provider))
        return data.get("result", "")
    # codex
    out = Path(workdir) / "out.txt"
    cmd = [exe, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-o", str(out), "-"]
    p = subprocess.run(cmd, input=SYSTEM + "\n\n" + prompt, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, cwd=workdir,
                       env=_env_for(exe), **flags)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(_friendly(p.stderr or p.stdout, provider))
    return out.read_text(encoding="utf-8")


def _friendly(err: str, provider: str) -> str:
    low = (err or "").lower()
    name = NAMES.get(provider, provider)
    if any(k in low for k in ("login", "auth", "401", "unauthorized", "api key")):
        return f"O {name} não está conectado à sua conta. Abra o Terminal, rode `{provider}` e faça login."
    return f"O {name} não respondeu como esperado: {(err or '').strip()[-300:]}"


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise RuntimeError("A IA não devolveu um resultado legível. Tente de novo.")
        return json.loads(m.group(0))


def build_prompt(words: list[dict], tasks: set[str]) -> str:
    lines, cur = [], []
    for i, w in enumerate(words):
        if i and w["s"] - words[i - 1]["e"] > 0.7 and cur:
            lines.append(" ".join(cur))
            cur = []
        cur.append(f"{w['id']}:{w['text']}")
    if cur:
        lines.append(" ".join(cur))
    want = []
    if "kw" in tasks:
        want.append('"kw": [ids] — palavras-chave para destacar na legenda (~1 a cada 5-7 palavras: '
                    'números, termos centrais, palavras de impacto; nunca artigos/preposições).')
        want.append('"emoji": {"id": "emoji"} — no máximo 1 emoji a cada 2 frases, só onde reforça a ideia.')
    if "fix" in tasks:
        want.append('"fix": {"id": "texto corrigido"} — só erros claros de transcrição (nomes próprios, '
                    'termos técnicos, palavras trocadas). Mantenha a pontuação da palavra.')
    if "cut" in tasks:
        want.append('"cut": [ids] — palavras a remover do vídeo: frases recomeçadas/repetidas (mantenha a '
                    'ÚLTIMA tentativa), gaguejadas, palavras de erro ("corta", "de novo", "pera"), '
                    'vícios em excesso ("tipo", "né"). Seja conservador: nunca remova conteúdo útil.')
    if "topics" in tasks:
        want.append('"topics": [{"id": id, "title": "..."}] — início de cada tópico/seção quando o vídeo '
                    'tem estrutura (listas, passos, dicas). Título curto (até 6 palavras) e pode terminar '
                    'com 1 emoji. Lista vazia se não houver seções claras.')
    if "hooks" in tasks:
        want.append('"hooks": ["...", "...", "..."] — 3 opções de título-gancho para o topo do vídeo, '
                    'até 8 palavras, que gerem curiosidade.')
    return ("Transcrição de um vídeo bruto, palavra por palavra no formato id:palavra "
            "(cada linha é um trecho entre pausas):\n\n" + "\n".join(lines) +
            "\n\nDevolva um JSON com as chaves:\n- " + "\n- ".join(want) +
            "\nUse apenas ids que existem acima.")


def enhance(project: dict, tasks: set[str], provider: str) -> dict:
    """Pede à IA e aplica no projeto. Devolve um resumo do que mudou."""
    words = [w for w in project["words"] if not w.get("removed")]
    if not words:
        raise RuntimeError("Não há fala transcrita neste vídeo.")
    data = parse_json(ask(build_prompt(words, tasks), provider))
    by_id = {w["id"]: w for w in project["words"]}
    ids = lambda xs: [int(x) for x in xs if str(x).lstrip("-").isdigit() and int(x) in by_id]  # noqa: E731
    summary = {"provider": NAMES[provider]}
    if "kw" in tasks and isinstance(data.get("kw"), list):
        for w in project["words"]:
            w["kw"] = False
        for i in ids(data["kw"]):
            by_id[i]["kw"] = True
        emo = data.get("emoji") or {}
        if isinstance(emo, dict):
            for w in project["words"]:
                w["emoji"] = ""
            for k, v in emo.items():
                if str(k).isdigit() and int(k) in by_id and isinstance(v, str):
                    by_id[int(k)]["emoji"] = v.strip()[:8]
                    by_id[int(k)]["kw"] = True
        summary["kw"] = sum(1 for w in project["words"] if w.get("kw"))
        summary["emoji"] = sum(1 for w in project["words"] if w.get("emoji") and w.get("kw"))
    if "fix" in tasks and isinstance(data.get("fix"), dict):
        n = 0
        for k, v in data["fix"].items():
            if str(k).isdigit() and int(k) in by_id and isinstance(v, str) and v.strip():
                if by_id[int(k)]["text"] != v.strip():
                    by_id[int(k)]["text"] = v.strip()
                    n += 1
        summary["fix"] = n
    if "cut" in tasks and isinstance(data.get("cut"), list):
        cut = ids(data["cut"])
        for i in cut:
            by_id[i]["removed"] = True
        summary["cut"] = len(cut)
    if "topics" in tasks and isinstance(data.get("topics"), list):
        topics = []
        for t in data["topics"]:
            if isinstance(t, dict) and str(t.get("id", "")).isdigit() and int(t["id"]) in by_id and t.get("title"):
                topics.append({"word_id": int(t["id"]), "text": str(t["title"]).strip()[:60]})
        project["settings"]["topics"] = topics
        summary["topics"] = len(topics)
    if "hooks" in tasks and isinstance(data.get("hooks"), list):
        hooks = [str(h).strip()[:90] for h in data["hooks"] if str(h).strip()][:3]
        summary["hooks"] = hooks
        if hooks and not (project["settings"].get("title") or "").strip():
            project["settings"]["title"] = hooks[0]
    return summary
