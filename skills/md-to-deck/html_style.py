"""HTML styling + slide rendering for the Talksmith deck (`build_html.py`).

Nothing static is hardcoded in Python: the **theme stylesheet** is `templates/html/theme.css`
(tokens + component classes, read at import) and the **per-slide-type markup** is one Jinja
template per catalog type under `templates/html/*.j2`. This module only computes each slide's
structured context, matches its icon against the live Material Symbols catalog (`icon_fetch.py`),
and renders the template. Unlike the native `.pptx` render, this is deterministic code: icons,
callout boxes, code surfaces, and card strips always render.

Public API:
  CSS                                  the theme stylesheet, loaded from templates/html/theme.css
  render_model_slide(slide, cache, ...)  render a slide-model.json slide via its template
  cover_from_deck(deck) / section_agenda(…)  the cover and per-section roadmap slides
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
# Neutral, distinct icons used (in order) when a label content-matches nothing — so unmatched
# items on a slide still get *different* icons instead of all falling to the same default.
_FALLBACK_ICONS = ["check_circle", "chevron_right", "star", "flag", "label",
                   "done", "arrow_forward", "adjust", "circle", "info"]

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


# Icons already placed on the current slide — an icon is never repeated within one slide
# (reset per slide in render_model_slide). When the best match is taken, fall to the next-best.
_USED_ICONS: set[str] = set()


def _reset_slide_icons() -> None:
    _USED_ICONS.clear()


def icon_for(label: str, body: str = "") -> str:
    """Content-match a concept to a Material Symbols icon using the live catalog. The concept
    **label** drives the choice; the body only nudges ties (so "Seguridad" → shield even if its
    body happens to mention "credenciales"). **No icon repeats within a slide** — if the top match
    is already used here, the next-best unused one is returned."""
    ltoks = _expand(_tokens(label))
    btoks = _expand(_tokens(body)) - ltoks
    if not _CAT_INDEX:                     # offline / not loaded → regex seed on the label
        t = _strip_accents(f"{label} {body}".lower())
        for pat, name in _SEED:
            if re.search(pat, t) and name not in _USED_ICONS:
                _USED_ICONS.add(name)
                return name
        return _DEFAULT_ICON
    scored = []
    for name, tset, pop in _CAT_INDEX:
        score = 3 * len(ltoks & tset) + len(btoks & tset)   # label weighted 3×, body 1×
        if name in ltoks:
            score += 6                     # exact name hit in the label is decisive
        if score > 0:
            scored.append((score, pop, name))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    for _, _, name in scored:              # highest score first, skipping icons already on this slide
        if name not in _USED_ICONS:
            _USED_ICONS.add(name)
            return name
    for name in _FALLBACK_ICONS:           # no match (or all matches used) → a distinct neutral icon
        if name not in _USED_ICONS:
            _USED_ICONS.add(name)
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
# per-template slide rendering — one Jinja template per slide type in templates/html/.
# Python computes the structured context (which template, cols, rows, matched icon name);
# the .j2 files own the *markup*.
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
    "single-point": "single-point.j2", "callout": "single-point.j2",
    "stat": "stat.j2", "content-text": "content-text.j2", "content+cards+image": "content-cards-image.j2",
    "closing-cta": "closing-cta.j2", "quote": "quote.j2", "timeline": "timeline.j2",
    "big-number": "big-number.j2", "pros-cons": "pros-cons.j2", "quiz": "quiz.j2",
    "fallback": "fallback.j2",
}


def _render(tmpl: str, cache, **ctx) -> str:
    global _CUR_CACHE
    _CUR_CACHE = cache
    return _ENV.get_template(tmpl).render(**ctx)


def section_agenda(sections, active: int, heading: str = "") -> str:
    """A section separator that doubles as the roadmap: the ordered section list on the left,
    the current section (big number + title) on the right, others dimmed."""
    return _render("section-agenda.j2", None, sections=sections, active=active)


# The bundled fallback is a neutral, unbranded placeholder — the plugin ships no institution
# branding. A subject repo supplies its own logo (see resolution order below).
_BUNDLED_LOGO = _HERE.parent.parent / "config" / "pptx-styles" / "placeholder-logo.png"


def _cover_logo(fm: dict, talk_root) -> str:
    """The cover's institution logo, embedded self-contained. Resolution order: frontmatter
    `logo:` → the Talk's `images/logo|cover-logo` → the subject repo's `config/logo.*`
    (set once at repo setup) → the bundled neutral placeholder → a text stand-in from the
    class name (only if no image is found)."""
    import base64
    cands = []
    lf = (fm.get("logo") or "").strip()
    if lf:
        cands += ([Path(talk_root) / lf] if talk_root else []) + [Path(lf)]
    if talk_root:
        for stem in ("logo", "cover-logo"):
            for ext in (".svg", ".png", ".jpg", ".jpeg"):
                cands.append(Path(talk_root) / "images" / f"{stem}{ext}")
        # Repo-level institution logo, shared by every Talk in the subject repo
        # (talk_root is `talks/<Talk>`, so the repo root is two levels up).
        repo_root = Path(talk_root).parent.parent
        for ext in (".svg", ".png", ".jpg", ".jpeg"):
            cands.append(repo_root / "config" / f"logo{ext}")
    cands.append(_BUNDLED_LOGO)
    for c in cands:
        try:
            if not c.is_file():
                continue
            if c.suffix.lower() == ".svg":
                svg = re.sub(r"<\?xml.*?\?>", "", c.read_text(encoding="utf-8"), flags=re.DOTALL).strip()
                return f'<span class="covlogoimg">{svg}</span>'
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(c.suffix.lower().lstrip("."), "image/png")
            b64 = base64.b64encode(c.read_bytes()).decode("ascii")
            return f'<img class="covlogoimg" alt="logo" src="data:{mime};base64,{b64}">'
        except OSError:
            continue
    txt = (re.sub(r"[^A-Za-z]", "", fm.get("class", ""))[:3] or "•").upper()
    return f'<span class="covlogotext">{_esc(txt)}</span>'


def _resolve_img(img, talk_root, asset_dir):
    """Resolve a model `{src,alt}` image to `(alt, Path|None)` for embed()."""
    if not img:
        return ("", None)
    src, alt = (img.get("src") or ""), (img.get("alt") or "")
    if not src or src.startswith(("http://", "https://")):
        return (alt, None)
    cands = ([asset_dir / src] if asset_dir else []) + ([Path(talk_root) / src] if talk_root else []) + [Path(src)]
    return (alt, next((c for c in cands if c.is_file()), None))


def cover_from_deck(deck: dict, talk_root=None, author_label: str = "Autor:",
                    modified_label: str = "Última modificación:") -> str:
    """The contractually-fixed cover, built from the model's `deck` object."""
    fm = {"logo": deck.get("logo") or "", "class": deck.get("class", ""),
          "presentation": deck.get("title", "")}
    return _render(
        "cover.j2", None,
        title=deck.get("title", ""), inst=deck.get("institution", ""),
        cls=deck.get("class", ""), author=deck.get("presenter", ""), date=deck.get("date", ""),
        logo=Markup(_cover_logo(fm, talk_root)),
        author_label=author_label, modified_label=modified_label)


# Templates whose markup places a matched icon next to each item / the point.
_ICON_ITEM_KINDS = {"concept-breakdown", "card-row", "icon-list", "content+cards+image", "closing-cta"}


def _labeled(items) -> list:
    """Normalize a list whose entries are strings or `{label,body}` dicts into `{label,body}`.
    The LLM decides whether an entry has a `label` (the emphasized lead before a colon) — the
    renderer never parses text to find one."""
    return [x if isinstance(x, dict) else {"label": "", "body": x} for x in (items or [])]


# highlight kinds → a fixed Material Symbols icon (the accent colour is set in CSS per kind).
_HL_ICON = {
    "note": "sticky_note_2", "example": "lightbulb", "definition": "menu_book",
    "quote": "format_quote", "important": "priority_high", "takeaway": "flag",
}


def _highlights(items) -> list:
    """Normalize the `highlights` list into `{kind, icon, label, body}`. The **fill** picks each
    entry's `kind` (one of _HL_ICON); the renderer maps it to its icon + accent style. Defaults to
    `takeaway`. Entries may be a string or `{body, label?, kind?}`."""
    out = []
    for x in (items or []):
        h = x if isinstance(x, dict) else {"body": x}
        kind = (h.get("kind") or "takeaway").lower()
        if kind not in _HL_ICON:
            kind = "takeaway"
        out.append({"label": h.get("label", ""), "body": h.get("body", ""),
                    "kind": kind, "icon": _HL_ICON[kind]})
    return out


def _resolve_item_icons(items: list) -> None:
    """Resolve each item's icon in place. The fill may **suggest** an `icon` (a Material Symbols
    name) per item, choosing distinct ones; those are reserved first, then any item without a
    suggestion is content-matched — and `icon_for` won't reuse an icon already on this slide."""
    for it in items:
        if it.get("icon"):
            _USED_ICONS.add(it["icon"])
    for it in items:
        it["icon"] = it.get("icon") or icon_for(it.get("label", ""), it.get("body", ""))


def render_model_slide(slide: dict, cache, talk_root=None, asset_dir=None) -> str:
    """Render one `slide-model.json` slide: map its template's fields onto the Jinja template's
    context. All semantics were resolved by the LLM fill step — this is a pure field mapping."""
    _reset_slide_icons()                   # icons don't repeat within a slide
    t = slide.get("template", "fallback")
    # highlights: optional emphasized takeaways / comments, rendered in a highlight band by the
    # `stage` macro — available to every content template (nothing in the source is ever dropped).
    ctx = {"section": slide.get("section", ""), "title": slide.get("title", ""),
           "highlights": _highlights(slide.get("highlights")),
           "reveal": slide.get("reveal", "")}   # "sequential" → items appear one at a time (Reveal fragments)
    ri = lambda im: _resolve_img(im, talk_root, asset_dir)
    lead = slide.get("lead", "")
    if t == "divider":
        ctx["number"] = slide.get("number")
    elif t == "statement":
        ctx["body"] = [slide["sub"]] if slide.get("sub") else []
    elif t == "concept-breakdown":
        cards = slide.get("cards", [])
        ctx["items"] = cards
        n = len(cards)
        ctx["cols"] = 1 if n == 1 else (2 if n in (2, 4) else 3)
    elif t == "card-row":
        ctx["items"], ctx["body"] = slide.get("cards", []), ([lead] if lead else [])
    elif t == "icon-list":
        ctx["items"], ctx["body"] = slide.get("rows", []), ([lead] if lead else [])
    elif t == "process":
        steps = slide.get("steps", [])
        ctx["items"] = steps
        ctx["labeled"] = any(s.get("label") for s in steps)
        ctx["body"] = [lead] if lead else []
    elif t == "figures":
        ctx["figs"] = [(f, ri(f.get("image"))) for f in slide.get("figures", [])]
    elif t == "image-grid":
        ctx["images"] = [ri(i) for i in slide.get("images", [])]
    elif t == "content-image":
        ctx["lead"], ctx["facts"] = lead, _labeled(slide.get("facts"))
        ctx["images"] = [ri(slide.get("image"))]
        ctx["layout"] = slide.get("layout", "text-left")
    elif t == "content+cards+image":
        ctx["items"], ctx["images"] = slide.get("cards", []), [ri(slide.get("image"))]
    elif t == "comparison":
        cols = slide.get("columns", [])
        rows = [[c.get("header", "") for c in cols]]
        maxn = max((len(c.get("cells", [])) for c in cols), default=0)
        for i in range(maxn):
            rows.append([(c.get("cells", [])[i] if i < len(c.get("cells", [])) else "") for c in cols])
        ctx["rows"] = rows
        ctx["ncols"] = len(cols) or 1
    elif t == "stat":
        stats = slide.get("stats", [])
        ctx["items"] = [{"label": s.get("value", ""), "body": s.get("caption", "")} for s in stats]
        ctx["cols"], ctx["lead"] = (min(len(stats), 4) or 1), lead
    elif t == "big-number":
        ctx["number"], ctx["caption"], ctx["more"] = slide.get("number", ""), slide.get("caption", ""), []
    elif t == "quote":
        ctx["quote"], ctx["attribution"] = slide.get("quote", ""), slide.get("attribution", "")
    elif t == "timeline":
        ctx["items"] = [{"label": m.get("label", ""), "body": m.get("body", "")} for m in slide.get("milestones", [])]
    elif t == "pros-cons":
        ctx["items"] = [{"label": "Ventajas", "body": " · ".join(slide.get("pros", []))},
                        {"label": "Riesgos", "body": " · ".join(slide.get("cons", []))}]
    elif t == "quiz":
        # question + optional choices show immediately; the answer (and the highlight on the
        # correct choice) reveal together on next-nav (Reveal fragments). Optional image at right.
        opts = slide.get("options", [])
        ctx["question"] = slide.get("question", "") or slide.get("title", "")
        ctx["options"] = opts
        ctx["answer"] = slide.get("answer", "")
        ctx["explanation"] = slide.get("explanation", "")
        ctx["answer_label"] = slide.get("answer_label", "Respuesta")
        ctx["image"] = ri(slide.get("image")) if slide.get("image") else None
        # `correct` selects the choice highlighted on reveal: an option string, a 1-based
        # index, or a letter (A/B/C…). -1 → no option highlighted.
        corr, ci = slide.get("correct"), -1
        if isinstance(corr, bool):
            pass
        elif isinstance(corr, int):
            ci = corr - 1 if corr >= 1 else corr
        elif isinstance(corr, str) and corr:
            if len(corr) == 1 and corr.upper().isalpha():
                ci = ord(corr.upper()) - 65
            else:
                ci = next((k for k, o in enumerate(opts) if str(o).strip() == corr.strip()), -1)
        ctx["correct_index"] = ci if 0 <= ci < len(opts) else -1
    elif t in ("single-point", "callout"):
        ctx["item"] = slide.get("point") or slide.get("callout") or {"label": "", "body": ""}
        ctx["tone"] = slide.get("tone", "blue" if t == "callout" else "pink")
        ctx["show_lead"] = False
    elif t == "code-example":
        code = slide.get("code", "")
        ctx["code"] = code.splitlines() if isinstance(code, str) else code
        ctx["body"] = slide.get("explanation", [])
    elif t == "content-text":
        ctx["big"], ctx["panels"] = slide.get("big", ""), slide.get("panels", [])
    elif t == "closing-hero":
        ctx["body"] = [slide["body"]] if slide.get("body") else []
    elif t == "closing-cta":
        ctx["items"] = slide.get("items", [])
    elif t == "fallback":
        ctx["big"] = slide.get("big", "") or slide.get("title", "")
    if t in _ICON_ITEM_KINDS and ctx.get("items"):
        _resolve_item_icons(ctx["items"])
    elif t in ("single-point", "callout") and ctx.get("item"):
        _resolve_item_icons([ctx["item"]])
    return _render(_TMPL.get(t, "fallback.j2"), cache, **ctx)


# The theme stylesheet lives in its own file (static CSS, no interpolation) — read at import,
# like the vendored reveal.css and the fonts. Edit templates/html/theme.css, not this string.
CSS = (_HERE / "templates" / "html" / "theme.css").read_text(encoding="utf-8")

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
function fitCover(st){                       // full-bleed text slides (quote/statement/closing-hero) have no .cfit
  var cf=st.querySelector('.hero,.stmt,.quotewrap'); if(!cf) return;
  cf.style.transform='none';
  var cs=getComputedStyle(st), availH=st.clientHeight-parseFloat(cs.paddingTop)-parseFloat(cs.paddingBottom);
  var h=cf.scrollHeight;
  if(h>availH+1){ var s=Math.max(0.4, availH/h); cf.style.transformOrigin='center center'; cf.style.transform='scale('+s.toFixed(4)+')'; }
}
function fitAll(scope){ var r=(scope||document);
  r.querySelectorAll('.reveal .slides section .cbody').forEach(fitContent);
  r.querySelectorAll('.reveal .slides section .stage.cover').forEach(fitCover); }
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


# IBM Plex Sans/Mono — vendored woff2, inlined as @font-face data-URIs (the Artifact CSP blocks
# font CDNs). A distinctive, embeddable editorial superfamily; the strict `.pptx` render keeps
# Helvetica/Courier — only the HTML deck uses these.
_FONT_FACES = [
    ("IBM Plex Sans", 400, "plex-sans-400.woff2"),
    ("IBM Plex Sans", 600, "plex-sans-600.woff2"),
    ("IBM Plex Sans", 700, "plex-sans-700.woff2"),
    ("IBM Plex Mono", 500, "plex-mono-500.woff2"),
]


def _fonts_css() -> str:
    import base64
    out = []
    for family, weight, fn in _FONT_FACES:
        p = _HERE / "vendor" / "fonts" / fn
        if not p.is_file():
            continue
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        out.append(f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;"
                   f"font-display:swap;src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(out)


# Runtime theme toggle — one discreet icon button (moon in light, sun in dark). `_THEME_EARLY`
# applies the saved/URL theme before Reveal renders (no flash); `_THEME_SWITCH` flips it on click,
# persists the choice, and re-layouts Reveal.
_THEME_EARLY = ("(function(){try{var q=new URLSearchParams(location.search).get('deck-theme');"
                "var t=q||localStorage.getItem('deckTheme')||'light';"
                "document.documentElement.setAttribute('data-deck-theme',t);}catch(e){}})();")
_THEME_SWITCH = ("(function(){var root=document.documentElement,btn=document.querySelector('[data-deck-toggle]');"
                 "if(!btn)return;function set(t){root.setAttribute('data-deck-theme',t);"
                 "try{localStorage.setItem('deckTheme',t);}catch(e){}"
                 "if(window.Reveal&&Reveal.layout)Reveal.layout();}"
                 "btn.addEventListener('click',function(){"
                 "set(root.getAttribute('data-deck-theme')==='dark'?'light':'dark');});})();")

# Idle-UI: the nav arrows + slide number (styled to hide by default via CSS) only appear while the
# pointer is moving — `html.deck-ui` is added on pointer activity and dropped after a short idle.
_IDLE_UI = ("(function(){var root=document.documentElement,t;"
            "function show(){root.classList.add('deck-ui');clearTimeout(t);"
            "t=setTimeout(function(){root.classList.remove('deck-ui');},2000);}"
            "['pointermove','mousedown','touchstart','wheel'].forEach(function(ev){"
            "document.addEventListener(ev,show,{passive:true});});})();")

# A small moon (shown in light → click for dark) + sun (shown in dark → click for light).
_THEME_ICONS = (
    '<svg class="ic-moon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">'
    '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
    '<svg class="ic-sun" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/>'
    '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>')


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
        f'<style>{_fonts_css()}</style>\n'
        f'<style>{reveal_css}</style>\n'
        f'<style>{CSS}</style>\n'
        f'<script>{_THEME_EARLY}</script>\n'
        f'<div class="reveal"><div class="slides">{body_html}</div></div>\n'
        f'<button class="deckthemes" data-deck-toggle type="button" '
        f'aria-label="Alternar tema claro / oscuro" title="Tema claro / oscuro">{_THEME_ICONS}</button>\n'
        f'<script>{reveal_js}</script>\n'
        f'<script>{notes_js}</script>\n'
        f'<script>{_REVEAL_INIT}</script>\n'
        f'<script>{_THEME_SWITCH}</script>\n'
        f'<script>{_IDLE_UI}</script>\n'
    )
