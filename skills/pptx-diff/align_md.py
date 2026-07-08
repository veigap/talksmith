#!/usr/bin/env python3
"""align_md.py — align final.md against a reconstructed finalpptx.md and emit a
structured diff explaining the text/image changes. Design C of the reverse pipeline.

Parses both files into slide trees (shared _pptxlib parser), aligns slides by
(section, slide#) with a normalized-title similarity fallback, then per aligned
slide computes: title change, content edits (bullet/line granularity), speaker-
notes edits, and image changes (added/removed/replaced/renamed by basename+hash).
Unaligned slides surface as slide_added / slide_deleted (deletes suggested only).

Usage:
  python3 align_md.py --final <final.md> --pptx <finalpptx.md>
                      [--inventory <inventory.json>] [--json | --human]
                      [-o <diff.json>]

Exit codes:
  0  diff produced (0 = no changes is still success)
  2  could not run (missing file)

stdlib only.
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

import _pptxlib as L

TITLE_MATCH_MIN = 0.6
LOW_CONF_MAX = 0.75


def _img_sha(talk_root: Path, ref_path: str) -> str | None:
    # remote refs — no local hash
    if ref_path.startswith(("http://", "https://")):
        return None
    p = talk_root / ref_path
    return L.sha256_file(p)


def _slide_image_list(talk_root: Path, slide) -> list[dict]:
    """Return the slide's images in reading order (positional ordinal = slot).
    Preserves duplicates — matters for slot alignment."""
    return [{
        "basename": im.basename,
        "path": im.path,
        "alt": im.alt,
        "sha": _img_sha(talk_root, im.path),
        "line": im.line,
    } for im in slide.images]


def _title_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, L.normalize_title(a), L.normalize_title(b)).ratio()


def _align(final_slides, pptx_slides):
    """Greedy best-ratio alignment. Returns (pairs, only_final, only_pptx)."""
    scored = []
    for i, a in enumerate(final_slides):
        for j, b in enumerate(pptx_slides):
            ratio = _title_ratio(a.title, b.title)
            same_loc = (a.section_key == b.section_key and a.slide_num == b.slide_num
                        and a.slide_num != 0)
            score = ratio + (0.5 if same_loc else 0.0)
            if same_loc or ratio >= TITLE_MATCH_MIN:
                scored.append((score, ratio, i, j))
    scored.sort(reverse=True)
    used_a: set[int] = set()
    used_b: set[int] = set()
    pairs = []
    for score, ratio, i, j in scored:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        pairs.append((i, j, ratio))
    only_final = [i for i in range(len(final_slides)) if i not in used_a]
    only_pptx = [j for j in range(len(pptx_slides)) if j not in used_b]
    return pairs, only_final, only_pptx


def _diff_units(final_units, pptx_units, orig_final, orig_pptx,
                headings: list[str] | None = None):
    """Return list of (op, from_text, to_text) from a SequenceMatcher over
    normalized units, echoing the original (un-normalized) source lines.

    Applies the "original wins on formatting" rule via
    `L.content_semantically_contained` — if the deck's rendered line carries a
    strict subset of the source line's meaning (same key words, less prose),
    the change is suppressed so the source's formatting is preserved. This
    catches the common case where the deck's body-shape extraction produces
    pill headings / card titles ("POR QUÉ RESPUESTAS DISTINTAS") for what the
    source expresses as full sentences ("- Hook: le hago la misma pregunta…").

    `headings` — extra context strings (slide title + section name) that
    inserted deck lines are checked against too. Catches the common pattern
    where the deck's section-pill text ("CÓMO GENERA EL MODELO") appears as
    a "new" body line but is really redundant with the slide's H1 section
    heading.
    """
    headings = headings or []
    sm = difflib.SequenceMatcher(None, final_units, pptx_units)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            fa = orig_final[i1:i2]
            fb = orig_pptx[j1:j2]
            n = max(len(fa), len(fb))
            for k in range(n):
                from_text = fa[k] if k < len(fa) else ""
                to_text = fb[k] if k < len(fb) else ""
                if from_text and to_text and \
                        L.content_semantically_contained(from_text, to_text):
                    continue  # deck says a subset of what source says — keep source
                # Also: if the deck's TO is semantically contained in any of
                # the slide's heading strings (section H1, slide H2), it's a
                # redundant pill/heading, not real content.
                if to_text and any(
                        L.content_semantically_contained(h, to_text) for h in headings):
                    continue
                out.append(("modified", from_text, to_text))
        elif tag == "delete":
            for k in range(i1, i2):
                out.append(("removed", orig_final[k], ""))
        elif tag == "insert":
            for k in range(j1, j2):
                inserted = orig_pptx[k]
                # Redundant with an unchanged source line?
                if any(L.content_semantically_contained(src, inserted)
                        for src in orig_final):
                    continue
                # Redundant with the slide/section heading?
                if any(L.content_semantically_contained(h, inserted)
                        for h in headings):
                    continue
                out.append(("added", "", inserted))
    return out


def _orig_units(body_lines):
    """Return (normalized_units, original_source_lines) in parallel, dropping
    blanks/rules/comments/fences so they align with content_units().
    Handles multi-line HTML comments (e.g. `<!-- ascii-note: ... -->` blocks
    whose intent/emphasize/labels lines would otherwise leak into diffs)."""
    norm = []
    orig = []
    in_fence = False
    in_comment = False
    for raw in body_lines:
        if L.FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment:
            if L.COMMENT_CLOSE.search(raw):
                in_comment = False
            continue
        if "<!--" in raw and not L.COMMENT_CLOSE.search(raw):
            in_comment = True
            continue
        s = raw.strip()
        if not s or s in ("---", "***", "___") or s.startswith("<!--") or s.startswith("-->"):
            continue
        # Image refs are diffed separately (image ops) — don't double-report as prose.
        if L.IMAGE_REF.sub("", s).strip() == "":
            continue
        nrm = L.normalize_prose(raw)
        if nrm:
            norm.append(nrm)
            orig.append(s)
    return norm, orig


def build_diff(final_md: str, pptx_md: str, talk_root: Path) -> dict:
    # Both files' image refs are Talk-root-relative (`images/...`,
    # `reconcile/staging/...`) even though finalpptx.md lives under reconcile/,
    # so resolve every ref against the one Talk root.
    final_root = talk_root
    pptx_root = talk_root
    final_tree = L.parse_md_slides(final_md)
    pptx_tree = L.parse_md_slides(pptx_md)
    fs = final_tree["slides"]
    ps = pptx_tree["slides"]

    pairs, only_final, only_pptx = _align(fs, ps)

    changes: list[dict] = []
    counter = [0]

    def cid() -> str:
        counter[0] += 1
        return f"c{counter[0]:03d}"

    def conf(ratio: float) -> str:
        return "low" if ratio < LOW_CONF_MAX else "high"

    for i, j, ratio in sorted(pairs, key=lambda t: (fs[t[0]].section_key, fs[t[0]].slide_num)):
        a, b = fs[i], ps[j]
        loc = {"section": a.section_key, "slide": a.slide_num, "title": a.title}
        c = conf(ratio)

        # title
        if L.normalize_title(a.title) != L.normalize_title(b.title):
            changes.append({"id": cid(), "kind": "title", "op": "modified",
                            **loc, "from": a.title, "to": b.title, "confidence": c})

        # Heading context — used to suppress deck-side pill/section-header
        # text that's redundant with the slide's own H1/H2 titles.
        headings = [h for h in (a.title, a.section_title, b.title, b.section_title) if h]

        # content
        fn, fo = _orig_units(a.field_body("content"))
        pn, po = _orig_units(b.field_body("content"))
        for op, ftext, ttext in _diff_units(fn, pn, fo, po, headings=headings):
            changes.append({"id": cid(), "kind": "content", "op": op, **loc,
                            "from": ftext, "to": ttext, "confidence": c})

        # notes
        fnotes = a.field_body("speaker notes") or a.field_body("notes")
        pnotes = b.field_body("speaker notes") or b.field_body("notes")
        fnn, fno = _orig_units(fnotes)
        pnn, pno = _orig_units(pnotes)
        for op, ftext, ttext in _diff_units(fnn, pnn, fno, pno, headings=headings):
            changes.append({"id": cid(), "kind": "notes", "op": op, **loc,
                            "from": ftext, "to": ttext, "confidence": c})

        # images — slot-based alignment. Byte-hash gives us the "definitely
        # unchanged" fast path (works even for reordered images); positional
        # ordinal handles the "same slot, resized or edited" case that byte
        # or dimension comparison would miss.
        f_imgs = _slide_image_list(final_root, a)
        p_imgs = _slide_image_list(pptx_root, b)

        paired_f: set[int] = set()
        paired_p: set[int] = set()

        # Pass 1: byte-identical pairs (order-agnostic). These are unchanged.
        for pi, pv in enumerate(p_imgs):
            if pi in paired_p or not pv["sha"]:
                continue
            for fi, fv in enumerate(f_imgs):
                if fi in paired_f or not fv["sha"]:
                    continue
                if fv["sha"] == pv["sha"]:
                    paired_f.add(fi)
                    paired_p.add(pi)
                    break  # unchanged — no change record

        # Pass 1.5: silently absorb ASCII-backed slots. If the final.md image
        # has a `<basename>.ascii` sidecar on disk, its true source is the ASCII
        # fence in draft.md — Polish regenerates the PNG from that ASCII on
        # every run, so any deck-side byte drift (Keynote recompressing on
        # save) is disposable. Treat as unchanged. Positional matching: the
        # k-th ASCII-backed final image consumes the k-th unpaired deck image.
        unp_f = [i for i in range(len(f_imgs)) if i not in paired_f]
        unp_p = [j for j in range(len(p_imgs)) if j not in paired_p]
        for pos, fi in enumerate(unp_f):
            sidecar = final_root / "images" / (Path(f_imgs[fi]["path"]).stem + ".ascii")
            if not sidecar.exists():
                continue
            paired_f.add(fi)
            if pos < len(unp_p):
                paired_p.add(unp_p[pos])

        # Pass 2: remaining images pair by positional ordinal within the slide.
        rem_f = [i for i in range(len(f_imgs)) if i not in paired_f]
        rem_p = [i for i in range(len(p_imgs)) if i not in paired_p]
        for slot, (fi, pi) in enumerate(zip(rem_f, rem_p), 1):
            fv, pv = f_imgs[fi], p_imgs[pi]
            changes.append({"id": cid(), "kind": "image", "op": "replaced", **loc,
                            "target_basename": fv["basename"],   # what to overwrite in images/
                            "from_sha": fv["sha"], "to_sha": pv["sha"],
                            "pptx_path": pv["path"],
                            "slot": slot, "confidence": c})
            paired_f.add(fi)
            paired_p.add(pi)

        # Pass 3: extras — new in deck, or gone from deck.
        for pi in range(len(p_imgs)):
            if pi in paired_p:
                continue
            pv = p_imgs[pi]
            changes.append({"id": cid(), "kind": "image", "op": "added", **loc,
                            "basename": pv["basename"], "to_sha": pv["sha"],
                            "pptx_path": pv["path"], "alt": pv["alt"],
                            "confidence": c})
        for fi in range(len(f_imgs)):
            if fi in paired_f:
                continue
            fv = f_imgs[fi]
            changes.append({"id": cid(), "kind": "image", "op": "removed", **loc,
                            "basename": fv["basename"], "confidence": c})

    # unaligned
    for j in only_pptx:
        b = ps[j]
        changes.append({
            "id": cid(), "kind": "slide_added", "op": "added",
            "section": b.section_key, "after_slide": b.slide_num, "title": b.title,
            "payload": {
                "title": b.title,
                "content": b.field_body("content"),
                "notes": b.field_body("speaker notes") or b.field_body("notes"),
                "images": [{"alt": im.alt, "path": im.path} for im in b.images],
            },
            "confidence": "low",
            "reason": "no final.md slide matched within title similarity",
        })
    for i in only_final:
        a = fs[i]
        changes.append({
            "id": cid(), "kind": "slide_deleted", "op": "suggested",
            "section": a.section_key, "slide": a.slide_num, "title": a.title,
            "final_heading_line": a.heading_line, "final_end_line": a.end_line,
            "confidence": "low",
            "reason": "slide absent from deck (may have been cut at render — not auto-applied)",
        })

    summary = {
        "aligned": len(pairs),
        "added_slides": len(only_pptx),
        "deleted_slides": len(only_final),
        "title_changes": sum(1 for c in changes if c["kind"] == "title"),
        "content_edits": sum(1 for c in changes if c["kind"] == "content"),
        "note_edits": sum(1 for c in changes if c["kind"] == "notes"),
        "image_changes": sum(1 for c in changes if c["kind"] == "image"),
    }
    return {"final_md": final_md, "pptx_md": pptx_md, "summary": summary, "changes": changes}


def _human(diff: dict) -> str:
    s = diff["summary"]
    lines = [
        f"diff: {s['aligned']} aligned slides — "
        f"{s['title_changes']} title, {s['content_edits']} content, "
        f"{s['note_edits']} notes, {s['image_changes']} image change(s); "
        f"{s['added_slides']} added, {s['deleted_slides']} deleted"
    ]
    by_slide: dict[tuple, list[dict]] = {}
    specials: list[dict] = []
    for c in diff["changes"]:
        if c["kind"] in ("slide_added", "slide_deleted"):
            specials.append(c)
            continue
        key = (c.get("section"), c.get("slide"), c.get("title"))
        by_slide.setdefault(key, []).append(c)
    for (sec, sld, title), items in by_slide.items():
        low = " ⚠ low-confidence match" if any(i.get("confidence") == "low" for i in items) else ""
        lines.append(f"\n  Section {sec} › Slide {sld} \"{title}\"{low}")
        for c in items:
            if c["kind"] == "image":
                if c["op"] == "replaced":
                    tgt = c.get("target_basename") or c.get("basename")
                    lines.append(f"    ⟳ image modified in slot {c.get('slot','?')}: {tgt} (deck bytes will overwrite images/{tgt})")
                elif c["op"] == "added":
                    lines.append(f"    + image added: {c['basename']}")
                elif c["op"] == "removed":
                    lines.append(f"    - image removed: {c['basename']}")
            elif c["op"] == "modified":
                lines.append(f"    ~ [{c['kind']}] {c['from']!r} → {c['to']!r}")
            elif c["op"] == "added":
                lines.append(f"    + [{c['kind']}] {c['to']!r}")
            elif c["op"] == "removed":
                lines.append(f"    - [{c['kind']}] {c['from']!r}")
    for c in specials:
        if c["kind"] == "slide_added":
            lines.append(f"\n  + SLIDE ADDED in section {c['section']}: \"{c['title']}\" ({c['reason']})")
        else:
            lines.append(f"\n  - SLIDE DELETED (suggested) {c['section']}.{c['slide']} \"{c['title']}\" ({c['reason']})")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", required=True)
    ap.add_argument("--pptx", required=True, help="reconstructed finalpptx.md, e.g. <talk>/reconcile/finalpptx.md")
    ap.add_argument("--talk", help="Talk root (default: parent dir of --final). "
                    "Image refs on both sides resolve against this.")
    ap.add_argument("--inventory", help="optional inventory.json (enriches image classification)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--human", action="store_true")
    ap.add_argument("-o", "--output", help="default: <talk>/reconcile/finalpptx.diff.json")
    args = ap.parse_args(argv)

    for f in (args.final, args.pptx):
        if not Path(f).is_file():
            print(f"failed: file not found: {f}", file=sys.stderr)
            return 2

    talk_root = Path(args.talk).resolve() if args.talk else Path(args.final).resolve().parent
    diff = build_diff(args.final, args.pptx, talk_root)
    out_path = Path(args.output) if args.output else talk_root / "reconcile" / "finalpptx.diff.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(diff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.human:
        print(_human(diff))
    else:
        print(json.dumps(diff, indent=2, ensure_ascii=False))
    print(f"\ndiff: wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
