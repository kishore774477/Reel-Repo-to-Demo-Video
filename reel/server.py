"""FastAPI app: the build pipeline as an API, and the dashboard."""
from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .build import make_reel
from .sample import generate
from .video import video_backend

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv("REEL_DATA", ROOT / "data"))
SECOND_PRESETS = [20, 30, 45, 60, 90]


class BuildReq(BaseModel):
    repo: str | None = None          # None / "sample" -> the bundled sample
    seconds: float = 45.0
    max_screenshots: int = 4
    cta_text: str | None = None
    render: bool = True


def _sample_repo() -> Path:
    p = DATA / "sample_repo"
    if not (p / "README.md").exists():
        generate(p)
    return p


def create_app(precompute: bool = True) -> FastAPI:
    state: dict = {"gen": 0, "rendering": False}

    out_dir = DATA / "current"

    def build(req: BuildReq) -> None:
        repo = req.repo if req.repo and req.repo != "sample" else _sample_repo()
        shutil.rmtree(out_dir, ignore_errors=True)
        state["gen"] += 1
        r = make_reel(repo, out_dir, target_seconds=req.seconds, max_screenshots=req.max_screenshots, cta_text=req.cta_text, render=req.render)
        state["result"], state["req"] = r, req

    build(BuildReq(render=False))   # the storyboard only: instant, so the app starts serving right away

    if precompute:
        def render_sample():
            gen = state["gen"]
            try:
                from .video import render_video
                r = state["result"]
                state["rendering"] = True
                path, backend = render_video(r.frame_paths, [s.duration for s in r.storyboard.scenes], out_dir)
                if state["gen"] == gen:                     # nobody built something else while this ran
                    r.video_path, r.backend = path, backend
            finally:
                state["rendering"] = False
        threading.Thread(target=render_sample, daemon=True).start()

    app = FastAPI(title="Reel", version=__version__, description="Turn a repo's README and screenshots into a short captioned demo video.")
    app.state.get = lambda: state

    def R():
        if "result" not in state:
            raise HTTPException(409, "nothing built yet")
        return state["result"]

    @app.get("/api/meta")
    def meta():
        return {"version": __version__, "backend": video_backend(), "second_presets": SECOND_PRESETS, "req": state["req"].model_dump(), "rendering": state["rendering"]}

    @app.get("/api/storyboard")
    def storyboard():
        r = R()
        return r.to_dict()

    @app.post("/api/build")
    def build_(req: BuildReq):
        if not 5 <= req.seconds <= 300:
            raise HTTPException(400, "seconds must be between 5 and 300")
        if not 0 <= req.max_screenshots <= 10:
            raise HTTPException(400, "max_screenshots must be between 0 and 10")
        try:
            build(req)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return R().to_dict()

    @app.post("/api/reset")
    def reset():
        build(BuildReq())
        return R().to_dict()

    @app.get("/api/frame/{index}")
    def frame(index: int):
        r = R()
        if not 0 <= index < len(r.frame_paths):
            raise HTTPException(404, f"no frame {index} (0..{len(r.frame_paths) - 1})")
        return FileResponse(r.frame_paths[index])

    @app.get("/api/video")
    def video():
        r = R()
        if not r.video_path or not Path(r.video_path).exists():
            raise HTTPException(404, "no video for this build (render=false, or nothing built yet)")
        media = "video/mp4" if r.backend == "mp4" else "image/gif"
        return FileResponse(r.video_path, media_type=media)

    @app.get("/")
    def index():
        return FileResponse(ROOT / "web" / "index.html")

    app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
    return app
