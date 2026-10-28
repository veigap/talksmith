#!/usr/bin/env python3
"""Build a visual gallery of the animate-svg reference cases: output/index.html.

Reads the layout the pass leaves: `<case>.svg` (the base, untouched) beside `<case>.anim.svg` (the
animated version the slide points at); a dropped attempt, kept for review, is
`.critique/<case>.dropped.svg`.

Run:  python3 tests/skills/animate-svg/build_gallery.py   (then open output/index.html)

One card per case that has been run: the animated SVG playing (with a replay button), the approved
still beside it, the brief, and the critic's verdict when `output/.critique/<case>.verdict.txt`
exists. Everything is inlined, so the page is self-contained — and since every diagram lands in
one document, exactly as in the deck, it also shows that their scoped animations do not collide.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
sys.path.insert(0, str(HERE.parents[2] / "skills" / "md-to-deck"))
from html_style import _ns_svg_ids  # noqa: E402  (the deck's own id namespacing for inlined SVG)


def _inline(path: Path, prefix: str) -> str:
    svg = re.sub(r"<\?xml.*?\?>", "", path.read_text(encoding="utf-8"), flags=re.DOTALL).strip()
    return _ns_svg_ids(svg, prefix)


def _brief(note: str) -> list[str]:
    m = re.search(r"^\s*animation\s*:.*?$(.*?)(?=^\s*[A-Za-z_-]+\s*:|-->)", note, re.S | re.M)
    return [re.sub(r"^\s*\d+\.\s*", "", l).strip() for l in (m.group(1) if m else "").splitlines() if l.strip()]


def main() -> int:
    cards = []
    for case in sorted(p for p in HERE.iterdir() if p.is_dir() and (p / "note.txt").is_file()):
        still, anim = OUT / f"{case.name}.svg", OUT / f"{case.name}.anim.svg"
        dropped = OUT / ".critique" / f"{case.name}.dropped.svg"
        label = "Animated — what the slide shows (&lt;stem&gt;.anim.svg)"
        if not anim.is_file():
            if not dropped.is_file():
                continue
            anim, label = dropped, "Dropped attempt — not shipped; the slide keeps the still"
        ctx = json.loads((case / "context.json").read_text(encoding="utf-8"))
        verdict = OUT / ".critique" / f"{case.name}.verdict.txt"
        v = verdict.read_text(encoding="utf-8").strip() if verdict.is_file() else "not critiqued yet"
        status = "ok" if v.lower().startswith("clean") else "dropped" if v.lower().startswith("dropped") else "pending" if v.lower().startswith(("pending", "not critiqued")) else "issues"
        steps = "".join(f"<li>{html.escape(s)}</li>" for s in _brief((case / "note.txt").read_text(encoding="utf-8")))
        cards.append(f"""
<section class="card" id="{case.name}">
  <header><h2>{html.escape(case.name)}</h2><span class="title">{html.escape(ctx.get('slide_title', ''))}</span>
    <span class="badge {status}">{html.escape(v.splitlines()[0][:60])}</span>
    <button class="replay" type="button">↻ Replay</button></header>
  <div class="pair">
    <figure class="anim"><figcaption>{label}</figcaption>{_inline(anim, f"a-{case.name}-")}</figure>
    <figure class="still"><figcaption>Base — the approved still, untouched (&lt;stem&gt;.svg)</figcaption>{_inline(still, f"s-{case.name}-") if still.is_file() else "<p>—</p>"}</figure>
  </div>
  <details><summary>Brief and critique</summary><ol>{steps}</ol><pre>{html.escape(v)}</pre></details>
</section>""")
    page = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>animate-svg gallery</title>
<style>
:root{{--ink:#1F1E1E;--muted:#6B6560;--line:#D8D2CE;--bg:#F2EEEE;--accent:#DA1B2E}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Helvetica,Arial,sans-serif}}
.top{{position:sticky;top:0;z-index:2;background:#fff;border-bottom:1px solid var(--line);padding:12px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}}
.top h1{{font-size:18px;margin:0}} .top nav a{{color:var(--muted);margin-right:10px;text-decoration:none}}
main{{max-width:1500px;margin:0 auto;padding:16px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;margin:0 0 20px;padding:14px 16px}}
.card header{{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}}
.card h2{{font-size:17px;margin:0}} .title{{color:var(--muted)}}
.badge{{font-size:12px;padding:2px 8px;border-radius:99px;background:var(--bg)}}
.badge.ok{{background:#E3F1E6;color:#1E5B2C}} .badge.issues{{background:#F9D2D6;color:#8A1020}} .badge.dropped{{background:#E8E2DE;color:#3B3535}}
.replay{{margin-left:auto;border:1px solid var(--line);background:#fff;border-radius:6px;padding:4px 10px;cursor:pointer}}
.pair{{display:grid;grid-template-columns:3fr 2fr;gap:16px;margin-top:10px}}
@media (max-width:900px){{.pair{{grid-template-columns:1fr}}}}
figure{{margin:0}} figcaption{{font-size:12px;color:var(--muted);margin-bottom:4px}}
figure svg{{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:6px;background:#fff}}
details{{margin-top:10px}} pre{{white-space:pre-wrap;background:var(--bg);padding:8px;border-radius:6px;font-size:13px}}
</style>
<div class="top"><h1>animate-svg — reference cases</h1><button class="replay" id="all" type="button">↻ Replay all</button>
<nav>{"".join(f'<a href="#{n}">{n}</a>' for n in re.findall(r'<section class="card" id="([^"]+)"', "".join(cards)))}</nav></div>
<main>{"".join(cards) or "<p>No case has been run yet.</p>"}</main>
<script>
function replay(root){{ root.querySelectorAll('figure.anim svg').forEach(function(s){{
  s.getAnimations({{subtree:true}}).forEach(function(a){{ a.cancel(); a.play(); }}); }}); }}
document.querySelectorAll('.card .replay').forEach(function(b){{ b.onclick=function(){{ replay(b.closest('.card')); }}; }});
document.getElementById('all').onclick=function(){{ replay(document); }};
</script></html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"gallery: {OUT / 'index.html'} ({len(cards)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
