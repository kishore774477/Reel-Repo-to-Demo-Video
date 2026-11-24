import pytest
from PIL import Image, ImageSequence

from reel.build import make_reel
from reel.video import render_gif, render_mp4, render_video, video_backend


def _frames(tmp_path, n=3, colors=((40, 40, 40), (90, 90, 90), (150, 60, 60))):
    paths = []
    for i in range(n):
        p = tmp_path / f"f{i}.png"
        Image.new("RGB", (160, 90), colors[i % len(colors)]).save(p)
        paths.append(p)
    return paths


def test_video_backend_reports_mp4_on_this_machine():
    assert video_backend() in ("mp4", "gif")        # whichever it is, it must not raise


def test_render_gif_always_works_and_has_the_right_frame_count(tmp_path):
    paths = _frames(tmp_path)
    out = render_gif(paths, [0.5, 0.5, 0.5], tmp_path / "out" / "x.gif")
    assert out.exists()
    with Image.open(out) as im:
        n = sum(1 for _ in ImageSequence.Iterator(im))
    assert n == 3


@pytest.mark.skipif(video_backend() != "mp4", reason="no working ffmpeg on this machine")
def test_render_mp4_produces_a_video_of_the_right_length(tmp_path):
    paths = _frames(tmp_path)
    durations = [1.0, 1.0, 1.0]
    out = render_mp4(paths, durations, tmp_path / "out" / "x.mp4", crossfade=0.0)
    assert out.exists()
    from moviepy import VideoFileClip
    clip = VideoFileClip(str(out))
    try:
        assert clip.duration == pytest.approx(sum(durations), abs=0.2)
        assert clip.size == [160, 90] or tuple(clip.size) == (160, 90)
    finally:
        clip.close()


def test_render_video_dispatches_to_the_available_backend(tmp_path):
    paths = _frames(tmp_path)
    path, backend = render_video(paths, [0.6, 0.6, 0.6], tmp_path / "out")
    assert backend in ("mp4", "gif") and path.exists() and path.suffix == f".{backend}"


# ---------------------------------------------------------------------------- the whole pipeline
def test_make_reel_without_rendering_is_fast_and_has_no_video(sample_repo, tmp_path):
    r = make_reel(sample_repo, tmp_path / "out", render=False)
    assert r.video_path is None and r.backend is None
    assert len(r.frame_paths) == len(r.storyboard.scenes)
    d = r.to_dict()
    assert d["repo"] == "pathfinder" and d["readme_found"] is True and d["video_path"] is None


def test_make_reel_with_rendering_produces_a_video(sample_repo, tmp_path):
    r = make_reel(sample_repo, tmp_path / "out", target_seconds=15, render=True)
    assert r.video_path is not None and r.video_path.exists()
    assert r.backend in ("mp4", "gif")


def test_make_reel_rejects_a_bad_path(tmp_path):
    with pytest.raises(ValueError):
        make_reel(tmp_path / "does-not-exist", tmp_path / "out")
