"""Turn a parsed README into an ordered list of scenes with durations that add up to the target length.

Every scene starts with a *base* duration (how long that kind of content needs to be read comfortably: a title
card is quick, a screenshot with a caption needs a beat longer). Those bases rarely sum to exactly the requested
length, so they are scaled — proportionally, then clamped to a readable minimum and a not-dull maximum — to hit
the target without the fast-food-ad or slideshow-nobody-asked-for failure modes on either side.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .parse import RepoInfo

KIND_BASE = {"title": 3.0, "problem": 4.5, "differs": 3.5, "architecture": 4.0, "screenshot": 4.0, "cta": 3.0}
MIN_SCENE, MAX_SCENE = 2.0, 8.0


@dataclass
class Scene:
    kind: str              # title | problem | differs | architecture | screenshot | cta
    heading: str
    body: str
    image: object = None   # pathlib.Path or None
    duration: float = 0.0

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "heading": self.heading, "body": self.body, "duration": round(self.duration, 2)}
        d["image"] = str(self.image) if self.image else None
        return d


@dataclass
class Storyboard:
    scenes: list = field(default_factory=list)
    target_seconds: float = 45.0

    @property
    def total_seconds(self) -> float:
        return sum(s.duration for s in self.scenes)

    def to_dict(self) -> dict:
        return {"target_seconds": self.target_seconds, "total_seconds": round(self.total_seconds, 2), "scenes": [s.to_dict() for s in self.scenes]}


def _fit_durations(scenes: list, target_seconds: float) -> None:
    """Scale every scene's base duration by one factor so the total lands on the target, clamped to a readable range.
    A single clamped pass is enough for the scene counts this ever runs on (a handful); it is not a general solver."""
    if not scenes:
        return
    base_total = sum(s.duration for s in scenes)
    if base_total <= 0:
        return
    scale = target_seconds / base_total
    for s in scenes:
        s.duration = max(MIN_SCENE, min(MAX_SCENE, s.duration * scale))


def build_script(info: RepoInfo, target_seconds: float = 45.0, max_screenshots: int = 4, cta_text: str | None = None) -> Storyboard:
    if target_seconds <= 0:
        raise ValueError("target_seconds must be positive")
    scenes = [Scene("title", info.title, info.tagline, duration=KIND_BASE["title"])]
    if info.intro:
        scenes.append(Scene("problem", "The problem", info.intro, duration=KIND_BASE["problem"]))
    for row in info.differs[:3]:
        idea, what = row[0], row[1] if len(row) > 1 else ""      # a third ("vs. the alternative") column, if any, is left for the reader
        scenes.append(Scene("differs", idea, what, duration=KIND_BASE["differs"]))
    if info.architecture:
        scenes.append(Scene("architecture", "How it works", info.architecture, duration=KIND_BASE["architecture"]))
    for path, caption in info.screenshots[:max_screenshots]:
        scenes.append(Scene("screenshot", caption, "", image=path, duration=KIND_BASE["screenshot"]))
    cta = cta_text or (f"Try it: {info.cta_url}" if info.cta_url else f"Clone {info.name} and run start.bat")
    scenes.append(Scene("cta", "See it for yourself", cta, duration=KIND_BASE["cta"]))
    _fit_durations(scenes, target_seconds)
    return Storyboard(scenes, target_seconds)
