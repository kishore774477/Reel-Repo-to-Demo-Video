"""Command line: python -m reel <command>"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .build import make_reel
from .sample import generate
from .video import video_backend


def main(argv=None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="reel", description="Turn a repo's README and screenshots into a short demo video")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build", help="build a video from a repo")
    p.add_argument("repo")
    p.add_argument("--out", default="out")
    p.add_argument("--seconds", type=float, default=45.0)
    p.add_argument("--max-screenshots", type=int, default=4)
    p.add_argument("--script-only", action="store_true", help="print the scene plan without rendering a video")
    p = sub.add_parser("demo", help="build the bundled sample repo")
    p.add_argument("--out", default="out")
    p.add_argument("--seconds", type=float, default=45.0)
    a = ap.parse_args(argv)

    repo = a.repo if a.cmd == "build" else None
    if a.cmd == "demo":
        repo = Path(tempfile.mkdtemp()) / "pathfinder-sample"
        generate(repo)
    try:
        r = make_reel(repo, a.out, target_seconds=a.seconds, max_screenshots=getattr(a, "max_screenshots", 4), render=not getattr(a, "script_only", False))
    except ValueError as e:
        sys.exit(str(e))

    print(f"{r.info.title} — {r.info.tagline or '(no tagline found)'}")
    if not r.info.readme_found:
        print("  (no README.md found; the video is just a title and a CTA card)")
    print(f"\n{len(r.storyboard.scenes)} scenes, {r.storyboard.total_seconds:.1f}s (asked for {r.storyboard.target_seconds:.0f}s)\n")
    for i, s in enumerate(r.storyboard.scenes, 1):
        tag = f" [{Path(s.image).name}]" if s.image else ""
        print(f"  {i:>2}. {s.duration:>4.1f}s  {s.kind:<12} {s.heading}{tag}")
    if r.video_path:
        print(f"\nwrote {r.video_path} ({r.backend})")
        if r.backend == "gif":
            print("(no working ffmpeg found — fell back to an animated GIF; 'pip install moviepy imageio-ffmpeg' for a real .mp4 with crossfades)")
    else:
        print(f"\n(--script-only: no video rendered. video_backend() on this machine: {video_backend()})")


if __name__ == "__main__":
    main()
