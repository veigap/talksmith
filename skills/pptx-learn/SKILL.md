---
name: talksmith:pptx-learn
description: Learn strict styling / distribution / positioning patterns from a deck a presenter hand-corrected — an LLM-heavy analysis, not a mechanical diff. `learn_patterns.py` (needs `python-pptx`) is the evidence layer: it diffs the human-edited `.pptx` against the **as-generated** baseline and surfaces the *recurring* geometry deltas (title nudged, image resized, pill moved, fill changed) with counts. The **LLM is the analyst**: it examines the before/after slides (multimodal where renders are available) plus the measured deltas and reasons about the *why* and the *decision* behind each change — most importantly judging whether a delta is a **generalizable template rule** (promote) or a **content-specific one-off** (discard), which the recurrence count alone cannot decide. Confirmed patterns — each carrying its design rationale — are appended to the project file `config/strict-learnings.md` for human promotion into the plugin's `config/pptx-styles/pptx-strict/conformance-patterns.md`. **strict-only.** Runs **auto** after `talksmith:pptx-merge` and **on-demand**. No Cowork dependency (rendering for the multimodal pass is best-effort via libreoffice; degrades to deltas-only).
---

# talksmith:pptx-learn — Learn strict patterns from human edits

Talksmith renders a strict deck; the presenter opens it in Keynote/PowerPoint and hand-corrects positions, sizes, fonts, and fills. Those corrections are the best possible signal for what the generator *should* have done. This skill turns a deck's real edits into **declarative conformance patterns** the strict renderer can apply next time.

**This is an LLM-heavy analysis, not a mechanical diff.** The Python measures; the LLM decides. A geometry delta is only evidence — the *value* is in the reasoning the measurement can't supply:

- **Why** did the presenter make this change? (e.g. "the template floats divider titles too high above the dead space")
- **Does it generalize?** A recurring delta can still be a **content-specific one-off** — the human nudged three titles because *those* titles were long, not because *all* titles should move. Recurrence count can't tell a template rule from a coincidence; only judgement (ideally seeing the before/after slides) can. Promoting a coincidence as a rule would degrade every future deck, so this filter is the point of the skill.
- **What decision** does it encode, stated as a rule with a defensible rationale.

The Python (`learn_patterns.py`) exists to keep that reasoning **grounded** — the LLM never invents a delta the diff didn't measure — and to do the counting/aggregation cheaply. But the analysis is the LLM's job.

**strict-only.** Free-form and html-strict render their own layouts and are never judged against a fixed template, so there is nothing to learn against. If the render being reconciled was not strict, this skill **no-ops** and says so.

## The two decks it compares

| | What | Where |
|---|---|---|
| **Baseline (B)** — as generated | The deck Talksmith produced, before any human touched it | geometry snapshot `output/final.generated.geometry.json` (written at strict render — see [`md-to-deck` SKILL.md](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/SKILL.md) → *Output*) |
| **Edited (A)** — human-corrected | The `.pptx` the presenter edited and handed to reconcile | the deck path passed to `talksmith:pptx-extract` |

The geometry snapshot is what makes B survive **in-place editing** of `output/final.pptx`. If the snapshot is absent (older render, or a non-strict render), the skill no-ops.

## When it runs

1. **Auto — end of the reverse pipeline.** After [`talksmith:pptx-merge`](${CLAUDE_PLUGIN_ROOT}/skills/pptx-merge/SKILL.md) finishes reincorporating deck edits into `draft.md`, if the render was strict and the baseline snapshot exists, run this skill on the same edited deck. The human deck is already inventoried by `pptx-extract`, so this is cheap.
2. **On-demand.** `/talksmith:pptx-learn <edited.pptx> --talk talks/<Talk> --baseline <geometry.json|as-generated.pptx>` — mine any delivered deck for patterns without a full reconcile.

## Process

0. **Gate.** Confirm the render was strict and a baseline exists (`output/final.generated.geometry.json`, or an as-generated `.pptx` passed explicitly). If not → emit `[pptx-learn] no-op: <reason>` and stop. Never learn from free-form/html-strict.

1. **Measure — Python surfaces evidence.** Run [`learn_patterns.py`](learn_patterns.py):

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-learn/learn_patterns.py diff \
     --baseline talks/<Talk>/output/final.generated.geometry.json \
     --edited   <edited.pptx> \
     --min-recur 3 \
     -o talks/<Talk>/reconcile/learn-candidates.json
   ```

   It matches slides (by title, then order) and shapes (by role, then nearest position), computes per-shape deltas (move / resize / refont / refill), and keeps deltas that **recur across ≥ `--min-recur` slides** with a consistent direction. Each carries a `summary`, the median delta (EMU / pt / hex), the slide `class` + shape `role`, and the evidence `count` + `slides`. **This is evidence, not conclusions** — recurrence is a *pre-filter* that discards single nudges, not a promotion decision.

1.5. **See the change (multimodal, best-effort).** For each candidate's evidence slides, render the **baseline** slide and the **edited** slide to PNG so the LLM can look at the actual before/after, not just EMU numbers — reuse the md-to-deck rasterization path (`libreoffice --headless --convert-to pdf` → `pdftoppm`) on both decks and pair them by slide. If libreoffice is unavailable, skip this and analyse from the deltas + the slides' text content; note `multimodal: unavailable` in the report.

2. **Analyse — the LLM decides (the heavy step).** For each measured candidate, reason about the *before/after* (the PNGs from 1.5 where available) together with the delta and the slide content, and produce a judgement:
   - **Why** the presenter made the change — the design decision behind it.
   - **Generalizable vs one-off** — is this a *template rule* (every divider title should move up because the template floats them) or a *content-specific* fix (these titles were long)? **Discard content-specific deltas** even if they recurred; recurrence got them onto the list, judgement decides if they leave it. This filter is the skill's whole reason to exist.
   - Only for the survivors, write a `conformance-patterns.md`-shaped entry (see its *Entry schema*): stable `id`, `applies-to`, human-readable `rule`, the **`why`** (the rationale — required), the machine-checkable `measure` (from the median delta), `interpret:` true/false, `status: candidate`, `evidence` (count + slides + `multimodal: yes|unavailable`), `since`. Convert EMU deltas to a concrete target (e.g. "divider title baseline ≈ 0.9in from top") where the `why` supports a constant; otherwise set `interpret: true` and describe the direction. Never emit a delta the diff didn't measure, and never emit a pattern you can't justify with a `why`.

3. **Append to the project learnings file.** Add each entry to **`config/strict-learnings.md`** (project-owned). On first run create it with a one-line header (`# Strict conformance learnings — candidates mined by talksmith:pptx-learn. Promote to the plugin's strict/conformance-patterns.md at Step 8.`) followed by a `## Candidates` heading; entries are `conformance-patterns.md`-shaped fenced blocks with `status: candidate`. Never write the plugin's `conformance-patterns.md` — that is human-curated promotion only. De-dupe against entries already present (same `applies-to` + `role` + delta direction → bump the evidence count, don't duplicate).

4. **Report** in plain language: how many candidate patterns were found and where they landed (e.g. *"Spotted 2 things you consistently adjust: divider titles moved up ~0.2in on all 6 dividers, and content images grown slightly. Saved as suggestions in config/strict-learnings.md for you to approve."*). Suppress the geometry/tag mechanics.

## Promotion (human, at Step 8)

`strict-learnings.md` candidates are **suggestions, not rules** — they do not affect renders until promoted. At Step 8 (Learnings), the orchestrator surfaces any open candidates for the presenter to *Promote* / *Skip* / *Promote with edits*. A promoted pattern is moved into the plugin's [`conformance-patterns.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/pptx-strict/conformance-patterns.md) with `status: promoted`; from then on the strict renderer applies it. This mirrors the editorial `learnings.md` promotion flow.

## Rules

- **strict-only, non-destructive.** Reads decks + writes only `config/strict-learnings.md` (project) and `reconcile/learn-candidates.json`. Never edits the plugin's bundled patterns, `draft.md`, `final.md`, or any deck.
- **Recurrence, not one-offs.** A pattern must recur (`--min-recur`, default 3) — a single manual tweak on one slide is not a rule.
- **Degrade quietly.** No baseline / not strict / `python-pptx` missing → no-op with a one-line reason; never block the reconcile.
- **Python measures, the LLM analyses and judges.** `learn_patterns.py` produces the grounded numbers (deltas + recurrence); the LLM does the real work — the *why*, the *decision*, and the generalizable-vs-one-off call — ideally on the before/after renders. It never invents a delta the diff didn't measure, and never promotes a delta it can't explain with a defensible `why`.
- **Recurrence pre-filters; judgement decides.** A recurring delta is a candidate, not a rule. Content-specific deltas are discarded at the analysis step even when they recurred.
