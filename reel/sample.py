"""A tiny synthetic project folder (a README with a title, tagline, "what makes it different" table and
architecture section, plus three generated placeholder screenshots) so Reel has something to demo without
pointing it at a real project. The screenshots are drawn, not real UI, and the README says so.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

README = """# Pathfinder: a route planner that explains its detours

Most route planners give you a line on a map and nothing else. Pathfinder shows *why* it picked that road instead
of the faster-looking one next to it — live traffic, a closed bridge, a school-zone slowdown — as a short note
on every turn, so a 20-minute detour never feels arbitrary.

## What makes it different

| Idea | What it does |
|---|---|
| Explains every detour | Each turn carries a one-line reason: traffic, a closure, a time-of-day rule. |
| Live re-routing | Recomputes the plan every 90 seconds without losing the explanation trail. |
| Works offline | A cached map tile set and a local routing graph mean no connection is required. |

## How it works

A graph of road segments is weighted by live and historical conditions; Dijkstra's algorithm finds the shortest
weighted path, and every edge on that path keeps the reason it was weighted the way it was, which is what turns
into the on-turn explanation.

## Screenshots

![Route overview with the explained turn-by-turn list](screenshots/overview.png)
![A single detour explained with the live reason](screenshots/detour.png)
"""

PANELS = [
    ("overview.png", "Route overview", ["9:14 am · 3 turns ahead", "Turn 1: left on 5th — avoids a closed bridge", "Turn 2: right on Elm — school zone, 3-5pm only", "Turn 3: straight on Birch — fastest segment"]),
    ("detour.png", "Detour explained", ["Why this detour?", "Live traffic: 5th Ave is 12 min slower right now", "Historical: this slowdown clears by 9:40am", "Alternative: Elm Street, +2 min, no slowdown"]),
    ("map.png", "Live map", ["Pathfinder · live", "Recalculating in 42s", "3 of 7 segments re-weighted this cycle"]),
]
BG, PANEL, ACCENT, TEXT, MUTED = (18, 18, 17), (26, 26, 25), (57, 135, 229), (240, 239, 236), (143, 142, 134)


def _font(size: int):
    from PIL import ImageFont
    for path in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_panel(title: str, lines: list) -> Image.Image:
    img = Image.new("RGB", (960, 600), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((24, 24, 936, 90), fill=PANEL)
    d.text((44, 44), title, fill=TEXT, font=_font(28))
    y = 130
    for i, line in enumerate(lines):
        d.rectangle((24, y, 936, y + 70), fill=PANEL)
        d.text((44, y + 22), line, fill=TEXT if i == 0 else MUTED, font=_font(20))
        y += 84
    d.rectangle((24, 560, 220, 576), fill=ACCENT)
    return img


def generate(target: str | Path) -> Path:
    root = Path(target)
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(README, encoding="utf-8")
    shots = root / "screenshots"
    shots.mkdir(exist_ok=True)
    for filename, title, lines in PANELS:
        _draw_panel(title, lines).save(shots / filename)
    return root
