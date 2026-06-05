"""FastAPI web app: a job description in, a free-course study table out.

Routes:
  GET  /                 the input form
  GET  /providers        provider availability (JSON)
  POST /generate         run the pipeline, render the table, return links + preview
  GET  /download/{job}/{filename}   serve a generated file
"""
from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .generator import GenerationError, generate_plan
from .providers import list_providers
from .render_table import render_csv, render_html, render_markdown

BASE = Path(__file__).resolve().parent
GEN = BASE.parent / "generated"
GEN.mkdir(exist_ok=True)

# Generated output accumulates one dir per run; sweep dirs older than this on each
# request. Set GENERATED_TTL_HOURS=0 to disable cleanup and keep everything.
GENERATED_TTL_HOURS = float(os.environ.get("GENERATED_TTL_HOURS", "24"))

JOB_RE = re.compile(r"[0-9a-f]{32}")

MEDIA = {".md": "text/markdown", ".csv": "text/csv", ".html": "text/html"}


def cleanup_generated(root: Path, ttl_hours: float) -> int:
    """Delete job dirs older than `ttl_hours`; return how many were removed.

    Only touches 32-hex dirs we created, never anything else dropped in
    `generated/`. A non-positive TTL disables cleanup.
    """
    if ttl_hours <= 0 or not root.exists():
        return 0
    cutoff = time.time() - ttl_hours * 3600
    removed = 0
    for child in root.iterdir():
        if not (child.is_dir() and JOB_RE.fullmatch(child.name)):
            continue
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        except OSError:
            pass
    return removed


app = FastAPI(title="Interview Prep Mapper")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))


def safe_slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name or "").strip("_")
    return slug[:40] or "role"


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"providers": list_providers()}
    )


@app.get("/providers")
def providers():
    return list_providers(include_models=True)


@app.post("/generate")
def generate(
    jd: str = Form(...),
    provider: str = Form("mock"),
    model: str = Form(""),
    instructions: str = Form(""),
):
    cleanup_generated(GEN, GENERATED_TTL_HOURS)
    try:
        plan = generate_plan(jd, provider, model or None, instructions=instructions)
    except GenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not plan.rows:
        raise HTTPException(
            status_code=400,
            detail=("No learnable requirements found — the description may be only "
                    "degree/experience qualifications, or too short. Try a fuller posting."),
        )

    job = uuid.uuid4().hex
    job_dir = GEN / job
    job_dir.mkdir(parents=True, exist_ok=True)
    slug = safe_slug(plan.role)

    names = {
        "md": f"{slug}_PrepPlan.md",
        "csv": f"{slug}_PrepPlan.csv",
        "html": f"{slug}_PrepPlan.html",
    }
    (job_dir / names["md"]).write_text(render_markdown(plan), encoding="utf-8")
    (job_dir / names["csv"]).write_text(render_csv(plan), encoding="utf-8")
    (job_dir / names["html"]).write_text(render_html(plan), encoding="utf-8")

    def url(key):
        return f"/download/{job}/{names[key]}"

    return {
        "job": job,
        "files": [
            {"label": "Table — Markdown", "url": url("md")},
            {"label": "Table — CSV", "url": url("csv")},
            {"label": "Table — HTML", "url": url("html")},
        ],
        "preview": plan.model_dump(),
    }


@app.get("/download/{job}/{filename}")
def download(job: str, filename: str):
    if not JOB_RE.fullmatch(job):
        raise HTTPException(status_code=404, detail="Not found")
    path = (GEN / job / filename).resolve()
    if not str(path).startswith(str(GEN.resolve()) + "/") or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    media = MEDIA.get(path.suffix, "application/octet-stream")
    return FileResponse(str(path), media_type=media, filename=filename)
