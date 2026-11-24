"""Frames -> an actual video file: an .mp4 with crossfades if moviepy and a usable ffmpeg are available, an
animated .gif (no crossfades, no audio, but needs only Pillow) if they are not. ``video_backend()`` says which
one a given run would use, so the dashboard and the README can report it honestly rather than assume.
"""
from __future__ import annotations

from pathlib import Path

FPS = 24
CROSSFADE = 0.4


def video_backend() -> str:
    try:
        import imageio_ffmpeg  # noqa: F401
        import moviepy  # noqa: F401
    except ImportError:
        return "gif"
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "gif"
    return "mp4" if exe and Path(exe).exists() else "gif"


def render_mp4(frame_paths: list, durations: list, out_path: str | Path, crossfade: float = CROSSFADE) -> Path:
    from moviepy import ImageClip, concatenate_videoclips, vfx

    clips = []
    for i, (p, dur) in enumerate(zip(frame_paths, durations)):
        clip = ImageClip(str(p)).with_duration(dur)
        if i > 0:
            fade = min(crossfade, dur / 2)
            clip = clip.with_effects([vfx.CrossFadeIn(fade)])
        clips.append(clip)
    pad = -min(crossfade, min(durations) / 2) if len(clips) > 1 else 0
    video = concatenate_videoclips(clips, method="compose", padding=pad)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(str(out_path), fps=FPS, codec="libx264", audio=False, logger=None)
    video.close()
    return out_path


def render_gif(frame_paths: list, durations: list, out_path: str | Path) -> Path:
    from PIL import Image

    frames = [Image.open(p).convert("P", palette=Image.ADAPTIVE) for p in frame_paths]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=[int(d * 1000) for d in durations], loop=0)
    return out_path


def render_video(frame_paths: list, durations: list, out_dir: str | Path, basename: str = "demo") -> tuple:
    """Returns ``(path, backend)``. Falls back to a GIF if the mp4 path raises (missing/broken ffmpeg) rather
    than failing the whole render — the storyboard still has somewhere to end up."""
    out_dir = Path(out_dir)
    backend = video_backend()
    if backend == "mp4":
        try:
            return render_mp4(frame_paths, durations, out_dir / f"{basename}.mp4"), "mp4"
        except Exception:
            backend = "gif"
    return render_gif(frame_paths, durations, out_dir / f"{basename}.gif"), "gif"
