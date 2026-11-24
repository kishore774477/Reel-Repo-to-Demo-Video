"""Reel: turn any repo's README and screenshots into a short captioned demo video.

    from reel import make_reel
    r = make_reel("path/to/repo", "out/", target_seconds=45)
    r.video_path          # an .mp4 (crossfades, needs moviepy + ffmpeg) or a .gif (always works)
    r.storyboard.scenes   # what went into it, and for how long
"""
from __future__ import annotations

from .build import ReelResult, make_reel
from .parse import RepoInfo, parse_repo
from .script import Scene, Storyboard, build_script

__version__ = "0.1.0"
__all__ = ["ReelResult", "RepoInfo", "Scene", "Storyboard", "build_script", "make_reel", "parse_repo", "__version__"]
