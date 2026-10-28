#!/usr/bin/env python3
"""Reference TRAINING animation: a trained head on a frozen encoder, real toy model in numpy.

The full cycle SKILL.md -> *Training animations* asks for, in order, one caption per scene:
data + target -> forward -> loss (formula and value) -> backward (the gradient reaches the
trained weights; the frozen encoder gets none) -> update W <- W - eta*dL/dW -> many fast steps
with a loss curve on a FIXED scale while the prediction map improves. The gradient is checked
against finite differences before anything is drawn, and every colour scale is fixed across
steps, so the gradient strip visibly fades as the loss falls.

    <python> training_loop.py [--preview]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT") or
                                os.path.join(os.path.dirname(__file__), "..", "..", ".."),
                                "skills", "animate-diagram"))
from anim_helpers import (Anim, ACCENT, DIV, INK, MUTED, arrow, box, caption, curve,  # noqa: E402
                          formula, grad_check, label, num, t, tensor, vector)

# ---- real computation: 40 points, frozen random features, logistic head ------------------------
rng = np.random.default_rng(3)
n = 20
ang = rng.uniform(0, np.pi, 2 * n)
X = np.r_[np.c_[np.cos(ang[:n]), np.sin(ang[:n])],
          np.c_[1 - np.cos(ang[n:]), 0.5 - np.sin(ang[n:])]] + rng.normal(0, 0.12, (2 * n, 2))
y = np.r_[np.zeros(n), np.ones(n)]
A, c = rng.normal(0, 1.6, (8, 2)), rng.normal(0, 0.8, 8)       # the frozen encoder
phi = lambda Z: np.tanh(Z @ A.T + c)                            # noqa: E731
F = phi(X)


def loss(w, b=0.0):
    p = 1 / (1 + np.exp(-(F @ w + b)))
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)), p


def grads(w, b):
    L, p = loss(w, b)
    return L, p, F.T @ (p - y) / len(y), np.mean(p - y)


ETA, STEPS = 1.5, 30
w, b = np.zeros(8), 0.0
_, _, gw0, _ = grads(w, b)
grad_check(lambda W: loss(W, b)[0], w, gw0)                    # real gradients or none
hist = []
for k in range(STEPS + 1):
    L, p, gw, gb = grads(w, b)
    hist.append(dict(w=w.copy(), b=b, L=L, gw=gw, p=p))
    w, b = w - ETA * gw, b - ETA * gb
Ls = [h["L"] for h in hist]
assert Ls[-1] < Ls[0]
GMAX = np.abs(hist[0]["gw"]).max()                              # fixed scale: the strip fades
WMAX = max(np.abs(h["w"]).max() for h in hist)
gx = np.linspace(-1.6, 2.6, 70)
gy = np.linspace(-1.2, 1.7, 50)
GX, GY = np.meshgrid(gx, gy)
GRID = phi(np.c_[GX.ravel(), GY.ravel()])

# ---- layout (px) ---------------------------------------------------------------------------------
CY = 400
DX, DY, DW, DH = 60, CY - 180, 380, 300                          # data / prediction panel
ENC, HEAD, LOSS = (500, 220), (800, 220), (1080, 200)            # (x, width) of each block
BY, BH = CY - 60, 120


def to_px(P):
    return (DX + (P[:, 0] - gx[0]) / (gx[-1] - gx[0]) * DW,
            DY + (gy[-1] - P[:, 1]) / (gy[-1] - gy[0]) * DH)


def draw(ax, st):
    s, h = st["scene"], hist[st.get("k", 0)]
    # data panel: the target classes, and (from the forward pass on) the prediction map p(x)
    if s >= 2:
        pm = 1 / (1 + np.exp(-(GRID @ h["w"] + h["b"]))).reshape(GY.shape)[::-1]
        tensor(ax, DX, DY, DW, DH, pm, cmap=DIV, vmin=0, vmax=1, interp="bilinear", alpha=0.55)
    else:
        tensor(ax, DX, DY, DW, DH, np.full((2, 2), 0.5), cmap=DIV, vmin=0, vmax=1)
    px, py = to_px(X)
    ax.scatter(px, py, s=70, c=[ACCENT if v else INK for v in y], edgecolors="white",
               linewidths=1.5, zorder=8)
    label(ax, DX + DW / 2, DY - 30, "40 points, target class 0 / 1", size=20, bold=True)
    label(ax, DX + DW / 2, DY + DH + 28, "background: predicted p(class 1)" if s >= 2 else " ",
          size=18, color=MUTED)
    # blocks: the encoder is frozen, the head is trained
    box(ax, ENC[0], BY, ENC[1], BH, "encoder", "φ = tanh(Ax + c)", state="frozen")
    box(ax, HEAD[0], BY, HEAD[1], BH, "head", "p = σ(w·φ + b)",
        state="active" if s in (2, 5) else "trained")
    box(ax, LOSS[0], BY, LOSS[1], BH, "loss", f"L = {num(h['L'])}" if s >= 3 else " ",
        state="active" if s == 3 else ("done" if s > 3 else "ghost"))
    # forward arrows
    fwd = s == 2
    arrow(ax, [(DX + DW + 10, CY), (ENC[0] - 10, CY)], active=fwd)
    arrow(ax, [(ENC[0] + ENC[1] + 10, CY), (HEAD[0] - 10, CY)], active=fwd)
    arrow(ax, [(HEAD[0] + HEAD[1] + 10, CY), (LOSS[0] - 10, CY)], active=fwd)
    label(ax, (ENC[0] + ENC[1] + HEAD[0]) / 2, CY - 26, "φ (8)", size=18, color=MUTED)
    # the weights of the head, on a fixed scale
    vector(ax, HEAD[0] + (HEAD[1] - 8 * 22) / 2, BY + BH + 34, h["w"], cell=22, horizontal=True,
           vmin=-WMAX, vmax=WMAX, shape="w (8)")
    if s >= 4:   # backward: dL/dw travels from the loss back to the head — and stops there
        gk = hist[st.get("k", 0)]["gw"]
        gxp = HEAD[0] + (HEAD[1] - 8 * 22) / 2
        vector(ax, gxp, BY - 70, gk, cell=22, horizontal=True, vmin=-GMAX, vmax=GMAX)
        label(ax, gxp + 4 * 22, BY - 96, "∂L/∂w", size=20, bold=True, color=ACCENT)
        arrow(ax, [(LOSS[0] + LOSS[1] / 2, BY - 10), (LOSS[0] + LOSS[1] / 2, BY - 59),
                   (gxp + 8 * 22 + 12, BY - 59)], active=s == 4)
        label(ax, ENC[0] + ENC[1] / 2, BY + BH + 46, "no gradient: not updated", size=18,
              color=MUTED)
    # the loss and the update rule, written out
    if s >= 3:
        formula(ax, 830, 640, r"$L = -\frac{1}{40}\sum\,[\,y\,\log p + (1-y)\log(1-p)\,]$",
                size=22, color=ACCENT if s == 3 else INK)
    if s >= 5:
        formula(ax, 830, 712, r"$w \leftarrow w - \eta\,\partial L/\partial w,\ \ \eta = 1.5$",
                size=22, color=ACCENT if s == 5 else INK)
    # loss curve, fixed scale, in the corner
    if s >= 3:
        curve(ax, 1340, BY, 200, BH + 40, Ls, n=st.get("k", 0) + 1, vmax=Ls[0] * 1.05)
        label(ax, 1540, BY + BH + 66, f"{t('step')} {st.get('k', 0)}", size=18, ha="right",
              color=MUTED)
    caption(ax, st["cap"])


anim = Anim(__file__, lang="en")
anim.frame(draw, {"scene": 1, "cap": "Training data: 40 points in 2D, each with its target class"},
           seconds=1.8, key=True)
anim.frame(draw, {"scene": 2, "cap": "Forward: frozen encoder φ(x) → head p = σ(w·φ + b), "
                                     "with w = 0 at the start"}, seconds=2.0, key=True)
anim.frame(draw, {"scene": 3, "cap": f"Loss: binary cross-entropy over the 40 points, "
                                     f"L = {num(Ls[0])}"}, seconds=2.0, key=True)
anim.frame(draw, {"scene": 4, "cap": "Backward: ∂L/∂w = mean((p − y)·φ) reaches the head; "
                                     "the encoder receives no update"}, seconds=2.2, key=True)
anim.frame(draw, {"scene": 5, "k": 1, "cap": "Update: w ← w − η·∂L/∂w (one step)"},
           seconds=1.6, key=True)
for k in range(2, STEPS + 1):
    anim.frame(draw, {"scene": 6, "k": k,
                      "cap": f"Repeat for {STEPS} steps: L falls from {num(Ls[0])} to "
                             f"{num(Ls[-1])} (toy model in numpy)"},
               seconds=0.16, key=k == STEPS)
anim.hold(3.0)
anim.save()
