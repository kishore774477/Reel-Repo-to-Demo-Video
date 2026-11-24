"""Read a repo's README and pick out the pieces a demo video needs: a title, a tagline, the problem it opens with,
a "what makes it different" table, an architecture section, and whatever screenshots it has.

Nothing here is an LLM call — it is markdown-shaped heuristics, the same kind every project in this series' own
README uses (a `# Title`, a tagline line, a "## What makes it different" table), so it reads this series' own
READMEs well by construction. A README with none of that still gets a title, a tagline guessed from the first
paragraph, and no table/architecture scene — documented, not silently invented.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
SCREENSHOT_DIRS = ("screenshots", "screenshot", "images", "img", "assets", "docs/images", "docs/screenshots", "media")
BADGE_LINE = re.compile(r"^\s*(\[!\[.*?\]\(.*?\)\]\(.*?\)\s*)+$")
HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
IMG_MD = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
TABLE_SEP = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")


@dataclass
class RepoInfo:
    root: Path
    name: str
    title: str
    tagline: str
    intro: str
    differs: list = field(default_factory=list)       # [(idea, what_it_does), ...]
    architecture: str = ""
    screenshots: list = field(default_factory=list)    # [(path, caption), ...]
    cta_url: str | None = None
    readme_found: bool = True


def _is_prose(line: str) -> bool:
    t = line.strip()
    if not t or t.startswith(("```", "|", ">", "<")) or BADGE_LINE.match(t):
        return False
    return True


def _strip_fences(lines: list) -> list:
    """Drop the contents of fenced code blocks (and the fences themselves) so code never gets read as prose."""
    out, inside = [], False
    for ln in lines:
        if ln.strip().startswith("```"):
            inside = not inside
            continue
        if not inside:
            out.append(ln)
    return out


def _strip_md(s: str) -> str:
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\*\*([^*]*)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return s.strip()


def _split_sections(lines: list) -> dict:
    """``## heading`` -> the body lines under it (down to the next ``##`` or end)."""
    out: dict = {}
    cur, buf = None, []
    for ln in lines:
        m = HEADING.match(ln)
        if m and len(m.group(1)) <= 2:
            if cur is not None:
                out[cur] = buf
            cur, buf = m.group(2).strip(), []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        out[cur] = buf
    return out


def _table_rows(lines: list) -> list:
    rows = []
    for ln in lines:
        if TABLE_SEP.match(ln) or not TABLE_ROW.match(ln):
            continue
        cells = [_strip_md(c) for c in ln.strip().strip("|").split("|")]
        if cells and cells[0].lower() not in ("idea", "what", "feature", "setting", "name"):
            rows.append(tuple(cells))
    return rows


def _paragraphs(lines: list) -> list:
    """Every run of consecutive prose lines, stopping each at a heading, a table, a badge line or a blank line.
    Code fences are removed first so a fenced block is never read as a paragraph."""
    out, buf = [], []
    for ln in _strip_fences(lines):
        if HEADING.match(ln) or (ln.strip() == "" and buf) or (not _is_prose(ln) and buf):
            if buf:
                out.append(" ".join(buf))
            buf = []
            if HEADING.match(ln):
                break
        if _is_prose(ln):
            buf.append(ln.strip())
    if buf:
        out.append(" ".join(buf))
    return out


def _first_paragraph(lines: list, after: int = 0, min_len: int = 40) -> str:
    """The first paragraph that is long enough on its own — a one-line tagline right after the title is skipped
    in favour of the real opening paragraph that follows it."""
    for para in _paragraphs(lines[after:]):
        text = _strip_md(para)
        if len(text) >= min_len:
            return text
    return ""


MIN_SCREENSHOT_PX = 80   # a real screenshot; a status badge or a small logo is smaller than this on at least one side


def _large_enough(p: Path) -> bool:
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.width >= MIN_SCREENSHOT_PX and im.height >= MIN_SCREENSHOT_PX
    except Exception:
        return False


def _find_screenshots(root: Path, referenced: dict) -> list:
    found: list = []
    seen: set = set()

    def add(p: Path, caption: str = ""):
        if p.exists() and p not in seen and _large_enough(p):
            seen.add(p)
            found.append((p, caption or _caption_from_name(p)))

    for alt, src in referenced.items():
        if not src.startswith(("http://", "https://")):
            p = (root / src).resolve()
            add(p, alt)
    for d in SCREENSHOT_DIRS:
        folder = root / d
        if folder.is_dir():
            for p in sorted(folder.iterdir()):
                if p.suffix.lower() in IMAGE_EXTS:
                    add(p)
    return found


def _caption_from_name(p: Path) -> str:
    name = re.sub(r"[-_]+", " ", p.stem)
    name = re.sub(r"\d+$", "", name).strip()
    return name[:1].upper() + name[1:] if name else p.stem


def _cta_url(root: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True, timeout=5)
        url = r.stdout.strip()
        return url or None
    except (OSError, subprocess.SubprocessError):
        return None


def parse_repo(path: str | Path, max_screenshots: int = 6) -> RepoInfo:
    root = Path(path).resolve()
    if not root.is_dir():
        raise ValueError(f"not a folder: {root}")
    name = root.name
    readme = next((root / f for f in ("README.md", "readme.md", "Readme.md", "README.MD") if (root / f).exists()), None)
    if readme is None:
        readme = next(iter(root.glob("[Rr][Ee][Aa][Dd][Mm][Ee].md")), None)
    if readme is None:
        return RepoInfo(root, name, name.replace("-", " ").replace("_", " "), "", "", [], "", [], _cta_url(root), readme_found=False)

    text = readme.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    title, tagline = name.replace("-", " ").replace("_", " "), ""
    body_start = 0
    for i, ln in enumerate(lines):
        m = HEADING.match(ln)
        if m and len(m.group(1)) == 1:
            raw = m.group(2).strip()
            if ":" in raw:
                t, _, tg = raw.partition(":")
                title, tagline = _strip_md(t), _strip_md(tg)
            else:
                title = _strip_md(raw)
            body_start = i + 1
            break
    if not tagline:
        tagline = _first_paragraph(lines, body_start, min_len=10)
        if len(tagline) > 140 or "\n" in tagline:
            tagline = ""
    intro = _first_paragraph(lines, body_start, min_len=40)
    if intro and intro == tagline:
        intro = _first_paragraph(lines, body_start + 2, min_len=40) or intro

    sections = _split_sections(lines)
    differs: list = []
    for heading, blines in sections.items():
        if re.search(r"\bdiffer", heading, re.I) or "what makes it different" in heading.lower():
            differs = _table_rows(blines)[:5]
            break
    architecture = ""
    for heading, blines in sections.items():
        if re.search(r"architecture|how it works|how this works|design\b", heading, re.I):
            architecture = _strip_md(" ".join(l.strip() for l in blines if _is_prose(l))[:400])
            break

    referenced = dict(IMG_MD.findall(text))
    screenshots = _find_screenshots(root, referenced)[:max_screenshots]
    return RepoInfo(root, name, title, tagline, intro, differs, architecture, screenshots, _cta_url(root))
