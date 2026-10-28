"""Shared plumbing for the model-reading audits.

This was the OOXML reader the `.pptx`-parsing audits shared — namespace map, slide relationships,
solid-fill colour, PNG dimensions. Those audits existed to verify that an LLM following a prose
spec had actually produced the deck the model described; the `.pptx` is now measured mechanically
from the rendered HTML, so there is nothing to second-guess and they are gone. What survived is
the one helper that was never about OOXML at all: walking a model for its content strings.
"""

from __future__ import annotations


def model_strings(obj) -> list[str]:
    """Every content string under a model slide (or a whole model), depth-first.

    **Keys beginning with `_` are excluded, and that exclusion is load-bearing.** `_choice` is the
    classification trace, and it restates the slide's source text in its own rationale — so a line
    the fill step actually dropped would still turn up in the walk, and a coverage audit would
    cheerfully confirm its own blind spot. `_source` is a freshness stamp, not content, for the
    same reason.
    """
    out: list[str] = []

    def walk(o) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if not k.startswith("_"):
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, str):
            out.append(o)

    walk(obj)
    return out
