---
name: talksmith:generate-image
description: Tool-agnostic image generation for the image-illustrator's Step-6 aside pass. Takes a resolved prompt + aspect + output path and produces one raster image using whatever image-generation capability the session exposes (an MCP image tool, the host's native image generation). Returns `unavailable` — never fails the build — when no such capability is present. Only produces output on models/sessions that support image generation.
---

# talksmith:generate-image — one prompt → one image (tool-agnostic)

The generation backend the [`image-illustrator`](${CLAUDE_PLUGIN_ROOT}/agents/image-illustrator.md) dispatches once per `<slide_id>.json` args file (from [`talksmith:polish-images`](../polish-images/SKILL.md) `prepare-render-args`). Its contract is deliberately **backend-agnostic**: the prompt is already fully composed (subject + palette + aspect + no-text overlay), so this skill's only job is to route it to an available image generator and save the result.

**This is guidance, not a deterministic script.** Image generation depends on a capability the *session* provides — there is no bundled model. This skill tells the dispatched subagent how to find and use whatever is available, and what to do when nothing is.

## Inputs (from the args file)

| Field | Meaning |
|---|---|
| `prompt` | The fully-resolved generation prompt. Send it **verbatim** — do not re-expand, re-summarize, or add to it. The palette, aspect, and no-text constraints are already in it. |
| `aspect` | `portrait` (the aside column is a tall full-bleed strip → target ~2:3, e.g. 832×1248). `landscape` / `square` are accepted for completeness but the aside pass always passes `portrait`. |
| `output_path` | Absolute path to write the PNG to (e.g. `talks/<Talk>/images/<slide-id>-<n>-aside.png`). |
| `prompt_file` | The `.imgprompt` sidecar (original description + enriched prompt), for reference only. |

## Procedure

1. **Find an image-generation capability**, in this order — stop at the first that exists:
   - An **MCP image-generation tool** connected to the session. Discover it with `ToolSearch` (queries like `generate image`, `text to image`, `image generation`); a matching tool typically takes a prompt/size and returns image bytes or a file/URL.
   - The **host's native image generation**, if the running model/agent exposes one.
2. **Generate** with the `prompt` verbatim, requesting the `aspect` dimensions (portrait ~2:3). Request PNG if the backend lets you choose format.
3. **Save to `output_path`.** If the backend returns a URL or a temp file, fetch/copy the bytes to `output_path` (create parent `images/` if needed). If it returns base64, decode and write. The file at `output_path` must be a real raster image — the [`md-to-deck`](../md-to-deck/SKILL.md) PPTX prerequisite loads it via PIL, so a broken/empty file fails the later build.
4. **Report** `generated: <output_path>` back to the image-illustrator.

## When no capability is present — `unavailable`, never a failure

If step 1 finds **no** image-generation tool, do **not** fabricate, download a stock image, or draw a substitute. Return `unavailable` to the image-illustrator, which records the directive `unresolved: no_image_capability`, **leaves the slide's text intact** (the aside simply doesn't appear), and continues. This mirrors how the `.pptx` render modes are Cowork-only: the feature degrades, it never blocks Polish. The presenter is told at the end that an aside was requested but couldn't be generated here — so re-running Step 6 in a session that *does* have image generation will produce it (the directive is still in `final.md` until `cleanup`, and the `draft.md` source always is).

## Boundaries

- **Never invents subject matter.** The prompt is authoritative and complete; send it as-is.
- **Never embeds text, logos, or watermarks** — the prompt already forbids them; if a backend offers a "no text" toggle, set it.
- **Atmospheric only.** This skill produces mood imagery for an aside column. Anything that must be *read* (a chart, screenshot, labeled diagram) is not its job — the image-illustrator refuses text-bearing directives upstream.
- Writes exactly one file, at `output_path`. Idempotency stamping is `polish-images`' job, not this skill's.
