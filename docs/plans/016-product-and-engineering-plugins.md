# 016 — `product` and `engineering`: one plugin for planning, documentation and analysis — plan (2026-11-20)

**Goal:** Replace the `dev` and `business-analysis` plugins with two plugins.
- **`product`** holds all planning, documentation, requirements and business-analysis work, in one
  folder, `product/`.
- **`engineering`** holds the technical workflow that every stack plugin depends on: debugging,
  verify-before-done, quality-constraints, source-grounding, the code audits. Its folder is
  `engineering/`, renamed from `engineering-practices/`.

The `be-documenter` and `be-feature-documenter` agents drop their `be-` prefix. Every reference in the
library moves to the new paths and names. A project switches over through the migration section that
M3 writes.

**Status:** Written 2026-11-20 from the owner's interview (`## Answered questions (2026-11-20)`).
M1, M2 and M3 are built (2026-11-20): `product/` and `engineering/` hold the moved tree, the manifest
registers both, every path and name uses the new ones, and the catalog, `README.md` (with the switch
section), `CONTRIBUTING.md`, `CLAUDE.md` and the owner's `~/.claude/CLAUDE.md` describe them. Built but
unverified: Claude Code loading the two new plugins (needs a restart), and any project switched over.
- **Starts after 015 merges into `master`.** 015 edits many of the files this plan moves. Running both
  at once would turn every 015 edit into a conflict on a moved path (D6).
- **Next:** G1.
- **Known conflict:** branch `plan-queue/010-agents-md-dual-harness-b58e49` has 2 commits touching 2
  files this plan moves. Whichever of 010 and 016 merges second resolves them against the new paths.
- **Metered:** about 4 sessions of subscription usage. The user starts the queue.

**Test design:** none. The plan serves no stories and changes skill text, manifests and two lint
scripts. The checks are `tools/plugin-surface-check.py`, `tools/skill-lint.py`, `tools/token-audit.py`
and `tools/test_skill_lint.py`, which already exist, plus the greps in §5.

**Documentation task:** none. This is the skills library, and the skill text is the documentation. M3
updates the catalog, `README.md`, `CONTRIBUTING.md` and `CLAUDE.md` from the moved tree. No product
behaviour changes for a documenter to trace.

**Telemetry smoke:** none. No service is built.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| One plugin for planning, documentation, requirements and business analysis | Split three ways. `dev` ships the feature interview, `writing-plans` and `domain-modeling` (in `engineering-practices/`), the eight planning skills, `solution-planner` and the three documentation skills and two documenter agents (in `backend/_shared/`), and `requirements-author` (in `business-analysis/agents/`). The `business-analysis` plugin ships the ten `ba-*` skills that `requirements-author` runs, and it depends on `dev` (`.claude-plugin/marketplace.json`) | Everything moves to `product/` and registers as `product` (M1) |
| A small technical plugin the stacks depend on | `dev` doubles as it. 17 plugins list `dev` in `dependencies`, and stack text calls `dev:verify` 49 times and `dev:debugging` 48 times | `engineering`, with what is left of `engineering-practices/` (M1). Every `dev:` call is renamed (M2) |
| Documenter names that fit their scope | `be-documenter` and `be-feature-documenter` document every stack but carry the backend prefix. `plan-format.md` §5 and `CLAUDE.md` "Planning" name them as the `DOC1` agent | Renamed to `documenter` and `feature-documenter` (M1 renames the files, M2 renames the references) |
| One rules skill per plugin | `dev:rules` installs `plans.md`, `audits.md` and `feature-docs.md` to `.claude/rules/dev/`. `business-analysis:rules` installs nine files to `.claude/rules/business-analysis/` | `product:rules` installs its eleven files to `.claude/rules/product/`. `engineering:rules` installs `audits.md` to `.claude/rules/engineering/` (M1) |
| Stack hand-offs that work without `product` | Stacks get planning through `dev`, so `/dev:refine` and `/dev:feature` always resolve | Stacks depend on `engineering` only (D4). Each stack hand-off to a `product` skill or command says it needs `product` enabled (M2) |
| A project can switch over | — | M3 writes the switch into `README.md` and updates the owner's `~/.claude/CLAUDE.md` (D8) |
| The library's own docs describe the new layout | The catalog, `README.md`, `CONTRIBUTING.md` and `CLAUDE.md` describe `dev` and `business-analysis` | M3 |

## 2. The target layout

Every move is a `git mv`, so history follows the file. The folder names inside `product/skills/` keep
their old basenames (D5). Paths are relative to the repo root.

| From | To | Plugin |
|---|---|---|
| `engineering-practices/brainstorming/` | `product/skills/brainstorming/` | product |
| `engineering-practices/writing-plans/` | `product/skills/writing-plans/` | product |
| `engineering-practices/domain-modeling/` | `product/skills/domain-modeling/` | product |
| `engineering-practices/notebooklm/` | `product/skills/notebooklm/` | product |
| `engineering-practices/bundled/notebooklm/` | `product/bundled/notebooklm/` | product |
| `engineering-practices/rules/plans.md`, `feature-docs.md` | `product/skills/rules/` | product |
| `engineering-practices/commands/{refine,plan-system,document-system,document-feature}.md` | `product/commands/` | product |
| `backend/_shared/{solution-blueprint,data-model-plan,experience-plan,api-surface-plan,integration-plan,epic-map,delivery-plan,session-budget,codebase-survey,feature-trace,business-documentation}/` | `product/skills/<same name>/` | product |
| `backend/_shared/agents/solution-planner.md` | `product/agents/solution-planner.md` | product |
| `backend/_shared/agents/be-documenter.md` | `product/agents/documenter.md` | product |
| `backend/_shared/agents/be-feature-documenter.md` | `product/agents/feature-documenter.md` | product |
| `business-analysis/agents/{business-analyst,requirements-author}.md` | `product/agents/` | product |
| `business-analysis/commands/business-analysis.md` | `product/commands/business-analysis.md` | product |
| `business-analysis/skills/ba-*/` (ten folders) | `product/skills/ba-*/` | product |
| `business-analysis/skills/rules/*.md` except `SKILL.md` (nine rule files) | `product/skills/rules/` | product |
| `business-analysis/skills/rules/SKILL.md` and `engineering-practices/rules/SKILL.md` | merged into a new `product/skills/rules/SKILL.md` (§3) | product |
| `engineering-practices/rules/audits.md` | `engineering/rules/audits.md` | engineering |
| `engineering-practices/commands/audit.md` | `engineering/commands/audit.md` | engineering |
| everything else in `engineering-practices/` | `engineering/<same path>` | engineering |

What does not move:
- `backend/_shared/code-review/` and `backend/_shared/pattern-guide/` stay, because the `be-*` plugins
  bundle them.
- `extras/` and `communication/` stay (O11).

After the moves, `backend/_shared/agents/` and `business-analysis/` are empty and gone.

**The manifests** (`.claude-plugin/marketplace.json`):
- **`engineering`.** Skills: `systematic-debugging`, `verify-before-done`, `quality-constraints`,
  `source-grounding`, `writing-for-agents`, `spec-vs-code-audit`, `feature-audit`, `rules`. Agent:
  `code-auditor`. Command: `audit`. Dependencies: none.
- **`product`.** Skills: `brainstorming`, `writing-plans`, `domain-modeling`, `notebooklm`, the eleven
  planning and documentation skills, the ten `ba-*` skills, `rules`. Agents: `solution-planner`,
  `documenter`, `feature-documenter`, `requirements-author`, `business-analyst`. Commands: `refine`,
  `plan-system`, `document-system`, `document-feature`, `business-analysis`. Dependencies:
  `["engineering"]`. Its planners and documenters load `agent-orientation-cache` (7 references) and
  `source-grounding` (3).
- **`dependencies`.** The 17 plugins that list `dev` list `engineering` instead. None lists `product`
  (D4).
- **Unregistered folders.** `agent-orientation-cache`, `code-comments` and `standards-audit-engine`
  stay unregistered and are loaded by path, as now.

**Paths still resolve without `product`.** Every plugin's `source` is `./`, the whole repo. A stack file
that loads `${CLAUDE_PLUGIN_ROOT}/product/skills/writing-plans/references/plan-format.md` by path finds
it whether or not `product` is enabled. Only a skill or command invoked by name (`product:feature`,
`/product:refine`) needs the plugin enabled (D4).

## 3. The name map

The skill `name:` values do not change. Only the plugin prefix in front of them changes.

| Old | New |
|---|---|
| `dev:debugging`, `dev:verify`, `dev:quality-constraints`, `dev:source-grounding`, `dev:writing-for-agents`, `dev:audit-spec`, `dev:audit-feature` | `engineering:<same>` |
| `dev:feature`, `dev:plan-feature`, `dev:domain-modeling`, `dev:notebooklm`, `dev:plan-blueprint`, `dev:plan-data-model`, `dev:plan-experience`, `dev:plan-api-surface`, `dev:plan-integrations`, `dev:plan-epic-map`, `dev:plan-delivery`, `dev:plan-session-budget`, `dev:doc-codebase-survey`, `dev:doc-feature-trace`, `dev:doc-business-model` | `product:<same>` |
| `dev:rules` | `product:rules` where the text is about plans or feature docs, `engineering:rules` where it is about audits |
| `/dev:refine`, `/dev:plan-system`, `/dev:document-system`, `/dev:document-feature` | `/product:<same>` |
| `/dev:audit` | `/engineering:audit` |
| `business-analysis:<skill>` (scoping, epics, stories, story-review, knowledge-base, process-flow, state-grid, decision-table, dependency-map, conflict-check, rules) | `product:<same>` |
| `/business-analysis:business-analysis` | `/product:business-analysis` |
| `be-documenter` | `documenter` |
| `be-feature-documenter` | `feature-documenter` |
| `.claude/rules/dev/` | `.claude/rules/product/` (plans, feature docs), `.claude/rules/engineering/` (audits) |
| `.claude/rules/business-analysis/` | `.claude/rules/product/` |
| the plugin names `dev` and `business-analysis` in prose | `engineering` or `product`, by what the sentence is about |

**Only the names in this table are rewritten.** `dev:run` in `security/commands/assess-repo.md:22` is
the target repo's own skill, not one of ours, and it stays as it is. So does `pnpm dev:…` and any other
`dev:` that is not followed by a name in this table.

**The merged `product:rules` skill** keeps the procedure, report and run-by-a-person-or-model sections of
`engineering-practices/rules/SKILL.md`. It changes three things:
- The target is `.claude/rules/product/`.
- The file table lists all eleven rule files with their `paths:` globs. It takes the nine
  business-analysis rows from `business-analysis/skills/rules/SKILL.md`.
- One step removes the old folders. When `.claude/rules/dev/plans.md`, `.claude/rules/dev/feature-docs.md`
  or anything in `.claude/rules/business-analysis/` is identical to the plugin's copy, the skill deletes
  it. When one differs, the skill asks, as step 4 does.

**`engineering:rules`** is the same skill cut down to `audits.md`, with target
`.claude/rules/engineering/`. It has the same old-folder step for `.claude/rules/dev/audits.md`.

## 4. How the rewrite is done

M1 and M2 each write a Python script in the session's scratchpad and run it. The scripts never sit in
the repo. A script holds the §2 or §3 table as data and rewrites only exact matches.

**Never rewritten:**
- `docs/plans/implemented/`. Filed plans are never edited.
- `docs/audits/`. Audit rounds are never rewritten.
- This plan file. It names the old paths on purpose.
- `tools/fixtures/` and the synthetic marketplaces inside `tools/test_skill_lint.py`. Their `dev` is a
  made-up plugin, and the tests assert on it.
- `.git/`.

**Rewritten:**
- The live plans in `docs/plans/` (005, 006, 007, 013, 015), whose prompts are living text.
- Every other tracked file.

**Rewritten by hand, after the script:** each stack-side reference to a `product` skill or command. The
script finds them, but the sentence around each one has to change. About 21 references sit outside
`engineering/` and `product/`: `dev:refine` 7, `dev:doc-feature-trace` 6, `dev:feature` 4,
`dev:plan-system` 2, `dev:plan-api-surface` 1, plus `requirements-author` and documenter hand-offs. Each
one keeps the hand-off and adds that it needs `product` enabled. For example: "hand to `/product:refine`
(the `product` plugin; when the project does not enable it, say so and stop)". The `engineering:` calls
need no such note, because every stack depends on `engineering`.

## 5. What G1 sweeps

```bash
python3 tools/plugin-surface-check.py                   # OK
python3 tools/skill-lint.py | tail -1                   # findings ≤ the count in M1's As built note
python3 tools/token-audit.py --violations-only          # exit 0
python3 -m pytest tools/test_skill_lint.py -q           # green
python3 tools/qa-version-check.py                       # OK
X='--exclude-dir=implemented --exclude-dir=audits --exclude-dir=fixtures --exclude-dir=.git'
grep -rnE $X 'engineering-practices/|backend/_shared/(solution-blueprint|data-model-plan|experience-plan|api-surface-plan|integration-plan|epic-map|delivery-plan|session-budget|codebase-survey|feature-trace|business-documentation|agents)|business-analysis/' . | grep -v '^./docs/plans/016-'   # prints nothing
grep -rnE $X '\bdev:(debugging|verify|quality-constraints|source-grounding|writing-for-agents|audit|audit-spec|audit-feature|feature|plan-[a-z-]+|domain-modeling|notebooklm|doc-[a-z-]+|rules|refine|document-system|document-feature)\b|business-analysis:|be-(feature-)?documenter|rules/dev/|rules/business-analysis/' . | grep -v '^./docs/plans/016-' | grep -v '^./tools/test_skill_lint.py'   # prints nothing
python3 -c "import json;d=json.load(open('.claude-plugin/marketplace.json'));n={p['name'] for p in d['plugins']};assert {'engineering','product'}<=n and not n&{'dev','business-analysis'};print('OK')"
```

What none of these can show is whether Claude Code loads the two new plugins. The surface check proves
every registered path exists, and the user proves the rest after a restart (Status).

**What a halfway stop leaves:**
- After M1: the tree is moved and the surface check is green, but text still calls the old names.
  `dev:verify` reaches nothing until M2 lands.
- After M2: the library works under the new names, but the catalog, README and migration section still
  describe the old layout.

## 6. Decisions

**D1 — `dev` is renamed, not kept.** Its non-technical half becomes `product`, and its technical half
moves out into `engineering`. Owner's answer to O1.

| Option | Verdict | Why |
|---|---|---|
| Rename `dev` and move the technical half out | **chosen** | The owner's answer. A plugin named `dev` that holds the requirements interview and the business analyst reads wrong |
| Split `dev`, keeping its name for the technical half | rejected | Fewer renames of `dev:verify`. But the owner chose a clean name for each half |
| Fold `business-analysis` into `dev` and keep the name | rejected | Fewest renames, but "dev" keeps covering non-technical work |

Cost: about 230 files change, and every project that enables `dev` or `business-analysis` switches over
(§3, M3).

**D2 — `product` holds planning, documentation, requirements and all of business analysis.** The code
and spec audits stay with the technical half, because they read code. The office-document skills in
`extras/` stay out. Owner's answers to O2 and O6.

**D3 — The technical skills form their own plugin, `engineering`.** They are not copied into each
stack. That follows the "bundle within a category, depend across categories" rule. Owner's answer to O3.
Cost: `dev:verify` and `dev:debugging` are renamed in about 100 places.

**D4 — Stacks depend on `engineering` only, and `product` is enabled per project.** A stack hand-off to
`product` names the plugin and stops when the project lacks it (§4). Owner's answer to O4.

Cost: a project that enables only a stack plugin no longer gets the planning lane by default. Today it
does, through `dev`. Path-loaded files still resolve (§2). Only invocation by name needs the plugin.

**D5 — One folder per plugin, and folder basenames kept.** `product/skills/ba-scoping-writeup/` keeps
its name. The `ba-` prefix is on the folder, never on the skill name, so the surface check's
banned-prefix rule is not hit. Renaming the ten folders would add churn for no reader. Owner's answer to
O5 (one folder) and O10 (`engineering/` too).

**D6 — The plan runs after 015 merges.** 015 edits `writing-plans`, `delivery-plan`, `session-budget`,
the documenter agents and the BA agents. Moving them under it would turn each of its tasks into a
conflict. Owner's answer to O7.

| Option | Verdict | Why |
|---|---|---|
| Plan now, run after 015 | **chosen** | No conflicts. 015's prompts stay valid |
| Pause 015, restructure first | rejected | Every 015 prompt would have to be rewritten to the new paths |
| Run side by side | rejected | Merge conflicts on every moved file 015 touches |

**D7 — `writing-plans`, with the plan-format contract and `rules/plans.md`, belongs to `product`.**
Stack and qa agents that execute a plan task read plan-format by path, which still resolves (§2). Their
prompt already carries the rules they need. Owner's answer to O8.

**D8 — The old plugin names are removed outright, with a migration section and no alias stubs.** M3
writes the per-project switch and edits the owner's `~/.claude/CLAUDE.md`. Owner's answers to O9 and O12.

**D9 — (2026-11-20, M2) `dev:scoping`, `dev:epics`, `dev:stories`, `dev:story-review` and
`dev:knowledge-base` were rewritten too.** §3 lists `business-analysis:<skill>` for these names, but the
old `dev` plugin registered the same five skills (015 O10), so text called them `dev:<name>` as well.
Leaving them would have left about 64 calls that reach nothing. They became `product:<name>`. Reading A (§3 as
written) keeps them as `dev:`; reading B (built) renames them. A `dev:` name that is not ours (`dev:run`)
stays. Cost: none beyond the diff.

**D10 — (2026-11-20, M3) `product` registers 26 skills, not 25.** M1's As built and the catalog's plugin
table (M2) said 25. The manifest lists 26: `brainstorming`, `writing-plans`, `domain-modeling`,
`notebooklm`, the eleven planning and documentation skills, the ten `ba-*` skills and `rules`, which is
§2's own list. Reading A (25) was a miscount; reading B (26, built) is what `marketplace.json` holds. M3
corrected the catalog and README. Cost: none.

**D11 — (2026-11-20, M3) The README switch section avoids the colon forms of the old names.** §3 and §5's
second grep treat `dev:rules`, `business-analysis:` and `rules/dev/` as stale anywhere outside the plan.
The migration section has to name the old plugins, so it names them as the `dev` and `business-analysis`
plugins and the folders `.claude/rules/dev` and `.claude/rules/business-analysis` (no trailing slash), and
gives the prefix change in prose. Reading A (write `dev:verify` in a table) fails G1's grep; reading B (built)
passes it and reads as well. Cost: no example of an old typed name.

## Answered questions (2026-11-20)

**O1 — What happens to `dev`: split it, make it the one plugin, or rename it and move the technical half out: rename `dev`, move the technical half out.**
**O2 — What goes into the one non-technical plugin: planning, docs and requirements, and all of business-analysis. Not the office documents from `extras/`, and not the code and spec audits.**
**O3 — Where the technical skills go: a new plugin, `engineering`, that every stack depends on.**
**O4 — Do stacks also depend on the non-technical plugin: no. It is enabled per project, and stack hand-offs to it say so.**
**O5 — Do the files move into one folder per plugin: yes, one folder.**
**O6 — The plugin's name: `product`.**
**O7 — When the restructure runs: plan now, run after 015 merges.**
**O8 — Which plugin owns `writing-plans`: `product`.**
**O9 — How the old names retire: removed, with a migration task, no alias stubs.**
**O10 — Which borderline skills move to `product`: `domain-modeling`, `notebooklm` and the feature interview. `writing-for-agents` stays in `engineering`. The documenters drop their `be-` prefix, and `engineering-practices/` is renamed `engineering/`.**
**O12 — Does the migration edit the owner's `~/.claude/CLAUDE.md` or only list the change: edit it.**

## Open questions

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| O11 | `communication/` (`stakeholder-updates`, `meeting-notes`) is under construction and unregistered. It is non-technical work. Should it join `product` when it leaves construction? | (a) yes, as `product` skills · (b) its own plugin · (c) decide then | nothing in this plan | the owner |

## 7. Tasks

### M1 — The two folders, the manifests, the rules skills and the lint scripts

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `product/` and `engineering/` hold every file §2 maps to them, and
`.claude-plugin/marketplace.json` registers `engineering` and `product` and no `dev` or
`business-analysis`. `python3 tools/plugin-surface-check.py` prints OK.
**Depends on:** — (015 merged into `master`, D6).
**Budget:** ~150k. Drivers:
- `CLAUDE.md` 25k.
- This plan §2–§4 12k.
- The `dev`, `business-analysis` and stack entries of `marketplace.json` ~25k.
- `tools/plugin-surface-check.py` and `tools/skill-lint.py` ~15k.
- Both rules `SKILL.md` files ~10k.
- The move script and its output ~25k.
- The new `product:rules` and `engineering:rules` ~20k.
- The check output ~15k.

**Gate: own tests.**
- `python3 tools/plugin-surface-check.py`
- `python3 -m pytest tools/test_skill_lint.py -q`
- `python3 tools/skill-lint.py product engineering | tail -1`

- **Baseline.** Record `python3 tools/skill-lint.py | tail -1` before any change, in As built. G1
  compares against it.
- **The move.** A scratchpad script runs §2's table as `git mv`, then deletes the emptied
  `backend/_shared/agents/` and `business-analysis/`.
- **Rules skills.** Write `product/skills/rules/SKILL.md` and `engineering/rules/SKILL.md` per §3.
  `name: rules` in both. Descriptions follow R1 of
  `engineering/writing-for-agents/SKILL.md`: "Use when installing or updating the product
  standards…" and "…the engineering standards…".
- **Manifest.** Replace the `dev` and `business-analysis` entries with `engineering` and `product` (§2),
  each with the skills, agents, commands and dependencies §2 lists. Write each description from the two
  old ones, keeping only what moved into that plugin:
  - `engineering`: "The technical workflow every stack plugin depends on: …".
  - `product`: "Planning, documentation, requirements and business analysis for a project: …".

  Replace `dev` with `engineering` in all 17 `dependencies` arrays.
- **`tools/plugin-surface-check.py`.** Split `FRONT_DOORS["dev"]`:
  - `engineering`: `debugging verify quality-constraints source-grounding writing-for-agents audit-spec audit-feature`.
  - `product`: `feature plan-feature notebooklm`.

  Rewrite any comment or docstring path that names `engineering-practices/`.
- **`tools/skill-lint.py`.** Rewrite the docstring path at `:2`, and any path constant naming a moved
  folder.
- **`tools/test_skill_lint.py`.** Only the real-path case at `:92` becomes `engineering/debugging/`.
  Its synthetic `dev` marketplaces stay (§4).
- **Not in M1:**
  - Rewriting references inside the moved files or anywhere else (M2).
  - The catalog, README, CONTRIBUTING and `CLAUDE.md` (M3).
  - The surface check passes on paths alone, so text that still says `dev:verify` is expected after M1
    (§5 halfway stop).

- **As built (2026-11-20):**
  - Baseline before any change: `python3 tools/skill-lint.py | tail -1` → `0 findings`. After M1 it is
    `31 findings`, all R8 and all from moved paths: relative links crossing a moved folder
    (`../../../engineering-practices/…`, `…/backend/_shared/experience-plan/…`) and three `references/…`
    pointers that resolved through a code-span skill path now stale (`product/agents/documenter.md:43`,
    `devops/agents/devops-auditor.md:36`, `qa/manual/agents/qa-feature-spec-writer.md:23`). M2 fixes them
    (its gate is at or below 0).
  - The move: 44 `git mv` steps run from a scratchpad script (not in the repo), then
    `engineering-practices/` → `engineering/` whole. `business-analysis/` and `backend/_shared/agents/`
    are gone; `backend/_shared/` holds `code-review/` and `pattern-guide/` only. The old
    `business-analysis/skills/rules/SKILL.md` is deleted (merged into `product/skills/rules/SKILL.md`).
  - `.claude-plugin/marketplace.json`: `engineering` (8 skills, `code-auditor`, `/audit`, no
    dependencies) and `product` (25 skills, 5 agents, 5 commands, depends on `engineering`) replace `dev`
    and `business-analysis`. 16 stack and cross-category plugins plus `product` list `engineering`
    (that is the plan's "17"); nothing lists `product`.
  - `product/skills/rules/SKILL.md` lists all eleven files with their `paths:`; step 5 retires
    `.claude/rules/dev/{plans,feature-docs}.md` and `.claude/rules/business-analysis/*`.
    `engineering/rules/SKILL.md` is `audits.md` only, step 5 retires `.claude/rules/dev/audits.md`.
    For a differing old file, `replace` deletes it; `keep`, `beside` and nobody-to-ask keep it and list it.
  - `tools/plugin-surface-check.py` FRONT_DOORS split; `tools/skill-lint.py:2` and
    `tools/test_skill_lint.py:92` re-pathed.
  - Gate: `python3 tools/plugin-surface-check.py` → `OK`; `python3 -m pytest tools/test_skill_lint.py -q`
    → `95 passed`; `python3 tools/skill-lint.py product engineering | tail -1` → `1 finding`
    (`product/skills/writing-plans/references/web-routes.md:7`, an M2 path). `token-audit
    --violations-only` exit 0 and `qa-version-check` OK.
  - Not committed by this session: the Plan Queue commits the work (the session was told not to commit).

### M2 — Every reference to a moved path or a renamed name

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** The two greps in §5 print nothing. Every stack hand-off to a `product` skill or command
says it needs `product` enabled (§4).
**Depends on:** M1 (the moved tree).
**Budget:** ~170k. Drivers:
- `CLAUDE.md` 25k.
- This plan §2–§4 12k.
- The rewrite script ~15k.
- Its diff summary ~20k.
- The ~21 stack hand-offs, each read in context and rewritten by hand: ~60k.
- The `dev:rules` sentences that split by subject ~15k.
- The check output ~20k.

**Gate: own tests.**
- §5's two greps, which print nothing.
- `python3 tools/plugin-surface-check.py`
- `python3 tools/skill-lint.py | tail -1`, at or below M1's baseline.

- **Paths.** The script rewrites every path from §2's table across the tree, minus §4's exclusions, and
  `${CLAUDE_PLUGIN_ROOT}/engineering-practices/…` paths with them.
- **Names.** The script rewrites exactly the names in §3's table. Notes:
  - `be-feature-documenter` goes before `be-documenter`, so the longer name is not cut.
  - Agent `name:` frontmatter in `product/agents/documenter.md` and `feature-documenter.md` changes
    with it.
  - `dev:run` and any `dev:` not in the table stay.
- **By hand.** Two kinds of reference:
  - Each `dev:rules` mention: `product:rules` or `engineering:rules`, by what the sentence is about.
  - Each prose mention of the plugins `dev` and `business-analysis`: list them with
    `grep -rnwE 'dev|business-analysis'` over the tree minus §4's exclusions, and rewrite each one that
    names the plugin.
- **Stack hand-offs.** List with
  `grep -rnE 'product:|/product:|documenter|requirements-author' qa frontend mobile desktop backend data devops security tooling training-data design observability`.
  Rewrite each per §4.
- **Live plans.** 005, 006, 007, 013 and 015 are rewritten with everything else. Their filed siblings in
  `docs/plans/implemented/` are not.
- **Not in M2:** restructuring the catalog's sections and the README's plugin list (M3). M2 rewrites
  their names only.

- **As built (2026-11-20):**
  - Script (scratchpad, not in the repo): resolved every `../` link against the file's old location and
    recomputed it from the new one, then applied §2's paths and §3's names as exact regexes. 233 files
    changed. It skipped the two rules `SKILL.md` files (their retire step names the old folders on purpose)
    and `tools/test_skill_lint.py`. `be-feature-documenter` ran before `be-documenter`; both agents'
    `name:` now match their file names.
  - By hand: `dev:rules` split by file location (`product/` → `product:rules`, `engineering/` →
    `engineering:rules`), prose mentions of the plugins in `marketplace.json`, `README.md`, the catalog,
    `CLAUDE.md`, `CONTRIBUTING.md`, `.skill-template/agent.md`, the live plans 005 and 006, and the rule
    files' header lines (`product rules vN`, `engineering rules v1`; versions not bumped).
  - The stack plugin descriptions in `marketplace.json` (7 stack plugins, 5 `be-*`, `devops`) now say the
    planner, documenters and feature interview come from `product`, which a project enables itself.
  - Hand-offs: 13 stack agents' "Don't re-plan; that is `solution-planner`'s" now names the `product`
    plugin; `qa-test-planner`, `qa-test-case-designer` and `qa-feature-spec-writer` say `product:*` loads by
    path whether or not `product` is enabled; `tooling-engineer`, `design-auditor`, `design/prototype`,
    `devops/threat-modeling`, `test-plan-writer`, `requirements-breakdown/references/connections.md`,
    `security-test-planner`, `data-architect` and `product-analytics` each say the plugin is needed.
  - The retire step's "identical → delete" test (`cmp`) passes only for an old rules copy with no old
    names in it. After this task every old copy differs, so the skill asks (or keeps and lists, with nobody
    to ask). That is the safe branch of M1's step 5, and it stands. D9.
  - Gate: both §5 greps print nothing (run under `bash`: in `zsh` the unquoted `$X` is not split and the
    exclusions silently do nothing); `python3 tools/plugin-surface-check.py` → `OK`;
    `python3 tools/skill-lint.py | tail -1` → `0 findings`; `python3 -m pytest tools/test_skill_lint.py -q`
    → `95 passed`; `token-audit --violations-only` exit 0 (`qa-test-planner.md` 13,971 and
    `qa-test-case-designer.md` 13,988 of 14,000 characters: no slack left); `qa-version-check` OK.
  - Not committed by this session: the Plan Queue commits the work.

### M3 — The catalog, README, CONTRIBUTING, CLAUDE.md and the migration

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:**
- `docs/skills-catalog.md` has an "Engineering catalog" and a "Product catalog", and no
  "Engineering-practices" or "Business-analysis" catalog.
- The `CLAUDE.md` repo map has `engineering/` and `product/` rows.
- `README.md` has a "Switching from `dev` and `business-analysis`" section.
- The owner's `~/.claude/CLAUDE.md` names `engineering:rules`, `product:rules` and
  `.claude/rules/product/plans.md`.

**Depends on:** M2 (the renamed text).
**Budget:** ~150k. Drivers:
- `CLAUDE.md` 25k.
- This plan §1–§3 and D4 12k.
- The catalog's scope line, plugin list and its two sections at `:427–:480` ~25k.
- The README's plugin table and install section ~20k.
- `CONTRIBUTING.md` 3k.
- `~/.claude/CLAUDE.md` 3k.
- Writes ~45k.
- Check output ~15k.

**Gate: own tests.**
- `python3 tools/skill-lint.py | tail -1`, at or below M1's baseline.
- `python3 tools/token-audit.py --violations-only`
- `grep -nE 'Engineering-practices catalog|Business-analysis catalog' docs/skills-catalog.md`, which prints nothing.

- **The catalog.**
  - Merge the two old sections into "Engineering catalog" (the technical workflow, the audits, the
    unregistered path-loaded skills).
  - Add a "Product catalog" with four parts: the chain from the feature interview to the plan, the
    planning lane, the documentation lane, and the business-analysis authoring and reasoning lanes.
  - Fix the scope line at `:7` and every plugin count.
- **`CLAUDE.md`.**
  - Repo map: replace the `engineering-practices/` and `business-analysis/` rows with `engineering/` and
    `product/` rows.
  - Drop "planning (`solution-planner`) + reverse-docs (`be-documenter`)" from the `backend/` row.
  - The intro line says which plugins depend on which.
  - Read the "Planning" section once more for prose that M2's script could not see.
- **`README.md`.**
  - Replace the plugin rows for `dev` and `business-analysis`.
  - Add the switch section:
    1. In `.claude/settings.json` `enabledPlugins`, replace `dev@skills-library` with
       `engineering@skills-library`. Add `product@skills-library` where the project plans or documents.
       Replace `business-analysis@skills-library` with `product@skills-library`.
    2. Restart the session, then run `engineering:rules` and `product:rules`. They install the new
       folders and delete each old rules file that is identical to the plugin's copy (§3).
    3. Commit `.claude/rules/` where the project commits its settings.
- **`CONTRIBUTING.md`.** Fix every path and plugin name it lists.
- **`~/.claude/CLAUDE.md`.** This is outside the repo and is not committed (D8). Edit it:
  - `dev:rules` → `engineering:rules`, `product:rules`.
  - `business-analysis:rules` → `product:rules`.
  - `.claude/rules/dev/plans.md` once `dev:rules` → `.claude/rules/product/plans.md` once `product:rules`.
  - "plus `dev` and `design` listed explicitly" → "plus `engineering`, `product` and `design` listed
    explicitly".
- **Not in M3:** any skill text (M1, M2), and switching any project over (the owner, per README).

- **As built (2026-11-20):**
  - `docs/skills-catalog.md`: `## Engineering catalog` (`:427`) and `## Product catalog` (`:454`) replace the
    two old sections. Engineering holds the 8 registered skills, `code-auditor`, the audit lanes and the
    unregistered orientation-cache, code-comments and standards-audit-engine. Product has four parts: Part 1
    the chain (`product:feature`, `product:plan-feature`, `domain-modeling`, `notebooklm`), Part 2 the planning
    lane, Part 3 the documentation lane, Part 4 the business-analysis authoring and reasoning lanes. Parts 2
    and 3 were the `solution-planner` and `documenter` text in the Backend catalog: moved whole, and the
    Backend catalog keeps a one-paragraph pointer. Scope line, plugin table (24 plugins, unchanged) and
    command table checked; the scope line now says 26 skills.
  - `CLAUDE.md`: the repo-map rows, the `backend/` row and the "Planning" prose were already right from M2;
    the intro line under "Repository map" now says which plugins depend on `engineering` and `design`, and
    that nothing depends on `product`.
  - `README.md`: plugin rows, the dependency table and the command sections were right from M2. Added the
    D4 sentence after the dependency table (a stack brings `engineering`, not `product`), the `product`
    bullet's opening, and the section "Switching from `dev` and `business-analysis`" before "Typing names": a
    was/is table, the three steps, and the line that every old rules copy differs and so is asked about
    (D9). `communication/` in the layout block no longer says BA and user stories.
  - `CONTRIBUTING.md`: paths and names were right from M2; added the sentence on `product` being enabled per
    project and never a dependency.
  - `~/.claude/CLAUDE.md` (outside the repo, not committed, D8): the four replacements. Lines 10-11, 23-25.
  - Gate: `skill-lint | tail -1` → `0 findings`; `token-audit --violations-only` exit 0, no violations; the
    catalog-heading grep prints nothing; `plugin-surface-check` → `OK`; both §5 greps print nothing under
    `bash`.
  - Not committed by this session: the Plan Queue commits the work. Not verified: Claude Code loading the
    two plugins, and no project has been switched over.

### G1 — The whole sweep, and filing the plan

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** Every command in §5 passes on the merged tree, and the plan is filed.
**Depends on:** M3.
**Budget:** ~90k. Drivers:
- `CLAUDE.md` 25k.
- This plan §5 and the As built notes 10k.
- The sweep output ~25k.
- Fixes ~20k.
- The merge ~10k.

**Gate (this is the last runnable task, so it runs the whole set once more across the plan, in
order):** the commands in §5.

- Run §5 once. Fix each failure at the narrowest file, rerun only what failed, then run §5 once more.
- Read `product/skills/rules/SKILL.md` and `engineering/rules/SKILL.md` against §3. The lint cannot see
  a rule-file table row that names a file not beside it.
- Merge `master` into the plan's branch (close-out step 6). Where a plan merged since M1 wrote an old
  path or name, rewrite it per §2–§3.
- **Status, when filing.** Name as unverified that no session has loaded `engineering` or `product`.
  The user restarts, types `/product:refine` and `/engineering:audit`, and runs `product:rules` in one
  project.
- **Not in G1:** new restructuring. A finding outside §5 goes into Status as a follow-up.

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
4. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
5. **Commit the work** — the code, its tests and these plan edits together, on the current branch (under
   Plan Queue, the plan's branch in its worktree; never check out the default branch), adding only your
   own files, by path — never `git add -A`. Your prompt block is still in the plan.
6. **Merge, gate task only** — if you are the task that ran the whole set and this plan runs on its own
   branch, merge the default branch into it now, resolve every conflict by keeping both sides' rows,
   re-run the failing suites if code conflicted, and commit the merge, so the plan merges back cleanly
   and the documentation task after you documents the merged code.
7. **Your own block** — only now delete it, and update the line above the blocks that says which have
   landed, in a follow-up commit of its own: `docs: delete <id>'s prompt (<plan>)`. Do not stop between
   the two commits. Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming
   the blocker and its owner. When the queue says other tasks of this plan are running beside you, do
   not commit, stash, reset or check out at all: make this deletion your last edit, and the queue
   commits the work and the deletion together.
8. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified), `git mv` this plan into `docs/plans/implemented/`, same name and
   number — a `solution-planner` pack moves its whole initiative folder — and add its row to that
   folder's README where there is one, in the same follow-up commit.

## Prompts — one per task

Run them in order, one session each. Each block is complete on its own. Every gate runs locally, in the
session that runs the task.

- **Start only after plan 015 has merged into `master`** (D6).
- M1, M2, M3 and G1 run one after another. Each one rewrites files the next one reads, so none runs
  beside another.
- No prompt switches a project over or pushes.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| — | 015 merged into `master` | **the user** | — | — | — |
| M1 | `docs` | `general-purpose` | none (after 015) | — | ~150k |
| M2 | `docs` | `general-purpose` | M1 | — | ~170k |
| M3 | `docs` | `general-purpose` | M2 | — | ~150k |
| G1 | `docs` | `general-purpose` | M3 | — | ~90k |
| — | restart, try `/product:refine`, switch projects per README | **the user** | G1 | — | — |

M1, M2 and M3 have landed. G1 is live.

---

### G1 — The whole sweep, and filing the plan (general-purpose, docs)

````
Depends on: M3
Agent: general-purpose · Stack: docs

Task G1 of docs/plans/016-product-and-engineering-plugins.md. The goal: every command in §5 passes on
the merged tree, and the plan is filed.

Read, in this order:
1. CLAUDE.md: "Planning".
2. The plan: §3, §5, every As built note, task G1, and "Close-out — every task".

Do:
- Run §5 once. Fix each failure at the narrowest file, rerun only what failed, then run §5 once more.
- Read product/skills/rules/SKILL.md and engineering/rules/SKILL.md against §3. Each table row must name
  a file beside the skill.
- Merge `master` into the plan's branch (close-out step 6). Where a plan merged since M1 wrote an old
  path or name, rewrite it per §2–§3 and run §5 again.

Traps:
- No new restructuring. A finding outside §5 goes into Status as a follow-up.
- Run §5's greps under `bash` (`bash -c '…'`): in `zsh` the unquoted `$X` is not split and the exclusions
  do nothing. Delete `.pytest_cache` after the pytest run, because the greps read the whole tree.
- `qa/manual/agents/qa-test-planner.md` and `qa-test-case-designer.md` sit at 13,971 and 13,988 of the
  14,000-character agent budget: an edit there must be neutral in length.
- The plan file itself names the old paths on purpose. §5's greps exclude it. The README's switch section
  names the `dev` and `business-analysis` plugins on purpose, worded so §5's greps pass (D11): leave it.
- `product` registers 26 skills (D10), not the 25 in M1's As built.
- Status names as unverified that no session has loaded `engineering` or `product`. The user restarts,
  types `/product:refine` and `/engineering:audit`, and runs `product:rules` in one project.

Gate (this is the last runnable task, so it runs the whole set once more across the plan, in order):
  the commands in §5.

Commit: `chore: 016 G1 — the sweep`.
Close out per the plan's "Close-out — every task" before you stop. Your prompt is the last, so close-out
step 8 files the plan.
````
