# s2-4-1-three-layers — animation log

## Iteration 1 (approved_still: .critique/s2-4-1-three-layers.png — cairosvg)
defects:
- [F4] Frame 16 (t = 17.8 s), and every frame from frame 2 (t = 3.1 s) on: the "ingest" and "render" labels are set in italic; in the approved still both are upright roman.

Not revised: the base declares `font-style="italic"`; the approved still came from cairosvg, which does not synthesize italic. A renderer difference, not the animation's — the comparison was fixed (`capture_frames.py` now writes `still.png`, the base drawn by Chrome) and iteration 1 re-run.

## Iteration 1, re-run (approved_still: .critique/s2-4-1-three-layers.anim/still.png — Chrome)
clean

## Outcome
animated
