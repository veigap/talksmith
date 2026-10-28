#!/usr/bin/env python3
"""Reference INFERENCE animation: a 3-block pipeline, input -> conv 3x3 -> max-pool 2x2.

Shows the idiom every generated script follows (SKILL.md -> *Writing the generator*): real
numpy computation on a synthetic input, a pure `draw(ax, st)` per state, one caption per stage,
the active block in the accent, exact shapes under every tensor (32 - 3 + 1 = 30, 30 / 2 = 15),
ONE channel of the feature maps labelled as such, and a final frame that is the complete static
diagram. Run it to see the contract's outputs land next to it:

    <python> inference_pipeline.py            # -> inference_pipeline.gif / .png, .critique/…
    <python> inference_pipeline.py --preview  # key frames only, for layout iteration
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT") or
                                os.path.join(os.path.dirname(__file__), "..", "..", ".."),
                                "skills", "animate-diagram"))
from anim_helpers import (Anim, ACCENT, DIV, MUTED, arrow, box, caption, label, tensor,  # noqa: E402
                          window)

# ---- real computation ------------------------------------------------------------------------
N, K, C = 32, 3, 4
yy, xx = np.mgrid[0:N, 0:N]
x = ((np.hypot(xx - 11, yy - 12) < 7) | ((abs(xx - 23) < 5) & (abs(yy - 21) < 6))).astype(float)
kernels = np.array([[[1, 0, -1], [2, 0, -2], [1, 0, -1]],        # vertical edges (shown)
                    [[1, 2, 1], [0, 0, 0], [-1, -2, -1]],        # horizontal edges
                    [[1, 1, 1], [1, 1, 1], [1, 1, 1]],           # blur
                    [[0, 1, 0], [1, -4, 1], [0, 1, 0]]], float)  # laplacian
M = N - K + 1                                                   # 30
conv = np.zeros((M, M, C))
for i in range(M):
    for j in range(M):
        conv[i, j] = (kernels * x[i:i + K, j:j + K]).sum((1, 2))
P = M // 2                                                      # 15
pool = conv.reshape(P, 2, P, 2, C).max((1, 3))
assert conv.shape == (30, 30, 4) and pool.shape == (15, 15, 4)
V = np.abs(conv[..., 0]).max()                                  # one fixed scale for both maps

# ---- layout (px): five columns spread evenly over the canvas, centred --------------------------
S_IN, S_CONV, S_POOL, BW, BH = 320, 300, 150, 190, 110
widths = [S_IN, BW, S_CONV + 18, BW, S_POOL + 18]
gap = (1600 - 2 * 60 - sum(widths)) / 4
xs = [60 + sum(widths[:i]) + gap * i for i in range(5)]
CY = 400
KC = 40                                                         # kernel cell


def draw(ax, st):
    stage = st["stage"]
    # input
    tensor(ax, xs[0], CY - S_IN / 2, S_IN, S_IN, x, shape="32×32×1", cmap="gray_r", vmin=0, vmax=1,
           border=ACCENT if stage == 1 else None)
    label(ax, xs[0] + S_IN / 2, CY - S_IN / 2 - 30, "input", size=21, bold=True)
    # blocks
    for bx, title, sub, live in [(xs[1], "Conv 3×3", "4 filters", 2),
                                 (xs[3], "Max-pool", "2×2, stride 2", 3)]:
        state = "active" if stage == live else ("done" if stage > live else "ghost")
        box(ax, bx, CY - BH / 2, BW, BH, title, sub, state=state)
    # the filter whose channel is shown, with its real weights
    kx, ky = xs[1] + (BW - 3 * KC) / 2, CY + BH / 2 + 50
    tensor(ax, kx, ky, 3 * KC, 3 * KC, kernels[0], cmap=DIV, vmin=-2.5, vmax=2.5)
    for i in range(3):
        for j in range(3):
            v = kernels[0, i, j]
            label(ax, kx + (j + .5) * KC, ky + (i + .5) * KC, f"{v:g}", size=18,
                  color="white" if abs(v) >= 1.5 else None)      # legible on the dark cells
    label(ax, kx + 1.5 * KC, ky + 3 * KC + 26, "filter 1 of 4", size=18, color=MUTED)
    # arrows: input -> conv -> map -> pool -> map, each lit while its stage runs
    ends = [(xs[0] + S_IN, xs[1], 2), (xs[1] + BW, xs[2], 2), (xs[2] + S_CONV + 18, xs[3], 3),
            (xs[3] + BW, xs[4], 3)]
    for a, b, live in ends:
        arrow(ax, [(a + 10, CY), (b - 10, CY)], active=stage == live)
    # conv output (channel 1 of 4), filled row by row; ONE fixed colour scale throughout
    rows = st.get("conv_rows", M if stage > 2 else 0)
    shown = np.full((M, M), np.nan)
    shown[:rows] = conv[:rows, :, 0]
    tensor(ax, xs[2], CY - S_CONV / 2, S_CONV, S_CONV, shown, shape="30×30×4", cmap=DIV,
           vmin=-V, vmax=V, channels=C)
    if stage == 2 and 0 < rows < M:   # the 3×3 window that produced the newest output row
        cell = S_IN / N
        window(ax, xs[0] + st["col"] * cell, CY - S_IN / 2 + (rows - 1) * cell, K * cell, K * cell)
    # pool output
    prow = st.get("pool_rows", P if stage > 3 else 0)
    pshown = np.full((P, P), np.nan)
    pshown[:prow] = pool[:prow, :, 0]
    tensor(ax, xs[4], CY - S_POOL / 2, S_POOL, S_POOL, pshown, shape="15×15×4", cmap=DIV,
           vmin=-V, vmax=V, channels=C)
    if stage == 3 and 0 < prow < P:   # the 2×2 block of the conv map that feeds the newest row
        cell = S_CONV / M
        window(ax, xs[2] + st["col"] * 2 * cell, CY - S_CONV / 2 + (prow - 1) * 2 * cell,
               2 * cell, 2 * cell)
    caption(ax, st["cap"])


anim = Anim(__file__, lang="en")
anim.frame(draw, {"stage": 1, "cap": "Input: a synthetic 32×32 image, 1 channel"}, seconds=1.6, key=True)
cap2 = "Conv 3×3: each output = sum of a 3×3 patch × weights; 4 filters → 30×30×4 (32 − 3 + 1)"
for r in range(1, M + 1):
    anim.frame(draw, {"stage": 2, "conv_rows": r, "col": (r * 7) % (M - 1), "cap": cap2}, seconds=0.1)
anim.frame(draw, {"stage": 2, "conv_rows": M, "cap": cap2}, seconds=1.0, key=True)
cap3 = "Max-pool 2×2: keeps the maximum of each 2×2 block → 15×15×4 (half per side)"
for r in range(1, P + 1):
    anim.frame(draw, {"stage": 3, "pool_rows": r, "col": (r * 4) % P, "cap": cap3}, seconds=0.17)
anim.frame(draw, {"stage": 3, "pool_rows": P, "cap": cap3}, seconds=1.0, key=True)
anim.frame(draw, {"stage": 4, "cap": "32×32×1 → conv 3×3 → 30×30×4 → max-pool 2×2 → 15×15×4"},
           seconds=3.0, key=True)
anim.save()
