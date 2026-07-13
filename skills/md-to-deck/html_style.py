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
  icon_for(label, body)                concept → Material Symbols name (matched vs the live catalog)
  load_catalog(cache)                  fetch + index the Material Symbols catalog once
  render_slide(kind, u, section, cache) one slide's inner HTML for catalog template `kind`
  page(body, title, subtitle, mode)    wrap slides into a full self-contained HTML document
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from icon_fetch import fetch_icon, fetch_catalog  # noqa: E402

ACCENT = "DA1B2E"
_DEFAULT_ICON = "bolt"

# The icon *choice* comes from the live Material Symbols catalog (fetch_catalog) — not a hardcoded
# icon map. This is only a thin **Spanish → English** bridge so a Spanish concept word can match
# the catalog's English tags (e.g. "seguridad" → the tags of `shield`/`security`). Language help,
# not icon selection.
_ES_EN = {
    "seguridad": "security", "seguro": "security", "segura": "security", "privacidad": "privacy",
    "riesgo": "risk warning", "amenaza": "threat warning", "ataque": "threat", "atacante": "threat",
    "dato": "data", "datos": "data", "base": "database", "almacenamiento": "storage",
    "costo": "payments money", "coste": "payments money", "precio": "price money",
    "presupuesto": "budget money", "pago": "payments", "ahorro": "savings",
    "tiempo": "schedule time", "latencia": "speed", "rapido": "speed", "velocidad": "speed",
    "usuario": "person", "usuarios": "group people", "equipo": "group team", "gente": "group people",
    "persona": "person", "cliente": "person", "clientes": "group",
    "codigo": "code", "programacion": "code", "modelo": "model", "red": "hub", "network": "hub",
    "conexion": "link", "conexiones": "hub", "herramienta": "build tool", "herramientas": "build tools",
    "trazabilidad": "history", "traza": "history", "deepfake": "face", "deepfakes": "face",
    "gobernanza": "policy", "gobierno": "policy", "cumplimiento": "verified compliance",
    "contrato": "contract description", "residencia": "location place", "ubicacion": "location",
    "borrar": "delete", "eliminar": "delete", "cifrado": "lock encryption", "cifrar": "lock",
    "credencial": "password key", "credenciales": "password key", "secreto": "lock key", "clave": "key password",
    "error": "error warning", "errores": "error", "alucinacion": "error", "falla": "error",
    "bug": "bug error", "problema": "warning error", "mito": "help", "realidad": "check",
    "agente": "robot", "agentes": "robot", "automatizacion": "bolt", "accion": "bolt", "ejecutar": "bolt",
    "prompt": "edit", "inyeccion": "bug", "deepfake": "face", "cara": "face", "caras": "face",
    "ley": "policy gavel", "leyes": "policy gavel", "auditoria": "checklist", "auditorias": "checklist",
    "practica": "checklist verified", "practicas": "checklist", "buena": "verified", "mejor": "star",
    "incidente": "warning report", "respuesta": "reply", "pregunta": "help", "preguntas": "help",
    "proveedor": "business", "empresa": "business", "negocio": "business", "organizacion": "business",
    "gestion": "settings", "configuracion": "settings", "mensaje": "message chat", "ejemplo": "lightbulb",
    "documento": "description document", "documentacion": "menu book", "aprender": "school", "curso": "school",
    "idea": "lightbulb", "consejo": "lightbulb tip", "analogia": "lightbulb",
    "metrica": "insights analytics", "metricas": "insights", "numero": "insights", "resultado": "insights",
    "impacto": "insights", "control": "tune", "permiso": "lock key", "permisos": "lock",
    "perimetro": "security", "frontera": "location", "vocabulario": "menu book", "concepto": "lightbulb",
    "arquitectura": "account tree", "fundamento": "foundation",
}
# Offline fallback only (catalog unavailable): a minimal regex seed so icons still resolve.
_SEED = [
    (r"segur|privac|riesgo|amenaza|protec", "shield"), (r"cifr|lock|credencial|secreto|clave", "lock"),
    (r"cost|precio|pago|presupuest|money", "payments"), (r"tiempo|latenc|schedule", "schedule"),
    (r"dato|data|base", "database"), (r"usuari|equipo|gente|persona|group", "group"),
    (r"cod|code|api|program", "code"), (r"idea|tip|analog|insight", "lightbulb"),
    (r"metric|result|número|analytic", "insights"), (r"conect|integr|hub|red|network", "hub"),
    (r"config|ajuste|setting", "settings"), (r"valid|verif|check|cumpl", "verified"),
    (r"agent|automat|acción|ejecut", "bolt"),
]

_STOP = {"de", "la", "el", "los", "las", "un", "una", "y", "o", "que", "en", "con", "para", "por",
         "del", "al", "es", "son", "se", "su", "lo", "sus", "una", "the", "of", "to", "and", "or",
         "in", "on", "for", "with", "is", "are", "a", "no", "si", "más", "mas"}
_WORD_RE = re.compile(r"[a-záéíóúñü]+", re.I)
_CAT_INDEX: list | None = None            # [(name, frozenset(tokens), popularity)] — built lazily


def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(_strip_accents((text or "").lower()))
            if len(w) >= 3 and w not in _STOP}


def load_catalog(cache) -> None:
    """Build the icon index from the live Material Symbols catalog (once). Falls back to the seed."""
    global _CAT_INDEX
    if _CAT_INDEX is not None:
        return
    cat = fetch_catalog(cache)
    if not cat:
        _CAT_INDEX = []                   # signal: catalog unavailable → icon_for uses _SEED
        return
    idx = []
    for name, meta in cat.items():
        toks = set()
        for tag in meta.get("tags", []):
            toks |= _tokens(tag)
        toks |= _tokens(name.replace("_", " "))
        idx.append((name, frozenset(toks), meta.get("pop", 0.0)))
    _CAT_INDEX = idx


def _expand(toks: set[str]) -> set[str]:
    out = set(toks)
    for w in toks:
        if w in _ES_EN:
            out |= _tokens(_ES_EN[w])
    return out


def icon_for(label: str, body: str = "") -> str:
    """Content-match a concept to a Material Symbols icon using the live catalog. The concept
    **label** drives the choice; the body only nudges ties (so "Seguridad" → shield even if its
    body happens to mention "credenciales")."""
    ltoks = _expand(_tokens(label))
    btoks = _expand(_tokens(body)) - ltoks
    if not _CAT_INDEX:                     # offline / not loaded → regex seed on the label
        t = _strip_accents(f"{label} {body}".lower())
        for pat, name in _SEED:
            if re.search(pat, t):
                return name
        return _DEFAULT_ICON
    best, best_score, best_pop = _DEFAULT_ICON, 0, -1.0
    for name, tset, pop in _CAT_INDEX:
        score = 3 * len(ltoks & tset) + len(btoks & tset)   # label weighted 3×, body 1×
        if name in ltoks:
            score += 6                     # exact name hit in the label is decisive
        if score > best_score or (score == best_score and score > 0 and pop > best_pop):
            best, best_score, best_pop = name, score, pop
    return best if best_score > 0 else _DEFAULT_ICON


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
# per-template slide rendering — `u` is a slide_model._parse_unit dict
# --------------------------------------------------------------------------- #

def _title_block(section, title):
    pill = f'<span class="pill">{_esc(section)}</span>' if section else ""
    t = f'<h2 class="stitle">{_esc(title)}</h2>' if title else ""
    return pill + t


def _mk(head, content):
    """A content slide: a fixed header (pill + title, anchored) + a centred content region.
    Returns the inner `.stage`; build_html wraps it in a Reveal `<section>`."""
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
            f'<div class="ccard">{icon(icon_for(it["label"], it.get("body","")), cache)}'
            f'<h3>{_esc(it["label"])}</h3><p>{_esc(it.get("body",""))}</p></div>' for it in items)
        return _mk(head, f'<div class="cards c{cols}">{cs}</div>')

    if kind == "process":
        if any(it.get("label") for it in items):        # labeled steps → numbered card strip
            cs = "".join(
                f'<div class="ncard"><div class="strip">{i}</div><div class="nbody">'
                f'<h4>{_esc(it["label"])}</h4><p>{_esc(it.get("body",""))}</p></div></div>'
                for i, it in enumerate(items, 1))
            return _mk(head, f'<div class="numrow">{cs}</div>')
        rows = "".join(                                  # plain numbered steps → vertical numbered list
            f'<div class="steprow"><span class="stepn">{i}</span>'
            f'<p>{_esc(it.get("body",""))}</p></div>' for i, it in enumerate(items, 1))
        return _mk(head, f'<div class="steps">{rows}</div>')

    if kind == "card-row":
        cs = "".join(
            f'<div class="rcard">{chip(icon_for(it["label"], it.get("body","")), cache)}'
            f'<h3>{_esc(it["label"])}</h3><p>{_esc(it.get("body",""))}</p></div>' for it in items)
        return _mk(head, f'{lead}<div class="cardrow">{cs}</div>')

    if kind == "icon-list":
        cs = "".join(
            f'<div class="ilrow">{icon(icon_for(it["label"], it.get("body","")), cache)}'
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
                         f'<div class="callout {tone}">{icon(icon_for(it["label"], it.get("body","")), cache)}'
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

    # fallback / lead+points — styled, NEVER plain paragraphs: a prominent lead statement +
    # the remaining lines as accented point panels (the "lead + facts" catalog shape).
    if not body:
        return _mk(head, "")
    if len(body) == 1:
        return _mk(head, f'<p class="big2">{_esc(body[0])}</p>')
    big = f'<p class="big2">{_esc(body[0])}</p>'
    panels = "".join(f'<div class="fpoint">{_esc(b)}</div>' for b in body[1:7])
    return _mk(head, f'<div class="leadpoints">{big}<div class="fpoints">{panels}</div></div>')


def section_agenda(sections, active: int, heading: str = "") -> str:
    """A section-divider slide that re-shows the agenda (numbered section list) with the active
    section accent-highlighted — reshown at each section start (slide-templates.md agenda)."""
    rows = "".join(
        f'<div class="agrow {"on" if k == active else ""}"><span class="agn">{k+1}</span>'
        f'<span>{_esc(s)}</span></div>' for k, s in enumerate(sections))
    return _mk(_title_block("", heading or "Agenda"), f'<div class="agenda">{rows}</div>')


def cover_slide(fm: dict, author_label: str = "Autor:", modified_label: str = "Última modificación:") -> str:
    """The contractually-fixed cover — same recipe as free-form §2 / strict §4, in HTML:
    title top-left, class + author/date lower-left, institution logo bottom-right."""
    title = _esc(fm.get("presentation", ""))
    cls = _esc(fm.get("class", ""))
    author = _esc(fm.get("presenter", ""))
    date = _esc(fm.get("date", ""))
    logo = _esc((re.sub(r"[^A-Za-z]", "", fm.get("class", ""))[:3] or "•").upper())
    return ('<div class="stage cov">'
            f'<div class="covtop"><h1 class="covt">{title}</h1></div>'
            f'<div class="covmeta"><p class="covc">{cls}</p>'
            f'<p class="cova">{author_label} {author}<br>{modified_label} {date}</p></div>'
            f'<div class="covlogo">{logo}</div>'
            '</div>')


CSS = r"""
:root{--red:#DA1B2E;--pill:#F9D2D6;--call-pink:#F7BBC1;--call-blue:#B8E6F5;--card:#F2EEEE;
--ink:#1F1E1E;--body:#3B3535;--code-bg:#F2F2F2;--kw:#D73A49;--st:#005CC5;--cm:#6A737D;--slide:#fff;
--page:#E8E4E1;--panel:#FBFAF9;--fi:#2A2626;--fm:#6E6663;--hair:#D8D2CE;
--sans:"Helvetica Neue",Helvetica,Arial,sans-serif;--mono:"Courier New",ui-monospace,monospace;}
@media(prefers-color-scheme:dark){:root{--page:#191615;--panel:#221E1D;--fi:#EFEAE7;--fm:#A69D98;--hair:#332D2B;}}
:root[data-theme=light]{--page:#E8E4E1;--panel:#FBFAF9;--fi:#2A2626;--fm:#6E6663;--hair:#D8D2CE;}
:root[data-theme=dark]{--page:#191615;--panel:#221E1D;--fi:#EFEAE7;--fm:#A69D98;--hair:#332D2B;}
*{box-sizing:border-box}html,body{margin:0;background:var(--page)}
/* ---- Reveal theme — aligned with Talksmith strict tokens (fonts, palette) ---- */
.reveal{font-family:var(--sans);color:var(--fi);-webkit-font-smoothing:antialiased}
.reveal .backgrounds{background:var(--page)}
.reveal .slides{text-align:left}
.reveal .slides>section{height:100%;padding:0;container-type:inline-size}
.reveal .slides>section.slide{background:var(--slide)}
.reveal ::selection{background:var(--pill)}
.reveal .progress{color:var(--red)}.reveal .controls{color:var(--red)}
.reveal .slide-number{background:transparent;color:var(--fm);font-family:var(--mono);font-size:15px;right:12px;bottom:10px}
/* ---- slide templates (our practices, unchanged) ---- */
.stage{position:relative;height:100%;padding:5cqw 5.5cqw;display:flex;flex-direction:column}
.shead{flex:0 0 auto;margin-bottom:2.6cqw}
/* content region below the fixed header. Reveal scales the whole slide to the window but does
   NOT shrink per-slide content, so a tiny fit pass (INIT) scales .cfit to fill the width and
   fit the height — the one thing neither Reveal nor CSS can do (fit-with-reflow). */
.cbody{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;justify-content:flex-start;overflow:hidden}
.cfit{width:100%;transform-origin:top left}
.cfit>*{margin-top:0!important;margin-bottom:0!important}
.pill{align-self:flex-start;background:var(--pill);color:var(--ink);font-weight:700;font-size:2.2cqw;letter-spacing:.06em;text-transform:uppercase;padding:.9cqw 2cqw;border-radius:2cqw}
.stitle{font-weight:800;color:var(--ink);letter-spacing:-.01em;font-size:4.2cqw;margin:2.4cqw 0 0;line-height:1.08;text-wrap:balance}
.stitle.ag{font-size:5cqw}.lead{color:var(--body);font-size:2.6cqw;margin:1.8cqw 0 0;max-width:56ch}
.ic{display:block}.ic svg{width:100%;height:100%;display:block}
.stage.cover{justify-content:center}.stmt{margin:auto 0}
.big{font-size:6.2cqw;font-weight:800;color:var(--ink);line-height:1.05;margin:0;letter-spacing:-.01em;text-wrap:balance}
.sub{font-size:2.8cqw;color:var(--body);margin:3cqw 0 0}
/* cover — free-form §2 recipe (title top-left, class/author lower-left, logo bottom-right),
   pure CSS: the title band reserves space so the meta sits at the recipe position for normal
   titles and simply flows DOWN for long ones — never overlapping. (cqw is width-based; on a
   fixed 16:9 slide a cqw maps to a constant fraction of height, so vertical rhythm is stable.) */
.stage.cov{padding:5.8cqw 5.4cqw 4cqw;justify-content:flex-start}
.covtop{min-height:22cqw;display:flex;align-items:flex-start}
.covt{font-size:5.6cqw;font-weight:800;color:var(--ink);margin:0;line-height:1.07;letter-spacing:-.02em}
.covmeta{max-width:74%}
.covc{font-size:2.6cqw;font-weight:700;color:var(--ink);margin:0}
.cova{font-size:2.05cqw;color:var(--body);margin:1.6cqw 0 0;line-height:1.5}
.stage.cov .covlogo{position:absolute;right:5.4cqw;bottom:4cqw;width:13cqw;height:10.5cqw;border:2px solid var(--card);border-radius:1.5cqw;display:grid;place-items:center;font-weight:800;color:var(--red);font-size:3.2cqw}
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
/* plain numbered steps (no per-step label) — a vertical numbered list */
.steps{display:flex;flex-direction:column;gap:1.8cqw}
.steprow{display:flex;gap:2.4cqw;align-items:flex-start}
.stepn{flex:0 0 auto;width:5cqw;height:5cqw;border-radius:50%;background:var(--red);color:#fff;font-weight:800;font-size:2.6cqw;display:grid;place-items:center;margin-top:.2cqw}
.steprow p{margin:0;font-size:2.6cqw;color:var(--body);line-height:1.35}
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
/* fallback / lead+points — a lead statement + accented point panels (never plain paragraphs) */
.leadpoints{display:flex;flex-direction:column;gap:2.6cqw}
.fpoints{display:flex;flex-direction:column;gap:1.6cqw}
.fpoint{background:var(--card);border-left:.7cqw solid var(--red);border-radius:1.2cqw;padding:1.8cqw 2.4cqw;font-size:2.5cqw;color:var(--body);line-height:1.3}
.ctpanels{display:grid;grid-template-columns:repeat(3,1fr);gap:2cqw;margin-top:3cqw}.ctp{background:var(--card);border-radius:1.6cqw;padding:2.4cqw;font-size:2.2cqw;color:var(--body);font-weight:600}
.ctagrid{display:grid;grid-template-columns:repeat(2,1fr);gap:2.2cqw;margin-top:auto}
.ctacard{background:var(--card);border-radius:2cqw;padding:2.4cqw;display:flex;flex-direction:column;gap:.8cqw}.ctacard .ic{width:4.6cqw;height:4.6cqw}.ctacard h4{margin:0;font-size:2.7cqw;font-weight:800;color:var(--ink)}.ctacard p{margin:0;font-size:2.1cqw;color:var(--red);font-family:var(--mono)}
.hero{margin:auto 0;display:flex;flex-direction:column;gap:2cqw}.qa{font-size:16cqw;font-weight:800;color:var(--ink);line-height:.9;letter-spacing:-.02em}.qc{font-size:2.4cqw;color:var(--body);font-family:var(--mono)}
/* speaker notes live in <aside class="notes"> — Reveal hides them on the slide, shows them in speaker view */
@media(prefers-reduced-motion:reduce){.reveal .slides section{transition:none!important}}
"""

# Reveal.js configuration — navigation, scaling, transitions, PDF export, speaker notes all
# handled by Reveal. The ONLY custom code is fitContent(): a per-slide content-fit (scale .cfit
# to fill width + fit height), which Reveal has no equivalent for and CSS can't do (reflow).
_REVEAL_INIT = """
function fitContent(cb){
  var cf=cb.querySelector('.cfit'); if(!cf) return;
  var rw=cb.clientWidth, rh=cb.clientHeight; if(rh<20||rw<20) return;
  var s=1;                                   // solve: laid out at width rw/s, visual height (h*s) must fit rh
  for(var k=0;k<5;k++){ cf.style.transform='none'; cf.style.width=(rw/s)+'px';
    var h=cf.scrollHeight; var ns=Math.max(0.35, Math.min(1, rh/h));
    if(Math.abs(ns-s)<0.005){ s=ns; break; } s=ns; }
  cf.style.width=(rw/s)+'px';
  var vh=cf.scrollHeight*s; cf.style.marginTop=Math.max(0,(rh-vh)/2)+'px';   // centre vertically
  cf.style.transform='scale('+s.toFixed(4)+')';                             // origin top-left → fills width, no side void
}
function fitAll(scope){ (scope||document).querySelectorAll('.reveal .slides section .cbody').forEach(fitContent); }
Reveal.initialize({
  width:1280, height:720, margin:0.04, minScale:0.2, maxScale:2.0,
  controls:true, progress:true, slideNumber:'c/t', hash:true, center:false,
  transition:'slide', backgroundTransition:'fade', overview:true, touch:true,
  keyboard:true, pdfSeparateFragments:false, plugins:[ RevealNotes ]
}).then(function(){ fitAll();
  Reveal.on('slidechanged', function(e){ if(e.currentSlide) fitAll(e.currentSlide); });
  Reveal.on('resize', function(){ setTimeout(fitAll, 60); });
});"""


def _vendor(name: str) -> str:
    """Read a vendored Reveal.js asset (inlined so the deck is self-contained + offline)."""
    return (_HERE / "vendor" / "reveal" / name).read_text(encoding="utf-8")


def page(body_html: str, title: str = "", subtitle: str = "", mode: str = "deck") -> str:
    """Assemble the full self-contained Reveal.js deck: vendored CSS/JS inlined, our theme
    layered on top, slides as <section>s. Presentation, navigation, scaling, transitions,
    speaker notes (press `s`), and PDF export (open with `?print-pdf`) are all Reveal's."""
    reveal_css = _vendor("reset.css") + "\n" + _vendor("reveal.css")
    reveal_js = _vendor("reveal.js")
    notes_js = _vendor("notes.js")
    return (
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{_esc(title)}</title>\n'
        f'<style>{reveal_css}</style>\n'
        f'<style>{CSS}</style>\n'
        f'<div class="reveal"><div class="slides">{body_html}</div></div>\n'
        f'<script>{reveal_js}</script>\n'
        f'<script>{notes_js}</script>\n'
        f'<script>{_REVEAL_INIT}</script>\n'
    )
