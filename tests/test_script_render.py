import pytest
from PIL import Image

from reel.parse import parse_repo
from reel.render import render_frame, render_storyboard, wrap_text
from reel.script import KIND_BASE, MAX_SCENE, MIN_SCENE, Scene, build_script


def test_build_script_covers_title_problem_differs_architecture_screenshots_cta(sample_repo):
    info = parse_repo(sample_repo)
    sb = build_script(info)
    kinds = [s.kind for s in sb.scenes]
    assert kinds[0] == "title" and kinds[-1] == "cta"
    assert kinds.count("differs") == 3 and kinds.count("screenshot") == 3 and "architecture" in kinds and "problem" in kinds
    assert sb.scenes[0].heading == "Pathfinder" and sb.scenes[-1].body            # the CTA has something to say


def test_durations_are_clamped_and_fit_the_target(sample_repo):
    info = parse_repo(sample_repo)
    for target in (20, 45, 90):
        sb = build_script(info, target_seconds=target)
        assert all(MIN_SCENE <= s.duration <= MAX_SCENE for s in sb.scenes)
        # within the clamp range the fit should be close; outside it, it's the clamp that wins, not the target
        unclamped = sum(KIND_BASE[s.kind] for s in sb.scenes)
        if target / unclamped * max(KIND_BASE.values()) <= MAX_SCENE and target / unclamped * min(KIND_BASE.values()) >= MIN_SCENE:
            assert sb.total_seconds == pytest.approx(target, rel=0.02)


def test_degenerate_targets_do_not_crash(sample_repo):
    info = parse_repo(sample_repo)
    tiny = build_script(info, target_seconds=0.001)
    assert all(s.duration >= MIN_SCENE for s in tiny.scenes)
    huge = build_script(info, target_seconds=10_000)
    assert all(s.duration <= MAX_SCENE for s in huge.scenes)
    with pytest.raises(ValueError):
        build_script(info, target_seconds=0)
    with pytest.raises(ValueError):
        build_script(info, target_seconds=-5)


def test_max_screenshots_limits_scenes(sample_repo):
    info = parse_repo(sample_repo)
    sb = build_script(info, max_screenshots=1)
    assert sum(1 for s in sb.scenes if s.kind == "screenshot") == 1


def test_cta_uses_the_repo_name_when_there_is_no_remote(sample_repo):
    info = parse_repo(sample_repo)
    sb = build_script(info)
    assert "start.bat" in sb.scenes[-1].body or info.name in sb.scenes[-1].body


def test_custom_cta_text_is_used(sample_repo):
    info = parse_repo(sample_repo)
    sb = build_script(info, cta_text="Go try it now")
    assert sb.scenes[-1].body == "Go try it now"


def test_a_readme_with_nothing_extracted_still_gets_a_title_and_cta(tmp_path):
    from reel.parse import parse_repo as pr
    (tmp_path / "bare-repo").mkdir()
    info = pr(tmp_path / "bare-repo")
    sb = build_script(info)
    assert [s.kind for s in sb.scenes] == ["title", "cta"]


def test_to_dict_round_trips_the_shape(sample_repo):
    info = parse_repo(sample_repo)
    sb = build_script(info)
    d = sb.to_dict()
    assert d["target_seconds"] == 45.0 and len(d["scenes"]) == len(sb.scenes)
    assert d["scenes"][0]["kind"] == "title" and isinstance(d["scenes"][0]["image"], type(None))
    img_scene = next(s for s in d["scenes"] if s["kind"] == "screenshot")
    assert isinstance(img_scene["image"], str)


# ---------------------------------------------------------------------------- rendering
def test_wrap_text_breaks_on_width_and_ellipsizes_when_truncated():
    img = Image.new("RGB", (10, 10))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    long_text = "word " * 40
    lines = wrap_text(d, long_text, font, max_width=200)
    assert len(lines) > 1
    assert all(d.textlength(ln, font=font) <= 200 + 1 for ln in lines)
    limited = wrap_text(d, long_text, font, max_width=200, max_lines=2)
    assert len(limited) == 2 and limited[-1].endswith("…")


def test_wrap_text_short_text_is_one_line_no_ellipsis():
    img = Image.new("RGB", (10, 10))
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img)
    lines = wrap_text(d, "short text", ImageFont.load_default(), max_width=1000, max_lines=3)
    assert lines == ["short text"]


def test_render_frame_produces_the_right_size_for_every_kind(sample_repo):
    info = parse_repo(sample_repo)
    sb = build_script(info)
    for i, s in enumerate(sb.scenes):
        img = render_frame(s, i, len(sb.scenes))
        assert img.size == (1280, 720)


def test_render_storyboard_writes_one_png_per_scene(sample_repo, tmp_path):
    info = parse_repo(sample_repo)
    sb = build_script(info)
    paths = render_storyboard(sb, tmp_path / "frames")
    assert len(paths) == len(sb.scenes)
    assert all(p.exists() and p.suffix == ".png" for p in paths)
    assert [p.name for p in paths] == sorted(p.name for p in paths)       # frame_00, frame_01, ... in order


def test_a_missing_screenshot_file_does_not_crash_the_render():
    s = Scene("screenshot", "Ghost", "", image="C:/definitely/not/a/real/file.png", duration=4.0)
    img = render_frame(s, 0, 1)
    assert img.size == (1280, 720)       # falls through to the text layout instead of raising
