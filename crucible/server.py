"""
crucible/server.py — Local web app: upload a git repo, pick base and PR, verify its findings.

Verify-only: the uploaded repo must already contain attacker output
(runs/<name>/findings.json or runs/<name>/findings/<lens>.json, plus the tests they point to).
Crucible then runs the deterministic proof gates and builds the report. No AI runs here.

    .venv/bin/python -m crucible.cli serve     # http://127.0.0.1:8765

This runs the uploaded repo's tests on this machine, so it only listens on 127.0.0.1.
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import threading
import uuid
import zipfile
from dataclasses import asdict
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from crucible.layout import load_layout
from crucible.merge import run_merge
from crucible.report import build_report
from crucible.verify import run_verification

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".crucible-work"
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
_SKIP_DIRS = {".venv", "venv", "node_modules", ".crucible-work", "__pycache__", ".pytest_cache",
              "worktrees", "junit"}

app = FastAPI(title="Crucible")
uploads: dict[str, dict] = {}
jobs: dict[str, dict] = {}
_job_lock = threading.Lock()   # one verification at a time (stdout is captured per job)

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=True)


# ── Repo intake ───────────────────────────────────────────────────────────────

def _safe_rel(path: str) -> PurePosixPath:
    rel = PurePosixPath(path.replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise HTTPException(400, f"Unsafe path in upload: {path!r}")
    return rel


def _find_repo_root(base: Path) -> Path:
    """The upload itself, or its single top-level folder, must contain .git."""
    if (base / ".git").exists():
        return base
    children = [c for c in base.iterdir() if c.is_dir() and c.name != "__MACOSX"]
    if len(children) == 1 and (children[0] / ".git").exists():
        return children[0]
    raise HTTPException(
        400, "No .git folder found. Upload the whole repository including its .git folder "
             "(zip it with hidden files), so Crucible can compare branches.")


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        raise HTTPException(400, f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _inspect(upload_id: str) -> dict:
    repo: Path = uploads[upload_id]["repo"]
    _git(repo, "worktree", "prune")
    refs = _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/tags").splitlines()
    # A run dir holds findings.json (merged) or findings/<lens>.json (per-lens attacker output)
    candidates = list(repo.rglob("findings.json")) + [d for d in repo.rglob("findings") if d.is_dir()]
    run_dirs = sorted({
        str(c.parent.relative_to(repo)) for c in candidates
        if not (_SKIP_DIRS | {".git"}) & set(c.relative_to(repo).parts)
    })
    base_guess = next((r for r in ("main", "master") if r in refs), refs[0] if refs else "")
    return {
        "upload_id": upload_id,
        "name": uploads[upload_id]["name"],
        "refs": refs,
        "base_guess": base_guess,
        "run_dirs": run_dirs,
        "layout": asdict(load_layout(repo)),
    }


def _new_upload(name: str) -> tuple[str, Path]:
    upload_id = uuid.uuid4().hex[:10]
    dest = WORK / "uploads" / upload_id
    dest.mkdir(parents=True)
    return upload_id, dest


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...), paths: list[str] = Form(default=[])) -> dict:
    """Accept either one .zip of a repo, or a folder (files + their relative paths)."""
    total = 0
    if len(files) == 1 and (files[0].filename or "").lower().endswith(".zip"):
        upload_id, dest = _new_upload(files[0].filename)
        data = await files[0].read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Upload is larger than 200 MB")
        if not zipfile.is_zipfile(io.BytesIO(data)):
            shutil.rmtree(dest, ignore_errors=True)
            raise HTTPException(400, "That file is not a valid .zip archive")
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for member in zf.infolist():
                rel = _safe_rel(member.filename)
                target = dest / rel
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(member))
        name = files[0].filename
    else:
        if len(paths) != len(files):
            raise HTTPException(400, "Folder upload needs one relative path per file")
        upload_id, dest = _new_upload("folder")
        for f, p in zip(files, paths):
            data = await f.read()
            total += len(data)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Upload is larger than 200 MB")
            target = dest / _safe_rel(p)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        name = PurePosixPath(paths[0]).parts[0] if paths else "folder"
    uploads[upload_id] = {"repo": _find_repo_root(dest), "name": name}
    return _inspect(upload_id)


class LocalRepo(BaseModel):
    path: str


@app.post("/api/local")
def local_repo(body: LocalRepo) -> dict:
    """Copy a repo that is already on this machine (the original is never modified)."""
    src = Path(body.path).expanduser().resolve()
    if not (src / ".git").exists():
        raise HTTPException(400, f"{src} is not a git repository (no .git folder)")
    upload_id, dest = _new_upload(src.name)
    shutil.copytree(src, dest / src.name, symlinks=True,
                    ignore=shutil.ignore_patterns(*_SKIP_DIRS))
    uploads[upload_id] = {"repo": dest / src.name, "name": src.name}
    return _inspect(upload_id)


# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    upload_id: str
    base: str
    pr: str
    run_dir: str
    layout: dict[str, str] = {}


class _JobLog(io.TextIOBase):
    def __init__(self, job: dict):
        self.job = job

    def write(self, s: str) -> int:
        self.job["log"] += s
        return len(s)


def _run_job(job_id: str) -> None:
    job = jobs[job_id]
    repo: Path = uploads[job["upload_id"]]["repo"]
    run_dir = repo / job["run_dir"]
    layout = load_layout(repo, job["layout"])
    with _job_lock, contextlib.redirect_stdout(_JobLog(job)):
        job["status"] = "running"
        try:
            print(f"repo: {uploads[job['upload_id']]['name']}   base: {job['base']}   pr: {job['pr']}")
            print(f"layout: {asdict(layout)}\n")
            # Verify-only: drop results of any earlier fix run so the report shows this run only
            (run_dir / "fix_check.json").unlink(missing_ok=True)
            timing_path = run_dir / "timing.json"
            if timing_path.exists():
                timing = json.loads(timing_path.read_text())
                for stage in ("fix", "verify_after_fix"):
                    timing.pop(stage, None)
                timing_path.write_text(json.dumps(timing, indent=2))
            if not (run_dir / "findings.json").exists():
                print("no findings.json, merging per-lens findings/ …")
                run_merge(run_dir, repo)
            run_verification(job["pr"], job["base"], run_dir, repo, keep=False, layout=layout)
            build_report(run_dir, repo, job["base"], layout)
            verdicts = json.loads((run_dir / "verdicts.json").read_text())
            job["result"] = {
                "total": len(verdicts),
                "proven": sum(v["verdict"] == "PROVEN" for v in verdicts),
                "rejected": sum(v["verdict"] == "REJECTED" for v in verdicts),
                "verdicts": [{k: v.get(k) for k in ("id", "lens", "claim", "basis", "verdict", "reason")}
                             for v in verdicts],
            }
            job["report"] = run_dir / "report.html"
            job["status"] = "done"
            print("done: report ready")
        except HTTPException as e:
            job["status"], job["error"] = "failed", e.detail
        except Exception as e:  # surfaced to the page; the job log has the details
            job["status"], job["error"] = "failed", f"{type(e).__name__}: {e}"
            print(f"\nFAILED: {job['error']}")


@app.post("/api/jobs")
def start_job(req: JobRequest) -> dict:
    if req.upload_id not in uploads:
        raise HTTPException(404, "Unknown upload; upload the repository again")
    repo: Path = uploads[req.upload_id]["repo"]
    for ref in (req.base, req.pr):
        _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if req.base == req.pr:
        raise HTTPException(400, "Base and PR must be different")
    run_dir = (repo / _safe_rel(req.run_dir))
    if not ((run_dir / "findings.json").exists() or (run_dir / "findings").is_dir()):
        raise HTTPException(400, f"{req.run_dir} has no findings.json or findings/ folder")
    job_id = uuid.uuid4().hex[:10]
    jobs[job_id] = {**req.model_dump(), "status": "queued", "log": "", "result": None, "error": None}
    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = jobs.get(job_id) or {}
    if not job:
        raise HTTPException(404, "Unknown job")
    return {
        "status": job["status"], "log": job["log"], "error": job["error"], "result": job["result"],
        "report_url": f"/jobs/{job_id}/report.html" if job.get("report") else None,
    }


@app.get("/jobs/{job_id}/report.html")
def job_report(job_id: str) -> FileResponse:
    job = jobs.get(job_id)
    if not job or not job.get("report"):
        raise HTTPException(404, "No report for this job yet")
    return FileResponse(job["report"], media_type="text/html")


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home() -> str:
    summary_path = ROOT / "runs" / "summary.json"
    totals = json.loads(summary_path.read_text())["totals"] if summary_path.exists() else None
    return _env.get_template("studio.html.j2").render(totals=totals)


if (ROOT / "dashboard").exists():
    app.mount("/dashboard", StaticFiles(directory=ROOT / "dashboard", html=True), name="dashboard")
if (ROOT / "runs").exists():
    app.mount("/runs", StaticFiles(directory=ROOT / "runs", html=True), name="runs")


def serve(port: int = 8765) -> None:
    import uvicorn
    WORK.mkdir(exist_ok=True)
    uvicorn.run(app, host="127.0.0.1", port=port)
