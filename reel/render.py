"""One scene -> one 1280x720 frame, drawn with Pillow (no video library needed for this part): the dark theme
every dashboard in this series uses, a heading, a wrapped body or a letterboxed screenshot, a caption, and a
footer of progress dots so a static frame still shows where it sits in the story.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG, ACCENT, TEXT, MUTED, PANEL = (18, 18, 17), (57, 135, 229), (240, 239, 236), (143, 142, 134), (26, 26, 25)
KIND_LABEL = {"title": "", "problem": "THE PROBLEM", "differs": "WHAT MAKES IT DIFFERENT", "architecture": "HOW IT WORKS", "screenshot": "", "cta": ""}
_FONT_CANDIDATES = {"regular": (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"),
                     "bold": (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
                     "semibold": (r"C:\Windows\Fonts\seguisb.ttf", r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf")}
_cache: dict = {}


def _font(weight: str, size: int) -> ImageFont.ImageFont:
    key = (weight, size)
    if key not in _cache:
        font = None
        for path in _FONT_CANDIDATES.get(weight, _FONT_CANDIDATES["regular"]):
            try:
                font = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
        _cache[key] = font or ImageFont.load_default()
    return _cache[key]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int | None = None) -> list:
    """Greedy word wrap to ``max_width``; if that makes more than ``max_lines``, keep only the first ``max_lines``
    and ellipsize the last one so it still fits."""
    lines: list = []
    cur = ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if not cur or draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        kept, last = lines[:max_lines], lines[max_lines - 1]
        while draw.textlength(last + "…", font=font) > max_width and len(last) > 1:
            last = last[:-1]
        kept[-1] = last.rstrip() + "…"
        return kept
    return lines


def _fit_image(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    r = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))))


def render_frame(scene, index: int, total: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    label = KIND_LABEL.get(scene.kind, "")
    if label:
        d.text((80, 64), label, fill=ACCENT, font=_font("semibold", 20))

    if scene.kind == "title":
        lines = wrap_text(d, scene.heading, _font("bold", 72), W - 160, max_lines=2)
        y = H // 2 - 40 * len(lines) - (30 if scene.body else 0)
        for ln in lines:
            d.text((W // 2, y), ln, fill=TEXT, font=_font("bold", 72), anchor="ma")
            y += 84
        if scene.body:
            d.text((W // 2, y + 10), scene.body, fill=MUTED, font=_font("regular", 30), anchor="ma")
        d.rectangle((W // 2 - 60, H - 90, W // 2 + 60, H - 84), fill=ACCENT)

    elif scene.kind == "screenshot" and scene.image and Path(scene.image).exists():
        shot = Image.open(scene.image).convert("RGB")
        box_w, box_h = W - 160, H - 260
        fitted = _fit_image(shot, box_w, box_h)
        x, y = (W - fitted.width) // 2, 110 + (box_h - fitted.height) // 2
        d.rectangle((x - 10, y - 10, x + fitted.width + 10, y + fitted.height + 10), outline=ACCENT, width=3)
        img.paste(fitted, (x, y))
        if scene.heading:
            d.text((W // 2, H - 110), scene.heading, fill=TEXT, font=_font("semibold", 28), anchor="ma")

    else:
        y = 150
        heading_font = _font("bold", 44 if scene.kind != "differs" else 40)
        for ln in wrap_text(d, scene.heading, heading_font, W - 160, max_lines=2):
            d.text((80, y), ln, fill=TEXT, font=heading_font, anchor="la")
            y += 56
        if scene.body:
            y += 24
            for ln in wrap_text(d, scene.body, _font("regular", 28), W - 160, max_lines=6):
                d.text((80, y), ln, fill=MUTED, font=_font("regular", 28), anchor="la")
                y += 42

    # progress dots
    n = max(total, 1)
    dot_w, gap = 28, 10
    start_x = W // 2 - (n * dot_w + (n - 1) * gap) // 2
    for i in range(n):
        x0 = start_x + i * (dot_w + gap)
        d.rectangle((x0, H - 30, x0 + dot_w, H - 24), fill=ACCENT if i == index else (50, 50, 47))
    return img


def render_storyboard(storyboard, out_dir) -> list:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, scene in enumerate(storyboard.scenes):
        p = out_dir / f"frame_{i:02d}.png"
        render_frame(scene, i, len(storyboard.scenes)).save(p)
        paths.append(p)
    return paths
