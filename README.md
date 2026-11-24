# Reel: turn a repo's README into a 45-second demo video

Every project in this series ends with a README that has a title, a tagline, a "what makes it different" table,
and (sometimes) a screenshot or two. That is already a storyboard — nobody writes a good README by accident, it
already has the beats a demo video needs. **Reel reads one and renders it**: a title card, the problem it opens
with, up to three rows of what makes it different, an architecture note if there is one, the screenshots, and a
closing card — no LLM call, just markdown-shaped heuristics, timed to fit whatever length you ask for.

This is Day 7's *light* build in the series (`Daily-Project-Plan.md` calls for exactly this: "build once, use 23
times" for the remaining days' LinkedIn posts), so the scope here is smaller than the agent-simulation projects
around it — one real pipeline, well tested, rather than a market or a miner.

```
 README.md + screenshots/
        │  a title (# heading), a tagline, the opening paragraph, a "what makes it different" table,
        │  an "architecture" / "how it works" section, every image referenced or found in a screenshots/ folder
        ▼
 scenes  title → problem → up to 3 differentiators → architecture → screenshots → CTA
        │  each scene's base duration (a title card is quick; a screenshot needs a beat longer) is scaled by
        │  one factor to hit the target length, clamped to a readable 2-8 seconds
        ▼
 frames  Pillow draws each scene onto a 1280x720 dark-themed PNG (the same palette every dashboard in this series uses)
        ▼
 video   moviepy + a bundled ffmpeg (no system install needed) crossfades the frames into an .mp4;
         no working ffmpeg → falls back to an animated .gif automatically
```

## What makes it different

| Idea | What it does |
|---|---|
| **Reads the README, not a model's idea of it** | A title from `# heading`, a tagline from "Title: tagline" or the first short line, the opening paragraph as the problem, a markdown table under a "different" heading as the differentiators. No API key, nothing invented when a section is missing — a thin README gets a thin, honestly thin, video. |
| **Fits a target length, not a fixed slide time** | Every scene kind has a base duration; they're scaled by one factor to land on the length you ask for (20s, 45s, 90s...), clamped so nothing flashes by in under 2 seconds or drags past 8. |
| **A real screenshot finder** | Every image the README references plus anything sitting in a `screenshots/`-shaped folder, deduplicated, filtered by actual pixel dimensions (not file size — a tiny, highly-compressible test image is still a real screenshot; a status badge is small either way). |
| **Works with nothing installed** | `imageio-ffmpeg` bundles a static ffmpeg binary via pip — no system ffmpeg, no PATH setup. If that still somehow fails, it falls back to an animated GIF rather than erroring out. |
| **The dashboard never blocks on a render** | Building a storyboard is instant; rendering a video (10-45s) happens in a background thread so the app starts serving immediately — an earlier version of this blocked `uvicorn` from even opening the port until the first video finished, which is exactly the kind of thing worth fixing before calling it done. |

## See it work (no API key needed)

The bundled sample is "Pathfinder", a fictional route planner, with a real README (title, tagline, intro, a 3-row
differentiator table, an architecture section) and three generated placeholder screenshots (drawn with Pillow, not
real UI — the README and this one say so). `python -m reel demo` builds it:

```
Pathfinder — a route planner that explains its detours

10 scenes, 45.0s (asked for 45s)
   1.  3.6s  title        Pathfinder
   2.  5.5s  problem      The problem
   3.  4.3s  differs      Explains every detour
   4.  4.3s  differs      Live re-routing
   5.  4.3s  differs      Works offline
   6.  4.9s  architecture How it works
   7.  4.9s  screenshot   Route overview with the explained turn-by-turn list [overview.png]
   8.  4.9s  screenshot   A single detour explained with the live reason [detour.png]
   9.  4.9s  screenshot   Map [map.png]
  10.  3.6s  cta          See it for yourself

wrote data\demo_out\demo.mp4 (mp4)
```

On this machine that is a real **.mp4, 1280x720, 24fps, ~41.4 seconds** (crossfades overlap scenes, so a rendered
video's actual length is a little under the storyboard's total — nine 0.4s transitions trim 3.6s off the 45.0s
storyboard here, and that arithmetic is exact, not approximate).

### Tested on a real repo in this series, not just the sample

I pointed Reel at a copy of **Bazaar's own README** (Day 6 of this series) with two screenshots I captured live
from its running dashboard (the Market tab and the Market-vs-fixed-crew tab) dropped into a `screenshots/`
folder — nothing written for this test, just what that project's README already says about itself:

```
Bazaar — a market where agents bid for work, so reputation can route around a bad one

8 scenes, 45.0s (asked for 45s)
   1.  4.7s  title        Bazaar
   2.  7.0s  problem      The problem
   3.  5.4s  differs      Allocation is a market, not a hire
   4.  5.4s  differs      Reputation is earned, not claimed
   5.  5.4s  differs      The claim and the real skill are different things
   6.  6.2s  screenshot   The market tab: who won the work and the rolling success rate [market.jpg]
   7.  6.2s  screenshot   The market vs the fixed crew, across many seeds [compare.jpg]
   8.  4.7s  cta          See it for yourself

wrote ...\bazaar_real_out\demo.mp4 (mp4)
```

It picked up the title, the tagline, the intro paragraph, all three rows of Bazaar's differentiator table (a
3-column table there — Idea / What it does / what fixed-role crews do instead — Reel keeps the first two and
leaves the third for the reader), and both real dashboard screenshots with their README alt text as captions,
without anything project-specific in Reel's code. That is the actual bar for "build once, use 23 times": it has
to work on this series' own READMEs without being told about them.

### What this does and does not do

* **There is no LLM here.** The parsing is markdown-shaped heuristics (headings, a table, an intro paragraph).
  It reads this series' own READMEs well because they are shaped that way on purpose; a README with no headings,
  no table and no screenshots gets a two-scene video — a title card and a CTA — not an invented "what makes it
  different" row.
* **Ten scenes is the ceiling, not a target.** Up to three differentiator rows and four screenshots (configurable)
  are included; a README with twelve rows in its table still gets three scenes, the first three.
* **The duration fit is a single scaling pass, clamped**, not a solver. At very short or very long targets the
  clamp wins and the total stops tracking the request exactly — the CLI and the dashboard both show the actual
  total next to the one you asked for, so this is visible, not silently wrong.

## Run it

```powershell
start.bat                        # creates .venv, installs, opens http://127.0.0.1:8170
# or
python -m venv .venv ; .venv\Scripts\pip install -r requirements.txt ; .venv\Scripts\python run.py
```

Dashboard tabs: **Build** (point it at a folder, or leave it blank for the sample; pick a target length and how
many screenshots; tick "render a video" or leave the storyboard-only instant path), **Storyboard** (every scene
with its real rendered thumbnail, heading, body and duration, plus a timeline bar), **Video** (an inline player —
`<video>` for an mp4, `<img>` for a gif — with a download button and a badge saying which backend you got),
**How it works**.

```powershell
python -m reel demo                                   # build the bundled sample
python -m reel build C:\path\to\a\repo --seconds 30    # build a real repo at 30 seconds
python -m reel build C:\path\to\a\repo --script-only   # print the scene plan, no rendering (fast)
python examples\make_a_reel.py                         # the library in 25 lines
python examples\make_a_reel.py C:\path\to\a\repo out\mine 30
```

```python
from reel import make_reel
r = make_reel("path/to/a/repo", "out/", target_seconds=45)
r.video_path          # an .mp4 (crossfades, needs moviepy + ffmpeg) or a .gif (always works) — or None if render=False
r.storyboard.scenes    # [Scene(kind, heading, body, image, duration), ...]
```

| HTTP | |
|---|---|
| `GET /api/meta` | version, video backend on this machine, whether a background render is in progress |
| `GET /api/storyboard` | the current build's scenes, durations, and the video path/backend |
| `POST /api/build` | `{repo, seconds, max_screenshots, cta_text, render}` → rebuild |
| `GET /api/frame/{i}` · `GET /api/video` | a scene's rendered PNG; the assembled video, as `video/mp4` or `image/gif` |
| `POST /api/reset` | back to the bundled sample |

Configure with `REEL_PORT`, `REEL_DATA` (see `.env.example`). There is no API key anywhere in this project.

## Tests

```powershell
.venv\Scripts\python -m pytest -q        # 42 tests; most run in well under a second, a handful render real video/GIF so the full suite takes 1-3 minutes
```

They check: title/tagline/colon-splitting, the first-real-paragraph search correctly skips code fences and
too-short leading lines rather than giving up, the "what makes it different" table keeps its first two columns
whatever its width, screenshots are filtered by actual pixel size (a regression: file-size filtering wrongly
dropped small-but-legitimate test images), `max_screenshots` is respected; duration fitting is clamped and close
to the target inside the clamp range, degenerate targets (near-zero, huge, zero, negative) don't crash; every
scene kind renders to a 1280x720 frame and a missing screenshot file falls back to a text layout instead of
raising; GIF rendering always works and an mp4 render (skipped if this machine has no working ffmpeg) produces a
video of the right length and size; the API never blocks on a video render and its background precompute
eventually finishes; the CLI's `demo`, `build` and `--script-only` paths.

## Limitations

* No LLM, by design — good for "no API key, instant," not for a README that buries its best material in prose with no headings or table.
* Ten agents' worth of judgement calls (which heading counts as "architecture," what counts as a screenshot) are regex-shaped, not learned; an unusual README structure will get a thinner video rather than a wrong one, but still thinner than a human editor would make.
* Captions come from markdown alt text or a cleaned-up filename — there is no scene-detection or OCR on the screenshots themselves.
* Rendering an .mp4 for a 45-second, 10-scene video took about 20-45 seconds on this machine; that is moviepy/ffmpeg overhead, not something this project tries to speed up.
