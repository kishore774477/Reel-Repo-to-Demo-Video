"""Build a demo video from a repo.

    python examples/make_a_reel.py                              # the bundled sample
    python examples/make_a_reel.py path\\to\\a\\repo out\\mine 30
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reel import make_reel                 # noqa: E402
from reel.sample import generate           # noqa: E402

repo = sys.argv[1] if len(sys.argv) > 1 else None
out = sys.argv[2] if len(sys.argv) > 2 else "out"
seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 45.0

if repo is None:
    import tempfile
    repo = Path(tempfile.mkdtemp()) / "pathfinder-sample"
    generate(repo)

r = make_reel(repo, out, target_seconds=seconds)
print(f"{r.info.title} — {r.info.tagline or '(no tagline found)'}\n")
for s in r.storyboard.scenes:
    tag = f" [{Path(s.image).name}]" if s.image else ""
    print(f"  {s.duration:>4.1f}s  {s.kind:<12} {s.heading}{tag}")
print(f"\n{r.storyboard.total_seconds:.1f}s of {seconds:.0f}s asked for")
print(f"wrote {r.video_path} ({r.backend})")
