"""HTML styling + slide rendering for the Talksmith deck (`build_html.py`).

The theme + tokens (palette, Helvetica/Courier) live in the `CSS` string; the per-slide-type
**markup lives in Jinja templates** under `templates/html/` (one `.j2` per catalog template).
This module computes each slide's structured context and renders its template — the split keeps
markup out of Python. Real Material Symbols icons are matched against the live catalog
(`icon_fetch.py`) and inlined. Unlike the native `.pptx` render, this is deterministic code:
icons, callout boxes, code surfaces, and card strips always render.

Public API:
  CSS                                  the theme stylesheet (tokens + component classes)
  render_slide(kind, u, section, cache) render a slide's inner HTML via its template
  cover_slide(fm) / section_agenda(…)  the cover and per-section agenda slides
  icon_for(label, body)                concept → Material Symbols name (matched vs the live catalog)
  load_catalog(cache)                  fetch + index the Material Symbols catalog once
  page(body, title, subtitle, mode)    wrap slides into a self-contained Reveal.js document
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
# per-template slide rendering — one Jinja template per slide type in templates/html/.
# Python computes the structured context (which template, cols, rows, matched icon name);
# the .j2 files own the *markup*. `u` is a slide_model._parse_unit dict.
# --------------------------------------------------------------------------- #

from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402
from markupsafe import Markup  # noqa: E402

_ENV = Environment(
    loader=FileSystemLoader(str(_HERE / "templates" / "html")),
    autoescape=select_autoescape(enabled_extensions=("j2", "html"), default=True),
    trim_blocks=True, lstrip_blocks=True)
_CUR_CACHE = None                          # bound per render so templates can call icon()/chip()

_ENV.globals.update(
    icon=lambda name: Markup(icon(name, _CUR_CACHE)),
    chip=lambda name: Markup(chip(name, _CUR_CACHE)),
    embed=lambda alt, path: Markup(_embed(alt, path)),
    icon_for=icon_for,
)

# catalog template id → template file
_TMPL = {
    "divider": "divider.j2", "statement": "statement.j2", "closing-hero": "closing-hero.j2",
    "concept-breakdown": "concept-breakdown.j2", "process": "process.j2", "card-row": "card-row.j2",
    "icon-list": "icon-list.j2", "code-example": "code-example.j2", "figures": "figures.j2",
    "image-grid": "image-grid.j2", "content-image": "content-image.j2", "comparison": "comparison.j2",
    "single-point": "single-point.j2", "callout": "single-point.j2", "agenda": "agenda.j2",
    "stat": "stat.j2", "content-text": "content-text.j2", "content+cards+image": "content-cards-image.j2",
    "closing-cta": "closing-cta.j2", "fallback": "fallback.j2",
}


def _render(tmpl: str, cache, **ctx) -> str:
    global _CUR_CACHE
    _CUR_CACHE = cache
    return _ENV.get_template(tmpl).render(**ctx)


def render_slide(kind, u, section, cache) -> str:
    """Compute the structured context for a slide, then render its template. All markup lives
    in templates/html/<kind>.j2; this only decides the template and precomputes derived values."""
    title, items, body = u.get("title", ""), u.get("items", []), u.get("body", [])
    images, code = u.get("images", []), u.get("code_lines", [])
    ctx = dict(section=section, title=title, items=items, body=body, images=images, code=code)

    if kind == "concept-breakdown":
        n = len(items)
        ctx["cols"] = 1 if n == 1 else (2 if n in (2, 4) else 3)   # 2→2col · 3→row · 4→2×2 · 5–6→3col
    elif kind == "process":
        ctx["labeled"] = any(it.get("label") for it in items)
    elif kind in ("figures", "image-grid"):
        kind = "image-grid" if (kind == "image-grid" or not items) else "figures"
        ctx["figs"] = [(it, images[k] if k < len(images) else ("", None)) for k, it in enumerate(items)]
    elif kind == "content-image":
        ctx["leads"] = body[:2]
    elif kind == "comparison":
        rows = []
        for ln in body:
            if ln.count("|") >= 2:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):    # skip the --- rule row
                    rows.append(cells)
        if not rows:
            kind = "fallback"                                       # no real table → fall back
        ctx["rows"] = rows
    elif kind in ("single-point", "callout"):
        ctx["item"] = items[0] if items else {"label": "", "body": (body[0] if body else "")}
        ctx["tone"] = "blue" if kind == "callout" else "pink"
        ctx["show_lead"] = kind == "single-point"
    elif kind == "stat":
        ctx["cols"] = min(len(items), 4) or 1
    elif kind == "content-text":
        ctx["big"] = body[0] if body else title
        ctx["panels"] = [it["label"] + ((": " + it["body"]) if it.get("body") else "") for it in items] \
            or body[1:]
    elif kind == "agenda":
        ctx["sections"] = [it["label"] for it in items] or body
        ctx["active"] = 0
        ctx["title"] = title or "Agenda"

    if kind == "fallback":
        ctx["big"] = body[0] if body else ""
        ctx["points"] = body[1:7] if len(body) > 1 else []

    return _render(_TMPL.get(kind, "fallback.j2"), cache, **ctx)


def section_agenda(sections, active: int, heading: str = "") -> str:
    """A section-divider slide that re-shows the agenda with the active section highlighted."""
    return _render("agenda.j2", None, sections=sections, active=active, title=heading or "Agenda", section="")


def cover_slide(fm: dict, author_label: str = "Autor:", modified_label: str = "Última modificación:") -> str:
    """The contractually-fixed cover — same recipe as free-form §2 / strict §4, in HTML."""
    return _render(
        "cover.j2", None,
        title=fm.get("presentation", ""), cls=fm.get("class", ""),
        author=fm.get("presenter", ""), date=fm.get("date", ""),
        logo=(re.sub(r"[^A-Za-z]", "", fm.get("class", ""))[:3] or "•").upper(),
        author_label=author_label, modified_label=modified_label)


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
.cfit{width:100%;transform-origin:top left;display:flex;flex-direction:column;gap:3cqw}
.cfit>*{margin-top:0!important;margin-bottom:0!important}
.pill{align-self:flex-start;background:var(--pill);color:var(--ink);font-weight:700;font-size:2.2cqw;letter-spacing:.06em;text-transform:uppercase;padding:.9cqw 2cqw;border-radius:2cqw}
.stitle{font-weight:800;color:var(--ink);letter-spacing:-.01em;font-size:4.2cqw;margin:2.4cqw 0 0;line-height:1.08;text-wrap:balance}
.stitle.ag{font-size:5cqw}.lead{color:var(--body);font-size:2.6cqw;margin:1.8cqw 0 0;max-width:56ch}
.ic{display:block}.ic svg{width:100%;height:100%;display:block}
.stage.cover{justify-content:center}.stmt{margin:auto 0}
.big{font-size:6.2cqw;font-weight:800;color:var(--ink);line-height:1.05;margin:0;letter-spacing:-.01em;text-wrap:balance}
.sub{font-size:2.8cqw;color:var(--body);margin:3cqw 0 0}
/* section eyebrow on full-bleed statement/hero slides (the section they belong to) */
.steyebrow{font-size:2.1cqw;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--red);margin:0 0 2.4cqw}
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
.stepn{flex:0 0 auto;width:3.6cqw;height:3.6cqw;border-radius:50%;background:transparent;border:.3cqw solid var(--red);color:var(--red);font-weight:800;font-size:1.9cqw;display:grid;place-items:center;margin-top:.4cqw}
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
  var vh=cf.scrollHeight*s; cf.style.marginTop=Math.max(0,(rh-vh)*0.36)+'px';   // upper-third, not dead-centre
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
