# Screenshots — capture mechanics

Loaded by `SKILL.md` when a run has an environment to capture from, or is a capture pass. A screenshot shows a person where they are and what they are looking at. It replaces a paragraph of "on the left, below the summary…"; it never replaces the steps.

## Where they come from

The running product, captured by you: a running, **non-production** environment, signed in with a test login for the role the task belongs to — administrators included. Never taken from production, a design file, a mock-up or the code. Logins are used in the browser and nowhere else: never written into a guide, the orientation cache, a plan, a trace or the report.

The run asks **once** for the environment and a test login per role — in the message of the scope or area-split gate it already shows — and never waits on the answer by itself.

## Capture pass

A later run given the environment does only this for a pending guide: sign in as each role, check every bold label against the screen (the screen wins; a difference is fixed in the guide and is an open question), capture, and replace the `pending` line with `captured from …`. No re-trace.

## Which tasks

- Pick the tasks where the picture saves the most words: the first time a person meets a screen, a form with several fields, a busy administration screen, a path with three or more arrows.
- Skip a task whose screen an earlier screenshot in the guide already shows.
- Never one per step, never one of automatic work, never one in *Rules and limits*, *Good to know* or the overview.
- A guide whose tasks have screens has at least one, unless its `**Screenshots:**` line says `pending` or `waived` (lint ERROR otherwise; `pending` raises a WARN so the guide is not mistaken for finished).

## What it shows

- The task's screen in the state the task describes, with the control from the `**Where:**` line visible. When the task has an `**Example**`, the screen shows the example's values (Ana, the Basic plan, £6.00) so the picture and the text agree.
- Desktop viewport, 1280 × 800, the visible window only — not a full-page scroll. Crop to one region (a dialog, a form) when the rest of the screen is noise.
- **Test data only.** No real person's name, email or payment detail, no secret, key or token, no internal address. If a screen cannot be shown without one, choose another record or ask.
- Every bold label the task's steps name is visible on it and spelled the same. When the running screen's label differs from the code's text, the screen wins and the difference is an open question.

## How it is written and filed

- Right under the `**Where:**` line: `![<what the screen shows, one sentence in the client's words>](screenshots/<guide-name>/<task-slug>.png)`. The alt text is mandatory — it is what a screen reader and a reader without images get.
- The file sits beside the guide at that relative path: `areas/screenshots/<area>/`, `docs/features/screenshots/<NNN>-<slug>/`. `<task-slug>` is the task heading in kebab case. PNG.
- Capture with the browser tools the agent grants (`browser_navigate`, sign in, act, then `browser_take_screenshot`), and move the file into place when the tool saved it elsewhere.
- Screenshots are committed with the guide — they are part of it. On an update, a task whose screen or steps changed is captured again; a screenshot whose task is gone is deleted.
