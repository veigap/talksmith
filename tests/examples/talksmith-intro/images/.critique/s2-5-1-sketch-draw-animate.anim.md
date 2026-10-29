# s2-5-1-sketch-draw-animate — animation log

## Iteration 1 (approved_still: .critique/s2-5-1-sketch-draw-animate.png — cairosvg)
defects:
- [F4] Frames 5–16: the three captions under the panels are italic; upright in the approved still.

Not revised: the base declares `font-style="italic"`; cairosvg does not synthesize italic. Renderer difference — comparison fixed (`still.png` from Chrome) and iteration 1 re-run.

## Iteration 1, re-run (approved_still: .critique/s2-5-1-sketch-draw-animate.anim/still.png — Chrome)
defects:
- [P5] Frames 13–15: in AND ANIMATES the «critic: approved» badge does not land as its own step — no frame shows the caption settled before the approval arrives.
- [P2] Frames 5 and 11: the document token brushes the «Polish» / «brief» label for the whole trip.

## Revision
Arrow labels now land with the token's arrival (not on screen while it passes); token shrunk to 10×12; timeline respaced so the AND ANIMATES caption settles (14.1 s) before its badge lands alone (15.2 s).

## Iteration 2
clean

## Outcome
animated
