---
name: notebooklm
description: Use when querying the user's own Google NotebookLM notebooks for cited answers via browser automation. Triggers "ask my NotebookLM". Not for grounding in official docs (source-grounding).
---

# NotebookLM

Each question opens a real Chrome session (via `patchright`) against Google NotebookLM, reads the answer Gemini builds **only from the sources the user uploaded**, and closes. The value is an answer that cites the user's own documents instead of the model's memory.

The tool is bundled at `engineering-practices/bundled/notebooklm/`. **Its own files are authoritative for the procedure**: authentication, the notebook library, the question interface, the follow-up rule and cleanup. This file states only where the library departs from them. Never paraphrase the bundled files from memory — read them.

## Before first use

Print this line to the user, verbatim, before the first command of a session:

> may break when NotebookLM changes; drives real Chrome via patchright against Google NotebookLM

## Load order

Resolve against `${CLAUDE_PLUGIN_ROOT}/engineering-practices/bundled/notebooklm/` from an installed plugin, or `engineering-practices/bundled/notebooklm/` in this repo.

1. Read the bundled `SKILL.md` end to end, then `AUTHENTICATION.md` before the first sign-in.
2. Run every script through the bundled `scripts/run.py` wrapper by absolute path — `python <bundled>/scripts/run.py <script>.py …`. The wrapper resolves its own directory, so the working directory does not matter. The bundled text's `python scripts/run.py` is relative to the skill directory and fails from anywhere else.
3. Read `references/` only when a command fails.
4. Apply the overrides below. Where one is silent, the bundled text holds.

## Overrides

| Bundled tool | Here | Why |
|---|---|---|
| Runs wherever the skill loads | **Local Claude Code only, never the web UI.** | The tool needs a visible Chrome, Google's network and a persistent profile; the web sandbox blocks them. |
| Any Google account | **A dedicated Google account**, as the bundled text itself advises. Never the user's personal or work account. | Browser automation of a Google product can get an account flagged. |
| Notebooks are whatever the user adds | **Notebooks must be shared publicly, and a notebook holding anything sensitive is never queried.** Ask once, at `notebook_manager.py add`, whether the notebook is safe to share; if the user cannot say, do not add it. | Questions and answers pass through Google and the agent's context. |
| 50 queries/day on a free account, mentioned only in a limitation list | **Before a batch of queries, state the budget:** how many this run will spend against the free-tier daily cap of 50, and how many are left if the user already ran some today. | A follow-up loop can burn the cap silently. |
| "Always ask follow-ups until complete" | Kept, **capped at the stated run budget**. Stop and report the gap when the budget is spent. | The bundled loop has no bound. |
| State and venv under the skill directory | **Not patched** (see Where state lives). | The bundled scripts stay unpatched so the override table above stays the only delta. |

## Where state lives

The tool resolves `SKILL_DIR` from the script's own location (`scripts/config.py`), so everything it writes lands **inside the bundled folder**:

| Path under `bundled/notebooklm/` | Holds |
|---|---|
| `.venv/` | the Python environment, created by `run.py` on first use |
| `data/browser_state/` | the signed-in Chrome profile and `state.json` cookies — **the Google session** |
| `data/auth_info.json`, `data/library.json` | auth status, the notebook library |

- **In this repo** that is the working tree. The root `.gitignore` must ignore `engineering-practices/bundled/notebooklm/data/` and `.venv/`; confirm with `git check-ignore -q` before the first sign-in, and never commit either.
- **From an installed plugin** that is the plugin cache. **A plugin update replaces the folder and wipes the Google session, the library and the venv** — the user signs in and re-adds notebooks again. Tell them this before sign-in. The bundled text says `~/.claude/skills/notebooklm/data/`; that path is wrong for this install.
- The session is a signed-in Google profile on disk. Do not copy it, print it or attach it anywhere.

## Prerequisites

Python 3 and Chrome; `run.py` installs `patchright==1.55.2` and `python-dotenv==1.0.0` into the venv on first use. Sign-in needs a **visible** browser and a person: tell the user a window will open for Google login. This skill never signs in on its own and never types credentials.

## Handoffs

- A framework, API or version question → `source-grounding`, not the user's notebooks.
- A notebook answer the plan or a decision depends on → cite the notebook name and the question asked.
