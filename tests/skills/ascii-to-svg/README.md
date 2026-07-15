# `ascii-to-svg` / `polish-ascii` fixture

The visual reference for the **Step-6 Polish pipeline**, the way
[`tests/skills/md-to-deck/`](../md-to-deck/) is the reference for the HTML render.

`final.md` is a fixture Talk: nine slides, each lifted **verbatim** — art, prose and
speaker notes — out of a production Talk in a separate working directory. Nothing here is
synthetic. Hand-written ASCII has a texture that invented fixtures don't (ragged columns,
mixed box-drawing styles, labels that nearly collide), and that texture is what the render
and critique loop actually has to survive.

One slide per section, so each block gets a stable `sN-1-1` id that won't renumber when a
slide is added.

## What each block is here to exercise

| id | source | shape | why it's in the set |
|---|---|---|---|
| `s1-1-1` | hiperparametros-ai · `s3-2-1` | 63×4 · ~7.9:1 | Widest, thinnest art. The frame is easy to over-declare — prime aspect-audit bait. |
| `s2-1-1` | claude-cowork · `s2-3-1` | 72×5 · ~7.2:1 | Wide left-to-right flow; arrows that have to *land* on their target. |
| `s3-1-1` | claude-cowork · `s5-3-1` | 70×6 · ~5.8:1 | **No `ascii-note`** → the sparse-context path. Also a **legacy-tagged fence**, so it exercises the heuristic detection rule rather than the canonical ` ```ascii ` tag. |
| `s4-1-1` | seguridad-governance-ai · `sc-4-1` | 57×6 · ~4.8:1 | From the 2026-07-15 production run. |
| `s5-1-1` | seguridad-governance-ai · `s1-10-1` | 55×9 · ~3.1:1 | The block whose production render declared `viewBox="0 0 680 295"` (2.30:1) around art that wanted ~2.91:1 — and that day's visual critique passed it clean, correctly, since a PNG rasterizes *from* the viewBox and cannot reveal it. It reached the PPTX audit a full render cycle later. **This slide is not a regression test for that** — see the warning below. |
| `s6-1-1` | claude-cowork · `s7-3-1` | 99×15 · ~3.3:1 | Widest lines in the set; dense two-panel layout. |
| `s7-1-1` | seguridad-governance-ai · `s2-2-1` | 47×14 · ~1.7:1 | From the 2026-07-15 production run. |
| `s8-1-1` | claude-cowork · `s4-5-1` | 84×29 · ~1.5:1 | Tallest and densest. Legitimately close to the checklist's *crowded panel* threshold — a fair test of whether the critic flags it instead of papering over it. |
| `s9-1-1` | claude-cowork · `s7-4-1` | 42×15 · ~1.4:1 | Most portrait art in the set. |

Aspect spread: **1.4:1 → 7.9:1**. That range is the point — a viewBox contract that only
works on comfortable landscape diagrams isn't a contract.

## Running it

The mechanical steps (from the repo root):

```bash
T=/tmp/ts-fixture && mkdir -p $T
python3 skills/polish-ascii/polish_ascii.py scan tests/skills/ascii-to-svg/final.md \
    --language Spanish > $T/plan.json
python3 skills/polish-ascii/polish_ascii.py annotate-renders --plan $T/plan.json \
    --renders tests/skills/ascii-to-svg/renders.json -o $T/plan.annotated.json
python3 skills/polish-ascii/polish_ascii.py extract \
    --final tests/skills/ascii-to-svg/final.md --plan $T/plan.annotated.json
python3 skills/polish-ascii/polish_ascii.py prepare-render-args \
    --plan $T/plan.annotated.json --out-dir $T/args --repo-root "$(pwd)"
```

Then the renders themselves — one subagent per `$T/args/<slide_id>.json`, each following
[`skills/ascii-to-svg/SKILL.md`](../../../skills/ascii-to-svg/SKILL.md) and dispatching a
blind [`diagram-critic`](../../../agents/diagram-critic.md). Finally:

```bash
python3 skills/polish-ascii/polish_ascii.py stamp-renders \
    --final tests/skills/ascii-to-svg/final.md --plan $T/plan.annotated.json
```

**Idempotency is part of what this fixture tests.** Re-run `prepare-render-args` after
stamping: it should report `reused 9 block(s)` and write **zero** args files. If it writes
any, the digest chain is broken — which is exactly the bug that made every production pass
re-render an unchanged Talk (the stamping worked; nothing ever called it).

Note `final.md` is checked in with its **ASCII fences intact** — `cleanup` (which rewrites
fences to image refs) is deliberately not part of the fixture run, because the fences *are*
the input. Don't run `cleanup` against it.

## The two checks that don't need an LLM

These run in milliseconds and catch the things judgement is bad at:

```bash
python3 skills/ascii-to-svg/validate_svg.py  tests/skills/ascii-to-svg/images/<name>.svg
python3 skills/ascii-to-svg/audit_aspect.py  tests/skills/ascii-to-svg/images/<name>.svg \
    --png tests/skills/ascii-to-svg/images/<name>.png
```

`audit_aspect.py` covers the one defect class **no** visual review can reach, for a
structural reason: the critique PNG is rasterized *from* the viewBox, so a wrong viewBox
produces a right-looking picture whose dead canvas reads as intentional whitespace. There
is nothing for an eye to find.

> **All nine renders pass the audit, and that verifies nothing about the audit.**
>
> It is tempting to read a green fixture suite as proof the check works. It isn't. These
> are good renders; a check that only ever sees good renders is indistinguishable from a
> check that always returns ok — and that is not hypothetical. This audit shipped with a
> bug that returned `ok: full-bleed` for *any* diagram with a full-canvas tinted
> background (it hard-coded white as the background colour instead of measuring it), and
> every fixture here stayed green the whole time.
>
> `s5-1-1` in particular is **not** a regression test for the production viewBox bug,
> despite being the block the bug happened to. Re-rendering it produces a *correct*
> diagram, so the audit passes and catches nothing. The bug lives in a specific SVG that
> no longer exists, not in the ASCII.
>
> The actual regression tests are in **[`test_audit_aspect.py`](test_audit_aspect.py)** —
> synthetic, deliberately broken, and required to *fail*:
>
> ```bash
> python3 tests/skills/ascii-to-svg/test_audit_aspect.py
> ```
>
> Run that after any change to `audit_aspect.py`. If a case stops failing, the audit has
> lost a capability — which the nine fixtures will not tell you.
