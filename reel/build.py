"""One call that runs the whole pipeline: parse the README, build the scene script, render the frames, and
assemble a video (or GIF) from them."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .parse import RepoInfo, parse_repo
from .render import render_storyboard
from .script import Storyboard, build_script
from .video import render_video


@dataclass
class ReelResult:
    info: RepoInfo
    storyboard: Storyboard
    frame_paths: list
    video_path: Path | None
    backend: str | None

    def to_dict(self) -> dict:
        return {"repo": self.info.root.name, "title": self.info.title, "tagline": self.info.tagline, "readme_found": self.info.readme_found,
                "storyboard": self.storyboard.to_dict(), "video_path": str(self.video_path) if self.video_path else None, "backend": self.backend}


def make_reel(repo_path: str | Path, out_dir: str | Path, target_seconds: float = 45.0, max_screenshots: int = 4,
              cta_text: str | None = None, render: bool = True) -> ReelResult:
    info = parse_repo(repo_path, max_screenshots=max(max_screenshots, 6))
    storyboard = build_script(info, target_seconds, max_screenshots, cta_text)
    out_dir = Path(out_dir)
    frame_paths = render_storyboard(storyboard, out_dir / "frames")
    video_path, backend = (None, None)
    if render:
        durations = [s.duration for s in storyboard.scenes]
        video_path, backend = render_video(frame_paths, durations, out_dir)
    return ReelResult(info, storyboard, frame_paths, video_path, backend)
