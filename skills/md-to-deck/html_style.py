"""Shared HTML styling + slide components for Talksmith's code-rendered outputs.

Two consumers share this module so the look never drifts:
  - the strict **style reference** (`config/pptx-styles/strict/style-reference/build_reference.py`);
  - the **HTML presentation** renderer (`build_html.py`) — a static site built from `final.md`.

Both render the catalog templates in the deck's own tokens (palette, Helvetica/Courier,
§7/§8/§9 geometry) with real Material Symbols icons fetched by name (`icon_fetch.py`) and
inlined. Unlike the native `.pptx` render, this is deterministic code: icons, callout boxes,
code surfaces, and card strips always render.

Public API:
  CSS                                  the full stylesheet (tokens + components + page frame)
  icon(name, cache) / chip(name,cache) inline a recoloured Material Symbols SVG
  icon_for(text)                       keyword → Material Symbols name (content-matched)
  render_slide(kind, u, section, cache) one slide's inner HTML for catalog template `kind`
  page(body, title, subtitle, mode)    wrap slides into a full self-contained HTML document
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon_fetch import fetch_icon  # noqa: E402

ACCENT = "DA1B2E"

# --- content-matched icon vocabulary: keyword → Material Symbols name -------- #
ICON_KEYWORDS = [
    (r"segurid|secur|privac|protec|riesgo|amenaza|guardrail", "shield"),
    (r"bloque|lock|cifr|encrypt|credencial|secreto|password", "lock"),
    (r"cost|precio|price|presupuesto|budget|pago|payment|econom", "payments"),
    (r"ahorr|saving|roi|ganancia", "savings"),
    (r"tiempo|latenc|schedule|horari|deadline|cuando", "schedule"),
    (r"histor|recenc|pasado|antes|previo", "history"),
    (r"dato|data|dataset|base de|database|almacen", "database"),
    (r"usuari|equipo|team|audiencia|persona|clínic|gente|group", "group"),
    (r"cod|code|api|program|desarroll|dev|script|terminal", "code"),
    (r"idea|tip|analog|intuic|insight|lightbulb|creativ", "lightbulb"),
    (r"velocid|rápid|speed|performance|rendimiento", "speed"),
    (r"alucin|error|falla|bug|fail|problema|mito", "error"),
    (r"aleator|random|shuffle|determin|variab", "shuffle"),
    (r"métric|metric|dato|result|chart|insight|analytic|número", "insights"),
    (r"conect|connect|integr|hub|mcp|red|network", "hub"),
    (r"config|ajuste|setting|mecanism|engine|gear", "settings"),
    (r"valid|verif|check|aprob|correct|calidad", "verified"),
    (r"conocim|document|referenc|libro|book|aprend|manual", "menu_book"),
    (r"curso|educ|escuela|school|enseñ|tutor", "school"),
    (r"colabor|foro|forum|comun|chat|convers", "forum"),
    (r"plugin|extens|módulo|module|paquete|package", "extension"),
    (r"proyect|project|carpeta|folder|workspace", "folder_open"),
    (r"razon|thinking|psicolog|mente|cerebr", "psychology"),
    (r"lanz|launch|deploy|inici|start|rocket", "rocket_launch"),
    (r"agent|automat|bolt|acción|action|ejecut", "bolt"),
]
_DEFAULT_ICON = "bolt"


def icon_for(text: str) -> str:
    t = (text or "").lower()
    for pat, name in ICON_KEYWORDS:
        if re.search(pat, t):
            return name
    return _DEFAULT_ICON


def _svg(name: str, cache, white: bool = False):
    p = fetch_icon(name, cache, color=ACCENT)
    if not p:
        return '<svg viewBox="0 -960 960 960"><circle cx="480" cy="-480" r="360" fill="#DA1B2E"/></svg>'
    s = p.read_text()
    if white:
        s = s.replace(f'fill="#{ACCENT}"', 'fill="#FFFFFF"', 1)
    s = re.sub(r'\swidth="\d+"', '', s, 1)
    s = re.sub(r'\sheight="\d+"', '', s, 1)
    return s


def icon(name, cache):
    return f'<span class="ic">{_svg(name, cache)}</span>'


def chip(name, cache):
    return f'<span class="chip">{_svg(name, cache, white=True)}</span>'


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _embed(alt, path):
    """Embed a resolved image self-contained: inline SVG, or a data-URI <img>, else a placeholder."""
    import base64
    if path is not None:
        try:
            p = Path(path)
            if p.suffix.lower() == ".svg":
                svg = p.read_text(encoding="utf-8")
                svg = re.sub(r"<\?xml.*?\?>", "", svg, flags=re.DOTALL).strip()
                return f'<div class="imgph svg">{svg}</div>'
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "gif": "image/gif", "webp": "image/webp"}.get(p.suffix.lower().lstrip("."))
            if mime:
                b64 = base64.b64encode(p.read_bytes()).decode("ascii")
                return f'<div class="imgph has"><img alt="{_esc(alt)}" src="data:{mime};base64,{b64}"></div>'
        except OSError:
            pass
    return f'<div class="imgph"><span>{_esc(alt) or "image"}</span></div>'


# --------------------------------------------------------------------------- #
# per-template slide rendering — `u` is a build_preview._parse_unit dict
# --------------------------------------------------------------------------- #

def _title_block(section, title):
    pill = f'<span class="pill">{_esc(section)}</span>' if section else ""
    t = f'<h2 class="stitle">{_esc(title)}</h2>' if title else ""
    return pill + t


def _mk(head, content):
    """A content slide: a **fixed** header (pill + title, never moves) + a content region
    that fits/scales independently. Keeps the title anchored regardless of content."""
    return (f'<div class="stage"><div class="shead">{head}</div>'
            f'<div class="cbody"><div class="cfit">{content}</div></div></div>')


def render_slide(kind, u, section, cache) -> str:
    title = u.get("title", "")
    items = u.get("items", [])
    body = u.get("body", [])
    images = u.get("images", [])
    code = u.get("code_lines", [])
    lead = f'<p class="lead">{_esc(body[0])}</p>' if body else ""
    head = _title_block(section, title)

    # ── full-bleed, centred — no fixed header ──
    if kind == "divider":
        return f'<div class="stage cover"><div class="stmt"><p class="big">{_esc(title)}</p></div></div>'
    if kind == "statement":
        sub = f'<p class="sub">{_esc(body[0])}</p>' if body else ""
        return f'<div class="stage cover"><div class="stmt"><p class="big">{_esc(title)}</p>{sub}</div></div>'
    if kind == "closing-hero":
        sub = f'<span class="qc">{_esc(body[0])}</span>' if body else ""
        return f'<div class="stage cover"><div class="hero"><span class="qa">{_esc(title)}</span>{sub}</div></div>'

    # ── content templates: fixed header via _mk, body in the fitting region ──
    if kind == "concept-breakdown":
        n = len(items)
        cols = 1 if n == 1 else (2 if n in (2, 4) else 3)   # 2→2col · 3→row · 4→2×2 · 5–6→3col
        cs = "".join(
            f'<div class="ccard">{icon(icon_for(it["label"]+" "+it.get("body","")), cache)}'
            f'<h3>{_esc(it["label"])}</h3><p>{_esc(it.get("body",""))}</p></div>' for it in items)
        return _mk(head, f'<div class="cards c{cols}">{cs}</div>')

    if kind == "process":
        cs = "".join(
            f'<div class="ncard"><div class="strip">{i}</div><div class="nbody">'
            f'<h4>{_esc(it["label"])}</h4><p>{_esc(it.get("body",""))}</p></div></div>'
            for i, it in enumerate(items, 1))
        return _mk(head, f'<div class="numrow">{cs}</div>')

    if kind == "card-row":
        cs = "".join(
            f'<div class="rcard">{chip(icon_for(it["label"]+" "+it.get("body","")), cache)}'
            f'<h3>{_esc(it["label"])}</h3><p>{_esc(it.get("body",""))}</p></div>' for it in items)
        return _mk(head, f'{lead}<div class="cardrow">{cs}</div>')

    if kind == "icon-list":
        cs = "".join(
            f'<div class="ilrow">{icon(icon_for(it["label"]+" "+it.get("body","")), cache)}'
            f'<div><h4>{_esc(it["label"])}</h4><p>{_esc(it.get("body",""))}</p></div></div>' for it in items)
        return _mk(head, f'{lead}<div class="iconlist">{cs}</div>')

    if kind == "code-example":
        codetxt = "<br>".join(_esc(l) for l in code[:18])
        expl = "".join(f'<p>{_esc(b)}</p>' for b in body[:3])
        return _mk(head, f'<div class="split"><div class="explain">{expl}</div>'
                         f'<div class="codebox">{codetxt}</div></div>')

    if kind in ("figures", "image-grid"):
        if kind == "image-grid" or not items:
            cs = "".join(_embed(a, p) for a, p in images)
            return _mk(head, f'<div class="imggrid">{cs}</div>')
        cs = "".join(f'<div class="figc">{_embed(*(images[k] if k < len(images) else ("","")))}'
                     f'<h4>{_esc(c["label"])}</h4><p>{_esc(c.get("body",""))}</p></div>'
                     for k, c in enumerate(items))
        return _mk(head, f'<div class="figs">{cs}</div>')

    if kind == "content-image":
        body_html = lead + "".join(f'<p class="lead">{_esc(b)}</p>' for b in body[1:2])
        pic = _embed(*images[0]) if images else _embed("", None)
        return _mk(head, f'<div class="ci"><div class="citext">{body_html}</div>{pic}</div>')

    if kind == "comparison":
        rows = []
        for ln in body:
            if ln.count("|") >= 2:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):  # skip the --- rule row
                    rows.append(cells)
        if rows:
            hd = '<div class="chead">' + "".join(f"<span>{_esc(c)}</span>" for c in rows[0]) + "</div>"
            br = "".join('<div class="crow">' + "".join(f"<span>{_esc(c)}</span>" for c in r) + "</div>"
                         for r in rows[1:])
            return _mk(head, f'<div class="compare">{hd}{br}</div>')

    if kind in ("single-point", "callout"):
        it = items[0] if items else {"label": "", "body": (body[0] if body else "")}
        tone = "blue" if kind == "callout" else "pink"
        return _mk(head, f'{lead if kind=="single-point" else ""}'
                         f'<div class="callout {tone}">{icon(icon_for(it["label"]+" "+it.get("body","")), cache)}'
                         f'<p><b>{_esc(it["label"])}</b> {_esc(it.get("body",""))}</p></div>')

    if kind == "agenda":
        entries = [it["label"] for it in items] or body
        rows = "".join(f'<div class="agrow {"on" if k==0 else ""}"><span class="agn">{k+1}</span>'
                       f'<span>{_esc(e)}</span></div>' for k, e in enumerate(entries))
        return _mk(_title_block(section, title or "Agenda"), f'<div class="agenda">{rows}</div>')

    if kind == "stat":
        cols = min(len(items), 4) or 1
        cells = "".join(f'<div class="stat"><span class="statn">{_esc(it["label"])}</span>'
                        f'<span class="statl">{_esc(it.get("body",""))}</span></div>' for it in items)
        return _mk(head, f'<div class="stats" style="grid-template-columns:repeat({cols},1fr)">{cells}</div>')

    if kind == "content-text":
        big = _esc(body[0]) if body else _esc(title)
        panels = "".join(f'<div class="ctp">{_esc(it["label"])}{": "+_esc(it["body"]) if it.get("body") else ""}</div>'
                         for it in items) or "".join(f'<div class="ctp">{_esc(b)}</div>' for b in body[1:])
        return _mk(_title_block(section, title),
                   f'<div class="ctext"><p class="big2">{big}</p><div class="ctpanels">{panels}</div></div>')

    if kind == "content+cards+image":
        cs = "".join(f'<div class="ccard sm">{icon(icon_for(it["label"]), cache)}'
                     f'<h3>{_esc(it["label"])}</h3><p>{_esc(it.get("body",""))}</p></div>' for it in items)
        pic = _embed(*images[0]) if images else _embed("", None)
        return _mk(head, f'<div class="cci"><div class="ccicards">{cs}</div>{pic}</div>')

    if kind == "closing-cta":
        cards = "".join(f'<div class="ctacard">{icon(icon_for(it["label"]), cache)}'
                        f'<h4>{_esc(it["label"])}</h4><p>{_esc(it.get("body",""))}</p></div>' for it in items)
        return _mk(head, f'<div class="ctagrid">{cards}</div>')

    # fallback: title + body paragraphs (no bullets)
    return _mk(head, "".join(f'<p class="lead">{_esc(b)}</p>' for b in body[:6]))


def cover_slide(fm: dict, author_label: str = "Autor:", modified_label: str = "Última modificación:") -> str:
    """The contractually-fixed cover — same recipe as free-form §2 / strict §4, in HTML:
    title top-left, class + author/date lower-left, institution logo bottom-right."""
    title = _esc(fm.get("presentation", ""))
    cls = _esc(fm.get("class", ""))
    author = _esc(fm.get("presenter", ""))
    date = _esc(fm.get("date", ""))
    logo = _esc((re.sub(r"[^A-Za-z]", "", fm.get("class", ""))[:3] or "•").upper())
    return ('<figure><div class="slide"><span class="snum">cover</span>'
            '<div class="stage cov">'
            f'<h1 class="covt">{title}</h1>'
            f'<div class="covmeta"><p class="covc">{cls}</p>'
            f'<p class="cova">{author_label} {author}<br>{modified_label} {date}</p></div>'
            f'<div class="covlogo">{logo}</div>'
            '</div></div></figure>')


def page(body_html: str, title: str = "", subtitle: str = "", mode: str = "deck") -> str:
    # A presentation, not a document: just the deck + the present-mode chrome.
    return HTML_DOC.replace("__BODY__", body_html)


CSS = r"""
:root{--red:#DA1B2E;--pill:#F9D2D6;--call-pink:#F7BBC1;--call-blue:#B8E6F5;--card:#F2EEEE;
--ink:#1F1E1E;--body:#3B3535;--code-bg:#F2F2F2;--kw:#D73A49;--st:#005CC5;--cm:#6A737D;--slide:#fff;
--page:#E8E4E1;--panel:#FBFAF9;--fi:#2A2626;--fm:#6E6663;--hair:#D8D2CE;
--sans:"Helvetica Neue",Helvetica,Arial,sans-serif;--mono:"Courier New",ui-monospace,monospace;}
@media(prefers-color-scheme:dark){:root{--page:#191615;--panel:#221E1D;--fi:#EFEAE7;--fm:#A69D98;--hair:#332D2B;}}
:root[data-theme=light]{--page:#E8E4E1;--panel:#FBFAF9;--fi:#2A2626;--fm:#6E6663;--hair:#D8D2CE;}
:root[data-theme=dark]{--page:#191615;--panel:#221E1D;--fi:#EFEAE7;--fm:#A69D98;--hair:#332D2B;}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--fi);font-family:var(--sans);-webkit-font-smoothing:antialiased;line-height:1.5}
.wrap{max-width:1100px;margin:0 auto;padding:44px 22px 80px}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--red);font-weight:700;margin:0 0 10px}
h1.title{font-size:clamp(26px,4vw,40px);line-height:1.08;margin:0 0 12px;font-weight:800;letter-spacing:-.01em;text-wrap:balance}
.lede{font-size:16px;color:var(--fm);max-width:64ch;margin:0}.lede b{color:var(--fi)}
.deck{display:flex;flex-direction:column;gap:26px;margin-top:38px}
.grid{display:grid;gap:34px;margin-top:40px}@media(min-width:820px){.grid{grid-template-columns:1fr 1fr}.grid .span{grid-column:1/-1}}
figure{margin:0}figcaption{display:flex;gap:10px;align-items:baseline;margin:11px 2px 0;flex-wrap:wrap}
.tmpl{font-family:var(--mono);font-size:12.5px;color:var(--red);font-weight:700;background:color-mix(in srgb,var(--red) 12%,transparent);padding:2px 8px;border-radius:4px}
.cap{font-size:13px;color:var(--fm)}
.slide{aspect-ratio:16/9;background:var(--slide);border-radius:10px;position:relative;border:1px solid var(--hair);box-shadow:0 1px 0 var(--hair),0 18px 40px -24px rgba(0,0,0,.45);overflow:hidden;container-type:inline-size}
.snum{position:absolute;right:2.5cqw;bottom:2cqw;font-size:1.8cqw;color:var(--fm);font-family:var(--mono);z-index:2}
.stage{position:absolute;inset:0;padding:5cqw 5.5cqw;display:flex;flex-direction:column}
.shead{flex:0 0 auto;margin-bottom:2.6cqw}
/* content region (below the fixed header): a positioned box the fit pass solves into.
   .cfit is widened so that after scaling it always spans the full width (big content,
   no side voids) while fitting the height, then centred vertically. Short content stays
   full-width and centred. Never overlaps the header (it lives in its own box). */
.cbody{flex:1 1 auto;min-height:0;position:relative;overflow:hidden}
.cfit{position:absolute;top:0;left:0;width:100%;transform-origin:top left}
.cfit>*{margin-top:0!important;margin-bottom:0!important}
.pill{align-self:flex-start;background:var(--pill);color:var(--ink);font-weight:700;font-size:2.2cqw;letter-spacing:.06em;text-transform:uppercase;padding:.9cqw 2cqw;border-radius:2cqw}
.stitle{font-weight:800;color:var(--ink);letter-spacing:-.01em;font-size:4.2cqw;margin:2.4cqw 0 0;line-height:1.08;text-wrap:balance}
.stitle.ag{font-size:5cqw}.lead{color:var(--body);font-size:2.6cqw;margin:1.8cqw 0 0;max-width:56ch}
.ic{display:block}.ic svg{width:100%;height:100%;display:block}
.stage.cover{justify-content:center}.stmt{margin:auto 0}
.big{font-size:6.2cqw;font-weight:800;color:var(--ink);line-height:1.05;margin:0;letter-spacing:-.01em;text-wrap:balance}
.sub{font-size:2.8cqw;color:var(--body);margin:3cqw 0 0}
/* cover — free-form §2 recipe proportions: title top-left, class/author lower-left, logo bottom-right */
.stage.cov{display:block;padding:0}
.stage.cov .covt{position:absolute;left:5.4%;right:22%;top:10.4%;font-size:5.6cqw;font-weight:800;color:var(--ink);margin:0;line-height:1.06;letter-spacing:-.02em}
.stage.cov .covmeta{position:absolute;left:5.4%;right:22%;top:47.6%}
.covc{font-size:2.6cqw;font-weight:700;color:var(--ink);margin:0}
.cova{font-size:2.05cqw;color:var(--body);margin:1.6cqw 0 0;line-height:1.5}
.stage.cov .covlogo{position:absolute;right:5.4%;top:56%;width:13cqw;height:10.5cqw;border:2px solid var(--card);border-radius:1.5cqw;display:grid;place-items:center;font-weight:800;color:var(--red);font-size:3.2cqw}
.agenda{margin-top:3cqw;display:flex;flex-direction:column;gap:1.6cqw}
.agrow{display:flex;align-items:center;gap:2.4cqw;font-size:3cqw;color:var(--body);font-weight:600}
.agn{width:4.4cqw;height:4.4cqw;border-radius:50%;background:var(--card);color:var(--body);display:grid;place-items:center;font-size:2.4cqw;font-weight:800;flex:0 0 auto}
.agrow.on{color:var(--ink);font-weight:800}.agrow.on .agn{background:var(--red);color:#fff}
.callout{display:flex;gap:2cqw;align-items:flex-start;border-radius:2cqw;padding:2.4cqw 2.8cqw;margin-top:2.6cqw}
.callout.pink{background:var(--call-pink)}.callout.blue{background:var(--call-blue)}
.callout .ic{width:4.6cqw;height:4.6cqw;flex:0 0 auto}.callout p{margin:0;font-size:2.6cqw;color:#000;line-height:1.35}
.callout.blue p{color:var(--ink)}.callout b{font-weight:800}.fig{color:var(--red);font-weight:800}
.cards{display:grid;gap:2.2cqw;margin-top:auto}.cards.c1{grid-template-columns:1fr}.cards.c2{grid-template-columns:1fr 1fr}.cards.c3{grid-template-columns:repeat(3,1fr)}
.ccard{background:var(--card);border-radius:2cqw;padding:2.8cqw 2.4cqw;display:flex;flex-direction:column;gap:1.2cqw}
.ccard .ic{width:5.8cqw;height:5.8cqw}.ccard h3{margin:0;font-size:2.9cqw;font-weight:800;color:var(--ink);line-height:1.1}
.ccard p{margin:0;font-size:2.25cqw;color:var(--body);line-height:1.3}.ccard.sm{padding:2.2cqw}.ccard.sm .ic{width:5cqw;height:5cqw}
.cardrow{display:grid;grid-template-columns:repeat(3,1fr);gap:2.2cqw;margin-top:auto}
.rcard{background:var(--card);border-radius:2cqw;padding:2.6cqw 2.2cqw;display:flex;flex-direction:column;gap:1.2cqw}
.chip{width:6cqw;height:6cqw;border-radius:50%;background:var(--red);display:grid;place-items:center;flex:0 0 auto}
.chip svg{width:62%;height:62%}.rcard h3{margin:0;font-size:2.8cqw;font-weight:800;color:var(--ink)}.rcard p{margin:0;font-size:2.2cqw;color:var(--body);line-height:1.3}
.iconlist{margin-top:2.4cqw;display:flex;flex-direction:column;gap:2.2cqw}
.ilrow{display:flex;gap:2.4cqw;align-items:flex-start}.ilrow .ic{width:4.6cqw;height:4.6cqw;flex:0 0 auto;margin-top:.4cqw}
.ilrow h4{margin:0 0 .6cqw;font-size:2.9cqw;font-weight:800;color:var(--ink)}.ilrow p{margin:0;font-size:2.4cqw;color:var(--body);line-height:1.3}
.numrow{display:grid;grid-template-columns:repeat(3,1fr);gap:2.2cqw;margin-top:auto}
.ncard{background:#fff;border:1px solid var(--card);border-radius:1.4cqw;display:flex;overflow:hidden}
.ncard .strip{background:var(--card);width:6cqw;display:grid;place-items:center;font-weight:800;color:var(--body);font-size:3.2cqw;flex:0 0 auto}
.ncard .nbody{padding:2.2cqw}.ncard h4{margin:0 0 .8cqw;font-size:2.7cqw;color:var(--ink);font-weight:800}.ncard p{margin:0;font-size:2.15cqw;color:var(--body);line-height:1.3}
.compare{margin-top:auto;display:flex;flex-direction:column;gap:1.2cqw}
.chead,.crow{display:grid;grid-template-columns:1fr 1.2fr 1.2fr;gap:1.6cqw;align-items:center}
.chead{font-weight:800;color:var(--ink);font-size:2.5cqw;padding-bottom:.6cqw;border-bottom:.4cqw solid var(--card)}
.crow{font-size:2.3cqw;color:var(--body)}.crow>span{background:var(--card);padding:1.4cqw 1.8cqw;border-radius:1.2cqw}.crow>span:first-child{font-weight:700;color:var(--ink);background:transparent;padding-left:0}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:2.4cqw;margin-top:auto}
.stat{background:var(--card);border-radius:2cqw;padding:3cqw 2.4cqw;display:flex;flex-direction:column;gap:1cqw}
.statn{font-size:6cqw;font-weight:800;color:var(--red);line-height:1;letter-spacing:-.02em}.statl{font-size:2.1cqw;color:var(--body);line-height:1.25}
.figs{display:grid;grid-template-columns:repeat(3,1fr);gap:2.2cqw;margin-top:auto}
.figc{display:flex;flex-direction:column;gap:1cqw}.figc h4{margin:.6cqw 0 0;font-size:2.6cqw;font-weight:800;color:var(--ink)}.figc p{margin:0;font-size:2.1cqw;color:var(--body);line-height:1.25}
.imgph{background:repeating-linear-gradient(45deg,#eee,#eee 6px,#e4e4e4 6px,#e4e4e4 12px);border:1px solid #ddd;border-radius:1.4cqw;aspect-ratio:16/9;display:grid;place-items:center;overflow:hidden}.imgph span{font-family:var(--mono);font-size:1.9cqw;color:#999}
.imgph.svg,.imgph.has{background:#fff;border:1px solid var(--card)}.imgph.svg svg,.imgph.has img{width:100%;height:100%;display:block;object-fit:contain}
.imggrid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.8cqw;margin-top:auto}
.ci{display:grid;grid-template-columns:1fr 1fr;gap:3cqw;align-items:center}.citext{display:flex;flex-direction:column;gap:1.6cqw}
.cci{display:grid;grid-template-columns:1.1fr 1fr;gap:3cqw;align-items:center}
.ccicards{display:flex;flex-direction:column;gap:1.8cqw}
.split{display:grid;grid-template-columns:1fr 1.05fr;gap:3cqw;margin-top:auto;align-items:center}
.explain p{margin:0 0 1.4cqw;font-size:2.5cqw;color:var(--body);line-height:1.35}
.codebox{background:var(--code-bg);border-radius:2cqw;padding:2.6cqw;font-family:var(--mono);font-size:2.05cqw;line-height:1.55;color:#000;overflow:hidden}
.codebox .kw{color:var(--kw)}.codebox .st{color:var(--st)}.codebox .cm{color:var(--cm)}
.ctext{margin:auto 0}.big2{font-size:4cqw;font-weight:700;color:var(--ink);line-height:1.15;margin:0;text-wrap:balance}
.ctpanels{display:grid;grid-template-columns:repeat(3,1fr);gap:2cqw;margin-top:3cqw}.ctp{background:var(--card);border-radius:1.6cqw;padding:2.4cqw;font-size:2.2cqw;color:var(--body);font-weight:600}
.ctagrid{display:grid;grid-template-columns:repeat(2,1fr);gap:2.2cqw;margin-top:auto}
.ctacard{background:var(--card);border-radius:2cqw;padding:2.4cqw;display:flex;flex-direction:column;gap:.8cqw}.ctacard .ic{width:4.6cqw;height:4.6cqw}.ctacard h4{margin:0;font-size:2.7cqw;font-weight:800;color:var(--ink)}.ctacard p{margin:0;font-size:2.1cqw;color:var(--red);font-family:var(--mono)}
.hero{margin:auto 0;display:flex;flex-direction:column;gap:2cqw}.qa{font-size:16cqw;font-weight:800;color:var(--ink);line-height:.9;letter-spacing:-.02em}.qc{font-size:2.4cqw;color:var(--body);font-family:var(--mono)}
.legend{margin-top:46px;background:var(--panel);border:1px solid var(--hair);border-radius:12px;padding:22px 24px}
.legend h2{margin:0 0 4px;font-size:16px;font-weight:800}.legend .sub{margin:0 0 16px;color:var(--fm);font-size:14px}
.legrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}
.leg{display:flex;gap:12px;align-items:flex-start}.swatch{width:32px;height:32px;border-radius:7px;flex:0 0 auto;border:1px solid var(--hair)}
.leg .k{font-weight:700;font-size:13.5px}.leg .v{font-size:12.5px;color:var(--fm)}.drop{color:var(--red);font-weight:700}
footer{margin-top:26px;color:var(--fm);font-size:12.5px}footer code{font-family:var(--mono)}
/* present mode — arrow-key navigation + full-screen, one slide at a time */
.toolbar{position:fixed;top:14px;right:16px;z-index:60;display:flex;gap:8px}
.btn{font:600 13px var(--sans);background:var(--red);color:#fff;border:0;border-radius:8px;padding:9px 15px;cursor:pointer}
.btn:focus-visible{outline:3px solid color-mix(in srgb,var(--red) 45%,#fff);outline-offset:2px}
.phint{position:fixed;bottom:14px;left:0;right:0;text-align:center;color:var(--fm);font:500 12px var(--sans);z-index:55;pointer-events:none}
:root:not([data-present]) .phint{display:none}
:root[data-present] body{overflow:hidden}
:root[data-present] .wrap{max-width:none;padding:0}
:root[data-present] .wrap>header,:root[data-present] .wrap>footer,:root[data-present] .legend,:root[data-present] figcaption,:root[data-present] .snum{display:none}
:root[data-present] .deck,:root[data-present] .grid{display:block;gap:0;margin:0}
:root[data-present] figure{position:fixed;inset:0;display:none;background:var(--page);place-items:center;padding:3vmin}
:root[data-present] figure.cur{display:grid}
:root[data-present] .slide{width:min(96vw,calc(94vh * 16/9));height:auto;aspect-ratio:16/9;box-shadow:0 24px 60px -20px rgba(0,0,0,.6)}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""

PRESENT_JS = """<div class="toolbar"><button class="btn" id="present-btn" aria-label="Present full screen">▶ Present</button></div>
<div class="phint"><span id="pcount"></span> &middot; → next &middot; ← back &middot; F full screen &middot; Esc exit &middot; click to advance</div>
<script>
(function(){
  var figs=[].slice.call(document.querySelectorAll('.deck>figure, .grid>figure'));
  var i=0, root=document.documentElement;
  function fit(){                                   // solve .cfit to fill the region width and fit its height; header stays put
    figs.forEach(function(f){
      var st=f.querySelector('.cbody'); if(!st) return;   // cover/statement/hero have no .cbody
      var cf=st.querySelector('.cfit'); if(!cf) return;
      var rw=st.clientWidth, rh=st.clientHeight;
      if(rh<20||rw<20){ cf.style.cssText='position:absolute;top:0;left:0;width:100%;transform-origin:top left'; return; }
      // Solve for scale s: laid out at width rw/s, the content's visual height (natural*s) must fit rh.
      // Widening reflows text shorter, so iterate to convergence (a few passes suffice).
      var s=1;
      for(var k=0;k<5;k++){
        cf.style.transform='none'; cf.style.width=(rw/s)+'px';
        var h=cf.scrollHeight;                      // natural height at this pre-scale width
        var ns=Math.max(0.4, Math.min(1, rh/h));    // scale so visual height fits rh; never upscale; floored to avoid runaway widening
        if(Math.abs(ns-s)<0.005){ s=ns; break; }
        s=ns;
      }
      cf.style.width=(rw/s)+'px';
      var vh=cf.scrollHeight*s;                      // final visual height
      cf.style.top=Math.max(0,(rh-vh)/2)+'px';       // centre vertically in the remaining space
      cf.style.transform='scale('+s.toFixed(4)+')';  // origin top-left → visual width = (rw/s)*s = rw (fills), no side void
    });
  }
  function show(n){ if(!figs.length)return; i=Math.max(0,Math.min(figs.length-1,n));
    figs.forEach(function(f,k){ f.classList.toggle('cur',k===i); }); var c=document.getElementById('pcount'); if(c)c.textContent=(i+1)+' / '+figs.length; fit(); }
  function present(on){ if(on){ root.setAttribute('data-present',''); show(i); } else { root.removeAttribute('data-present'); } setTimeout(fit,0); }
  function fs(){ if(!document.fullscreenElement){ (root.requestFullscreen||function(){})(); } else { (document.exitFullscreen||function(){})(); } }
  document.addEventListener('keydown',function(e){
    var p=root.hasAttribute('data-present');
    if(p&&(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown')){ e.preventDefault(); show(i+1); }
    else if(p&&(e.key==='ArrowLeft'||e.key==='PageUp')){ e.preventDefault(); show(i-1); }
    else if(p&&e.key==='Home'){ show(0); } else if(p&&e.key==='End'){ show(figs.length-1); }
    else if(p&&e.key==='Escape'){ present(false); }
    else if(e.key==='f'||e.key==='F'){ fs(); }
  });
  document.addEventListener('click',function(e){
    if(!root.hasAttribute('data-present')||e.target.closest('.toolbar'))return;
    show(i + (e.clientX>window.innerWidth/2 ? 1 : -1));
  });
  var b=document.getElementById('present-btn');
  if(b)b.addEventListener('click',function(){ present(true); fs(); });
  var t; window.addEventListener('resize',function(){ clearTimeout(t); t=setTimeout(fit,120); });
  document.addEventListener('fullscreenchange',function(){ setTimeout(fit,60); });
  function fitSoon(){ requestAnimationFrame(function(){ requestAnimationFrame(fit); }); setTimeout(fit,60); setTimeout(fit,300); }
  window.addEventListener('load',fitSoon);
  if(document.fonts&&document.fonts.ready){ document.fonts.ready.then(fitSoon); }
  if(document.readyState!=='loading'){ fitSoon(); } else { document.addEventListener('DOMContentLoaded',fitSoon); }
})();
</script>"""

HTML_DOC = ('<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            "<style>" + CSS + "</style>\n"
            '<div class="wrap"><div class="deck">__BODY__</div></div>'
            + PRESENT_JS)
