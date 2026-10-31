# 009 — Adopt six external skills — plan (2026-10-23)

**Goal:** Bring the additive parts of five community skill repos into the library in the house idiom:
four workflow skills **adapted** (`quality-constraints`, `source-grounding`, `decision-interview`,
`test-audit`), one tool skill **vendored** behind a house wrapper (`notebooklm`), and one external
framework **routed to** (`html-video`). Each comes with recorded provenance, registration and
cross-references. Nothing is installed wholesale.

**Status:** Not started. Next: S1–S5. They are independent, each creates only its own new folders, and
they may run side by side. W1 waits for all five, then registers them, writes the provenance, runs the
plan's only gate, and files the plan. After W1, **the user** runs the trigger smoke that CONTRIBUTING
"Testing a new skill" requires. Until then, all six skills are **unverified in a real session**. No
command ships, so the 65-command surface is unchanged. Two adoptions carry standing external risk:
`notebooklm`'s upstream is archived (D5), and `html-video` needs a framework the user installs (D6).

---

## 1. What already exists, and what is missing

Grounded in `engineering-practices/`, `qa/{_shared,java,dotnet}/`, `design/`, the two existing
`ATTRIBUTIONS.md`, `.claude-plugin/marketplace.json`, `CONTRIBUTING.md` "Names and registration" and
`docs/skills-catalog.md`.

| Need | Today | Gap |
|---|---|---|
| An agent polices its own run: it never silences a check, skips or weakens a test, or drops below the coverage floor | The rules are *stated* in CLAUDE.md (acceptance tests read-only, no `OR` assertions, no swallowed errors, 80% branch floor). `verify-before-done` checks evidence *at the end*. Nothing checks the agent *during* the work | **`engineering-practices/quality-constraints`** (S1), from addyosmani `constraint-driven-development` |
| Framework/API/version decisions grounded in the authoritative doc for the **detected** version, with the source cited | "Research-first" and "version-aware" are norms in CLAUDE.md, and `design/ui-ux-pro-max` is cited for design facts. No skill makes a coding agent fetch and cite the doc before deciding | **`engineering-practices/source-grounding`** (S1), from addyosmani `source-driven-development` |
| Closing every open branch of a design or plan, one question at a time, before work starts | `brainstorming` *opens* the space. `requirements-author` (`/dev:refine`) turns a loose ask into requirements. Neither drives an already-shaped design to a decision on every branch | **`engineering-practices/decision-interview`** (S2), from mattpocock `grilling` |
| Finding tests that cost more than they protect | `qa/java/skills/test-quality-check` and `qa/dotnet/skills/test-quality-check` mutation-score tests. That proves a test *catches* faults, not that it is *worth its upkeep*. There is no TS sibling and no pruning pass in any stack | **`qa/_shared/test-audit`** (S3), from gstack `/test-audit` |
| Querying the user's own NotebookLM notebooks for source-grounded answers | — | **`engineering-practices/notebooklm`** + **`engineering-practices/vendor/notebooklm/`** (S4), from PleasePrompto `notebooklm-skill` |
| Rendering an HTML composition to an MP4 (demo or walkthrough assets) | `design/motion` teaches animation presets. There is no path from markup to a video file | **`design/html-video`** (S5), routing to heygen `hyperframes` |

---

## 2. How each one is adopted

The library already has two integration modes. This plan uses both, plus a third for a framework:

| Mode | Precedent | Used for | Why |
|---|---|---|---|
| **Adapt** — rewrite the idea as a house skill and cite provenance | `engineering-practices/` from obra/superpowers | S1, S2, S3 | The value is the idea. The upstream text breaks house rules (inline comments, branch/subagent/tracker workflow, its own vocabulary) |
| **Vendor** — copy upstream byte-for-byte into `<domain>/vendor/<name>/`, unregistered. A registered house wrapper holds only the overrides | `qa/_shared/security-testing/source-audit` → `qa/_shared/vendor/security-audit/` (commit `d001181`) | S4 | It ships runnable scripts whose behaviour must not drift |
| **Route** — a thin house skill that defers to the upstream's own installed skills and teaches only the minimal flow and prerequisites | — (new) | S5 | HyperFrames is a framework (CLI, Puppeteer + FFmpeg engine, Lambda) with 7 skills of its own, installed with `npx hyperframes skills update`. Copying them would duplicate a moving upstream |

**Adapted skills follow `.skill-template/`** (`reference.SKILL.md` for S1/S2, `reviewer.SKILL.md` for S3),
CLAUDE.md's Comments rules, and the topic-only naming rule. Each carries a closing `## Provenance` line:
`<owner>/<repo>@<commit>`, license, adapted | vendored | routed.

---

## 3. The skills, where they live, and who registers them

| Task | `name:` | Folder | Registered in | Upstream (license) |
|---|---|---|---|---|
| S1 | `quality-constraints` | `engineering-practices/quality-constraints/` | `dev` | `addyosmani/agent-skills` → `constraint-driven-development` (MIT) |
| S1 | `source-grounding` | `engineering-practices/source-grounding/` | `dev` | `addyosmani/agent-skills` → `source-driven-development` (MIT) |
| S2 | `decision-interview` | `engineering-practices/decision-interview/` | `dev` | `mattpocock/skills` → `grilling` (MIT) |
| S3 | `test-audit` | `qa/_shared/test-audit/` | `qa-java` · `qa-dotnet` · `qa-typescript` | `garrytan/gstack` → `/test-audit` (MIT) |
| S4 | `notebooklm` | `engineering-practices/notebooklm/` + `engineering-practices/vendor/notebooklm/` (unregistered) | `dev` | `PleasePrompto/notebooklm-skill` (MIT, archived 2026-09-10) |
| S5 | `html-video` | `design/html-video/` | `design` | `heygen-com/hyperframes` (Apache-2.0) |

**Every S task creates only its own new folders.** No S task edits `marketplace.json`, the catalog,
README, an `ATTRIBUTIONS.md`, `.gitignore`, or another skill. That is what lets the five run side by
side in one working tree, because their files are disjoint and there is no build. Every shared-file edit
belongs to W1.

### What each skill must say

- **`quality-constraints`**: a cross-cutting skill, entered anytime and in the same register as
  `dev:verify`. It is loaded by an agent while it works and lists what the agent must not do: edit,
  skip or weaken an acceptance test; add an `OR` assertion; swallow an error; add a lint/analyzer
  suppression without a justification; exclude a file with behaviour from the coverage measure; mark a
  task `DONE` with a red test it did not record. For each item it names the evidence that proves the
  agent didn't, such as the `git diff` scope of the acceptance-test folder or the suppression's
  justification field. It checks against **CLAUDE.md and the plan's acceptance tests**. It does
  **not** adopt upstream's `CONSTRAINTS.md` file, because the rules already have a home (D1).
- **`source-grounding`**: before deciding a framework, API or version question, the agent detects the
  project's version (Version policy), fetches that version's official doc, and cites it (URL plus
  version) in its output. An answer from memory is labelled as such. It names `design/ui-ux-pro-max` as
  the authority for design facts, so the two never compete.
- **`decision-interview`**: one question at a time, never batched. Each answer is restated together with
  the branch it closes or opens. It stops only when no branch is open, then hands the resolved answers to
  `dev:design`'s approval gate or into a plan's `## Answered questions`. It runs in **a single
  interactive session, with no subagents**. It says when to use `/dev:refine` instead: a loose,
  multi-capability ask with no design yet.
- **`test-audit`**: a **read-only sweep saved to `docs/audits/`**, because the naming rule says
  `audit` means exactly that; it follows `code-auditor`'s versioned-file convention. It flags tests
  that assert nothing, duplicate a sibling, are brittle on implementation detail, or break a house
  test rule (one logical assertion, no `OR`, no `try`/`catch` in the body, no sleeps, no conditional
  logic). It ranks them by upkeep against protection and reports in the house review table
  (Severity · Location · Issue · Suggested fix). It **never edits or deletes a test**. It points to
  `test-quality-check` (java · dotnet) as the complement: mutation proves a test catches faults, and
  this skill proves a test is worth keeping.
- **`notebooklm`**: routes into the vendored tree on the `source-audit` model (load order, then
  overrides). It overrides upstream in five places:
  - Before first use it prints *"upstream archived 2026-09-10 — may break; drives real Chrome via
    patchright against Google NotebookLM"*.
  - It runs only in local Claude Code, never the web UI, because upstream's network needs are blocked
    in the sandbox there.
  - It requires a dedicated Google account, as upstream itself advises.
  - Notebooks must be shared publicly, and a notebook holding anything sensitive is never queried.
  - Before a batch of queries it states the per-run query budget against the free-tier daily cap.
- **`html-video`**: if the HyperFrames skills are installed (`/hyperframes`), defer to them. If not,
  give the install line (`npx hyperframes skills update`), the prerequisites (Node 22+, FFmpeg), the
  minimal composition shape (`data-start` / `data-duration`), and the render command, then stop. It
  does not teach Studio, the registry or Lambda. It links the upstream Apache-2.0 license and copies no
  code from the framework.

---

## 4. Cross-references W1 adds

One line each, in the existing skill:

| In | Points to | Line says |
|---|---|---|
| `engineering-practices/brainstorming/SKILL.md` | `decision-interview` | open the space here; close each branch there |
| `engineering-practices/verify-before-done/SKILL.md` | `quality-constraints` | the during-work counterpart to the end-of-work evidence gate |
| `engineering-practices/writing-plans/SKILL.md` | `source-grounding` | a plan's version-bound decision cites its doc |
| `qa/java/skills/test-quality-check/SKILL.md`, `qa/dotnet/skills/test-quality-check/SKILL.md` | `test-audit` | mutation proves it catches faults; `test-audit` proves it's worth keeping |
| `design/motion/SKILL.md` | `html-video` | markup → rendered MP4 |

---

## 5. Tasks

S1–S5 author the skills, and W1 registers, gates and files. This plan writes **no code of its own**:
the deliverables are Markdown, plus S4's vendored third-party Python. So there is **no coverage floor**
(the vendored files are third-party, left out by name per CLAUDE.md) and no telemetry smoke.
**The cost, stated once:** intermediate commits are ungated, so the registration is not known to be
consistent at any boundary before W1, and the plan cannot be stopped halfway and trusted.

### 5a. The gate (runs once, in W1)

1. `python3 tools/plugin-surface-check.py` prints `OK`. This enforces the topic-only names, the
   reserved list, no prefixes, one category per skill, and that every registered path exists.
2. Each new `SKILL.md`'s `name:` equals its folder name, and its `description:` carries trigger
   phrases plus a "Do NOT use for" clause naming its nearest sibling (per `.skill-template/`).
3. `grep -rnE "superpowers:|obra/|~/\.agents|CONSTRAINTS\.md|gh issue|git checkout -b" engineering-practices/{quality-constraints,source-grounding,decision-interview,notebooklm} qa/_shared/test-audit design/html-video`
   returns nothing, so no upstream workflow came along.
4. `test -f engineering-practices/vendor/notebooklm/LICENSE`, and
   `git check-ignore -q engineering-practices/vendor/notebooklm/data/x engineering-practices/vendor/notebooklm/.venv/x`
   succeeds.
5. `diff -r` of the vendored tree against a fresh clone of the upstream at S4's recorded commit
   (excluding `.git/`) is empty, which proves it is byte-for-byte.
6. `engineering-practices/ATTRIBUTIONS.md`, `qa/_shared/ATTRIBUTIONS.md` and `design/ATTRIBUTIONS.md`
   each have a section for every skill this plan put in their domain, giving repo, license, snapshot
   commit, retrieval date and mode.
7. **Trigger-collision review on paper:** for each new skill, write three phrases that should trigger it
   and one that should not. Check each against the descriptions of every skill in the same plugin.
   Rewrite any description where a phrase would plausibly route to a sibling. This is not the real-session
   smoke, which is the user's (§6).

### S1 — `quality-constraints` + `source-grounding`: two `dev` skills from one upstream repo

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering-practices/quality-constraints/SKILL.md` and
`engineering-practices/source-grounding/SKILL.md` exist, each saying what §3 requires of it, each ending in
`## Provenance` naming `addyosmani/agent-skills@<commit>` (MIT, adapted). Neither is registered.
**Depends on:** —
**Budget:** ~110k. CLAUDE.md ~25k, this plan §2/§3 ~8k, `.skill-template/reference.SKILL.md` ~3k,
`engineering-practices/verify-before-done/SKILL.md` as the house register ~8k, the two upstream skills
~15k, two writes ~35k, self-check ~15k.
**Gate: none.** This plan gates once, in W1. Do not run `plugin-surface-check.py` or any of §5a.

- Clone or fetch `addyosmani/agent-skills`, record the commit, and read the two upstream skills.
- One upstream fetch serves both skills, which is why they share a session (D2).
- **Not in S1:** registration, ATTRIBUTIONS and cross-references (W1).

### S2 — `decision-interview`: closing every open branch, one question at a time

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering-practices/decision-interview/SKILL.md` exists, saying what §3 requires, and
ends in `## Provenance` naming `mattpocock/skills@<commit>` (MIT, adapted). Not registered.
**Depends on:** —
**Budget:** ~95k. CLAUDE.md ~25k, this plan §1/§3 ~6k, `.skill-template/reference.SKILL.md` ~3k,
`engineering-practices/brainstorming/SKILL.md` ~8k, `business-analysis/agents/requirements-author.md`
(its interview step only) ~6k, upstream `grilling` + `grill-me` ~6k, the write ~25k, self-check ~15k.
**Gate: none.** Gates in W1.

- Record the upstream commit. Adapt the technique, not the text.
- **Not in S2:** the `brainstorming` pointer (W1).

### S3 — `test-audit`: a saved sweep for tests not worth their upkeep

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/_shared/test-audit/SKILL.md` exists, saying what §3 requires (read-only, saved to
`docs/audits/`, house review table, never edits a test), and ends in `## Provenance` naming
`garrytan/gstack@<commit>` (MIT, adapted). Not registered.
**Depends on:** —
**Budget:** ~100k. CLAUDE.md ~25k, this plan §1/§3 ~6k, `.skill-template/reviewer.SKILL.md` ~3k,
`qa/java/skills/test-quality-check/SKILL.md` ~10k, `engineering-practices/agents/code-auditor.md` (its
`docs/audits/` naming only) ~5k, upstream `/test-audit` ~8k, the write ~28k, self-check ~15k.
**Gate: none.** Gates in W1.

- Stack-agnostic: it names each stack's test runner idioms only as examples and binds to no tool.
- **Not in S3:** the two `test-quality-check` pointers and the three-plugin registration (W1).

### S4 — `notebooklm`: the vendored NotebookLM tool and its house wrapper

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering-practices/vendor/notebooklm/` holds the upstream tree byte-for-byte at a
recorded commit (no `data/`, no `.venv/`), and `engineering-practices/notebooklm/SKILL.md` routes into it
with the §3 overrides and ends in `## Provenance` naming `PleasePrompto/notebooklm-skill@<commit>` (MIT,
archived, vendored). Neither is registered.
**Depends on:** —
**Budget:** ~105k. CLAUDE.md ~25k, this plan §2/§3/D5 ~8k,
`qa/_shared/security-testing/source-audit/SKILL.md` (**the pattern to copy**) ~8k, the upstream tree
(SKILL, three scripts, `requirements.txt`, `AUTHENTICATION.md`) ~22k, the copy and the wrapper ~25k,
self-check ~15k.
**Gate: none.** Gates in W1. **Author only**: no `.venv`, no `pip install`, no query.

- Clone at the archive commit and copy the tree minus `.git/`, `data/` and `.venv/`.
- Read where the scripts write `data/` and `.venv/`. If that is inside the skill directory, an installed
  plugin keeps the Google session in the plugin cache, which a plugin update wipes. The wrapper must
  say so and tell the user where state lives. It does not patch the scripts (D5).
- **Not in S4:** the root `.gitignore` lines and registration (W1).

### S5 — `html-video`: route to HyperFrames for markup → MP4

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `design/html-video/SKILL.md` exists, saying what §3 requires (defer to installed
`/hyperframes`, otherwise the install line, prerequisites, minimal composition and render, then stop), and
ends in `## Provenance` naming `heygen-com/hyperframes@<commit>` (Apache-2.0, routed, no code copied).
Not registered.
**Depends on:** —
**Budget:** ~85k. CLAUDE.md ~25k, this plan §2/§3/D6 ~6k, `design/motion/SKILL.md` ~10k, upstream
README and the `skills/` layout ~12k, the write ~18k, self-check ~14k.
**Gate: none.** Gates in W1. Do not install HyperFrames or render anything.

- Record the commit and confirm the license file says Apache-2.0.
- **Not in S5:** the `design/motion` pointer and registration (W1).

### W1 — Register, attribute, cross-reference, gate and file

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** all six skills are registered as §3 says, with the matching edits:
- `marketplace.json` lists each skill, and the `dev`, `design` and three `qa-*` descriptions name the new
  skills.
- `docs/skills-catalog.md` and `README.md` list each skill, with every count that cites them bumped.
- The three `ATTRIBUTIONS.md` carry one section per skill; `engineering-practices/ATTRIBUTIONS.md` is new.
- The root `.gitignore` excludes `engineering-practices/vendor/notebooklm/{data,.venv}/`.
- The §4 pointers are in place.

§5a passes, and the plan is in `docs/plans/implemented/`.
**Depends on:** S1, S2, S3, S4, S5. It needs each recorded commit and final name from their `As built`
notes.
**Budget:** ~130k. CLAUDE.md ~25k, this plan whole ~14k, `marketplace.json` (the five plugin blocks)
~15k, catalog sections (engineering-practices, qa `_shared`, design) ~14k, README provenance table and
folder lines ~5k, the two existing `ATTRIBUTIONS.md` ~6k, the six new `SKILL.md` frontmatter and the seven
§4 targets ~12k, edits ~25k, gate output ~14k.
**Gate (this is the last runnable task, so it carries the plan's only gate):** §5a, steps 1–7 in order.
Fix what it finds. A bad name, a stray upstream reference or a collision may belong to any S task.

- `ATTRIBUTIONS` entries follow the section shape in `qa/_shared/ATTRIBUTIONS.md` (the `security-audit`
  entry): upstream, snapshot commit, retrieved date, license, and what the house file overrides.
- Update the README provenance table (the `engineering-practices` row now names three more upstreams)
  and the catalog's "6 in-scope skills" and "17 `dev` skills" counts.

---

## 6. After the plan: the trigger smoke (the user)

CONTRIBUTING "Testing a new skill" asks for a real session per skill: three phrases that should trigger
it, one that should not, and, for the one reviewer (`test-audit`), a run against tests with known
defects. W1 can only check descriptions on paper (§5a step 7). **The user** reinstalls `dev`, `design` and
one `qa-*` plugin and runs the smoke. Until then, `Status:` records all six skills as unverified in a
real session. This step has no prompt block, so it does not hold the plan in `docs/plans/`.

---

## Decisions

**D1 — The four workflow skills are adapted, not vendored, and the house rules stay in CLAUDE.md.**
The text of each upstream conflicts with house rules: inline comments, a branch/tracker workflow, and
for `constraint-driven-development` a new `CONSTRAINTS.md` artifact. The rules it would hold already live
in CLAUDE.md and the plan's acceptance tests. **Costs:** the skills drift from upstream, so each records
its snapshot commit to make a later diff possible. Adaptation is also a judgement call per skill.

**D2 — S1 carries both addyosmani skills.** They share one upstream, so one fetch and one commit cover
both. That leaves one fewer session, and the merged task is still ~110k. **Cost:** S1 is the largest
author task.

**D3 — S tasks create only new folders, and every shared file belongs to W1.** This lets S1–S5 run side
by side without colliding on `marketplace.json`, the catalog, README, `.gitignore` or a shared
`ATTRIBUTIONS.md`. **Cost:** W1 is one serialized task touching many files, and nothing is registered
until it lands.

**D4 — `test-audit` lives in `qa/_shared`, ships to all three `qa-*` plugins, and is a saved read-only
sweep.** It is stack-agnostic, so `_shared` fits, and bundling within the `qa` category is the house
rule. Under the one-meaning-per-word rule, the name `audit` commits it to saving its findings to
`docs/audits/`. It never edits a test (review behaviour). **Cost:** one more skill in three manifests,
and a saved file per run.

**D5 — `notebooklm` ships even though its upstream is archived and automates a Google product.**
| Option | Verdict | Why |
|---|---|---|
| Vendor it behind a house wrapper with the banner and overrides | **Chosen** | The user asked for it. Vendoring pins behaviour, and the wrapper makes the risk visible |
| Wait for a maintained fork | Rejected | None is named, and the user asked now |
| Patch the scripts (state location, account handling) | Rejected | It breaks byte-for-byte and makes the vendored tree ours to maintain |

**Costs:** it can stop working on any NotebookLM change, and Google may flag automated use. An installed
plugin may keep the session in its cache, so a plugin update logs the user out (S4 verifies this and
documents it). The vendored Python is third-party tool code. It is not covered by the Python-worker stack
default, which governs services.

**D6 — `html-video` routes to HyperFrames' own skills and copies nothing.** HyperFrames ships 7 skills and
a full framework, and both change upstream. The house skill only routes and covers the fallback flow.
Because no Apache-2.0 code is redistributed, its `NOTICE` duty does not enter the repo; an
`ATTRIBUTIONS` entry and a license link suffice. **Cost:** the capability needs Node 22+, FFmpeg and the
framework on the user's machine, and the skill says so.

**D7 — The rest of the original list is not adopted.**
| Rejected | Why |
|---|---|
| ECC (311 skills, 71 agents, hooks) | Overlaps most of the library and brings back the reviewer/dispatch machinery removed 2026-09-26 |
| ponytail | Its `shortcut:` comment ledger violates the no-inline-comments rule, and KISS already covers its intent |
| caveman | The global concise-reply preference covers it, and compressing output hurts plan and doc quality |
| claude-mem | Duplicates the built-in file memory |
| mattpocock `implement`/`implement-spec`/`triage`/`pr`, gstack `/ship` and role reviews | Assume branches, parallel subagents and an issue tracker, which conflicts with Plan-Queue execution |
| superpowers, ui-ux-pro-max, frontend-design, anthropics/skills | Already in the library or enabled |

## Answered questions (2026-10-23)

**O1 — Adapt, vendor or route each one?** Adapt S1–S3, vendor S4, route S5 (§2, D1, D5, D6).
**O2 — Which plugins?** S1, S2, S4 → `dev`; S3 → all three `qa-*`; S5 → `design` (§3).
**O3 — Ship `notebooklm` despite the archived upstream?** Yes, with the banner and overrides (D5).
**O4 — Skill names?** Topic-only per CONTRIBUTING: `quality-constraints`, `source-grounding`,
`decision-interview` ("requirements" already means `/dev:refine`), `test-audit`, `notebooklm`,
`html-video`.

---

## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit, adding only your own
   files, by path — never `git add -A`.

---

## Prompts — one per task

Run one session per block; each block is complete on its own. S1–S5 can start at once and run side by
side, since their files are disjoint and none builds anything. W1 waits for all five and is the gate.
**No S prompt may edit a file outside its own new folders** apart from this plan's close-out edits. **No
prompt installs or runs** NotebookLM or HyperFrames.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| S1 | `docs` | `general-purpose` | none | S2, S3, S4, S5 | ~110k |
| S2 | `docs` | `general-purpose` | none | S1, S3, S4, S5 | ~95k |
| S3 | `docs` | `general-purpose` | none | S1, S2, S4, S5 | ~100k |
| S4 | `docs` | `general-purpose` | none | S1, S2, S3, S5 | ~105k |
| S5 | `docs` | `general-purpose` | none | S1, S2, S3, S4 | ~85k |
| W1 | `docs` | `general-purpose` | S1, S2, S3, S4, S5 | — | ~130k |
| — | trigger smoke (§6) | **the user** | W1 | — | — |

All six prompts are live; none has landed.

---

### S1 — `quality-constraints` + `source-grounding` (general-purpose, docs)

````
Depends on: none

You are a skill author. Task S1 of docs/plans/009-external-skill-adoption.md: write two new dev skills,
adapted from one upstream repo.

Deliverable: engineering-practices/quality-constraints/SKILL.md and
engineering-practices/source-grounding/SKILL.md exist, each saying what plan §3 requires of it, each
ending in `## Provenance` naming `addyosmani/agent-skills@<commit>` (MIT, adapted). Neither is registered.

Read, in this order:
1. CLAUDE.md: Comments, Test code rules, Planning, Version policy.
2. The plan: §1 (first two rows), §2, §3 (the table, plus "What each skill must say" for these two),
   D1, D2, and "Close-out — every task".
3. .skill-template/reference.SKILL.md: the frontmatter and section shape.
4. engineering-practices/verify-before-done/SKILL.md: the register quality-constraints sits beside.
5. Upstream: clone github.com/addyosmani/agent-skills, record `git rev-parse HEAD`, and read
   constraint-driven-development and source-driven-development.

Traps:
- Adapt the idea; do not paste. Upstream's CONSTRAINTS.md artifact is not adopted (D1). The rules live
  in CLAUDE.md and the plan's acceptance tests.
- name: is topic-only and must equal the folder name. description: has trigger phrases and a
  "Do NOT use for" clause naming the nearest sibling (dev:verify; design/ui-ux-pro-max).
- Create only the two folders. No marketplace.json, catalog, README, ATTRIBUTIONS or cross-reference
  edits: those are W1's.

Gate: none. This plan gates once, in W1. Do not run tools/plugin-surface-check.py or any §5a step.

Commit: `feat(dev): quality-constraints and source-grounding skills (009 S1)`.
Put the upstream commit and both names in your As built note, since W1 reads them.
Close out per the plan's "Close-out — every task" before you stop.
````

### S2 — `decision-interview` (general-purpose, docs)

````
Depends on: none

You are a skill author. Task S2 of docs/plans/009-external-skill-adoption.md: write a new dev skill that
closes every open branch of a design, one question at a time.

Deliverable: engineering-practices/decision-interview/SKILL.md exists, saying what plan §3 requires, and
ends in `## Provenance` naming `mattpocock/skills@<commit>` (MIT, adapted). Not registered.

Read, in this order:
1. CLAUDE.md: Comments, Planning.
2. The plan: §1 (third row), §2, §3 (the table, plus "What each skill must say" → decision-interview),
   and "Close-out — every task".
3. .skill-template/reference.SKILL.md.
4. engineering-practices/brainstorming/SKILL.md: the skill this one complements.
5. business-analysis/agents/requirements-author.md: its interview step only. It is the /dev:refine front
   door, and your skill must say when to send the user there instead.
6. Upstream: clone github.com/mattpocock/skills, record `git rev-parse HEAD`, and read grilling and
   grill-me.

Traps:
- One interactive session. Describe no subagents.
- Do not use the word "requirements" in the name or the trigger phrases; that is /dev:refine's.
- Do not edit brainstorming/SKILL.md. W1 adds the pointer.

Gate: none. Gates in W1.

Commit: `feat(dev): decision-interview skill (009 S2)`.
Put the upstream commit in your As built note.
Close out per the plan's "Close-out — every task" before you stop.
````

### S3 — `test-audit` (general-purpose, docs)

````
Depends on: none

You are a skill author. Task S3 of docs/plans/009-external-skill-adoption.md: write a stack-agnostic qa
skill that sweeps a suite for tests not worth their upkeep.

Deliverable: qa/_shared/test-audit/SKILL.md exists, saying what plan §3 requires (read-only, saved to
docs/audits/, house review table, never edits a test), and ends in `## Provenance` naming
`garrytan/gstack@<commit>` (MIT, adapted). Not registered.

Read, in this order:
1. CLAUDE.md: Test code rules, Review behavior.
2. The plan: §1 (fourth row), §2, §3 (the table, plus "What each skill must say" → test-audit), D4, and
   "Close-out — every task".
3. .skill-template/reviewer.SKILL.md.
4. qa/java/skills/test-quality-check/SKILL.md: the mutation complement. There is no qa/_shared or TS
   version.
5. engineering-practices/agents/code-auditor.md: only how it names and versions files in docs/audits/.
6. Upstream: clone github.com/garrytan/gstack, record `git rev-parse HEAD`, and read /test-audit.

Traps:
- "audit" in a name means a saved read-only sweep (CONTRIBUTING "Names and registration"). The skill
  writes its report to docs/audits/ and changes no test.
- Stack-agnostic: name runner idioms only as examples. Bind to no tool.
- Do not edit either test-quality-check. W1 adds the pointers and the three-plugin registration.

Gate: none. Gates in W1.

Commit: `feat(qa): test-audit skill (009 S3)`.
Put the upstream commit in your As built note.
Close out per the plan's "Close-out — every task" before you stop.
````

### S4 — `notebooklm` (general-purpose, docs)

````
Depends on: none

You are a skill author. Task S4 of docs/plans/009-external-skill-adoption.md: vendor the NotebookLM tool
byte-for-byte and write the house wrapper, exactly as source-audit wraps the vendored security-audit.
You author only. Never create .venv, pip install, sign in or query.

Deliverable: engineering-practices/vendor/notebooklm/ holds the upstream tree byte-for-byte at a
recorded commit (no data/, no .venv/), and engineering-practices/notebooklm/SKILL.md routes into it with
the plan §3 overrides and ends in `## Provenance` naming `PleasePrompto/notebooklm-skill@<commit>` (MIT,
archived, vendored). Neither is registered.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3 (the table, plus "What each skill must say" → notebooklm), D5, and
   "Close-out — every task".
3. qa/_shared/security-testing/source-audit/SKILL.md: the pattern to copy (frontmatter, "Load order"
   resolving ${CLAUDE_PLUGIN_ROOT}/…/vendor/…, then "Overrides").
4. Upstream: clone github.com/PleasePrompto/notebooklm-skill, record `git rev-parse HEAD`, and read
   SKILL.md, scripts/*.py, requirements.txt and AUTHENTICATION.md.

Traps:
- Copy the tree minus .git/, data/ and .venv/, and change nothing. W1 diffs it against upstream at your
  commit.
- Find where the scripts put data/ and .venv/. If that is under the skill directory, an installed plugin
  keeps the Google session in the plugin cache and an update wipes it. Say so in the wrapper; do not
  patch the scripts (D5).
- Do not edit the root .gitignore; W1 adds the data/.venv lines. Do not register.

Gate: none. Gates in W1.

Commit: `feat(dev): vendor notebooklm-skill behind a house wrapper (009 S4)`.
Put the upstream commit and where state lives in your As built note.
Close out per the plan's "Close-out — every task" before you stop.
````

### S5 — `html-video` (general-purpose, docs)

````
Depends on: none

You are a skill author. Task S5 of docs/plans/009-external-skill-adoption.md: write a thin design skill
that routes markup→MP4 work to HyperFrames' own skills, with a minimal fallback. Copy no framework code.

Deliverable: design/html-video/SKILL.md exists, saying what plan §3 requires (defer to an installed
/hyperframes; otherwise install line, prerequisites, minimal composition and render, then stop), and ends
in `## Provenance` naming `heygen-com/hyperframes@<commit>` (Apache-2.0, routed, no code copied). Not
registered.

Read, in this order:
1. CLAUDE.md: Comments; "Design facts come from the vendored corpus".
2. The plan: §2 (the Route row), §3 (the table, plus "What each skill must say" → html-video), D6, and
   "Close-out — every task".
3. design/motion/SKILL.md: the house register and the sibling it routes from.
4. Upstream: github.com/heygen-com/hyperframes. Record the HEAD commit and read the README, the skills/
   layout and LICENSE (confirm Apache-2.0).

Traps:
- Route, don't re-teach. No Studio, registry or Lambda content.
- Copy no upstream file; link the license. The Apache NOTICE duty stays out of the repo (D6).
- Do not edit design/motion/SKILL.md and do not register; both are W1's.

Gate: none. Gates in W1. Do not install HyperFrames or render.

Commit: `feat(design): html-video skill routing to HyperFrames (009 S5)`.
Put the upstream commit and the confirmed license in your As built note.
Close out per the plan's "Close-out — every task" before you stop.
````

### W1 — register, attribute, cross-reference, gate, file (general-purpose, docs)

````
Depends on: S1, S2, S3, S4, S5

You are a skill author. Task W1 of docs/plans/009-external-skill-adoption.md: the six skills exist,
unregistered. Register them, record provenance, add the pointers, run the plan's only gate, and file
the plan.

Deliverable: all six skills are registered as plan §3 says, with the matching edits:
- marketplace.json lists each skill, and the dev, design and three qa-* descriptions name the new skills.
- docs/skills-catalog.md and README.md list each skill, with every count that cites them bumped.
- The three ATTRIBUTIONS.md carry one section per skill; engineering-practices/ATTRIBUTIONS.md is new.
- The root .gitignore excludes engineering-practices/vendor/notebooklm/{data,.venv}/.
- The §4 pointers are in place.
§5a passes, and the plan is in docs/plans/implemented/.

Read, in this order:
1. CLAUDE.md, and CONTRIBUTING.md "Names and registration".
2. The plan, whole. Above all §3, §4, §5a, §6, and every S task's As built note: the commits and the
   final names.
3. .claude-plugin/marketplace.json: the dev, design, qa-java, qa-dotnet and qa-typescript blocks. Match
   the shape of their "skills" arrays. qa/_shared/security-testing/source-audit shows a qa/_shared skill
   registered in all three.
4. qa/_shared/ATTRIBUTIONS.md (the security-audit section is the entry shape) and design/ATTRIBUTIONS.md.
5. docs/skills-catalog.md: the engineering-practices catalog (the "6 in-scope skills" and "17 dev
   skills" counts), the qa _shared list and the design list. In README.md: the folder line for
   engineering-practices and the provenance table row.
6. The seven §4 target files.

Gate (this is the last runnable task, so it carries the plan's only gate): §5a steps 1–7, in order.
`python3 tools/plugin-surface-check.py` must print OK. Fix what the gate finds; a bad name, a stray
upstream reference or a description collision may belong to any S task.

Traps:
- Register each skill in exactly the plugins §3 names. A skill folder is never registered by plugins of
  two categories.
- engineering-practices/vendor/notebooklm/ stays unregistered.
- Step 5 needs a fresh clone of the upstream at S4's commit in a scratch directory, never inside the repo.

Commit: `feat: register and attribute the six adopted skills; gate passed (009 W1)`.
Finish by telling the user the §6 trigger smoke is theirs to run, naming the plugins to reinstall.
Close out per the plan's "Close-out — every task" before you stop. Your deletion leaves no blocks, so
rewrite Status one final time (all six unverified in a real session until §6) and git mv this plan into
docs/plans/implemented/.
````
