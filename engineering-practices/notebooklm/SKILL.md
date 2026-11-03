---
name: notebooklm
description: Use when querying the user's own Google NotebookLM notebooks for cited answers via browser automation. Triggers "ask my NotebookLM". Not for grounding in official docs (source-grounding).
---

# NotebookLM

Each question opens a real Chrome session (via `patchright`) against Google NotebookLM, reads the answer Gemini builds **only from the sources the user uploaded**, and closes. The value is an answer that cites the user's own documents instead of the model's memory.

The tool is **PleasePrompto's `notebooklm-skill`, vendored untouched** at `engineering-practices/vendor/notebooklm/` (provenance below). **Upstream is authoritative for the procedure**: authentication, the notebook library, the question interface, the follow-up rule and cleanup. This file states only where the library departs from it. Never paraphrase upstream from memory — read it.

## Before first use

Print this line to the user, verbatim, before the first command of a session:

> upstream archived 2026-09-10 — may break; drives real Chrome via patchright against Google NotebookLM

## Load order

Resolve against `${CLAUDE_PLUGIN_ROOT}/engineering-practices/vendor/notebooklm/` from an installed plugin, or `engineering-practices/vendor/notebooklm/` in this repo.

1. Read upstream `SKILL.md` end to end, then `AUTHENTICATION.md` before the first sign-in.
2. Run every script through upstream's `scripts/run.py` wrapper by absolute path — `python <vendor>/scripts/run.py <script>.py …`. The wrapper resolves its own directory, so the working directory does not matter. Upstream's `python scripts/run.py` is relative to the skill directory and fails from anywhere else.
3. Read `references/` only when a command fails.
4. Apply the overrides below. Where one is silent, upstream holds.

## Overrides

| Upstream | Here | Why |
|---|---|---|
| Runs wherever the skill loads | **Local Claude Code only, never the web UI.** | Upstream needs a visible Chrome, Google's network and a persistent profile; the web sandbox blocks them. |
| Any Google account | **A dedicated Google account**, as upstream itself advises. Never the user's personal or work account. | Browser automation of a Google product can get an account flagged. |
| Notebooks are whatever the user adds | **Notebooks must be shared publicly, and a notebook holding anything sensitive is never queried.** Ask once, at `notebook_manager.py add`, whether the notebook is safe to share; if the user cannot say, do not add it. | Questions and answers pass through Google and the agent's context. |
| 50 queries/day on a free account, mentioned only in a limitation list | **Before a batch of queries, state the budget:** how many this run will spend against the free-tier daily cap of 50, and how many are left if the user already ran some today. | A follow-up loop can burn the cap silently. |
| "Always ask follow-ups until complete" | Kept, **capped at the stated run budget**. Stop and report the gap when the budget is spent. | Upstream's loop has no bound. |
| State and venv under the skill directory | **Not patched** (see Where state lives). | A patched script is a fork, and the vendored copy is diffed against upstream. |

## Where state lives

Upstream resolves `SKILL_DIR` from the script's own location (`scripts/config.py`), so everything it writes lands **inside the vendored folder**:

| Path under `vendor/notebooklm/` | Holds |
|---|---|
| `.venv/` | the Python environment, created by `run.py` on first use |
| `data/browser_state/` | the signed-in Chrome profile and `state.json` cookies — **the Google session** |
| `data/auth_info.json`, `data/library.json` | auth status, the notebook library |

- **In this repo** that is the working tree. The root `.gitignore` must ignore `engineering-practices/vendor/notebooklm/data/` and `.venv/`; confirm with `git check-ignore -q` before the first sign-in, and never commit either.
- **From an installed plugin** that is the plugin cache. **A plugin update replaces the folder and wipes the Google session, the library and the venv** — the user signs in and re-adds notebooks again. Tell them this before sign-in. Upstream's own text says `~/.claude/skills/notebooklm/data/`; that path is wrong for this install.
- The session is a signed-in Google profile on disk. Do not copy it, print it or attach it anywhere.

## Prerequisites

Python 3 and Chrome; `run.py` installs `patchright==1.55.2` and `python-dotenv==1.0.0` into the venv on first use. Sign-in needs a **visible** browser and a person: tell the user a window will open for Google login. This skill never signs in on its own and never types credentials.

## Handoffs

- A framework, API or version question → `source-grounding`, not the user's notebooks.
- A notebook answer the plan or a decision depends on → cite the notebook name and the question asked.

## Provenance

`PleasePrompto/notebooklm-skill@c80722d3f27d65e06b6579add201bf69b99101d0` — MIT, archived 2026-09-10, vendored byte-for-byte at `engineering-practices/vendor/notebooklm/` (the upstream tree minus `.git/`; `LICENSE` kept). To refresh, copy a new upstream commit over the folder, diff it, re-check each override row against the new text, and update the commit here.
