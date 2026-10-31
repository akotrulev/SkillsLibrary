---
name: html-video
description: Use when HTML/CSS/animation must become an MP4 file — a product demo, walkthrough or motion-graphic asset rendered from markup. Routes to HyperFrames' own `/hyperframes` skill when installed; otherwise gives the install line, prerequisites, the minimal composition shape and the render command, then stops. Triggers "render this to video", "make an MP4 from HTML", "demo video from markup". Not for deciding what the motion is (`design:motion`) or for in-app animation code (a stack's `animation`).
---

# HTML → MP4 — route to HyperFrames

HyperFrames (HeyGen, open source) renders HTML by seeking a paused timeline frame by frame, so each render is identical. It is a moving upstream framework with skills of its own; this skill **routes to them** and carries only the fallback needed to get started.

## When to use

- A demo, walkthrough or motion-graphic asset must exist as a video file, and it is authored as markup.
- `design:motion` has chosen *what* the motion is and a rendered file is now the deliverable.

Do **not** use it to pick the motion (`design:motion`) or to animate the running app (a stack's `animation`).

## Step 1 — is HyperFrames installed?

If `/hyperframes` is available (it comes with `/hyperframes-cli`), **stop here and follow it.** It holds the render contract, the work loop and the CLI by job; nothing below overrides it, and where it disagrees with this file, it wins.

## Step 2 — otherwise, install and prerequisites

| Need | Value |
|---|---|
| Skills | `npx hyperframes skills update` (installs the core set from upstream `main`) |
| Runtime | Node.js 22+ |
| Encoder | FFmpeg on `PATH` |

Install the skills, then return to Step 1. If the user will not install them, use the minimal flow below.

## Step 3 — the minimal flow

```bash
npx hyperframes init my-video
cd my-video
npx hyperframes render --output out.mp4
```

The root `index.html` is the composition. The contract that matters first:

- Every timed element carries `class="clip"`, `data-start` and `data-duration`, in seconds.
- The video's length is the **root's** `data-duration`; overrun is cut, an early end holds the last frame.
- Each composition builds **one paused timeline** and registers it as `window.__timelines["<data-composition-id>"]`.
- Animate from the timeline only — anything driven by wall-clock time will not render deterministically.

Confirm the output file is non-empty and its duration matches the root `data-duration` before calling it done.

## Stop here

This skill does not teach Studio, the block registry, hosted or Lambda rendering, media generation or Remotion migration. Those are HyperFrames' own skills (`/hyperframes-cli`, `/hyperframes-registry`, `/media-use`, `/remotion-to-hyperframes`) — install and use them.

## Provenance

- **Upstream:** [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes) @ `a04b45a6db0d1f724be9cf1985c3b13657195f0d`.
- **License:** Apache-2.0 — [`LICENSE`](https://github.com/heygen-com/hyperframes/blob/a04b45a6db0d1f724be9cf1985c3b13657195f0d/LICENSE).
- **Adoption:** routed. No upstream file or code is copied into this repository; the composition shape above is restated from upstream's `/hyperframes` contract in this skill's own words.

## Related

- [`design:motion`](../motion/SKILL.md) — chooses the motion this skill renders.
