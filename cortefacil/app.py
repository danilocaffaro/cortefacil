"""CorteFácil — servidor local. Rode:  python launcher.py  (abre o navegador sozinho)"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import traceback
import uuid
from pathlib import Path

import uvicorn
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

import engine
import llm
import setup_check
from styles import DEFAULT_SETTINGS, FORMATS, STYLES

ROOT = Path(__file__).parent
JOBS = Path(os.environ.get("CORTEFACIL_DATA", ROOT.parent / "projetos"))
JOBS.mkdir(parents=True, exist_ok=True)
VERSION = (ROOT.parent / "VERSION").read_text().strip() if (ROOT.parent / "VERSION").exists() else "dev"
SAMPLE = ROOT.parent / "samples" / "exemplo.mp4"
app = FastAPI(title="CorteFácil")
STATUS: dict[str, dict] = {}
GPU_LOCK = threading.Lock()


def job_dir(jid: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", jid):
        raise HTTPException(404, "Projeto não encontrado")
    d = JOBS / jid
    if not d.exists():
        raise HTTPException(404, "Projeto não encontrado")
    return d


def load(jid: str) -> dict:
    p = job_dir(jid) / "project.json"
    if not p.exists():
        raise HTTPException(409, "Projeto ainda em análise")
    return json.loads(p.read_text())


def save(jid: str, project: dict) -> None:
    (job_dir(jid) / "project.json").write_text(json.dumps(project, ensure_ascii=False, default=float))


def set_status(jid, **kw):
    STATUS.setdefault(jid, {}).update(kw)


def source_of(d: Path) -> Path:
    return next(d.glob("source.*"))


def _analyze(jid: str):
    d = JOBS / jid
    try:
        def prog(stage, p, msg):
            set_status(jid, stage=stage, progress=p, message=msg)
        with GPU_LOCK:
            project = engine.analyze(str(source_of(d)), d, prog)
        project["name"] = STATUS[jid].get("name", "video")
        save(jid, project)
        set_status(jid, state="ready", progress=1.0)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        set_status(jid, state="error", error=str(e))


def _render(jid: str):
    d = JOBS / jid
    try:
        project = load(jid)
        out = d / "final.mp4"
        tmp = d / "final.tmp.mp4"

        def prog(stage, p, msg):
            set_status(jid, render={"state": "running", "progress": p, "message": msg})
        engine.render(project, str(source_of(d)), d, str(tmp), prog)
        tmp.replace(out)
        set_status(jid, render={"state": "done", "progress": 1.0, "message": "Vídeo pronto!",
                                "version": uuid.uuid4().hex[:6]})
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        set_status(jid, render={"state": "error", "progress": 0, "message": str(e)})


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/favicon.png")
def favicon():
    return FileResponse(ROOT / "static" / "favicon.png", headers={"Cache-Control": "max-age=86400"})


@app.get("/fonts/{name}")
def fonts(name: str):
    f = ROOT / "fonts" / name
    if not re.fullmatch(r"[\w\-]+\.ttf", name) or not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="font/ttf", headers={"Cache-Control": "max-age=86400"})


@app.get("/api/setup")
def setup_status():
    return {**setup_check.status(), "version": VERSION, "sample": SAMPLE.exists()}


@app.post("/api/setup/prepare")
def setup_prepare():
    setup_check.prepare()
    return {"ok": True}


@app.post("/api/shutdown")
def shutdown():
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return {"ok": True}


def _new_job(name: str) -> tuple[str, Path]:
    jid = uuid.uuid4().hex[:12]
    d = JOBS / jid
    d.mkdir()
    STATUS[jid] = {"state": "analyzing", "stage": "upload", "progress": 0.0,
                   "message": "Recebido", "name": name}
    return jid, d


@app.post("/api/sample")
def sample():
    if not SAMPLE.exists():
        raise HTTPException(404, "Vídeo de exemplo não encontrado.")
    jid, d = _new_job("exemplo")
    shutil.copy(SAMPLE, d / "source.mp4")
    threading.Thread(target=_analyze, args=(jid,), daemon=True).start()
    return {"id": jid}


@app.get("/api/jobs")
def list_jobs():
    out = []
    for d in sorted(JOBS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:12]:
        pj = d / "project.json"
        if d.is_dir() and pj.exists():
            try:
                p = json.loads(pj.read_text())
                out.append({"id": d.name, "name": p.get("name", "video"),
                            "duration": p["meta"]["duration"], "done": (d / "final.mp4").exists()})
            except (ValueError, KeyError):
                continue
    return out


def _ai(jid: str, tasks: set[str], provider: str):
    try:
        set_status(jid, ai={"state": "running"})
        project = load(jid)
        summary = llm.enhance(project, tasks, provider)
        save(jid, project)
        set_status(jid, ai={"state": "done", "summary": summary})
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        set_status(jid, ai={"state": "error", "error": str(e)})


@app.post("/api/jobs/{jid}/ai")
def ai(jid: str, body: dict = Body(...)):
    load(jid)
    tasks = {t for t in body.get("tasks", []) if t in {"kw", "fix", "cut", "topics", "hooks"}}
    provider = llm.pick(body.get("provider") or "auto")
    if not provider:
        raise HTTPException(400, "Nenhum assistente de IA (Claude Code ou Codex) foi encontrado.")
    if not tasks:
        raise HTTPException(400, "Escolha pelo menos uma tarefa.")
    if ((STATUS.get(jid) or {}).get("ai") or {}).get("state") == "running":
        return {"ok": True}
    threading.Thread(target=_ai, args=(jid, tasks, provider), daemon=True).start()
    return {"ok": True, "provider": llm.NAMES[provider]}


@app.get("/api/config")
def config():
    return {"styles": STYLES, "formats": FORMATS, "defaults": DEFAULT_SETTINGS}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if ext not in {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}:
        raise HTTPException(400, "Formato não suportado. Use MP4, MOV, WEBM ou MKV.")
    jid, d = _new_job(Path(file.filename or "video").stem)
    with open(d / f"source{ext}", "wb") as fh:
        shutil.copyfileobj(file.file, fh, length=4 * 1024 * 1024)
    threading.Thread(target=_analyze, args=(jid,), daemon=True).start()
    return {"id": jid}


@app.get("/api/jobs/{jid}")
def job(jid: str):
    d = job_dir(jid)
    st = dict(STATUS.get(jid) or {})
    if not st:  # servidor reiniciado: recupera do disco
        st = {"state": "ready" if (d / "project.json").exists() else "error",
              "error": "Análise interrompida. Envie o vídeo novamente."}
        if (d / "final.mp4").exists():
            st["render"] = {"state": "done", "progress": 1, "version": "0"}
        STATUS[jid] = st
    if st.get("state") == "ready":
        project = load(jid)
        if (st.get("ai") or {}).get("state") == "done":
            STATUS[jid]["ai"] = {"state": "seen"}
        st["project"] = {k: project[k] for k in ("meta", "words", "settings")}
        st["project"]["name"] = project.get("name", "video")
        st["layout"] = engine.layout(project)
    return JSONResponse(st)


@app.put("/api/jobs/{jid}")
def update(jid: str, body: dict = Body(...)):
    project = load(jid)
    if "settings" in body:
        allowed = set(DEFAULT_SETTINGS)
        project["settings"].update({k: v for k, v in body["settings"].items() if k in allowed})
    if "words" in body:
        by_id = {w["id"]: w for w in project["words"]}
        for w in body["words"]:
            cur = by_id.get(w.get("id"))
            if not cur:
                continue
            for k in ("text", "kw", "removed", "emoji"):
                if k in w:
                    cur[k] = w[k]
    save(jid, project)
    return engine.layout(project)


@app.post("/api/jobs/{jid}/music")
async def music(jid: str, file: UploadFile = File(...)):
    d = job_dir(jid)
    ext = Path(file.filename or "m.mp3").suffix.lower()
    if ext not in {".mp3", ".m4a", ".wav", ".aac", ".ogg"}:
        raise HTTPException(400, "Use MP3, M4A, WAV, AAC ou OGG.")
    for old in d.glob("music.*"):
        old.unlink()
    name = f"music{ext}"
    with open(d / name, "wb") as fh:
        shutil.copyfileobj(file.file, fh)
    project = load(jid)
    project["settings"]["music"] = name
    save(jid, project)
    return {"music": name, "label": file.filename}


@app.post("/api/jobs/{jid}/render")
def start_render(jid: str):
    job_dir(jid)
    cur = (STATUS.get(jid) or {}).get("render") or {}
    if cur.get("state") == "running":
        return {"ok": True}
    set_status(jid, render={"state": "running", "progress": 0.0, "message": "Preparando"})
    threading.Thread(target=_render, args=(jid,), daemon=True).start()
    return {"ok": True}


@app.get("/api/jobs/{jid}/proxy")
def proxy(jid: str):
    return FileResponse(job_dir(jid) / "proxy.mp4", media_type="video/mp4")


@app.get("/api/jobs/{jid}/music")
def music_file(jid: str):
    d = job_dir(jid)
    m = next(d.glob("music.*"), None)
    if not m:
        raise HTTPException(404)
    return FileResponse(m)


@app.get("/api/jobs/{jid}/final")
def final(jid: str, download: int = 0):
    d = job_dir(jid)
    f = d / "final.mp4"
    if not f.exists():
        raise HTTPException(404, "Ainda não exportado")
    name = None
    if download:
        try:
            name = re.sub(r"[^\w\- ]", "", load(jid).get("name", "video"))[:60] + "_editado.mp4"
        except HTTPException:
            name = "video_editado.mp4"
    return FileResponse(f, media_type="video/mp4", filename=name)


if __name__ == "__main__":
    import launcher
    launcher.main()
