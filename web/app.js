"use strict";
// Reel dashboard: vanilla JS, no CDN, works offline.

const S = { meta: null, board: null, tab: "build", busy: false, repoInput: "" };
const $ = (q, el = document) => el.querySelector(q);
const $$ = (q, el = document) => [...el.querySelectorAll(q)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const KIND_COLOR = { title: "#3987e5", problem: "#d03b3b", differs: "#fab219", architecture: "#a78bfa", screenshot: "#2fb344", cta: "#3987e5" };

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body));
  return body;
}
const post = (p, d) => api(p, { method: "POST", body: JSON.stringify(d) });
function toast(msg, bad = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (bad ? " bad" : "");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.add("hidden"), 5000);
}

async function loadAll() {
  [S.meta, S.board] = await Promise.all([api("/api/meta"), api("/api/storyboard")]);
  $("#wschip").textContent = `${S.board.repo} · ${S.board.storyboard.scenes.length} scenes · ${S.board.storyboard.total_seconds.toFixed(0)}s · ${S.board.backend || "not rendered"}`;
}
async function boot() {
  try { await loadAll(); } catch (e) { toast(e.message, true); }
  $$("#tabs button").forEach((b) => b.addEventListener("click", () => { S.tab = b.dataset.tab; renderTab(); }));
  renderTab();
}
function renderTab() {
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === S.tab));
  ({ build: viewBuild, storyboard: viewStoryboard, video: viewVideo, how: viewHow })[S.tab]();
}
const view = () => $("#view");

// ------------------------------------------------------------------ BUILD
function viewBuild() {
  const req = S.meta.req;
  view().innerHTML = `
    <p class="lede">Point this at a folder with a README.md (and, ideally, some screenshots) and it builds a short captioned video: a title card, the problem from the README's opening paragraph,
      up to three rows of "what makes it different", an architecture note if there is one, your screenshots, and a closing card. Leave the path blank to use the bundled sample.</p>
    <div class="panel"><div class="form">
      <label>Repo folder (blank = bundled sample)<input type="text" id="repo" placeholder="C:\\path\\to\\a\\repo with a README.md" value="${esc(req.repo || "")}"></label>
      <div class="controls" style="grid-template-columns:repeat(3,minmax(120px,1fr)) auto">
        <label>Target length<select id="secs">${S.meta.second_presets.map((s) => `<option ${s === req.seconds ? "selected" : ""}>${s}</option>`).join("")}</select></label>
        <label>Max screenshots<input type="number" id="maxs" min="0" max="10" value="${req.max_screenshots}"></label>
        <label><input type="checkbox" id="render" ${req.render ? "checked" : ""}> Render a video (unchecked = just the storyboard, instant)</label>
        <button class="primary" id="go">Build</button>
      </div></div>
      <p class="small muted" style="margin-top:8px">Rendering an .mp4 takes a few seconds per scene. Without a working ffmpeg it falls back to an animated .gif automatically — the badge on the Video tab says which one you got.</p></div>
    <div class="tiles">${tile(S.board.readme_found ? "found" : "missing", "README.md")}${tile(S.board.storyboard.scenes.length, "scenes")}
      ${tile(S.board.storyboard.total_seconds.toFixed(1) + "s", `of ${S.board.storyboard.target_seconds.toFixed(0)}s asked for`)}${tile(S.board.backend || "–", "video backend")}</div>`;
  $("#go").addEventListener("click", async () => {
    if (S.busy) return;
    S.busy = true;
    const btn = $("#go"); btn.disabled = true; btn.textContent = "Building…";
    try {
      const body = { repo: $("#repo").value.trim() || null, seconds: +$("#secs").value, max_screenshots: +$("#maxs").value, render: $("#render").checked };
      S.board = await post("/api/build", body);
      S.meta.req = body;
      toast(`Built ${S.board.storyboard.scenes.length} scenes, ${S.board.storyboard.total_seconds.toFixed(1)}s`);
      $("#wschip").textContent = `${S.board.repo} · ${S.board.storyboard.scenes.length} scenes · ${S.board.storyboard.total_seconds.toFixed(0)}s · ${S.board.backend || "not rendered"}`;
      S.tab = "storyboard"; renderTab();
    } catch (e) { toast(e.message, true); }
    finally { S.busy = false; btn.disabled = false; btn.textContent = "Build"; }
  });
}
const tile = (v, l) => `<div class="tile"><div class="v">${esc(v)}</div><div class="l">${esc(l)}</div></div>`;

// ------------------------------------------------------------------ STORYBOARD
function viewStoryboard() {
  const sb = S.board.storyboard;
  const timeline = sb.scenes.map((s) => `<i style="width:${(s.duration / sb.total_seconds) * 100}%;background:${KIND_COLOR[s.kind] || "#8f8e86"}" title="${esc(s.kind)} · ${s.duration}s"></i>`).join("");
  view().innerHTML = `<p class="lede">${esc(S.board.title)}${S.board.tagline ? " — " + esc(S.board.tagline) : ""}</p>
    <div class="timeline">${timeline}</div>
    <div>${sb.scenes.map((s, i) => `<div class="storycard" style="border-left-color:${KIND_COLOR[s.kind] || "#8f8e86"}">
      ${s.image ? `<img class="thumb" src="/api/frame/${i}">` : `<img class="thumb" src="/api/frame/${i}" style="object-fit:contain">`}
      <div class="sbody"><span class="dur">${s.duration}s</span><div class="kind">${esc(s.kind)}</div><div class="head">${esc(s.heading)}</div><div class="txt">${esc(s.body)}</div></div></div>`).join("")}</div>`;
}

// ------------------------------------------------------------------ VIDEO
function viewVideo() {
  const backend = S.board.backend;
  if (!backend) {
    if (S.meta.rendering) {
      view().innerHTML = `<p class="lede">Rendering the sample video in the background — this takes a little while the first time. Checking again shortly…</p>`;
      setTimeout(async () => { try { S.meta = await api("/api/meta"); S.board = await api("/api/storyboard"); } catch (e) { /* server still busy */ } if (S.tab === "video") renderTab(); }, 2000);
    } else {
      view().innerHTML = `<p class="lede">No video for this build — it was built with "render a video" unchecked. Go to the Build tab, tick it, and build again.</p>`;
    }
    return;
  }
  view().innerHTML = `<p class="lede">${esc(S.board.title)}, ${S.board.storyboard.total_seconds.toFixed(1)}s<span class="backendpill ${backend}">${backend}</span></p>
    <div class="vidwrap">${backend === "mp4" ? `<video src="/api/video" controls autoplay loop></video>` : `<img class="gif" src="/api/video">`}</div>
    <p style="margin-top:10px"><a href="/api/video" download="reel.${backend}"><button class="primary">Download reel.${backend}</button></a></p>
    ${backend === "gif" ? '<p class="small muted">This machine\'s run fell back to a GIF (no usable ffmpeg found at render time) — no crossfades, no audio, but it always works.</p>' : ""}`;
}

// ------------------------------------------------------------------ HOW
function viewHow() {
  view().innerHTML = `<div class="prose panel">
    <h3>1. Read the README, not an LLM's summary of it</h3><p>A title from the first <code># heading</code>, a tagline from a "Title: tagline" line or the first short paragraph, the opening paragraph as "the problem",
      a markdown table under a heading matching "different" as the differentiators, a section matching "how it works" / "architecture" as the architecture note, and every image the README references plus anything sitting in a <code>screenshots/</code>-type folder.
      This is markdown-shaped heuristics, not a model call — it reads this series' own READMEs well because they are shaped that way on purpose.</p>
    <h3>2. Fit the scenes to a target length</h3><p>Every kind of scene has a base duration (a title card is quick, a screenshot with a caption needs a beat longer). Those bases are scaled by one factor, then clamped to a readable 2-8 second range, so a 10-scene story lands close to
      whatever length you ask for without a screenshot flashing by in under a second or a title card lingering for ten.</p>
    <h3>3. Draw each scene, then assemble them</h3><p>Pillow draws each scene onto a 1280x720 dark-themed frame — the same palette every dashboard in this series uses. If moviepy and a working ffmpeg are available (this project bundles one via <code>imageio-ffmpeg</code>, no system install needed),
      the frames become an .mp4 with half-second crossfades; if not, they become an animated .gif instead, with no crossfades or audio but no dependency on anything external either way.</p>
    <h3>Honest limits</h3><ul><li>There is no LLM here: the README parsing is heuristics, and a README that does not use headings or a "what makes it different" table will get a thin video — a title, maybe a first paragraph, and a CTA card, nothing invented to fill the gap.</li>
      <li>Crossfades overlap scenes, so a rendered .mp4's actual length is a little under the storyboard's total (each of the N-1 transitions trims about half a second).</li>
      <li>This was run against a real repo in this series (a copy of Bazaar's own README, with screenshots captured from its live dashboard) as well as the bundled sample — see the README for what that looked like.</li></ul></div>`;
}

boot();
