"""CorteFácil — servidor local. Rode:  python launcher.py  (abre o navegador sozinho)"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import threading
import traceback
import uuid
from pathlib import Path

import uvicorn
from urllib.parse import urlsplit

from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

import cloud_stt
import engine
import llm
import setup_check
import promo
import sfx
import updater
import validate
from styles import ANIMS, DEFAULT_SETTINGS, FONTS, FORMATS, STYLES

ROOT = Path(__file__).parent
JOBS = Path(os.environ.get("CORTEFACIL_DATA", ROOT.parent / "projetos"))
JOBS.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(JOBS, 0o700)  # vídeos só para o seu usuário
except OSError:
    pass
VERSION = (ROOT.parent / "VERSION").read_text().strip() if (ROOT.parent / "VERSION").exists() else "dev"
SAMPLE = ROOT.parent / "samples" / "exemplo.mp4"
app = FastAPI(title="CorteFácil")
STATUS: dict[str, dict] = {}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
MAX_VIDEO = 8 * 1024 ** 3     # 8 GB
MAX_MUSIC = 200 * 1024 ** 2   # 200 MB


@app.middleware("http")
async def only_local(request: Request, call_next):
    """O app só atende ele mesmo: bloqueia sites abertos no navegador que tentem usar a API local
    (DNS rebinding pelo Host; CSRF pelo Origin/Sec-Fetch-Site)."""
    host = (urlsplit("//" + (request.headers.get("host") or "")).hostname or "").lower()
    if host not in LOCAL_HOSTS:
        return JSONResponse({"detail": "Acesso permitido só pelo próprio computador."}, status_code=403)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and (urlsplit(origin).hostname or "").lower() not in LOCAL_HOSTS:
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
        if request.headers.get("sec-fetch-site") in ("cross-site", "same-site"):
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
    return await call_next(request)


def _save_upload(src, dest: Path, limit: int) -> None:
    total = 0
    with open(dest, "wb") as fh:
        while chunk := src.read(4 * 1024 * 1024):
            total += len(chunk)
            if total > limit:
                fh.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"Arquivo grande demais (máximo {limit // 1024 ** 2} MB).")
            fh.write(chunk)
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


@app.get("/api/prefs")
def prefs_get():
    return cloud_stt.public()


@app.put("/api/prefs")
def prefs_put(body: dict = Body(...)):
    cfg = cloud_stt.load()
    if body.get("stt") in ("local", "groq"):
        cfg["stt"] = body["stt"]
    if "groq_key" in body:
        key = (body.get("groq_key") or "").strip()
        if key:
            ok, msg = cloud_stt.test_key(key)
            if not ok:
                raise HTTPException(400, msg)
            cfg["groq_key"] = key
        else:
            cfg.pop("groq_key", None)
    if cfg.get("stt") == "groq" and not cfg.get("groq_key"):
        raise HTTPException(400, "Cole a sua chave da Groq para usar a transcrição na nuvem.")
    cloud_stt.save(cfg)
    return cloud_stt.public(cfg)


def _busy() -> bool:
    for st in STATUS.values():
        if st.get("state") == "analyzing":
            return True
        if (st.get("render") or {}).get("state") == "running" or (st.get("ai") or {}).get("state") == "running":
            return True
    return False


@app.get("/api/update")
def update_check(force: bool = False):
    cfg = cloud_stt.load()
    auto = cfg.get("update_check", True)
    info = updater.check(force=True) if force else (updater.check() if auto else {"current": updater.current(),
                                                                                  "dev": updater.is_dev_checkout(),
                                                                                  "available": False})
    return {**info, "auto": auto, "job": dict(updater.STATE)}


@app.put("/api/update")
def update_prefs(body: dict = Body(...)):
    cfg = cloud_stt.load()
    cfg["update_check"] = bool(body.get("auto", True))
    cloud_stt.save(cfg)
    return {"auto": cfg["update_check"]}


@app.post("/api/update")
def update_apply():
    info = updater.check()
    if not info.get("available"):
        raise HTTPException(400, "Você já está na versão mais recente.")
    if updater.STATE.get("state") in ("running", "restarting"):
        return {"ok": True}
    if _busy():
        raise HTTPException(409, "Espere terminar a análise ou a exportação em andamento.")
    updater.STATE.update(state="running", message="Preparando", progress=0.0)
    threading.Thread(target=updater.apply, args=(info["tag"], _busy), daemon=True).start()
    return {"ok": True}


@app.get("/api/promo")
def promo_get():
    cfg = cloud_stt.load()
    return promo.visible(cfg.get("promo_dismissed") or [], cfg.get("promo_check", True))


@app.put("/api/promo")
def promo_prefs(body: dict = Body(...)):
    cfg = cloud_stt.load()
    cfg["promo_check"] = bool(body.get("enabled", True))
    cloud_stt.save(cfg)
    return {"enabled": cfg["promo_check"]}


@app.post("/api/promo/dismiss")
def promo_dismiss(body: dict = Body(...)):
    cid = str(body.get("id") or "")
    if not promo.ID.fullmatch(cid):
        raise HTTPException(400)
    cfg = cloud_stt.load()
    cfg["promo_dismissed"] = ([x for x in cfg.get("promo_dismissed") or [] if x != cid] + [cid])[-200:]
    cloud_stt.save(cfg)
    return {"ok": True}


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


@app.get("/sfx/{kind}.wav")
def sfx_sound(kind: str):
    if kind not in sfx.SOUNDS:
        raise HTTPException(404)
    return Response(sfx.wav_bytes(kind), media_type="audio/wav", headers={"Cache-Control": "max-age=86400"})


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
    tasks = {t for t in body.get("tasks", []) if t in {"kw", "fix", "cut", "topics", "hooks", "callouts"}}
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
    return {"styles": STYLES, "formats": FORMATS, "defaults": DEFAULT_SETTINGS, "fonts": FONTS, "anims": ANIMS}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if ext not in {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}:
        raise HTTPException(400, "Formato não suportado. Use MP4, MOV, WEBM ou MKV.")
    jid, d = _new_job(Path(file.filename or "video").stem)
    try:
        _save_upload(file.file, d / f"source{ext}", MAX_VIDEO)
    except HTTPException:
        shutil.rmtree(d, ignore_errors=True)
        STATUS.pop(jid, None)
        raise
    threading.Thread(target=_analyze, args=(jid,), daemon=True).start()
    return {"id": jid}


@app.get("/api/jobs/{jid}")
def job(jid: str):
    d = job_dir(jid)
    st = dict(STATUS.get(jid) or {})
    if not st.get("state"):  # servidor reiniciado: recupera do disco
        rec = {"state": "ready" if (d / "project.json").exists() else "error",
               "error": "Análise interrompida. Envie o vídeo novamente."}
        if (d / "final.mp4").exists():
            rec["render"] = {"state": "done", "progress": 1, "version": "0"}
        st = {**rec, **st}
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
        project["settings"].update(validate.settings(body["settings"]))
    if "words" in body:
        by_id = {w["id"]: w for w in project["words"]}
        for w in body["words"] if isinstance(body["words"], list) else []:
            cur = by_id.get(w.get("id")) if isinstance(w, dict) else None
            if not cur:
                continue
            cur.update(validate.word(w))
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
    _save_upload(file.file, d / name, MAX_MUSIC)
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


@app.get("/api/jobs/{jid}/thumb")
def thumb(jid: str, t: float = 0.0):
    d = job_dir(jid)
    if not math.isfinite(t):
        raise HTTPException(400)
    t = max(0.0, min(t, float(load(jid)["meta"].get("duration") or 0) - 0.2))
    f = d / f"thumb_{int(t * 10)}.jpg"
    if not f.exists():
        engine.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0.0, t):.2f}", "-i", str(d / "proxy.mp4"),
                    "-frames:v", "1", "-q:v", "3", str(f)])
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="image/jpeg")


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
