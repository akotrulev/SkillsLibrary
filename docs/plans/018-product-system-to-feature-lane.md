# 018 — `product`: one system plan that hands each feature to `/product:plan-feature` — plan (2026-11-23)

**Goal:** Replace the `product` plugin's chained-but-separately-callable planning commands with two
front doors.
- **`/product:plan-system`** takes a vision for a whole system, in a new or an existing repo. It writes
  one system plan: the vision, a thin technical skeleton, the epics and a flat list of features. Each
  feature has a task block and a prompt that starts with `/product:plan-feature`.
- **`/product:plan-feature`** (renamed from `product:feature`) takes one feature, from that prompt or
  on its own. It runs the interview, the approved spec and the implementation plan in one run. It writes
  its result back into the system plan, or records that the user has put the feature on hold.

Every skill that is only a step inside one of the two front doors is hidden: neither the model nor the
user can call it on its own.

**Status:** S1, S2, F1 and F2 landed (2026-11-23). S1: `system-plan-format.md`, the four section skills and
`rules/system-plans.md`. S2: `solution-planner` runs NEW / EXISTING / EXTEND and writes
`docs/plans/<NNN>-<system>-system.md`, `/product:plan-system` routes to it, and `requirements-author`,
`/product:refine` and `delivery-plan` are gone from the tree and the manifest. F1: `/product:plan-feature`
(`brainstorming`) runs SYSTEM / NEW / SHAPED through spec, acceptance criteria, implementation plan,
write-back and on hold; `writing-plans` is hidden from the model and loaded by path; `TD` is keyed to a
spec's acceptance criteria in `plan-format.md` and `plans.md`. F2: `data-model-plan`, `experience-plan`,
`api-surface-plan` and `integration-plan` write the spec's `## Data model`, `## Experience` (with
`### Rendering plan`), `## API surface` and `## Integrations`, on top of §3 and earlier specs; their
examples are sections of one toy spec (D24). K1: `qa-test-planner`, `test-plan-writer`,
`qa-test-case-designer`, `/qa-…:test-plan` and `test-first` take a spec's acceptance criteria first (tag
`SPEC<NNN>-AC<k>`, D25) and still accept a story backlog; the documenter reads the spec as the source of
purpose; `business-analyst` has `BACKLOG AUDIT`. M1: the twelve step skills set `user-invocable: false`, surface-check rule 10 enforces it, every §7 hit outside
C1's files is rewritten, `session-budget` is re-keyed to the spec, and the audit register is renamed (D26).
Next: C1. Unverified: no run of `/product:plan-feature` in a scratch repo; Claude Code hiding the
twelve skills (D13); the catalog, README, `CLAUDE.md` and the product manifest description still name the
deleted lane until C1; follow-up for G1: S1's §3 example picks a Vite SPA where `rendering-strategy.md` would give
`ssr` (F2 As built).

**Test design:** none. The plan serves no stories and changes skill text, agent text, the manifest and
one lint script. The checks are `tools/plugin-surface-check.py`, `tools/skill-lint.py`,
`tools/token-audit.py`, `tools/test_skill_lint.py` and `tools/qa-version-check.py`, which already exist,
plus the greps in §7.

**Documentation task:** none. This is the skills library, and the skill text is the documentation. C1
updates the catalog, `README.md` and `CLAUDE.md` from the rewritten tree. No product behaviour changes
for a documenter to trace.

**Telemetry smoke:** none. No service is built.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| One command that turns a vision into a list of features | Two commands. `/product:refine` writes `requirements.md`, `epics.md` and `stories.md` and hands on (`product/commands/refine.md:15`, `product/agents/requirements-author.md:16`). `/product:plan-system` then writes a blueprint, a detail pack, an epic map and a task list for the whole system (`product/agents/solution-planner.md:72-83`). Neither one produces a list of features | `/product:plan-system` does the whole job and writes one system plan (S1 writes the format and the system-level skills, S2 the agent and the command) |
| The system plan hands each feature to the feature lane | The only link runs the other way: `requirements-author` sends one clear feature to `/product:feature` and stops (`product/agents/requirements-author.md:62`). `product:feature` sends a multi-capability ask to `/product:refine` (`product/skills/brainstorming/SKILL.md:18`) | Each feature's prompt in the system plan starts with `/product:plan-feature` (S1). `plan-feature` reads the system plan and writes its result back into it (F1) |
| Works in new and existing repos | `solution-planner` has NEW, DETAIL, RESUME and EXTEND modes over a requirements pack (`product/agents/solution-planner.md:51-66`). RESUME reconciles a detail pack (`product/skills/delivery-plan/references/reconcile.md`) | NEW, EXISTING and EXTEND over the vision and the code (S2, D17) |
| Thin system-level design | `solution-blueprint` writes a full `blueprint.md` (`product/skills/solution-blueprint/SKILL.md:13`). Five more skills add a data model, an experience plan, an API surface, integrations and a delivery plan for the whole system | `solution-blueprint` writes the skeleton section of the system plan only (S1, D3) |
| Vision and epics inside the system plan | `ba-scoping-writeup` writes `requirements.md` (`product/skills/ba-scoping-writeup/SKILL.md:9`). `ba-epic-writer` writes `epics.md` (`product/skills/ba-epic-writer/SKILL.md:34`). Their rules are `backlog-requirements.md` and `backlog-epics.md` | Both write sections of the system plan. The two rule files merge into `system-plans.md` (S1, D4, D18) |
| Which features can run side by side | `epic-map` arranges epics into lanes and waves from `epics.md` and `stories.md` (`product/skills/epic-map/SKILL.md:15`) | `epic-map` writes the system plan's features-side-by-side table (S1, D7) |
| A per-feature technical design | `data-model-plan`, `api-surface-plan`, `experience-plan` and `integration-plan` each need an approved `blueprint.md` and write their own file (`data-model-plan/SKILL.md:11`, `api-surface-plan/SKILL.md:13`, `experience-plan/SKILL.md:11`, `integration-plan/SKILL.md:16`) | `/product:plan-feature` loads each one the feature needs, and each writes a section of the spec (F2, D6) |
| One feature command with a name that matches the system command | `product:feature` is the interview and the spec (`product/skills/brainstorming/SKILL.md:2`). `product:plan-feature` is a separate skill that plans an approved spec (`product/skills/writing-plans/SKILL.md:2`), and the user can type either one | `/product:plan-feature` runs interview → spec → plan. `writing-plans` is hidden (F1, D12) |
| A feature can be put on hold | — | The system plan records `On hold` on the feature task and keeps its prompt (F1, D9) |
| Test design without stories | `TD` tasks are keyed to stories (`CLAUDE.md:78`, `product/skills/rules/plans.md:36`, `product/skills/writing-plans/references/plan-format.md:171-193`). The QA agents read `epics.md` and `stories.md` (`qa/manual/agents/qa-test-case-designer.md:36`, `qa/manual/test-plan-writer/SKILL.md:15`, `qa/_shared/test-first/SKILL.md:19-20`) | `TD` tasks are keyed to a feature spec's acceptance criteria. The QA agents and the documenter read the spec (F1, K1, C1, D11) |
| Step-only skills cannot be typed on their own | Every non-front-door skill sets `disable-model-invocation: true` only (`tools/plugin-surface-check.py:11-12`), so a user can still type `/product:plan-api-surface` | Each step-only `product` skill also sets `user-invocable: false`, and the surface check enforces it (M1, D13) |
| No dead lane left behind | `requirements-author`, `/product:refine`, `delivery-plan` and the `stories` step are wired into the manifest, the catalog, the README and about 60 files across the library (§6) | S2 deletes them. M1 rewrites every reference. C1 rewrites the catalog, `README.md` and `CLAUDE.md` |

## 2. The flow after this plan

```
/product:plan-system "<the vision>"            solution-planner
   interview in rounds → approval of vision + skeleton + feature list
   → docs/plans/<NNN>-<system>-system.md       (not queued in Plan Queue)

   the user pastes one feature prompt per fresh session:
/product:plan-feature F3 of docs/plans/<NNN>-<system>-system.md — <brief>
   interview → design (+ data model / experience / API / integrations sections as needed)
   → approved spec docs/specs/<NNN>-<feature>-design.md   (with ## Acceptance criteria AC1..ACn)
   → implementation plan docs/plans/<NNN>-<feature>.md      (queued in Plan Queue)
   → writes back: F3 As built (spec + plan paths), F3's prompt deleted
     or: F3 On hold (date, reason), prompt kept

/product:plan-feature "<one feature>"           the same run, no system plan to write back to
```

**What stays separate and unchanged:** `/product:document-system`, `/product:document-feature`,
`/product:business-analysis`, `notebooklm` and `rules`.

## 3. The system plan format

S1 writes it as `product/skills/solution-blueprint/references/system-plan-format.md`, modelled on
`plan-format.md`. The parts that differ are the point of the file.

**Path:** `docs/plans/<NNN>-<system>-system.md`. `NNN` takes the high-water mark across `docs/plans/`
and `docs/plans/implemented/`, like any plan. The `-system` suffix is what the rule files key on (D18).

**Sections, in order:**

| Section | Holds | Written from |
|---|---|---|
| Header | `# NNN — <System> — system plan (YYYY-MM-DD)`, `**Goal:**`, `**Status:**` (features specced, features on hold, next feature) | — |
| `## 1. What already exists, and what is missing` | `\| Need \| Today \| Gap \|`, one row per capability. In an existing repo `Today` cites `file:line`. A capability already built is a row with no gap and no feature | the code |
| `## 2. Vision and scope` | The ask verbatim, actors and their goals, the decision-maker, success measures, quality targets, in / out / deferred, constraints, assumptions, risks | `ba-scoping-writeup` |
| `## 3. The skeleton` | Stack and versions (`detected` / `stated` / `proposed`), architecture style, functional areas with their file trees and agents, auth, the shared entities (name, owner, one line each), cross-cutting conventions (error envelope, ids, pagination, telemetry base) | `solution-blueprint` |
| `## 4. Epics` | `E1…En`: a one-sentence goal each and the features that serve it | `ba-epic-writer` |
| `## 5. Features side by side` | `\| Feature \| Epic \| Areas and trees \| Depends on \| Refined beside \| Built beside \|` | `epic-map` |
| `## Decisions` · `## Answered questions (date)` · `## Open questions` | As in `plan-format.md` §2 | the interview |
| `## 6. Features` | One task block per feature, flat, `F1…Fn` | — |
| `## Close-out — every feature` | The write-back duties `plan-feature` runs, copied verbatim from the format file | the format file |
| `## Feature prompts — paste one per session` | The feature table, then one block per feature | — |

**The feature task block:**

````markdown
### F3 — Booking cancellation

**Epic:** E2 · **Command:** `/product:plan-feature`
**Deliverable:** an approved spec in `docs/specs/` and its implementation plan in `docs/plans/`, both committed.
**Depends on:** F1 (the member entity and auth).
**Brief:** <one paragraph: what it does and for whom, what is in and out, and the skeleton decisions (§3) it builds on.>
````

No `Stack`, `Agent`, `Budget` or `Gate` line. The session is the user's interview, and the
implementation plan it produces carries those lines for every task it holds.

**The feature prompt block.** The heading is `### F3 — Booking cancellation (/product:plan-feature)`.
The body is fenced in four backticks, and **its first line is the slash command**, so pasting the block
into a fresh session runs it (D10):

````markdown
/product:plan-feature F3 of docs/plans/021-gym-system-system.md — Booking cancellation

Members cancel their own bookings and staff cancel anyone's. In: cancellation, the refund rule, the
notification. Out: waitlist promotion (F5). Builds on §3's Member and Booking entities and the Auth0
roles.

Read the system plan's §2, §3, §5, D1–D<n> and task F3 first. Close out per its
"Close-out — every feature" when the plan is written, or when the user puts F3 on hold.
````

**Living text.** A feature whose spec settles something a later feature relies on rewrites that
feature's brief and prompt, in place. A feature the interview splits in two gets the next free `F` id
for the second half.

**Filing.** The system plan moves to `docs/plans/implemented/` when its last feature prompt is
deleted. A feature on hold keeps its prompt, so a plan with a held feature stays in `docs/plans/`.

## 4. The feature lane after this plan

`/product:plan-feature` is `product/skills/brainstorming` with `name: plan-feature` (D12, D14).

| Mode | Input | Runs | Output |
|---|---|---|---|
| **SYSTEM** | `F<n> of <system plan path>` | the interview, the design, the spec, then `writing-plans` | the spec, the implementation plan, the write-back |
| **NEW** | One feature described in words | the same, with no write-back | the spec and the implementation plan |
| **SHAPED** | A spec, design or plan with open questions | the interview only | each answer written back into that document |

A multi-capability ask in NEW mode goes to `/product:plan-system`, not to `/product:refine`.

**The spec gains three things:**
1. A `## Acceptance criteria` section, `AC1…ACn`, each one a condition a tester can mark met or not
   met. `TD` and `Q` tasks cite `<spec> AC<k>` (D11, D15).
2. One section per design skill the feature needed: `## Data model` (`data-model-plan`),
   `## Experience` (`experience-plan`, with its `### Rendering plan`), `## API surface`
   (`api-surface-plan`), `## Integrations` (`integration-plan`). A section the feature doesn't need is
   left out, not written empty (D6).
3. In SYSTEM mode, a `**System plan:**` line in the header naming the system plan and the `F` id.

**Write-back (SYSTEM mode), after the implementation plan is committed:**
1. Append `**As built (YYYY-MM-DD):** spec <path>, plan <path>` to the feature's task block, plus any
   decision the spec made that changes §3 (also appended to the system plan's `## Decisions`).
2. Rewrite the brief and prompt of every later feature whose assumptions changed.
3. Rewrite the system plan's `**Status:**` line.
4. Commit, then delete the feature's prompt block in a follow-up commit,
   `docs: delete F<n>'s prompt (<system plan>)`. When that leaves no blocks, `git mv` the system plan to
   `docs/plans/implemented/` in the same commit.

**On hold.** The user can stop at any round ("put this on hold"). The answers so far are written to the
spec with `**Status:** on hold`. The feature's task block gets
`**On hold (YYYY-MM-DD):** <reason> — spec draft <path>`, its prompt is kept, and both are committed.
Pasting the prompt again resumes from the draft.

## 5. Every `product` command, agent and skill after this plan

| Today | After | Task |
|---|---|---|
| `/product:refine` · `requirements-author` | Deleted. Scoping and epics move into `solution-planner` | S2 |
| `/product:plan-system` · `solution-planner` | Rewritten: NEW / EXISTING / EXTEND, thin skeleton, writes the system plan | S2 |
| `product:feature` (`brainstorming`) | `/product:plan-feature`: interview → spec → plan, SYSTEM mode, write-back, on hold | F1 |
| `product:plan-feature` (`writing-plans`) | Hidden, `name: writing-plans`, loaded by `plan-feature` after spec approval | F1, M1 |
| `scoping` (`ba-scoping-writeup`) | Hidden. Writes the system plan's §2 | S1, M1 |
| `epics` (`ba-epic-writer`) | Hidden. Writes §4 | S1, M1 |
| `plan-blueprint` (`solution-blueprint`) | Hidden. Writes §3, the thin skeleton | S1, M1 |
| `plan-epic-map` (`epic-map`) | Hidden. Writes §5 | S1, M1 |
| `plan-delivery` (`delivery-plan`) | Deleted with its references | S2 |
| `plan-session-budget` (`session-budget`) | Hidden. `writing-plans`' sizing reference | S2, M1 |
| `plan-data-model`, `plan-api-surface`, `plan-experience`, `plan-integrations` | Hidden. Each writes a section of a feature spec | F2, M1 |
| `stories` (`ba-story-writer`), `story-review` (`ba-story-quality-review`) | Hidden. Loaded only by `business-analyst`, which also takes over the review of an imported backlog | K1, M1 |
| `domain-modeling` | Unchanged (already loaded by path) | — |
| `document-*`, `business-analysis`, `notebooklm`, `rules`, the other `ba-*` skills | Unchanged, apart from references M1 rewrites | — |
| Rule files `backlog-requirements.md`, `backlog-epics.md` | Merged into `system-plans.md` | S1 |
| Rule file `backlog-stories.md` | Kept for `business-analyst` | — |

## 6. The name map

M1 rewrites every hit outside `docs/plans/implemented/`, `docs/audits/`, `auth/cognito-*`,
`communication/` and `product/skills/business-documentation/evals/`.

| Old | New |
|---|---|
| `product:feature`, `/product:feature` | `/product:plan-feature` |
| `product:plan-feature` meaning "an approved spec → a plan" | `writing-plans` (hidden), or `/product:plan-feature` where the text means the whole feature run |
| `/product:refine`, `requirements-author` | `/product:plan-system`, `solution-planner` |
| `requirements.md` · `epics.md` | the system plan's §2 · §4 |
| `stories.md`, `US<n> AC<k>` in the delivery lane | the feature spec's `## Acceptance criteria`, `<spec> AC<k>` (a story-based backlog stays a valid basis for QA and `business-analyst`) |
| `blueprint.md` | the system plan's §3 |
| `epic-map.md` | the system plan's §5 |
| `delivery-plan.md` | the feature's implementation plan |
| `data-model.md`, `experience-plan.md` (and its `§4a` rendering plan), `api-surface.md`, `integrations.md` | the feature spec's `## Data model`, `## Experience` (`### Rendering plan`), `## API surface`, `## Integrations` |
| `product:plan-delivery`, `product:plan-epic-map`, `product:plan-blueprint`, `product:plan-session-budget`, `product:plan-data-model`, `product:plan-api-surface`, `product:plan-experience`, `product:plan-integrations`, `product:scoping`, `product:epics`, `product:stories`, `product:story-review` | the skill's path (`product/skills/<folder>`): a hidden skill is named by path, never as a typeable `plugin:name` |

## 7. What G1 sweeps

```bash
python3 tools/plugin-surface-check.py                   # OK
python3 tools/skill-lint.py | tail -1                   # 0 findings (baseline 0 on 2026-11-23)
python3 tools/token-audit.py --violations-only          # exit 0
python3 -m pytest tools/test_skill_lint.py -q           # green
python3 tools/qa-version-check.py                       # OK
X='--exclude-dir=implemented --exclude-dir=audits --exclude-dir=evals --exclude-dir=cognito-blazor --exclude-dir=cognito-react --exclude-dir=communication --exclude-dir=.git'
grep -rnE $X 'product:feature\b|product:refine|requirements-author|product:(plan-delivery|plan-epic-map|plan-blueprint|plan-session-budget|plan-data-model|plan-api-surface|plan-experience|plan-integrations|scoping|epics|stories|story-review)\b|delivery-plan|(blueprint|epic-map|experience-plan|data-model|api-surface|integrations|requirements|epics)\.md' . | grep -v '^./docs/plans/'   # prints nothing
python3 - <<'EOF'
import json
p = next(p for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p['name'] == 'product')
assert not any('requirements-author' in a for a in p['agents'])
assert {c.rsplit('/', 1)[1] for c in p['commands']} == {'plan-system.md', 'document-system.md', 'document-feature.md', 'business-analysis.md'}
assert not any(s.endswith('/delivery-plan') for s in p['skills'])
print('OK')
EOF
```

`docs/plans/` is filtered out whole: the other live plans (`007-…`, `fine-tuning-house-models.md`) are
other work's records and keep their wording. `stories.md` is left out of the grep on purpose: `business-analyst`, the QA agents and
`backlog-stories.md` still accept a story backlog. None of these checks can show that Claude Code hides
a `user-invocable: false` skill from the `/` menu, or that Plan Queue skips the system plan. The user
proves both after a restart (Status).

**What a halfway stop leaves:**
- After S1: the format and the four system-level skills describe the system plan, but `/product:plan-system`
  still runs the old `solution-planner`, which no longer matches them.
- After S2: `/product:plan-system` writes system plans whose prompts call `/product:plan-feature`, which
  does not exist until F1.
- After F1: the lane runs end to end, but the four design skills still expect a `blueprint.md`.
- After F2 and K1: the lane is complete. The rest of the library still names the old commands and files
  until M1, and the step-only skills can still be typed.

## Decisions

**D1 — `/product:plan-system` is the one system command, run by `solution-planner`, in new and existing repos.**
Why: the user wants one entry for the whole system. Cost: `solution-planner` is rewritten rather than
trimmed, and its detail-pack depth is gone from system level (D3).

**D2 — The system plan is one file, `docs/plans/<NNN>-<system>-system.md`, holding a flat list of features, one prompt each.**
Why: the same shape as an implementation plan (task + prompt), and `plan-format.md`'s one-file rule.
Cost: no initiative folder. The specs and the implementation plans it produces live in `docs/specs/` and
`docs/plans/`, linked from each feature's `As built` note.

**D3 — System level writes a thin skeleton only.**
Stack, architecture, areas and their trees, auth, shared entities, cross-cutting conventions. Each
feature's data model, API, screens and integrations are designed in its own spec.

| Option | Verdict | Why |
|---|---|---|
| Thin skeleton | chosen | Each feature designs on top of what every feature binds to |
| Full blueprint pack | rejected | Designs every feature twice, once here and once in its spec |
| Vision + features only | rejected | The first feature would make system decisions alone |

Cost: two features designed in parallel can disagree on a shared detail the skeleton left open. The
write-back's living-text duty (§4) is the check.

**D4 — Vision and requirements are §2 of the system plan; there is no `requirements.md`.**
Cost: `ba-scoping-writeup`'s ten sections become one plan section, so its format is condensed.

**D5 — No stories in the delivery lane.** `ba-story-writer` and `ba-story-quality-review` are kept,
hidden, for `business-analyst`, which also takes over `requirements-author`'s AUDIT mode (reviewing a
backlog written elsewhere). Cost: a team that wants a story backlog has no command that writes one.

**D6 — The four design skills are loaded by `/product:plan-feature` per feature and write sections of the spec, not files.**
Why: one self-contained spec, the same reasoning as the one-file plan. Cost: a large feature's spec gets
long. The design skills' examples are rewritten as spec sections.

**D7 — The system plan's §5 replaces the epic map. `delivery-plan` is deleted. `session-budget` stays, hidden, as `writing-plans`' sizing reference.**
Cost: `delivery-plan`'s three sequencing shapes (feature-complete, agent-batched, platform-first) and
`reconcile.md` are deleted with it. `CLAUDE.md`'s batched-plan exception stays a general rule that
`writing-plans` applies inside one feature.

**D8 — `/product:refine` and `requirements-author` are deleted.** Their scoping and epic steps move into
`solution-planner`. Cost: existing initiative folders with `requirements.md` / `epics.md` / `stories.md`
are not migrated. `solution-planner`'s EXISTING mode reads them as input like any other document.

**D9 — Write-back and on hold are `plan-feature`'s duties, defined in the system plan's `## Close-out — every feature`.**
Approved and planned: `As built` + prompt deleted. On hold: a dated line, the prompt kept, the
answers so far in a spec draft. See §4.

**D10 — The system plan is not queued.** Its prompts section is headed `## Feature prompts — paste one per session`
rather than `## Prompts`, and each block's first line is the slash command, not `Depends on:`.
Why: each prompt opens an interactive interview, and a slash command runs only at the start of a
message. Cost: dependencies live in the task block and the table only. Unverified: that Plan Queue
ignores the heading. `plan-format.md` §6 says it scans for a `## Prompts` section. The user checks it
after G1 (Status).

**D11 — `TD` tasks are keyed to a feature spec's acceptance criteria.** "A plan that delivers a feature
plans its testing": the test plan (`qa-test-planner`) and the test cases (`qa-test-case-designer`) are
per feature, citing `<spec> AC<k>`. A plan built from a story backlog still qualifies. Cost: the QA
agents, `test-first`, `plan-format.md`, `plans.md` and `CLAUDE.md` all change wording (F1, K1, C1).

**D12 — `product:feature` is renamed `/product:plan-feature` and runs interview → spec → plan. `writing-plans` is a hidden step it loads.**
Why: it mirrors `/product:plan-system`. Cost: every reference to both old names changes (M1), and no
one can type "plan this spec" on its own. A spec written elsewhere goes in through SHAPED mode.

**D13 — A hidden skill sets both `disable-model-invocation: true` and `user-invocable: false`.**
Per code.claude.com/docs/en/skills (read 2026-11-23): `user-invocable: false` "hides it from the `/`
menu and doesn't run it when you type `/name`", and `disable-model-invocation: true` keeps it from the
Skill tool. Agents and front doors keep loading these skills by reading the file path. The surface check
gains rule 10: every skill in the new `HIDDEN` set sets both. Cost: `disable-model-invocation` also
stops a skill being preloaded through an agent's `skills:` frontmatter. No `product` agent uses that.
Unverified: that a skill with both flags is still registered without error. The user checks it after
the restart.

**D14 — Skill folders keep their names. Only `name:`, descriptions and outputs change.**
Why: fewer moved paths. Cost: the folder `brainstorming` holds `plan-feature`, as it holds `feature`
today.

**D15 — The spec gains `## Acceptance criteria` (`AC1…ACn`) and a `**System plan:**` header line in SYSTEM mode.**

**D16 — `/product:plan-system` interviews the way `plan-feature` does**: the frontier of open decisions,
at most four questions per AskUserQuestion round, the recommended option first. Then one blocking
approval of §2, §3 and the feature list before the file is written.

**D17 — `solution-planner`'s modes are NEW (no meaningful code), EXISTING (code, no system plan) and EXTEND (a system plan exists; new features take the next free `F` ids, never renumbered).**
DETAIL and RESUME are dropped. A written brief is input to NEW or EXISTING. Cost: there is no
reconcile path for a half-built old-style pack. EXISTING reads its code.

**D18 — `backlog-requirements.md` and `backlog-epics.md` merge into one rule file, `system-plans.md`, with `paths:` `docs/plans/*-system.md`.**
`plans.md` says a `*-system.md` plan follows `system-plans.md` for its feature blocks (no `Stack`,
`Agent`, `Budget` or `Gate`). `product:rules` retires the two old installed files, as 016 did for
`rules/dev/`.

**D19 — In a repo where the skeleton isn't built yet, `F1` is the foundation feature**: the scaffold,
auth wiring, the telemetry base, CI and the shared entities from §3. Every other feature depends on it.

**D20 — Standalone `/product:plan-feature` (NEW mode) keeps working without a system plan.**

**D21 (2026-11-23, S1) — The rewritten reference files take new names, and the format adds three small rules.**
The plan said to rewrite `blueprint-template.md`, `example-blueprint.md` and `example-epic-map.md` in
place. S1 renamed them `skeleton-template.md`, `example-skeleton.md` and
`example-features-side-by-side.md`, because the §7 grep's `(blueprint|epic-map|…)\.md` matches the old
names and G1 could never print nothing. The format also adds: a `**Mode:**` header line (NEW / EXISTING
/ EXTEND, D17); a `State` column in the feature-prompt table (`live`, `specced (plan NNN)`, `on hold`);
and, in the close-out, a decision that changes §3 corrects the §3 line in place citing its `D<n>`, so §3
always says what is true now. Cost: S2 writes the `**Mode:**` line and the `State` column, and F1's
write-back sets `State`.

**D22 (2026-11-23, S2) — `solution-planner`'s write reach includes the glossary rows and ADRs `domain-modeling` writes.**
S2's bullet gave the reach as the system plan and the orientation cache only, but the same bullet has
Step 1 load `domain-modeling` "as `brainstorming` step 5 does", and that step writes
`docs/business-model/glossary.md` rows and `docs/adr/` files as terms settle. The agent and the command
now name both. Cost: `business-analyst` no longer owns every write to the KB; the boundary line says
`solution-planner` writes glossary rows and nothing else there.

**D23 (2026-11-23, F1) — F1 also cleared the pack paths and hid `writing-plans`' routing headings.**
The bullets named `plan-format.md` §1, §5 and §8 and `plans.md:34-36`. F1 also removed the
`solution-planner` pack clause from §7's verbatim close-out (no initiative folder exists after D2), the
`docs/plans/*/delivery-plan.md` glob and pack path in `plans.md` (lines S2 left for M1), and the matching
row in `rules/SKILL.md:19`. `writing-plans`' "When to use" / "When NOT to use" became `## Input`, because
lint R6 bars routing headings on a skill with `disable-model-invocation: true`, and four of its paragraphs
were tightened to keep the body under 16,000 chars. Cost: a plan written before F1 carries the old §7
clause in its close-out, harmless now; M1 has three fewer hits to rewrite.

**D24 (2026-11-23, F2) — The design examples take new names and spec 006, and the validation catalog's project copy lives in `docs/specs/`.**
- The bullet said to rewrite each `example-*.md` in place. Their old names (`example-data-model.md`,
  `example-api-surface.md`, `example-integrations.md`, `example-experience-plan.md`) match F2's own grep,
  so they were renamed `example-<section>-section.md`, as D21 did for S1.
- The bullet named the toy spec `docs/specs/004-booking-cancellation-design.md`. The system-plan-format
  example S1 wrote already names F3's spec draft `docs/specs/006-booking-cancellation-design.md` (004 is
  the system plan, 005 F1's spec), so the examples use 006 and add F2's spec as 007.
- The old skill copied the catalog into the initiative folder; no folder exists after D2. Both readings:
  copy it into every spec's folder per feature (rejected: one copy per spec in one folder), or the first
  spec with an `## API surface` copies it to `docs/specs/validation-catalog.md` and every spec cites
  that copy (chosen).
- Cost: K1 and M1 point `test-first` and `tooling-engineer` at `docs/specs/validation-catalog.md`; a
  project whose specs live elsewhere (the user's preference wins, `plan-feature`'s Output format) keeps
  the copy beside them.

**D25 (2026-11-23, K1) — The backlog audit is a new `BACKLOG AUDIT` mode, and a spec-bound test is tagged `SPEC<NNN>-AC<k>`.**
- `business-analyst` already had an `AUDIT` mode (refresh the KB). Both readings: fold the backlog review
  into it (rejected: one mode name for two inputs, KB versus backlog) or add a mode beside it (chosen,
  `BACKLOG AUDIT`).
- The plan says tests cite `<spec> AC<k>`, but a tag cannot hold a path or a space. `test-first` tags
  `SPEC<NNN>-AC<k>` from the spec's number (unique in `docs/specs/`), `US<n>-AC<k>` from a backlog. Within
  one test plan or suite a row cites `AC<k>` alone, the spec named once in **Covers** or the header.
- Cost: a project whose specs live outside `docs/specs/` numbers them its own way; the tag still takes the
  spec's `NNN`.

**D26 (2026-11-23, M1) — The engineering audit register is renamed `<NNN>-<slug>-register.md`.**
- The §7 grep's `requirements\.md` matches `spec-vs-code-audit`'s register, `docs/audits/<NNN>-<slug>-requirements.md`,
  which has nothing to do with the deleted product lane. Both readings: leave it and let G1's grep carry
  three known hits (rejected: the deliverable is a grep that prints nothing), or rename the register
  (chosen: the file is already headed **Register:**).
- `spec-vs-code-audit/SKILL.md`, `engineering/rules/SKILL.md` and `engineering/rules/audits.md` (rules v2,
  `paths:` `docs/audits/*-register.md`) changed. `engineering:rules` step 6 also searches
  `'*-requirements.*'`, so a project's older registers are still found and a glob proposed for them.
- Cost: a project that re-installs the engineering rules loses the default glob for its old
  `*-requirements.md` registers until step 6's proposed glob is accepted; this repo's own
  `docs/audits/` holds none.

## Answered questions (2026-11-23)

- **O1 — How much design does the system command do up front:** a thin skeleton (D3).
- **O2 — Where do stories and acceptance criteria live:** stories are dropped from the lane; the
  acceptance criteria live in each feature spec (D5, D15).
- **O3 — What happens to `/product:refine` and `/product:plan-system`:** replaced by one command once
  every skill they use has a place in the new flow (D1, D8).
- **O4 — How is a held feature recorded, and is the system plan queued:** a dated line on its task; not
  queued (D9, D10).
- **O5 — The orphaned story skills:** kept, hidden, for `business-analyst` (D5).
- **O6 — The four design skills:** loaded by `/product:plan-feature` per feature (D6).
- **O7 — The ordering skills:** a features-side-by-side table; `delivery-plan` deleted; `session-budget`
  kept for `writing-plans` (D7).
- **O8 — Where the vision lives:** a section of the system plan (D4).
- **O9 — Write-back:** on approval the prompt is deleted with an `As built` note; on hold the prompt is
  kept (D9).
- **O10 — `TD` trigger:** keyed to feature acceptance criteria (D11).
- **O11 — The system command's agent:** `solution-planner`, rewritten; `requirements-author` deleted (D1, D8).
- **O12 — The system command's name:** `/product:plan-system` (D1).
- **O13 — `product:feature` → `/product:plan-feature`, and the existing `plan-feature`:** it becomes a
  hidden step (D12).

## Open questions

None blocks a task. The two unverified behaviours (D10, D13) are checked by the user after G1.

## 8. Tasks

### S1 — The system plan format and the four system-level skills

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `product/skills/solution-blueprint/references/system-plan-format.md` defines the system
plan as §3 describes. `solution-blueprint`, `ba-scoping-writeup`, `ba-epic-writer` and `epic-map` each
write their section of it (§3, §2, §4, §5) and nothing else. `product/skills/rules/system-plans.md`
replaces `backlog-requirements.md` and `backlog-epics.md`. `skill-lint` reports 0 findings over `product`.
**Depends on:** —
**Budget:** ~115k. Drivers:
- `CLAUDE.md` 25k.
- This plan §1–§5 and D2–D4, D7, D10, D14, D16–D19 10k.
- `solution-blueprint` with its references (44 KB) ~12.5k.
- `ba-scoping-writeup`, `ba-epic-writer`, `epic-map` and its example (43 KB) ~12k.
- `plan-format.md` §1–§2 and §6–§8 as the model ~6k.
- The rule files `plans.md`, `backlog-requirements.md`, `backlog-epics.md` and `rules/SKILL.md` ~4k.
- Writes: the format file ~5k, four skill rewrites ~16k, the new rule file and the table rows ~3k.
- Lint output and read-back ~10k. Churn ×1.2.

**Gate: own tests.**
- `python3 tools/skill-lint.py product | tail -1` → `0 findings`
- `python3 tools/plugin-surface-check.py` → `OK`
- `python3 tools/token-audit.py --violations-only` → exit 0

- **`system-plan-format.md`.** §3 of this plan, written as a format file: path and `NNN`, the sections in
  order with what each holds, the feature task block, the prompt block (first line the slash command),
  living text, filing. Then `## Close-out — every feature`, the verbatim text that every system plan
  copies above its prompts: §4's write-back steps 1–4 and the on-hold duty, worded for the session
  that `/product:plan-feature` runs. End with a filled example of one small system (three features, one
  on hold) in a fenced block.
- **`solution-blueprint/SKILL.md`.** Rescope to §3 of the system plan: stack and versions with evidence
  marks, architecture style, areas → trees → agents, auth, shared entities, cross-cutting conventions.
  Drop everything per-feature (key flows, per-area data, endpoints). Keep `references/architecture-style.md`.
  Rewrite `blueprint-template.md` as the §3 template and `example-blueprint.md` as a filled §3. Delete
  `key-flows-and-decisions.md` and `pack-cross-checks.md` when nothing outside `solution-planner.md` and
  the deleted `delivery-plan` cites them. Grep first, and keep a file that something else cites.
- **`ba-scoping-writeup/SKILL.md`.** Its output is the system plan's §2. Keep the ten concerns as
  subsections, condensed. Point its rules line at `system-plans.md`. Drop "written by
  `requirements-author` (`/product:refine`)".
- **`ba-epic-writer/SKILL.md`.** Its output is §4: `E1…En`, each a goal sentence, a plain-English line
  and the `F` ids that serve it. A feature, not a story, is the unit an epic lists. Point its rules line
  at `system-plans.md`.
- **`epic-map/SKILL.md` and `references/example-epic-map.md`.** Its output is §5's table over features:
  areas and trees from §3, `Depends on`, `Refined beside` (any two features whose decisions don't depend
  on each other), `Built beside` (disjoint trees). Prerequisites: §3 and §4 written. Drop lanes and
  waves.
- **Rule files.** Write `product/skills/rules/system-plans.md` (`paths: ["docs/plans/*-system.md"]`) from
  the rules in `backlog-requirements.md` and `backlog-epics.md` that still apply to §2 and §4, plus the
  feature-block rules from §3. Delete the two old files. In `plans.md`, add one line: a `*-system.md`
  plan's feature blocks follow `system-plans.md` and carry no `Stack`, `Agent`, `Budget` or `Gate`. In
  `rules/SKILL.md`, replace the two table rows with the `system-plans.md` row and add both old files to
  the step that retires installed files.
- **Not in S1:**
  - `solution-planner` and the command (S2).
  - `plan-format.md` (F1).
  - Hiding the skills (M1).
  - The skills still carry their old `name:` values, so the plugin surface is unchanged.
- **As built (2026-11-23):**
  - `product/skills/solution-blueprint/references/system-plan-format.md` (476 lines): §1 path, §2
    header, §3 sections, §4 feature task block, §5 `## Feature prompts — paste one per session` (heading
    `### F<n> — <title> (/product:plan-feature)`, first line the slash command), §6 living text and
    filing, §7 never, §8 the verbatim `## Close-out — every feature`, §9 a filled example
    (`004-workshop-booking-system.md`: F1 specced, F2 live, F3 on hold).
  - Renamed rather than rewritten in place (D21): `blueprint-template.md` → `skeleton-template.md`,
    `example-blueprint.md` → `example-skeleton.md`, `epic-map/references/example-epic-map.md` →
    `example-features-side-by-side.md`. Deleted `key-flows-and-decisions.md` and `pack-cross-checks.md`:
    the grep found only `solution-blueprint/SKILL.md:75`, `product/agents/solution-planner.md:83` and
    plan 015 in `implemented/` citing them. `solution-planner.md:83` still names `pack-cross-checks.md`;
    lint does not flag it (the path does not start with `references/`), and S2 rewrites that step.
  - `solution-blueprint/SKILL.md`: Steps 1–8 (read what exists, stack, architecture, areas → trees →
    agents with the catalog updated to the manifest's agents, auth, shared entities, conventions, hand
    the open decisions to the interview). No gate of its own: `solution-planner` holds the one approval.
    `architecture-style.md` kept, "blueprint" → "skeleton" at :5, :16, :25.
  - `ba-scoping-writeup`: §2 as nine `###` subsections; the tenth concern, open questions, goes to the
    plan's `## Open questions`. `ba-epic-writer`: §4 as one table `| Epic | Goal | In plain English |
    Features |`, and it hands the feature list (id, title, epic) to `solution-planner`. `epic-map`: §5's
    table, Steps 1–6, no lanes or waves.
  - `rules/system-plans.md` (`paths: ["docs/plans/*-system.md"]`); `backlog-requirements.md` and
    `backlog-epics.md` deleted. `plans.md` v5: the `*-system.md` line under "The document".
    `rules/SKILL.md`: ten files, the `system-plans.md` row, step 5 retires
    `backlog-{requirements,epics}.md` (written as a brace glob so the §7 grep stays quiet), step 6 finds
    system plans and story backlogs. `ba-story-quality-review/SKILL.md:23` no longer cites the deleted
    `backlog-epics.md`.
  - Names unchanged: `plan-blueprint`, `scoping`, `epics`, `plan-epic-map`; descriptions rewritten.
  - Gate: `skill-lint.py product` → `0 findings`; whole-library `skill-lint.py` → `0 findings`;
    `plugin-surface-check.py` → `OK`; `token-audit.py --violations-only` → exit 0;
    `pytest tools/test_skill_lint.py` → 95 passed.

### S2 — `solution-planner` and `/product:plan-system` write the system plan

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `product/agents/solution-planner.md` runs NEW, EXISTING and EXTEND (D17) and writes
`docs/plans/<NNN>-<system>-system.md` per `system-plan-format.md`. `/product:plan-system` routes to it.
`requirements-author`, `/product:refine` and `delivery-plan` are gone from the tree and the manifest.
`plugin-surface-check` prints `OK`.
**Depends on:** S1 (the format file and the four rescoped skills).
**Budget:** ~105k. Drivers:
- `CLAUDE.md` 25k.
- This plan §2–§5, D1, D7, D8, D16–D19 8k.
- `solution-planner.md` (14 KB) and `requirements-author.md` (11 KB) ~7k.
- Both commands ~1.5k.
- `system-plan-format.md` from S1 ~3k.
- `session-budget/SKILL.md` and its template (47 KB), for the prerequisite edit only ~6k by sections.
- The `product` manifest entry ~3k.
- Writes: the agent rewrite ~6k, the command ~1k, `session-budget` edits ~2k, manifest ~1k.
- Check output and read-back ~10k. Churn ×1.2.

**Gate: own tests.**
- `python3 tools/plugin-surface-check.py` → `OK`
- `python3 tools/skill-lint.py product | tail -1` → `0 findings`
- `python3 tools/token-audit.py --violations-only` → exit 0

- **`solution-planner.md`.** Rewrite it, keeping the house agent shape (lint R13 and R14: a `## Steps`
  table with `Load` and `Done when`, and a `## Report` holding `Mode:`):
  - Description: whole-system planner; a vision → the system plan's features, each handed to
    `/product:plan-feature`. Not for one feature (`/product:plan-feature`) or code.
  - Invariants: plans, never code; write reach `docs/plans/<NNN>-<system>-system.md` and
    `docs/agent-context/solution-planner.md`; the approval gate blocks (D16); evidence marks; inherit
    the stack and never upgrade it as a side effect.
  - Modes: NEW, EXISTING, EXTEND (D17). In EXISTING, already-built capabilities are §1 rows with
    `file:line` and no feature; old `requirements.md` / `epics.md` / `stories.md` and specs are input.
  - Steps:
    0. Orient (`engineering/agent-orientation-cache`).
    1. Interview in rounds (D16) about the vision and the skeleton's open decisions, loading
       `product/skills/domain-modeling` as `brainstorming` step 5 does.
    2. §2 (`product/skills/ba-scoping-writeup`).
    3. §3 (`product/skills/solution-blueprint`, `backend/_shared/pattern-guide` when a pattern decision is live).
    4. §4 and the feature list (`product/skills/ba-epic-writer`).
    5. §5 (`product/skills/epic-map`).
    6. **BLOCKING:** the user approves §2, §3 and the feature list.
    7. Write the file per `system-plan-format.md`: feature blocks, `## Close-out — every feature`, the
       prompts. F1 is the foundation when the skeleton isn't built (D19).
    8. Self-review: every §1 gap traces to a feature, every feature to a §1 row and an epic, every
       `Depends on` points backwards, every prompt's first line is the slash command.
  - Boundaries: `/product:plan-feature` designs each feature; `business-analyst` sweeps the KB;
    `documenter` runs first on a system with no documentation; it never loads the stack agents' skills.
  - Report: `Mode:`, the stack, the system plan path, the epic and feature counts, the next feature to
    paste, open questions.
- **`product/commands/plan-system.md`.** Description: plan a system from a vision — the system plan,
  one `/product:plan-feature` prompt per feature. Keep the three overriding rules, reworded: plans not
  code; Step 6 blocks; the system plan is not queued.
- **Delete** `product/agents/requirements-author.md`, `product/commands/refine.md` and
  `product/skills/delivery-plan/` (whole folder), and their three entries in `.claude-plugin/marketplace.json`.
- **`session-budget/SKILL.md`.** Its prerequisite becomes "a task list from `writing-plans` with `Files`
  filled in". Drop `epic-map.md` and `product:plan-delivery`. Rewrite the lines in
  `references/prompts-section-template.md` that name `delivery-plan.md` to name the feature's
  implementation plan.
- **Not in S2:**
  - The manifest's `product` description (C1).
  - References in other files (M1). `business-analyst.md` and the catalog still name
    `requirements-author` until then, and `skill-lint` may flag a dead path to a deleted file. Fix any
    such R8 finding inside `product/` here, by pointing it at the replacement in §5.
- **As built (2026-11-23):**
  - `product/agents/solution-planner.md` rewritten (12.3 KB, under the 14 KB agent budget): modes NEW,
    EXISTING, EXTEND (:49-51); `## Steps` table 0–8 with `Load` and `Done when` (:59-69), Step 6 the
    blocking approval of §2, §3 and the feature list (:67), Step 7 writes the file per
    `system-plan-format.md` with the `**Mode:**` line and every prompt-table `State` set to `live` (:68),
    Step 8 the self-review that replaces the deleted `pack-cross-checks.md` (:69); `## Report` opens with
    `Mode:`. Steps 2–5 draft in the session and send open decisions back to Step 1; nothing reaches disk
    before Step 7. `§1` is written in Step 4, with the feature list, since its `Gap` column names features.
  - `product/commands/plan-system.md` rewritten: routes to `solution-planner`; the three rules are plans
    not code, Step 6 blocks, the system plan is not queued.
  - Deleted: `product/agents/requirements-author.md`, `product/commands/refine.md`,
    `product/skills/delivery-plan/` (8 files), and their three entries in `.claude-plugin/marketplace.json`.
    The `product` description is untouched (C1).
  - `session-budget/SKILL.md`: prerequisite "a task list from `writing-plans` with `Files` filled in",
    output the feature's implementation plan `docs/plans/<NNN>-<feature>.md`, description
    "Not for ordering tasks (writing-plans)". `prompts-section-template.md`: every
    `…/delivery-plan.md` path is now `docs/plans/<NNN>-<feature>.md` (worked example
    `docs/plans/003-workshop-booking.md`).
  - EXISTING mode names the old pack as "an older initiative folder's requirements, epics and stories
    files", not by file name, so the §7 grep stays quiet on the agent.
  - No R8 finding appeared inside `product/` from the deletions, so nothing else was repointed. Textual
    mentions of the deleted lane remain for later tasks: `brainstorming/SKILL.md:3,12,18,33,101` and
    `writing-plans/references/plan-format.md:16,27,311` (F1); `integration-plan/SKILL.md:104,113` and its
    example (F2); `business-analyst.md:3,16,61` and `rules/plans.md:4,18`, `rules/SKILL.md:19` (M1).
  - Gate: `plugin-surface-check.py` → `OK`; `skill-lint.py product` → `0 findings` (whole library also
    `0 findings`); `token-audit.py --violations-only` → exit 0; `pytest tools/test_skill_lint.py` → 95 passed.
  - Unverified: no run of `/product:plan-system` in a scratch repo (the user's check after G1).

### F1 — `/product:plan-feature`: interview, spec, plan and write-back in one run

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `product/skills/brainstorming/SKILL.md` is `name: plan-feature` and runs SYSTEM, NEW
and SHAPED as §4 describes, including the acceptance criteria, the write-back and on hold.
`product/skills/writing-plans/SKILL.md` is `name: writing-plans` and is loaded by it. `plan-format.md`
and `plans.md` key `TD` tasks to a feature spec's acceptance criteria (D11). `plugin-surface-check`
prints `OK`.
**Depends on:** S2 (the system plan the write-back edits, and `solution-planner`'s hand-off).
**Budget:** ~105k. Drivers:
- `CLAUDE.md` 25k.
- This plan §2–§4, D6, D9–D12, D15, D20 8k.
- `brainstorming/SKILL.md` (10 KB) ~3k.
- `writing-plans/SKILL.md` (16 KB) ~4.5k.
- `plan-format.md` §4–§6 by sections ~8k.
- `system-plan-format.md` ~3k.
- `plans.md` and `tools/plugin-surface-check.py` ~4k.
- Writes: the `brainstorming` rewrite ~6k, edits to `writing-plans`, `plan-format.md` and `plans.md` ~6k,
  `FRONT_DOORS` ~0.5k.
- Check output and read-back ~10k. Churn ×1.2.

**Gate: own tests.**
- `python3 tools/plugin-surface-check.py` → `OK`
- `python3 tools/skill-lint.py product | tail -1` → `0 findings`
- `python3 tools/token-audit.py --violations-only` → exit 0

- **`brainstorming/SKILL.md`.**
  - Frontmatter: `name: plan-feature`. The description follows R3: "Use when one feature needs deciding
    and planning, from a system plan's prompt or on its own. Triggers "I want to add X", "plan this
    feature". Not for a whole system (plan-system)."
  - The front-door table: `/product:plan-feature` vs `/product:plan-system`.
  - Modes: SYSTEM, NEW, SHAPED (§4). SYSTEM reads the system plan's §2, §3, §5, its decisions and the
    feature's task block in step 1, and treats §3's decisions as settled. A question that would reopen
    one goes to the user as "this changes the system plan's D<n>".
  - Step 8 (design): for each design skill the feature needs, read its `SKILL.md` by path and write its
    section into the spec (§4 point 2). Name the four skills and when each applies.
  - Step 9: the spec format gains `## Acceptance criteria` and the optional design sections (§4). After
    approval, read `product/skills/writing-plans/SKILL.md` and follow it. In SYSTEM mode, then run the
    system plan's `## Close-out — every feature`.
  - On hold at any round (§4).
  - Remove every route to `requirements-author` and `/product:refine`.
- **`writing-plans/SKILL.md`.**
  - `name: writing-plans`. A description fit for a hidden skill.
  - Its input is the approved spec, with `## Acceptance criteria` as the `TD` and `Q` basis.
  - "When NOT to use" names `/product:plan-system`, not a task list from stories.
  - Step 5's sizing points at `product/skills/session-budget` for the detail.
- **`plan-format.md`.**
  - Line 16: the producers are `writing-plans` and `session-budget`.
  - §4 `TD`: "Plans that deliver a feature add the test-design family": the test plan per feature and the
    test cases per feature, citing `<spec> AC<k>`. A story-backlog plan still qualifies.
  - The `Q` deliverable example cites `<spec> AC<k>`.
  - §5 `DOC1` reads the spec as the source of purpose (or `stories.md` where a backlog exists).
  - The `solution-planner` pack paths in §1, §5 and §8 become the system plan.
- **`rules/plans.md:34-36`.** Re-key the `TD` rule the same way.
- **`tools/plugin-surface-check.py:45`.** `"product": frozenset("plan-feature notebooklm".split())`.
  `writing-plans` now sets `disable-model-invocation: true`.
- **Not in F1:**
  - The four design skills' own text (F2).
  - The QA agents and the documenter (K1).
  - `CLAUDE.md` (C1).
  - `user-invocable: false` (M1).
- **As built (2026-11-23):**
  - `product/skills/brainstorming/SKILL.md` rewritten: `name: plan-feature` (:2), the R3 description
    from the bullet (:3); the front-door table `/product:plan-feature` vs `/product:plan-system` (:12-16);
    modes SYSTEM / NEW / SHAPED (:22-30) with the SYSTEM reading list and "§3 and the decisions are
    settled", a reopening question worded "this changes the system plan's D<n>" (:32); step 8 names the
    four design skills by path with when each applies and the spec section each writes (:59-68); step 9
    approves the spec; step 10 reads `product/skills/writing-plans/SKILL.md`, then in SYSTEM mode runs the
    system plan's `## Close-out — every feature`, setting `State` to `specced (plan <NNN>)` and deleting
    the prompt only in the follow-up commit (:72); `## On hold` (:74); the spec format gains
    `**System plan:**`, `## Acceptance criteria` (`AC1…ACn`) and the four optional design sections (:88-116).
    No route to `requirements-author` or `/product:refine` is left. Step 10 was added rather than
    extending step 9, so approval and planning are separate `Done when`s.
  - `product/skills/writing-plans/SKILL.md`: `name: writing-plans`, `disable-model-invocation: true`
    (:2-4); `## Input` (:13) names the approved spec and its acceptance criteria as the `TD`/`Q` basis
    and routes the design to `/product:plan-feature` and a whole system to `/product:plan-system`;
    Step 5 points at `product/skills/session-budget/SKILL.md` (:146); the handoff returns to
    `plan-feature` step 10. To stay under the 16,000-char body budget, four paragraphs were tightened
    (intro, unit-of-work, property 1, human prerequisites) without changing their rules (D23).
  - `plan-format.md`: line 16 names `writing-plans` and `session-budget`; the path paragraph points a
    system plan at `system-plan-format.md`; §4's `Q` example cites `docs/specs/014-orders-design.md`
    AC1–AC9; §4 `TD` is "Plans that deliver a feature" (:174), per feature, citing `<spec> AC<k>`, a
    story backlog still qualifying; §5 `DOC1` reads the spec (or the backlog); the `solution-planner`
    pack paths in §1, §5, §7 and §8 are gone (D23).
  - `rules/plans.md`: the `TD` rule re-keyed (:36); the S1 system-plan line kept. Also its
    `docs/plans/*/delivery-plan.md` glob and pack path, and the matching row in `rules/SKILL.md:19` (D23).
  - `tools/plugin-surface-check.py:45`: `"product": frozenset("plan-feature notebooklm".split())`.
  - Gate: `plugin-surface-check.py` → `OK`; `skill-lint.py product` → `0 findings` (whole library also
    `0 findings`); `token-audit.py --violations-only` → exit 0; `pytest tools/test_skill_lint.py` → 95 passed.
  - Unverified: no `/product:plan-feature` run in a scratch repo, so the write-back and on-hold flows are
    unexercised (the user's check after G1).

### F2 — The four design skills write sections of a feature spec

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `data-model-plan`, `experience-plan`, `api-surface-plan` and `integration-plan` each take
the feature spec and the system plan's §3 as input and write their section of the spec (`## Data model`,
`## Experience` with `### Rendering plan`, `## API surface`, `## Integrations`). None of them names
`blueprint.md`, a pack file or a `US<n>`. Each example is a filled spec section.
**Depends on:** F1 (the spec format with the section names).
**Budget:** ~135k. Drivers:
- `CLAUDE.md` 25k.
- This plan §4, §6, D3, D6 4k.
- The four skills with their references (120 KB) ~34k.
- The spec format in `brainstorming/SKILL.md` ~3k.
- Writes: four `SKILL.md` rewrites ~20k, four examples rewritten as spec sections ~12k.
- Lint output and read-back ~10k. Churn ×1.2.
- Natural split if it runs over: `data-model-plan` and `api-surface-plan` first, then `experience-plan`
  and `integration-plan`.

**Gate: own tests.**
- `python3 tools/skill-lint.py product | tail -1` → `0 findings`
- `python3 tools/token-audit.py --violations-only` → exit 0
- `grep -rnE 'blueprint\.md|data-model\.md|experience-plan\.md|api-surface\.md|integrations\.md|epic-map\.md|delivery-plan|US[0-9<]' product/skills/{data-model-plan,experience-plan,api-surface-plan,integration-plan}` prints nothing

- **Each skill.**
  - Prerequisites: the feature's approved decisions in the spec, and the system plan's §3 (entities,
    conventions, auth) when the feature came from one. Standalone, the repo's existing code.
  - Output: the spec section, its subsections and their order.
  - Scope: this feature only, on top of the skeleton. An entity, endpoint or screen that §3 owns is
    referenced, never redefined.
  - Remove each "approved `blueprint.md`" gate. The spec approval in `plan-feature` is the gate.
- **`experience-plan`.** The rendering plan moves from `experience-plan.md` §4a to the spec's
  `### Rendering plan`, same table. `references/rendering-strategy.md` keeps its content; rewrite only
  its references to the plan file.
- **`api-surface-plan`.** `references/validation-catalog.md` keeps its content; it is the feature's
  validation catalog now.
- **Examples.** Rewrite each `example-*.md` as that section of one shared toy spec
  (`docs/specs/004-booking-cancellation-design.md` in the examples' text), so the four agree with each
  other.
- **Not in F2:** files outside these four skills that cite `experience-plan.md` §4a or `api-surface.md`
  (M1).
- **As built (2026-11-23):**
  - The four `SKILL.md` files rewritten, `name:` kept (D14), each with `## Input` (the spec so far, the
    system plan's §3 and the specs of the features it depends on; standalone, the code), `## Output`
    (its spec section and the subsections in order), `## Scope` (this feature only; what §3 or an
    earlier spec defined is a `### Builds on` row and a delta, never redefined; a §3 change is put to
    the user as "this changes the system plan's §3 <line>") and a `## Section template`. No approved
    `blueprint.md` gate: step 8's section approval and step 9's spec approval are the gate.
    `data-model-plan/SKILL.md:8-27`, `api-surface-plan/SKILL.md:8-31`, `experience-plan/SKILL.md:8-29`,
    `integration-plan/SKILL.md:8-32`. Every "Delivery task" column became "the implementation plan
    assigns it"; a blocking unknown's third place is a human prerequisite task `writing-plans` writes.
    `**Acceptance:**` lines cite the spec's own `AC<k>`.
  - `experience-plan`: the rendering plan is the spec's `### Rendering plan` (Step 5), same contract;
    `references/rendering-strategy.md` changed only at :3, :84, :93 and :129 (`RESUME` → "an existing
    app"). `api-surface-plan`: the spec cites `docs/specs/validation-catalog.md`, copied there by the
    first spec with an API surface (D24); `references/validation-catalog.md` changed only at its
    `data-model.md` / `api-surface.md` / `integrations.md` / `product:plan-integrations` references
    (:67, :94, :133, :149, :170, :171, :190, :198).
  - The examples were renamed `example-data-model-section.md`, `example-experience-section.md`,
    `example-api-surface-section.md`, `example-integrations-section.md` (D24) and rewritten as filled
    sections of `docs/specs/006-booking-cancellation-design.md`, F3 of the system-plan-format example
    `docs/plans/004-workshop-booking-system.md` (D24), sharing AC1–AC6 (listed in the data-model
    example), spec 005's tables and spec 007's screens and endpoints.
  - `state-grid` is named by path (`product/skills/ba-entity-state-grid/SKILL.md`), not as
    `product:state-grid`. The integration description was shortened to 194 chars for token-audit.
  - Gate: `skill-lint.py product` → `0 findings`; `token-audit.py --violations-only` → exit 0; the F2
    grep prints nothing; `plugin-surface-check.py` → `OK`.
  - Follow-up, outside F2's files: S1's §3 example (`system-plan-format.md` §9, `example-skeleton.md`)
    puts the app on a Vite SPA, while `rendering-strategy.md` gives signed-in pages that are not
    long-session tools `ssr`. The experience example shows it as a §3 question the owner settled (all
    `csr` kept); G1 decides whether the §3 example should say Next.js instead.
  - Unverified: no `/product:plan-feature` run has loaded these four files and written a spec section.

### K1 — QA and the documenter read the feature spec

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-test-planner`, `test-plan-writer`, `qa-test-case-designer`, `/qa-…:test-plan` and
`test-first` take a feature spec's `## Acceptance criteria` as their primary basis, citing
`<spec> AC<k>`, and still accept a story backlog. `business-documentation` reads the spec as the source
of purpose. `business-analyst` owns the AUDIT of an imported backlog (D5). `skill-lint` reports 0
findings over `qa` and `product`.
**Depends on:** F1 (the `TD` rule and the spec's acceptance criteria), F2 (same tree: both lint `product/`).
**Budget:** ~95k. Drivers:
- `CLAUDE.md` 25k.
- This plan §4, §6, D5, D11 4k.
- `qa-test-planner.md`, `qa-test-case-designer.md`, `test-plan-writer`, `test-plan.md`, `test-first`
  (46 KB) ~13k.
- `business-documentation/SKILL.md`, `documenter-invariants.md`, `delivery-note.md` (26 KB) ~7.5k.
- `business-analyst.md` (10 KB) ~3k.
- Writes: edits across nine files ~12k.
- Lint output and read-back ~10k. Churn ×1.2.

**Gate: own tests.**
- `python3 tools/skill-lint.py qa/manual qa/_shared/test-first product | tail -1` → `0 findings`
- `python3 tools/qa-version-check.py` → `OK`
- `python3 tools/plugin-surface-check.py` → `OK`

- **QA.**
  - `qa/manual/test-plan-writer/SKILL.md:15` and its §1 table row: the basis is a feature spec's
    acceptance criteria, then a story backlog, then the other sources.
  - The `Test Plan — <epic or feature>` heading is per feature first.
  - `qa-test-planner.md`'s chain ("you are step 3") is redrawn from §2 of this plan:
    `/product:plan-feature` → the feature's implementation plan → `TD`.
  - `qa-test-case-designer.md:16,36`: one suite per feature from the spec's acceptance criteria (a
    story's suite stays a valid input).
  - `qa/manual/commands/test-plan.md`: the argument is a spec path or a plan.
  - `qa/_shared/test-first/SKILL.md:19-20`: `Acceptance:` lines cite `<spec> AC<k>`. Journeys and test
    ids come from the spec's `## Experience`, the API from `## API surface` and the contract task's
    OpenAPI asset.
- **Documenter.** In `business-documentation/SKILL.md`, `references/documenter-invariants.md` and
  `references/delivery-note.md`: the plan's spec is the source of purpose. The delivery note's
  *Not delivered* table lists acceptance criteria not met (stories where a backlog exists).
  `delivery-note.md:39` "a plan with no stories" stays valid. Leave `evals/` unchanged: its story-based
  fixture is still a valid input.
- **`business-analyst.md`.** Line 61 routes design to `/product:plan-feature` and a vague initiative to
  `/product:plan-system`. Line 16's "`requirements-author` repairs those" becomes "the user, or
  `solution-planner` for a system plan". Add the AUDIT duty: a backlog written elsewhere gets a
  `product/skills/ba-story-quality-review` verdict per story, with no file changed.
- **Not in K1:** the design, frontend, mobile, tooling, data and backend references to the old pack
  files (M1).
- **As built (2026-11-23):**
  - QA. `qa/manual/test-plan-writer/SKILL.md`: the unit is one feature from its spec's acceptance criteria
    (:9), the basis a feature spec first, a story backlog second (:15), `# Test Plan — <feature or epic>`
    with **Covers** naming the spec and its AC range, §3 rows and §10 traces citing `AC<k>` of the spec in
    **Covers** (`US6 AC3` from a backlog), Ready/Done and the section rules keyed to acceptance criteria.
    `qa-test-planner.md:14-18`: the chain redrawn inline (`/product:plan-feature` 1 → implementation plan 2
    → `TD` 3–4 → `Q` 5 → implementation, gate, `DOC1` 6–8), since `solution-planner.md` no longer has a
    "delivery chain" section; a spec (or the plan that builds it) is the first input shape, one plan per
    feature; the backlog row stays. `qa-test-case-designer.md:14-17,36-37`: one suite per feature from the
    spec (`## Experience` journeys, `## Acceptance criteria` conditions), one per story from a backlog.
    `qa/manual/commands/test-plan.md` and (beyond the bullet) `test-cases.md`: the argument is a spec or
    its plan. `qa/_shared/test-first/SKILL.md:17-41`: inputs are the spec's `## API surface`,
    `docs/specs/validation-catalog.md`, `## Experience` (`### Journeys`, `### Screens` `Test ids:`,
    `### Rendering plan`); the tag is `SPEC<NNN>-AC<k>` (`SPEC006-AC2`), `US<n>-AC<k>` from a backlog,
    with the `TP-` id beside it (D25).
  - Documenter. `business-documentation/SKILL.md:21,25,103`, `documenter-invariants.md:24,37-38`: the
    plan's feature spec (goal, decisions, acceptance criteria) is the source of purpose, a story backlog
    where the plan was built from one. `delivery-note.md`: the template's first column is *Criterion*
    (`AC<k>`) and its stamp carries `spec` and `criteria`; a backlog plan keeps *Story* and `stories`; "a
    plan with no stories" became "no stories and no acceptance criteria" (it still puts `—`); the worked
    example stays the story-based plan 004, said so in its lead-in, matching `example-area.md` and the
    evals. The guide stamp gained an optional `spec` key (`guide-shape.md:88`, `system-overview.md:79`).
    Beyond the bullet, `product/agents/documenter.md:16` and `feature-documenter.md:77` pointed at the
    deleted "delivery chain" in `solution-planner.md`; both now draw it inline, and their report lines
    and `DOC1` scope read the spec. `evals/` unchanged.
  - `business-analyst.md`: description (:3) names the backlog audit and routes design to
    `/product:plan-feature`; :16 "the user repairs those, or `solution-planner` for a system plan"; a
    **BACKLOG AUDIT** mode row (:32) reads `product/skills/ba-story-quality-review/SKILL.md` by path, a
    verdict per story, no backlog or KB file changed, rewrites proposed per
    `product/skills/ba-story-writer/SKILL.md` in the report only; :61 routes to `/product:plan-feature` and
    `/product:plan-system`; the report gains a backlog-verdicts line (D25).
  - Token budget: `qa-test-planner.md` and `qa-test-case-designer.md` were already near token-audit's
    14,000-char agent budget; both were tightened elsewhere (Fix/Extend, orient, step-2 prose) without
    changing a rule, to 13,987 and 13,993 chars. The `business-analyst` description is 347 chars.
  - Gate: `skill-lint.py qa/manual qa/_shared/test-first product` → `0 findings`; `qa-version-check.py` →
    `OK`; `plugin-surface-check.py` → `OK`. Also `skill-lint.py` (whole library) → `0 findings`,
    `token-audit.py --violations-only` → exit 0, `pytest tools/test_skill_lint.py` → 95 passed.
  - Unverified: no `TD`/`Q`/`DOC1` task has run against a real spec, and `doc-lint.py` was not run on a
    delivery note with `spec`/`criteria` (its stamp check requires only `plan`, `source`, `audience`,
    `doc-lint.py:369-375`).

### M1 — Every remaining reference, and the hidden skills

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** The §7 grep prints nothing. Every skill in §5 marked "Hidden" sets both
`disable-model-invocation: true` and `user-invocable: false`, and `plugin-surface-check` enforces it
(rule 10). `skill-lint` reports 0 findings over the whole library.
**Depends on:** F2, K1 (the last files that change their own references).
**Budget:** ~120k. Drivers:
- `CLAUDE.md` 25k.
- This plan §5–§7, D13 5k.
- `tools/plugin-surface-check.py` (8 KB) ~2.5k.
- The §7 grep output ~6k.
- About 30 files edited at the grep hits, ~1.5k each by section ~45k.
- 12 frontmatter edits ~3k.
- Check output and read-back ~10k. Churn ×1.2.

**Gate: own tests.**
- `python3 tools/plugin-surface-check.py` → `OK`
- `python3 tools/skill-lint.py | tail -1` → `0 findings`
- `python3 tools/token-audit.py --violations-only` → exit 0
- `python3 -m pytest tools/test_skill_lint.py -q` → green
- the §7 grep prints nothing, except hits in `docs/skills-catalog.md`, `README.md` and `CLAUDE.md` (C1)

- **Hidden.** Add `user-invocable: false` beside `disable-model-invocation: true` in `writing-plans`,
  `session-budget`, `solution-blueprint`, `ba-scoping-writeup`, `ba-epic-writer`, `epic-map`,
  `data-model-plan`, `api-surface-plan`, `experience-plan`, `integration-plan`, `ba-story-writer` and
  `ba-story-quality-review`.
- **`tools/plugin-surface-check.py`.**
  - Add `HIDDEN = {"product": frozenset(<the twelve skill names>)}`.
  - Rule 10: a skill in `HIDDEN` sets `user-invocable: false` and `disable-model-invocation: true`, and a
    front door never sets `user-invocable: false`.
  - Add the rule to the docstring, with D13's doc citation.
- **References.** Run the §7 grep and rewrite each hit per §6. The known ones outside `product/`:
  - `design/ux-review/SKILL.md:44,96`, `design/ux-patterns/SKILL.md:112`,
    `design/agents/design-auditor.md:71,88`, `design/prototype/SKILL.md` (`/product:feature`).
  - `frontend/react/agents/fe-react.md:18`, `frontend/react/skills/project-setup/SKILL.md:50`,
    `frontend/blazor/agents/fe-blazor.md:16`, `frontend/blazor/skills/basics/SKILL.md:41`,
    `frontend/blazor/skills/project-setup/SKILL.md:42`.
  - `mobile/react-native/agents/mobile-react-native.md:17`, `mobile/android/agents/mobile-android.md:30`.
  - `qa/{typescript,java,dotnet}/skills/ui-test-author/playwright/references/server-rendered-pages.md:3`.
  - `tooling/_shared/capability-contract/SKILL.md:31`, `data/agents/data-architect.md`,
    `backend/rust/skills/database-code/SKILL.md:192`, `backend/rust/skills/pattern-writer/SKILL.md:290`.
  - `frontend/_shared/product-analytics/SKILL.md:80,227`: success metrics come from the system plan's §2.
  - `engineering/spec-vs-code-audit/SKILL.md`, `engineering/rules/SKILL.md`, `engineering/rules/audits.md`.
  - Inside `product/`: `ba-project-memory`, `domain-modeling` and its two references, `feature-trace`,
    `rules/SKILL.md`, `writing-plans/references/web-routes.md`, and anything S1–K1 left.
- **R12.** No line may tell a model to invoke a hidden skill. A hidden skill is named by its path and
  read, never called as `product:<name>`.
- **Not in M1:** `docs/skills-catalog.md`, `README.md` and `CLAUDE.md` (C1), and `docs/plans/implemented/`
  and `docs/audits/`, which are records and are never edited.
- **As built (2026-11-23):**
  - Hidden: the twelve skills set `user-invocable: false` on the line after `disable-model-invocation: true`
    (e.g. `product/skills/epic-map/SKILL.md:5`). `tools/plugin-surface-check.py` gains `HIDDEN` (keyed by
    the skills' `name:` values: `writing-plans plan-session-budget plan-blueprint scoping epics
    plan-epic-map plan-data-model plan-api-surface plan-experience plan-integrations stories
    story-review`) and rule 10 with D13's citation in the docstring. Proved: removing the line from
    `epic-map` printed `product: hidden skill 'plan-epic-map' must set user-invocable: false and
    disable-model-invocation: true`; restored, `OK`.
  - References: every §7 hit outside C1's files rewritten per §6. Experience, data-model and API-surface
    readers (design, fe, mobile, desktop, qa server-rendered pages and the three `qa-ui-*` agents,
    tooling, data-architect, backend rust) now cite the spec's `## Experience` / `### Rendering plan`,
    `## Data model`, `## API surface` and `docs/specs/validation-catalog.md`; `product-analytics` takes
    metrics from the system plan's §2 `### Success`; `ba-story-writer`, its example and
    `rules/backlog-stories.md` (rules v6) cite §2 `What it must do` / `Constraints` and are read by
    `business-analyst`; `feature-trace` takes stated intent from the spec's criteria, the system plan's
    §2 or a backlog; `tools/MISSION-CONTROL-MOVED.md` says the delivery-plan ingestion format is gone.
  - Beyond the grep: `session-budget` (SKILL.md and `references/prompts-section-template.md`) re-keyed
    to the spec: TD1/TD2/Q1/DOC1 templates read `## Acceptance criteria` and tag `SPEC<NNN>-AC<k>` (D25),
    one test plan and one suite per feature, the task table takes `plan-format.md` §6's columns (Epic,
    Story and Stream dropped), the filled example cites spec blocks. The four backend `pattern-writer`
    files say "the system plan skeleton's `Modules:` line", not "blueprint". The seven stack-plugin
    manifest descriptions name `/product:plan-system, /product:plan-feature`.
  - Engineering audit register renamed (D26).
  - Gate: `plugin-surface-check` OK; `skill-lint` 0 findings; `token-audit --violations-only` exit 0;
    `pytest tools/test_skill_lint.py` 95 passed; `qa-version-check` OK. §7 grep: 58 hits, all in C1's
    files — `docs/skills-catalog.md` 40, `README.md` 16, `CLAUDE.md` 1, and the `product` description at
    `.claude-plugin/marketplace.json:52` (C1's manifest bullet).
  - Left for later, outside §7: `documenter`, `business-documentation`, `codebase-survey` and
    `documenter-invariants.md` still say "a delivery plan's `DOC1`" (generic for an implementation plan,
    harmless).

### C1 — The catalog, the README, `CLAUDE.md` and the manifest description

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `docs/skills-catalog.md`, `README.md`, `CLAUDE.md` and the `product` description in
`.claude-plugin/marketplace.json` describe the two front doors, the system plan, the hidden steps and the
`TD` rule as this plan built them. The §7 grep prints nothing anywhere.
**Depends on:** M1.
**Budget:** ~110k. Drivers:
- `CLAUDE.md` 25k (already loaded, and edited).
- This plan §2, §5, D11–D13 4k.
- The catalog's product, QA-manual and command-count sections and its grep hits, not the whole 226 KB
  file ~22k.
- `README.md` sections at the grep hits and the product lane (`:19`, `:138`, `:152`, `:273`, `:410-450`) ~12k.
- The manifest description ~1k.
- Writes ~18k.
- Check output and read-back ~10k. Churn ×1.2.

**Gate: own tests.**
- the §7 grep prints nothing
- `python3 tools/skill-lint.py | tail -1` → `0 findings`
- `python3 tools/token-audit.py --violations-only` → exit 0

- **`CLAUDE.md`.**
  - The `Planning` section: the bullet "A plan that serves stories plans its testing" becomes "A plan
    that delivers a feature plans its testing" (D11), and its `In review` line follows.
  - The line naming `product:plan-feature`, `product:plan-delivery` and `product:plan-session-budget` as
    producers of the plan format names `writing-plans` and `session-budget`, plus the system plan's own
    format.
- **`docs/skills-catalog.md`.**
  - The product section: 2 front doors, the hidden steps, `requirements-author` and `delivery-plan` gone,
    the skill / agent / command counts recomputed from the manifest.
  - The command count line (`:28`) and the "two front doors, fenced" paragraph (`:49`).
  - The QA-manual entries that name `stories.md`.
- **`README.md`.** The product lane, the delivery chain diagram (`:418-443`), the command table and the
  counts.
- **Manifest.** The `product` description: `/product:plan-system` (a vision → a system plan of features),
  `/product:plan-feature` (a feature → spec → plan, written back), the documentation and analysis lanes.
  Keep it under token-audit's description budget.
- **Not in C1:** new restructuring. A finding outside §7 goes into `Status` as a follow-up.

### G1 — The whole sweep, and filing the plan

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** Every command in §7 passes on the merged tree, and the plan is filed.
**Depends on:** C1.
**Budget:** ~90k. Drivers:
- `CLAUDE.md` 25k.
- This plan §7 and the `As built` notes 10k.
- The sweep output ~20k.
- Fixes ~20k.
- The merge ~5k. Churn ×1.2.

**Gate (this is the last runnable task, so it runs the whole set once more across the plan, in order):**
the commands in §7.

- Run §7 once. Fix each failure at the narrowest file, rerun only what failed, then run §7 once more.
- Read the three hand-offs end to end:
  - `product/commands/plan-system.md` → `solution-planner.md` → `system-plan-format.md`.
  - The prompt block shape → `brainstorming/SKILL.md` SYSTEM mode → `writing-plans` → the write-back.
  - `writing-plans` `TD` → `qa-test-planner` → `test-first`.

  Every name and path one file hands to the next must exist. The lint cannot see a hand-off that names
  the wrong section.
- Merge `master` into the plan's branch (close-out step 6). Where a plan merged since S1 names an old
  command or file, rewrite it per §6.
- **Status, when filing.** Name as unverified:
  - No session has run `/product:plan-system` or `/product:plan-feature` yet.
  - Claude Code hiding the twelve `user-invocable: false` skills is unchecked (D13).
  - Plan Queue skipping `## Feature prompts` is unchecked (D10).

  The user restarts, runs `/product:plan-system` on a small vision in a scratch repo, pastes one feature
  prompt, puts another on hold, and checks that `/product:writing-plans` is not in the `/` menu.
- **Not in G1:** new restructuring.

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

- S1, S2, F1, F2, K1, M1, C1 and G1 run one after another. K1 needs only F1's work, but it waits for
  F2 because both edit files under `product/` that the other's lint run reads, so none runs beside
  another.
- No prompt pushes, and none switches a project over.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| S1 | `docs` | `general-purpose` | none | — | ~115k |
| S2 | `docs` | `general-purpose` | S1 | — | ~105k |
| F1 | `docs` | `general-purpose` | S2 | — | ~105k |
| F2 | `docs` | `general-purpose` | F1 | — | ~135k |
| K1 | `docs` | `general-purpose` | F1, F2 | — | ~95k |
| M1 | `docs` | `general-purpose` | F2, K1 | — | ~120k |
| C1 | `docs` | `general-purpose` | M1 | — | ~110k |
| G1 | `docs` | `general-purpose` | C1 | — | ~90k |
| — | restart, run `/product:plan-system` in a scratch repo, check the hidden skills and Plan Queue | **the user** | G1 | — | — |

S1, S2, F1, F2, K1 and M1 have landed, and their prompts are deleted.

---

### C1 — The catalog, the README, CLAUDE.md and the manifest description (general-purpose, docs)

````
Depends on: M1
Agent: general-purpose · Stack: docs

Task C1 of docs/plans/018-product-system-to-feature-lane.md: make the catalog, README.md, CLAUDE.md and
the product manifest description describe the lane this plan built.

Deliverable: docs/skills-catalog.md, README.md, CLAUDE.md and the product description in
.claude-plugin/marketplace.json describe the two front doors, the system plan, the hidden steps and the
TD rule as this plan built them. The §7 grep prints nothing anywhere.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §5, §7, D11–D13, task C1 and the As built notes above it, and "Close-out — every task".
3. The §7 grep's hits in the three files, and the sections the task names. Do not read the whole
   226 KB catalog. After M1 the only other hit is the product description at
   .claude-plugin/marketplace.json:52.
4. The product entry in .claude-plugin/marketplace.json.

Build: the task's bullets, in order. Recompute the product skill, agent and command counts from the
manifest; don't carry them over from the old text.

Traps:
- CLAUDE.md is loaded into every session: change only the bullets the task names.
- Keep the product description within token-audit's description budget.
- M1 renamed the engineering audit register to docs/audits/<NNN>-<slug>-register.md (D26): the catalog's
  spec-vs-code-audit and engineering-rules entries follow it.

Gate:
  the §7 grep                                        → prints nothing
  python3 tools/skill-lint.py | tail -1              → 0 findings
  python3 tools/token-audit.py --violations-only     → exit 0

Commit: `docs: catalog, README and CLAUDE.md describe the plan-system → plan-feature lane (018 C1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — The whole sweep, and filing the plan (general-purpose, docs)

````
Depends on: C1
Agent: general-purpose · Stack: docs

Task G1 of docs/plans/018-product-system-to-feature-lane.md: run the whole sweep on the merged tree,
fix what it finds, and file the plan.

Deliverable: Every command in §7 passes on the merged tree, and the plan is filed.

Read, in this order:
1. CLAUDE.md.
2. The plan: §7, every As built note, task G1, and "Close-out — every task".
3. The three hand-off chains the task names, end to end.

Run §7 once. Fix each failure at the narrowest file, rerun only what failed, then run §7 once more.

Traps:
- A failure may belong to any task above. Fix it where it is, and name that task in As built.
- Merge master into the plan's branch before filing (close-out step 6). Rewrite per §6 any old name a
  newly merged plan brought in.
- No new restructuring. A finding outside §7 goes into Status as a follow-up.

Gate (this is the last runnable task, so it runs the whole set once more across the plan, in order):
  the commands in §7.

Commit: `product: plan 018 sweep green (018 G1)`.
When filing, Status names as unverified: no session has run either front door; Claude Code hiding
the user-invocable: false skills (D13); Plan Queue skipping "## Feature prompts" (D10).
Close out per the plan's "Close-out — every task" before you stop.
````
