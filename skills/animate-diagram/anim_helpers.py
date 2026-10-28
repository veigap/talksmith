#!/usr/bin/env python3
"""Reusable helpers for `talksmith:animate-diagram` generator scripts.

A generator script (written per diagram into `talks/<Talk>/images/.anim/<stem>.py`) imports this
module, draws each frame as a pure function of a state, and hands the frames to `Anim`, which
enforces the animation contract in [`SKILL.md`](SKILL.md) — canvas, timing, final-frame hold,
size cap, palette — and writes every output:

    images/<stem>.gif                     the animation (loops)
    images/<stem>.png                     the final frame = the complete static diagram
    images/.critique/<stem>.frames/NN.png sampled frames for the blind critic
    images/.critique/<stem>.png           contact sheet of those frames

Coordinates are pixels on a 1600×900 canvas, origin top-left, y down. The palette is read from
`config/diagram-style.md` (its sole owner), never restated here.

CLI:
    python3 anim_helpers.py --check                    # deps, font, palette
    python3 anim_helpers.py frames <gif> -o <dir>      # sample frames out of any GIF

Needs numpy, matplotlib and Pillow (see `find_python.py` for locating an interpreter with them).
"""
from __future__ import annotations

import logging
import math
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, to_rgb  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, Arc  # noqa: E402
from PIL import Image  # noqa: E402

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent.parent
STYLE_MD = PLUGIN_ROOT / "config" / "diagram-style.md"

# ── the contract (SKILL.md → *Animation contract* is the prose owner of these numbers) ──────────
W, H, DPI = 1600, 900, 100
FPS = 12
FINAL_HOLD_S = 3.0
CYCLE_MIN_S, CYCLE_MAX_S = 12.0, 20.0
MAX_BYTES = 5_000_000
MIN_PT = 18                 # 18 pt at 100 dpi = 25 px at 1600 wide = 20 px at 1280 wide
CAPTION_Y = 845
MARGIN_MIN, MARGIN_MAX = 30, 140

# ── palette: parsed from diagram-style.md ───────────────────────────────────────────────────────
# Most specific first: the ground's row also mentions "the accent red".
_ROLE_KEYS = (("slide ground", "ground"), ("hairline", "rule"), ("code", "code"),
              ("callout", "callout"), ("pill", "pill"), ("card fill", "fill"),
              ("body text", "ink"), ("titles", "title"), ("accent", "accent"))
_FALLBACK = {"accent": "#DA1B2E", "title": "#1F1E1E", "ink": "#3B3535", "fill": "#F2EEEE",
             "pill": "#F9D2D6", "callout_pink": "#F7BBC1", "callout_blue": "#B8E6F5",
             "code": "#F2F2F2", "rule": "#D8D2CE", "ground": "#FFFFFF"}
_ROW = re.compile(r"^\|\s*`(#[0-9A-Fa-f]{6})`(?:\s*/\s*`(#[0-9A-Fa-f]{6})`)?\s*\|\s*(.+?)\s*\|\s*$")


def load_palette(path: Path = STYLE_MD) -> tuple[dict[str, str], list[str]]:
    """`(palette, missing_keys)` from the deck-palette table in diagram-style.md."""
    pal: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    for line in text.splitlines():
        m = _ROW.match(line.strip())
        if not m:
            continue
        hex1, hex2, role = m.group(1).upper(), m.group(2), m.group(3).lower()
        for needle, key in _ROLE_KEYS:
            if needle in role:
                if key == "callout":
                    pal["callout_pink"] = hex1
                    if hex2:
                        pal["callout_blue"] = hex2.upper()
                else:
                    pal.setdefault(key, hex1)
                break
    missing = [k for k in _FALLBACK if k not in pal]
    for k in missing:
        pal[k] = _FALLBACK[k]
    return pal, missing


PAL, PALETTE_MISSING = load_palette()
ACCENT, TITLE, INK, FILL = PAL["accent"], PAL["title"], PAL["ink"], PAL["fill"]
PILL, RULE, GROUND = PAL["pill"], PAL["rule"], PAL["ground"]
CALLOUT_PINK, CALLOUT_BLUE = PAL["callout_pink"], PAL["callout_blue"]


def mix(c1: str, c2: str, t: float) -> tuple[float, float, float]:
    """Blend two palette colours (t=0 → c1, t=1 → c2). Neutral greys are made this way, so
    nothing off-palette enters the drawing."""
    a, b = np.array(to_rgb(c1)), np.array(to_rgb(c2))
    return tuple(a + (b - a) * float(np.clip(t, 0, 1)))


MUTED = mix(INK, GROUND, 0.45)          # idle arrows, ghosted labels
SEQ = LinearSegmentedColormap.from_list("ts_seq", [GROUND, PILL, ACCENT])
DIV = LinearSegmentedColormap.from_list("ts_div", [INK, GROUND, ACCENT])

# ── type ────────────────────────────────────────────────────────────────────────────────────────


def _resolve_family() -> str:
    for fam in ("Helvetica", "Arial", "Liberation Sans", "Nimbus Sans", "DejaVu Sans"):
        try:
            font_manager.findfont(fam, fallback_to_default=False)
            return fam
        except Exception:
            continue
    return "DejaVu Sans"


FAMILY = _resolve_family()
plt.rcParams.update({
    # DejaVu behind the chosen face: matplotlib falls back per glyph, and DejaVu draws the
    # symbols captions need (Σ, ∂, η, ←, ×) that Helvetica-likes may lack.
    "font.family": [FAMILY, "DejaVu Sans"],
    "font.size": 20,
    "mathtext.fontset": "dejavusans",
    "figure.facecolor": GROUND,
    "axes.facecolor": GROUND,
    "text.color": INK,
})

# ── language ────────────────────────────────────────────────────────────────────────────────────
_TXT = {
    "es": {"trained": "se entrena", "frozen": "congelado", "channels": "1 de {c} canales",
           "loss": "pérdida", "step": "paso", "toy": "modelo de juguete en numpy",
           "simulated": "predicción simulada", "decimal": ","},
    "en": {"trained": "trained", "frozen": "frozen", "channels": "1 of {c} channels",
           "loss": "loss", "step": "step", "toy": "toy model in numpy",
           "simulated": "simulated prediction", "decimal": "."},
}
# A caption says which operation is applied and what changes — never what a model "wants".
_ANTHRO = {
    "es": r"\b(pide|piden|sabe|saben|entiende|entienden|mira|miran|quiere|quieren|consulta|"
          r"consultan|escribe|escriben|piensa|piensan|decide|deciden|cree|creen|busca|buscan)\b",
    "en": r"\b(asks?|knows?|understands?|looks?|wants?|consults?|writes?|thinks?|decides?|"
          r"believes?|searches)\b",
}
LANG = "es"
_WARN: list[str] = []


def set_lang(lang: str) -> str:
    """Accept `es`, `Spanish`, `español`, `en`, `English`… Unknown → English, with a warning."""
    global LANG
    l = (lang or "").strip().lower()
    LANG = "es" if l.startswith(("es", "span")) else "en"
    if LANG == "en" and not l.startswith(("en", "ing")):
        _WARN.append(f"language {lang!r} has no built-in strings; using English for badges")
    return LANG


def t(key: str, **kw) -> str:
    """A localized fixed string (badges, `1 de C canales`, …)."""
    return _TXT[LANG][key].format(**kw)


def num(x: float, nd: int = 2) -> str:
    """A number in the presentation language's decimal convention (`0,05` in Spanish)."""
    s = f"{x:.{nd}f}"
    return s.replace(".", _TXT[LANG]["decimal"])


# ── canvas ──────────────────────────────────────────────────────────────────────────────────────


def canvas():
    """A fresh 1600×900 white figure whose axes are pixel coordinates (y down)."""
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    return fig, ax


def capture(fig) -> Image.Image:
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())


# ── primitives ──────────────────────────────────────────────────────────────────────────────────


def label(ax, x, y, s, size=20, color=None, bold=False, ha="center", va="center", z=6, **kw):
    """Text, never below the legibility floor (MIN_PT); a smaller request is raised and counted."""
    if size < MIN_PT:
        _WARN.append(f"label {str(s)[:30]!r} asked for {size} pt — raised to {MIN_PT} pt")
        size = MIN_PT
    return ax.text(x, y, s, fontsize=size, color=color or INK, ha=ha, va=va, zorder=z,
                   fontweight="bold" if bold else "normal", **kw)


def caption(ax, s, size=22):
    """The one-line stage caption at the bottom: which operation is applied, what changes."""
    m = re.search(_ANTHRO[LANG], s, re.IGNORECASE)
    if m:
        _WARN.append(f"caption anthropomorphizes ({m.group(0)!r}): {s!r}")
    return label(ax, W / 2, CAPTION_Y, s, size=size, color=INK)


def halo(ax, x, y, w, h, r=14):
    for pad, al in ((14, 0.35), (7, 0.6)):
        ax.add_patch(FancyBboxPatch((x - pad, y - pad), w + 2 * pad, h + 2 * pad,
                                    boxstyle=f"round,pad=0,rounding_size={r + pad}",
                                    fc=PILL, ec="none", alpha=al, zorder=1))


def box(ax, x, y, w, h, title=None, sub=None, state="idle", r=12, title_size=22, sub_size=19,
        fc=None):
    """A labelled block. `state`:
    idle    — neutral fill, hairline border (not reached yet, or plain);
    active  — accent border + halo + accent title (the operation applied in this stage);
    done    — neutral fill, ink border (already applied);
    ghost   — white, faint border and text (layout shown ahead of the data);
    trained — accent border + "se entrena" badge (training animations);
    frozen  — neutral, hairline border, lock + "congelado" badge (training animations).
    """
    styles = {
        "idle": (FILL, RULE, 2.0, INK),
        "active": ("white", ACCENT, 3.6, ACCENT),
        "done": (FILL, INK, 2.0, INK),
        "ghost": ("white", RULE, 1.6, MUTED),
        "trained": (FILL, ACCENT, 3.2, INK),
        "frozen": (FILL, RULE, 2.0, INK),
    }
    f, e, lw, tc = styles[state]
    if state == "active":
        halo(ax, x, y, w, h, r)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc or f, ec=e, lw=lw, zorder=2))
    cy = y + h / 2
    if title and sub:
        label(ax, x + w / 2, cy - title_size * 0.75, title, size=title_size, bold=True, color=tc)
        label(ax, x + w / 2, cy + sub_size * 0.95, sub, size=sub_size, color=MUTED if state == "ghost" else INK)
    elif title:
        label(ax, x + w / 2, cy, title, size=title_size, bold=True, color=tc)
    if state == "trained":
        badge(ax, x + w, y, "trained")
    elif state == "frozen":
        badge(ax, x + w, y, "frozen")


def badge(ax, x_right, y_top, kind):
    """`se entrena` (accent) or lock + `congelado` (ink), sitting on a block's top edge."""
    txt = t(kind)
    col = ACCENT if kind == "trained" else INK
    w = 14 * len(txt) + (58 if kind == "frozen" else 30)
    x0, y0, h = x_right - w - 10, y_top - 20, 40
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=20",
                                fc="white", ec=col, lw=2.0, zorder=7))
    if kind == "frozen":
        lock(ax, x0 + 24, y0 + h / 2 + 2, 20, color=INK)
        label(ax, x0 + 44, y0 + h / 2, txt, size=MIN_PT, color=col, ha="left", z=8)
    else:
        label(ax, x0 + w / 2, y0 + h / 2, txt, size=MIN_PT, color=col, bold=True, z=8)


def lock(ax, x, y, s=20, color=None):
    """A padlock drawn as geometry (never a glyph), centred at (x, y)."""
    c = color or INK
    ax.add_patch(Rectangle((x - s * 0.5, y - s * 0.15), s, s * 0.75, fc=c, ec=c, zorder=9))
    ax.add_patch(Arc((x, y - s * 0.15), s * 0.7, s * 0.9, theta1=180, theta2=360,
                     ec=c, lw=2.2, zorder=9))


def arrow(ax, pts, active=False, lw=2.4, color=None, z=3):
    """A polyline arrow through `pts` [(x, y), …], head on the last segment. Route around blocks
    and labels with intermediate points (or through a `node`), never across them."""
    col = color or (ACCENT if active else MUTED)
    lw = 3.4 if active else lw
    xs, ys = zip(*pts)
    if len(pts) > 2:
        ax.plot(xs[:-1], ys[:-1], color=col, lw=lw, zorder=z, solid_capstyle="butt")
    ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=z,
                arrowprops=dict(arrowstyle="-|>,head_length=0.7,head_width=0.4", color=col,
                                lw=lw, shrinkA=0, shrinkB=0))


def window(ax, x, y, w, h, color=None, lw=3.0):
    """An outlined window on a tensor — the kernel, the pooling block, the receptive field being
    read in this frame. Accent by default: it is the thing the eye should follow."""
    ax.add_patch(Rectangle((x, y), w, h, fc="none", ec=color or ACCENT, lw=lw, zorder=7))


def node(ax, x, y, text="Σ", r=24, active=False):
    """A small junction (Σ, ⊕, ×) — where several inputs meet before one block, so their lines
    end on the node instead of crossing each other or a label."""
    ax.add_patch(Circle((x, y), r, fc="white", ec=ACCENT if active else INK, lw=2.4, zorder=5))
    label(ax, x, y, text, size=max(MIN_PT, int(r * 0.9)), color=ACCENT if active else INK, z=6)


def tensor(ax, x, y, w, h, arr, shape=None, cmap="gray", vmin=None, vmax=None, channels=None,
           border=None, interp="nearest", label_size=19, alpha=1.0):
    """An array drawn in a pixel rectangle, with its exact shape under it.

    `channels=C` draws a stack behind the face and labels it `1 de C canales`: an intermediate
    feature map is ONE channel of many, never the input image shrunk. Pass fixed `vmin`/`vmax`
    whenever the same quantity is shown across steps, so the colour scale does not re-normalize
    from frame to frame."""
    if channels and channels > 1:
        for k in (2, 1):
            ax.add_patch(Rectangle((x + 9 * k, y - 9 * k), w, h, fc=FILL, ec=RULE, lw=1.5,
                                   zorder=3))
    a = np.asarray(arr)
    ax.imshow(a, extent=(x, x + w, y + h, y), interpolation=interp, zorder=4, aspect="auto",
              cmap=cmap if a.ndim == 2 else None, vmin=vmin, vmax=vmax, alpha=alpha)
    ax.add_patch(Rectangle((x, y), w, h, fc="none", ec=border or INK, lw=1.6, zorder=5))
    ty = y + h + 24
    if shape:
        label(ax, x + w / 2, ty, shape, size=label_size)
        ty += 30
    if channels and channels > 1:
        label(ax, x + w / 2, ty, t("channels", c=channels), size=MIN_PT, color=MUTED)


def vector(ax, x, y, vals, cell=18, horizontal=False, cmap=None, vmin=-1, vmax=1, shape=None):
    """A pulled-out vector (one position's values through the channels = that region's
    embedding), as a strip of cells."""
    cm = plt.get_cmap(cmap) if isinstance(cmap, str) else (cmap or DIV)
    for i, v in enumerate(np.asarray(vals).ravel()):
        c = cm((float(v) - vmin) / (vmax - vmin + 1e-12))
        cx, cy = (x + i * cell, y) if horizontal else (x, y + i * cell)
        ax.add_patch(Rectangle((cx, cy), cell, cell, fc=c, ec="white", lw=1.0, zorder=5))
    n = len(np.asarray(vals).ravel())
    ww, hh = (cell * n, cell) if horizontal else (cell, cell * n)
    ax.add_patch(Rectangle((x, y), ww, hh, fc="none", ec=INK, lw=1.4, zorder=6))
    if shape:
        label(ax, x + ww / 2, y + hh + 22, shape, size=MIN_PT)


def curve(ax, x, y, w, h, values, n=None, vmax=None, title=None):
    """A small loss curve in a corner, drawn on a FIXED scale (`vmax`) so the drop is real."""
    vals = list(values)[: (len(values) if n is None else n)]
    vmax = vmax or (max(values) if len(values) else 1.0)
    ax.plot([x, x, x + w], [y, y + h, y + h], color=INK, lw=1.8, zorder=4)
    if title is None:
        title = t("loss")
    label(ax, x, y - 18, title, size=MIN_PT, ha="left", color=MUTED)
    if not vals:
        return
    total = max(len(values) - 1, 1)
    xs = [x + w * k / total for k in range(len(vals))]
    ys = [y + h - h * min(v, vmax) / vmax for v in vals]
    ax.plot(xs, ys, color=ACCENT, lw=2.6, zorder=5)
    ax.plot(xs[-1:], ys[-1:], "o", color=ACCENT, ms=8, zorder=6)


def formula(ax, x, y, tex, size=24, color=None, **kw):
    """A formula in mathtext (`r"$\\mathcal{L} = -\\log p$"`)."""
    return label(ax, x, y, tex, size=size, color=color, **kw)


def ease(u: float) -> float:
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def grad_check(loss_fn, W, grad, n=4, eps=1e-6, tol=1e-5, seed=0) -> float:
    """Compare an analytic gradient with central finite differences at `n` random entries of W.
    Raises if they disagree: a training animation draws real gradients or none."""
    rng = np.random.default_rng(seed)
    worst = 0.0
    for _ in range(n):
        idx = tuple(int(rng.integers(0, s)) for s in W.shape)
        Wp, Wm = W.copy(), W.copy()
        Wp[idx] += eps
        Wm[idx] -= eps
        numg = (loss_fn(Wp) - loss_fn(Wm)) / (2 * eps)
        err = abs(numg - grad[idx]) / max(1.0, abs(numg))
        worst = max(worst, err)
        if err > tol:
            raise AssertionError(f"gradient check failed at {idx}: numeric {numg} vs analytic {grad[idx]}")
    return worst


# ── GIF assembly ────────────────────────────────────────────────────────────────────────────────


def _hex_rgb(h: str) -> np.ndarray:
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)])


def _quantize(frames: list[Image.Image], colors: int) -> list[Image.Image]:
    """One shared palette for every frame (median cut over a sample), the brand colours pinned
    exactly, and a 5-bit LUT for speed — with exact matches for the pinned colours, so white
    stays pure white and the accent stays the accent."""
    sample = frames[:: max(1, len(frames) // 8)] + [frames[-1]]
    hw, hh = W // 2, H // 2               # NEAREST keeps every colour exact, at a quarter the cost
    mosaic = Image.new("RGB", (hw, hh * len(sample)))
    for i, f in enumerate(sample):
        mosaic.paste(f.resize((hw, hh), Image.NEAREST), (0, hh * i))
    pal = np.array(mosaic.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
                   .getpalette()[: 3 * colors]).reshape(-1, 3)
    pinned = [_hex_rgb(c) for c in dict.fromkeys((GROUND, INK, TITLE, ACCENT, FILL, RULE))]
    used: set[int] = set()
    slots = []
    for c in pinned:
        k = next(int(k) for k in np.argsort(((pal - c) ** 2).sum(1)) if int(k) not in used)
        pal[k] = c
        used.add(k)
        slots.append((int(c[0]) << 16 | int(c[1]) << 8 | int(c[2]), k))
    pal = pal.astype(np.int32)
    g = np.arange(32) * 8 + 4
    grid = np.stack(np.meshgrid(g, g, g, indexing="ij"), -1).reshape(-1, 3)
    lut = ((grid[:, None, :] - pal[None]) ** 2).sum(2).argmin(1).astype(np.uint8)
    flat = [int(v) for v in pal.ravel()]
    out = []
    for f in frames:
        a = np.asarray(f, dtype=np.uint8).astype(np.int32)
        r, gg, b = a[..., 0], a[..., 1], a[..., 2]
        idx = lut[((r >> 3) << 10) | ((gg >> 3) << 5) | (b >> 3)]
        key = (r << 16) | (gg << 8) | b
        for kc, k in slots:
            idx[key == kc] = k
        p = Image.fromarray(idx, "P")
        p.putpalette(flat)
        out.append(p)
    return out


def sample_indices(n_frames: int, keys: list[int], limit: int = 5) -> list[int]:
    """First frame, up to `limit-2` key frames spread evenly, last frame."""
    inner = [k for k in keys if 0 < k < n_frames - 1]
    room = max(0, limit - 2)
    if len(inner) > room:
        inner = [inner[round(i * (len(inner) - 1) / max(room - 1, 1))] for i in range(room)] if room else []
    return sorted(set([0] + inner + [n_frames - 1]))


def write_critique(frames: list[Image.Image], idxs: list[int], frames_dir: Path, sheet: Path) -> list[Path]:
    """The sampled frames at full size plus a 2-column contact sheet."""
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for n, i in enumerate(idxs, 1):
        p = frames_dir / f"{n:02d}.png"
        frames[i].save(p, optimize=True)
        paths.append(p)
    cw, ch = W // 2, H // 2
    rows = math.ceil(len(idxs) / 2)
    sh = Image.new("RGB", (cw * 2 + 12, rows * (ch + 12)), "white")
    for n, i in enumerate(idxs):
        th = frames[i].resize((cw, ch), Image.LANCZOS)
        sh.paste(th, ((n % 2) * (cw + 12), (n // 2) * (ch + 12)))
    sheet.parent.mkdir(parents=True, exist_ok=True)
    sh.save(sheet, optimize=True)
    return paths


def layout_audit(img: Image.Image) -> list[str]:
    """Mechanical check of the final frame's ink extent: nothing cut at an edge, margins in
    range, content centred, the canvas actually used. (The eye judges balance; this catches the
    cases an eye forgives at a glance.)"""
    a = np.asarray(img.convert("L"))
    ink = np.argwhere(a < 245)
    if not len(ink):
        return ["final frame is blank"]
    y0, x0 = ink.min(0)
    y1, x1 = ink.max(0)
    left, right, top, bottom = x0, W - 1 - x1, y0, H - 1 - y1
    out = []
    for name, m in (("left", left), ("right", right), ("top", top), ("bottom", bottom)):
        if m < MARGIN_MIN:
            out.append(f"ink reaches within {m}px of the {name} edge (keep 40-60px) — something may be cut")
    if max(left, right) > MARGIN_MAX:
        out.append(f"horizontal margins {left}px / {right}px — content off-centre or canvas under-used")
    if abs(left - right) > 90:
        out.append(f"content off-centre: left margin {left}px vs right {right}px")
    return out


class Anim:
    """One animation. Draw frames with `frame(draw, state, seconds)`, then `save()`.

    `draw(ax, state)` paints the WHOLE scene for one state on a fresh canvas — frames are pure
    functions of their state, so any frame can be re-rendered alone. Mark the end of each stage
    `key=True`: key frames are what the blind critic is shown.

    Paths derive from the script's own location (`images/.anim/<stem>.py`), so a copied script
    writes under its new stem. `--preview` on the script's command line renders only the key
    frames and the final one (fast layout iteration; no GIF).
    """

    def __init__(self, script: str, lang: str = "es", fps: int = FPS, colors: int = 64):
        p = Path(script).resolve()
        images = p.parent.parent if p.parent.name == ".anim" else p.parent
        self.stem = p.stem
        self.gif = images / f"{self.stem}.gif"
        self.png = images / f"{self.stem}.png"
        self.frames_dir = images / ".critique" / f"{self.stem}.frames"
        self.sheet = images / ".critique" / f"{self.stem}.png"
        self.fps, self.colors = fps, colors
        self.preview = "--preview" in sys.argv
        set_lang(lang)
        self._frames: list[Image.Image] = []
        self._durs: list[int] = []
        self._keys: list[int] = []
        self._lazy = None

    def _draw(self, draw, state) -> Image.Image:
        fig, ax = canvas()
        draw(ax, state)
        img = capture(fig)
        plt.close(fig)
        return img

    def frame(self, draw, state=None, seconds: float | None = None, key: bool = False) -> None:
        ms = int(round(1000 * (seconds if seconds is not None else 1 / self.fps)))
        if self.preview and not key:
            self._lazy = (draw, state, ms)
            return
        self._lazy = None
        self._frames.append(self._draw(draw, state))
        self._durs.append(ms)
        if key:
            self._keys.append(len(self._frames) - 1)

    def tween(self, draw, state_at, seconds: float, key_end: bool = False) -> None:
        """`round(seconds·fps)` frames, `state_at(u)` with u eased from 0 to 1."""
        n = max(2, int(round(seconds * self.fps)))
        for i in range(n):
            self.frame(draw, state_at(ease(i / (n - 1))), key=key_end and i == n - 1)

    def hold(self, seconds: float) -> None:
        """Extend the last frame (a pause at the end of a stage)."""
        if self._lazy is not None:
            d, s, ms = self._lazy
            self._lazy = (d, s, ms + int(seconds * 1000))
        elif self._durs:
            self._durs[-1] += int(seconds * 1000)

    def save(self) -> dict:
        if self._lazy is not None:                  # preview: the final frame is always drawn
            d, s, ms = self._lazy
            self._frames.append(self._draw(d, s))
            self._durs.append(ms)
        if not self._frames:
            raise SystemExit("anim: no frames drawn")
        frames, durs = self._frames, list(self._durs)
        warns = list(dict.fromkeys(_WARN))
        if PALETTE_MISSING:
            warns.append(f"palette keys not found in diagram-style.md, defaults used: {PALETTE_MISSING}")
        if any(f.size != (W, H) for f in frames):
            raise SystemExit(f"anim: every frame must be {W}x{H}")
        warns += layout_audit(frames[-1])
        idxs = sample_indices(len(frames), self._keys)
        crit = write_critique(frames, idxs, self.frames_dir, self.sheet)
        if self.preview:
            print(f"preview: {self.frames_dir} · frames: {len(crit)} · warnings: {'; '.join(warns) or 'none'}")
            return {"preview": True, "frames": [str(p) for p in crit], "warnings": warns}

        durs[-1] = max(durs[-1], int(FINAL_HOLD_S * 1000))
        cycle = sum(durs) / 1000
        if not CYCLE_MIN_S <= cycle <= CYCLE_MAX_S:
            warns.append(f"cycle is {cycle:.1f}s — the contract is {CYCLE_MIN_S:.0f}-{CYCLE_MAX_S:.0f}s")
        keys = set(self._keys) | {0, len(frames) - 1}
        colors = self.colors
        # Written to a temporary sibling and renamed into place: a run cut short (a killed
        # session, a full disk) once left several GIFs at 0 bytes under their real names, which
        # every later pass took for finished renders. A rename is all-or-nothing, so the
        # deliverable is either the previous complete file or the new complete one.
        tmp_gif = self.gif.with_name(f".{self.gif.name}.tmp")
        while True:
            pal = _quantize(frames, colors)
            pal[0].save(tmp_gif, format="GIF", save_all=True, append_images=pal[1:], duration=durs,
                        loop=0, optimize=True, disposal=1)
            size = tmp_gif.stat().st_size
            if size <= MAX_BYTES:
                break
            if colors > 32:
                colors = max(32, colors - 16)
                continue
            if len(frames) < 8:
                warns.append(f"GIF is {size / 1e6:.1f} MB, over the {MAX_BYTES / 1e6:.0f} MB cap")
                break
            # drop every other non-key frame, folding its time into the one before it
            nf, nd, nk = [frames[0]], [durs[0]], {0}
            for i in range(1, len(frames)):
                if i in keys or i % 2 == 0:
                    if i in keys:
                        nk.add(len(nf))
                    nf.append(frames[i])
                    nd.append(durs[i])
                else:
                    nd[-1] += durs[i]
            frames, durs, keys = nf, nd, nk
            warns.append("GIF over the size cap: frame rate halved on transitions")
        tmp_png = self.png.with_name(f".{self.png.name}.tmp")
        frames[-1].save(tmp_png, format="PNG", optimize=True)
        os.replace(tmp_gif, self.gif)
        os.replace(tmp_png, self.png)
        report = {"gif": str(self.gif), "png": str(self.png), "frames": len(frames),
                  "cycle_s": round(cycle, 1), "size_mb": round(self.gif.stat().st_size / 1e6, 2),
                  "critique_frames": [str(p) for p in crit], "contact_sheet": str(self.sheet),
                  "warnings": warns}
        # The skill's return line, verbatim (SKILL.md → *Caller contract*).
        print(f"animated: {self.gif} · png: {self.png} · critique_frames: {self.frames_dir} · "
              f"contact_sheet: {self.sheet} · cycle_s: {report['cycle_s']} · "
              f"size_mb: {report['size_mb']} · warnings: {'; '.join(warns) or 'none'}")
        return report


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────


def gif_frames(gif: Path) -> tuple[list[Image.Image], list[int]]:
    im = Image.open(gif)
    frames, durs = [], []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        frames.append(im.convert("RGB"))
        durs.append(int(im.info.get("duration", 0)))
    return frames, durs


def _cli(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="anim_helpers")
    ap.add_argument("--check", action="store_true", help="report deps, font and palette")
    sub = ap.add_subparsers(dest="cmd")
    fr = sub.add_parser("frames", help="sample critique frames out of a GIF")
    fr.add_argument("gif")
    fr.add_argument("-o", "--out", required=True, help="directory for NN.png (+ contact sheet beside it)")
    fr.add_argument("--n", type=int, default=5)
    a = ap.parse_args(argv)
    if a.check:
        print(f"ok: numpy {np.__version__}, matplotlib {matplotlib.__version__}, Pillow "
              f"{Image.__version__} ({sys.executable})")
        print(f"font: {FAMILY}")
        print(f"palette: {'complete' if not PALETTE_MISSING else 'defaults for ' + ', '.join(PALETTE_MISSING)} "
              f"(from {STYLE_MD})")
        return 0
    if a.cmd == "frames":
        frames, durs = gif_frames(Path(a.gif))
        # the longest-held frames are where stages end
        holds = sorted(sorted(range(len(durs)), key=lambda i: -durs[i])[: max(0, a.n - 2)])
        idxs = sample_indices(len(frames), holds, a.n)
        out = Path(a.out)
        for p in write_critique(frames, idxs, out, out.with_suffix(".png")):
            print(p)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
