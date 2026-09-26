# 001 — Library conformance sweep — plan (2026-09-26)

**Goal:** Bring every published folder of the library in line with the checks the 2026-09-26
engineering-practices review settled (§4), and clean up each folder's old plans, progress files and
leftovers along the way (§5). One repo-wide gate at the end proves it (§7).

**Status:** S1 and S2 landed 2026-09-26 (S1: engineering-practices, templates, CONTRIBUTING;
`.agent-template` removed. S2: the backend/_shared planning lane — `delivery-plan` and `session-budget`
now emit `## Close-out — every task`; `docs/plans/implemented/` created, holding
`planning-lane-rebuild.md` and `PLANNER-PLAN.md`). S3 landed 2026-09-26 (the backend/_shared
documenter and pattern lane, and backend/dotnet; `UNIT-TESTING-PLAN.md` and `DOCUMENTER-PLAN.md` filed
to `docs/plans/implemented/`, and the backend audit filed live as `docs/plans/backend-PLAN.md`). S4 landed
2026-09-26 (backend/java, backend/node and backend/python; the Gate line in `be-java`, `be-node` and
`be-python`, the seven be-python descriptions under budget). S5 landed 2026-09-26 (qa/dotnet API, BDD
and LLM lanes: the Gate line in three agents, 35 stale skill-path citations and 15 missing Do-NOT
clauses fixed; the stale-path and "Run what you write" families are carried into S6–S13, S15 and S16).
S6 landed 2026-09-26 (qa/dotnet UI, mobile and performance lanes and commands: the Gate line in three
agents, the production-uptime-checks names resolved, two new stale-path families — `performance/nbomber`
and `qa/_shared/api-contract-testing` — fixed across qa/dotnet and carried into S7–S11, S13 and G1).
S7 landed 2026-09-26 (qa/java API, BDD and LLM lanes: the Gate line in three agents, the two K1 names,
21 stale paths, the six qa/java `Node 20` hits and 25 descriptions; the LLM agent's `qa/manual` write-up
became a hand-off, D15). S8 landed 2026-09-26 (qa/java UI, mobile and performance lanes and commands:
the Gate line in three agents, the production-uptime-checks names resolved, seven Do-NOT clauses added;
one open question raised, O9). S9 landed 2026-09-26 (qa/typescript API, BDD and LLM lanes: the Gate
line in three agents, 63 `Node 20` hits moved to Node 24 with the realtime Node-20 boundary reworded as an EOL
flag, 20 stale paths, the K1 name and 23 descriptions; the LLM agent's `qa/manual` write-up became a hand-off,
D15). S10 landed 2026-09-26 (qa/typescript UI, mobile and performance lanes and commands: the Gate line in
three agents, the last 23 `Node 20` hits moved to Node 24 so qa/typescript holds only flagged EOL lines, the
production-uptime-checks names resolved, eight Do-NOT clauses added). S11 landed 2026-09-26 (qa/_shared and
qa/manual: the Gate line in three agents, the two mobile security descriptions and `qa-test-case-designer`
under budget, nine Do-NOT clauses added, 20 stale paths fixed; the "(Stage N, forthcoming)" family is carried
into S17 and S18). S12 landed 2026-09-26 (qa/cicd and qa/reporting: the Gate line in six agents,
`qa-ci-pipelines` → `qa-ci-pipelines-<stack>` in the three `flaky-test-quarantine` skills, every Node 20 and
.NET 8 default moved to Node 24 / .NET 10, the `test-reports` green-washing samples fixed against
`ci-conventions` with the quarantine lane stated as its one exception, D16; the .NET 8 and
`continue-on-error` families are carried into S13, S14 and S17). S13 landed 2026-09-26 (frontend/blazor,
frontend/react and the three published auth folders: the Gate line in `fe-blazor` and `fe-react`, `fe-react`
649 and `data-grid` 495 under budget, the K1 name and six stale paths fixed, `auth0-blazor`'s .NET 8 default
moved to .NET 10; `frontend/PLAN.md` filed live as `docs/plans/frontend-PLAN.md`, its Blazor port unbuilt).
S14 is next. S1–S18 are ungated: the edits from S1 to S13 are built but unverified until G1 runs §7.

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| Every name a skill, agent or command cites resolves to something that exists | Removed-skill names: 0 left after `c6a97d1`. 15 other backticked names resolve to nothing (§6.1), e.g. `qa-ci-pipelines` ×11 across 7 files, `qa-performance-k6` ×6, `qa-test-quality-check-typescript` ×3. Relative `.md` links: 18 broken, all deliberate examples inside templates | Resolve or remove the 15, folder by folder (S1–S18); G1 proves 0 |
| Agents obey a plan task's `Gate:` line | 44 agent files carry run-the-suite exit criteria (165 `green` hits, e.g. `backend/dotnet/agents/be-dotnet.md` Step 3 "`dotnet test` green"); none of the 54 in-scope agents mentions `Gate:` | Add the fixed Gate line (§4 K2) to every in-scope agent and to the agent template |
| No branch, worktree, reviewer or inline-execution flow | Those skills are gone (`0eecfce`, `817f7df`); 42 agents now say "Work in the checkout you are given — never create a branch or worktree." Skills outside those edits are unchecked | K3 sweep per folder |
| Units of planned work are called tasks, and plan-writing skills emit the plan format | 152 `phase`/`slice`/`milestone` hits in 81 files, domain versus plan use not yet separated; `plan-format.md` §7 (the close-out) added in `817f7df`, but `delivery-plan` and `session-budget` do not emit it yet | K4 sweep; S2 aligns the planning lane |
| Prompts state a rule and its reason, without dated emphasis | 35 dated-emphasis hits in 30 files (`Iron Law`, `HARD-GATE`, `Announce at start`, …): 11 in `engineering-practices`, 11 in `backend/_shared`; 54 all-caps rule words in 39 files; unsourced statistics in `systematic-debugging` and `standards-audit-engine` | K5 sweep |
| Versions follow CLAUDE.md's version policy | 122 `Node 20` + 7 `node:20` (86 of them in 44 `qa/typescript` files), 7 `Spring Boot 2` + 3 `Java 17` in `backend/java`, 2 `Python 3.10`, 2 `Node 18`, 1 `React 17` (§6.3) | K6 sweep; migration and down-level lanes judged, not bulk-replaced |
| Descriptions carry triggers and a Do-NOT clause, within `tools/token-audit.py`'s budgets | `python3 tools/token-audit.py` (2026-09-26): 34 skill descriptions over 500 chars, 11 agent descriptions over 650 (§6.2), plus 160 body/file size violations (D6). Marketplace: 0 missing paths | K7: fix the 45 description violations and check every description |
| Instructions name the project's own commands, not defaults | The one known case (`ep-worktrees`' `npm install`) left with that skill; other folders unchecked | K8 sweep |
| Old plans, progress files and leftovers are filed or removed | 5 root `*-PLAN.md`; `backend/{PLAN,DOCUMENTER-PLAN,PLANNER-PLAN,UNIT-TESTING-PLAN}.md`; `frontend/PLAN.md`; `meta/PLAN.md`; 5 unnumbered files in `docs/plans/`, no `docs/plans/implemented/` yet; 6 tracked build files under `tools/mission-control/.next/`; tracked `.claude/settings.local.json`; `.agent-template/AGENT.md` beside `.skill-template/agent.md` | Apply §5 per folder; G1 takes the root |
| The `claude-api` copy `training-data` ships is current | `ai-development/claude-api` was imported 2026-07-12 from `anthropics/skills`; its models table says "cached: 2026-04-15". Upstream `skills/claude-api` is at `main` `33375500` (2026-09-24). The only house edit since import is the description trimmed to 464 chars (`fc94a9a`) | S15 re-vendors it (O5, D11) |
| The engineering-practices review's leftovers | `brainstorming` names `frontend-design` and a "`design` canvas skill", and neither exists; `CONTRIBUTING.md:75` says a skill's name matches its folder, but every skill is plugin-prefixed; four audit files copy one contract | S1 |
| README, catalog and CLAUDE.md match what landed, and the check can be rerun | Updated for the removed skills; no repeatable check beyond `tools/token-audit.py` | G1 reconciles the docs; §7 is the rerunnable check |

## 2. Scope

**In scope:** everything a published plugin ships (`.claude-plugin/marketplace.json`), plus the
authoring templates.

| Folder(s) | Task |
|---|---|
| `engineering-practices/`, `.skill-template/`, `.agent-template/`, `CONTRIBUTING.md` | S1 |
| `backend/_shared/`: planning lane (`agents/solution-planner.md`, `commands/`, `solution-blueprint`, `data-model-plan`, `experience-plan`, `api-surface-plan`, `integration-plan`, `epic-map`, `delivery-plan`, `session-budget`) | S2 |
| `backend/_shared/`: the rest (`agents/be-documenter.md`, `agents/be-feature-documenter.md`, `pattern-guide`, `code-review`, `codebase-survey`, `feature-trace`, `business-documentation`), and `backend/dotnet/` | S3 |
| `backend/java/`, `backend/node/`, `backend/python/` | S4 |
| `qa/dotnet/`: the API, BDD and LLM lanes | S5 |
| `qa/dotnet/`: the UI, mobile and performance lanes, and `qa/dotnet/commands/` | S6 |
| `qa/java/`: the API, BDD and LLM lanes | S7 |
| `qa/java/`: the UI, mobile and performance lanes, and `qa/java/commands/` | S8 |
| `qa/typescript/`: the API, BDD and LLM lanes | S9 |
| `qa/typescript/`: the UI, mobile and performance lanes, and `qa/typescript/commands/` | S10 |
| `qa/_shared/`, `qa/manual/` | S11 |
| `qa/cicd/`, `qa/reporting/` | S12 |
| `frontend/blazor/`, `frontend/react/` (not `vendor/`), `auth/_shared/`, `auth/auth0-blazor/`, `auth/auth0-react/` | S13 |
| `design/` (not `ui-ux-pro-max/data/` or `ui-ux-pro-max/scripts/`), `observability/` | S14 |
| `data/`, `training-data/` | S15 |
| `business-analysis/`, `tooling/` | S16 |
| `devops/` | S17 |
| `security/` | S18 |
| Repo root, `docs/`, `tools/`, `meta/PLAN.md`, README, `docs/skills-catalog.md`, CLAUDE.md | G1 |

**A lane** in the qa stacks is an agent plus every skill under `qa/<stack>/skills/` that its
skill-loading list names. A skill two lanes load belongs to the API/BDD/LLM task.

**Out of scope (D5):** `design/ui-ux-pro-max/data/` and `scripts/` (vendored corpus, the design source
of truth), `frontend/react/vendor/` (vendored seeds), `ai-development/` (vendored; `training-data`
ships its `claude-api` copy, which S15 replaces wholesale from upstream and never hand-edits, D11), `extras/` and `meta/` (not
published), and `communication/`, `frontend/react-native/`, `auth/cognito-*/` (under construction,
per CLAUDE.md).

## 3. How a sweep task runs

Every S task runs these steps over each of its folders, in order:

1. **Search.** Run §4's recipes with `DIR` set to the folder. They are searches, not the gate; every
   task runs them. Only G1 runs §7.
2. **Read the agents in full.** Every file under the folder's `agents/` and `commands/`. Flow, exit
   criteria and cross-skill contracts live there, and so do most logical conflicts.
3. **Read the descriptions.** The K7 recipe prints every description with its length.
4. **Read what the hits point at.** Open each file a recipe hit, and read the section around the hit.
   Read a whole SKILL.md only when the fix needs it: a K5 rewrite, or a K4 plan-shape change.
5. **Fix in place.** Apply each check's fix. Keep the file's voice and structure; change the defect,
   not the prose around it. Never edit a vendored tree (D5), and never rename a skill or agent. Where
   a fix needs a decision only the user can make, leave the text, add an `## Open questions` row, and
   list it under "Left for the user".
6. **Clean up** the folder per §5.
7. **Carry families forward.** A finding family that will recur in folders not yet swept (a renamed
   skill cited everywhere, a sentence every agent copies) goes into the prompt blocks below yours as a
   trap (Close-out step 3).
8. **Record** the `As built` note, classed the way every audit write-up in this library is:

```markdown
- **As built (YYYY-MM-DD):** <folders>. Gate line added to <n> agents.
  Data issues (stale facts — names, versions, paths): <n> fixed — <2–3 examples with file:line>.
  Code issues (prompt defects — dated emphasis, missing Do-NOT clause, default command, over-budget
  description): <n> fixed — <examples>.
  Logical conflicts (two instructions that cannot both hold): <n> fixed — <examples>.
  Cleanup: <moved / deleted, with paths>.
  Left for the user: <items, and why each needs a decision>.
```

## 4. The checks

**Recipes.** Set `DIR` to one folder at a time. `EXCL` keeps the vendored trees out.

```bash
DIR=qa/dotnet
EXCL='/ui-ux-pro-max/(data|scripts)/|/vendor/'
g() { grep -rEn --include='*.md' "$1" "$DIR" | grep -vE "$EXCL"; }

g 'ep-(test-driven-development|worktrees|finish-branch|delegate-to-subagents|requesting-code-review|receiving-code-review|executing-plans)|/dev-build|Task tool|TaskCreate|TaskUpdate|TodoWrite'
g '\bgreen\b'
g 'worktree|[Bb]ranch|reviewer subagent|should I continue'
g '\b([Pp]hases?|[Ss]lices?|[Ss]tages?|[Mm]ilestones?)\b'
g 'Iron Law|Violating the letter|HARD-GATE|REQUIRED SUB-SKILL|Announce at start|[Uu]ltrathink|YOU MUST|CRITICAL:|your human partner|\b(MUST|NEVER|ALWAYS|DO NOT)\b|[0-9]+% vs'
g 'Node (1[0-9]|20)\b|node:(1[0-9]|20)\b|Spring Boot 2|React 1[0-7]\b|Next\.js 1[0-3]\b|Python 3\.(8|9|10|11)\b|Java (8|11|17)\b|net[5-7]\.0'
g 'npm (install|ci|test)|dotnet (restore|test|build)|gradlew (build|test)|pip install|poetry install'
find "$DIR" \( -iname '*plan*.md' -o -iname '*progress*.md' -o -iname '*handoff*.md' -o -iname '*resume*.md' -o -iname '*moved*.md' \) -not -name SKILL.md
git ls-files "$DIR" | grep -E '(^|/)(\.next|node_modules|dist)/|\.DS_Store$'
```

The line order matches the checks: K1 removed names, K2, K3, K4, K5, K6, K8, K9 files, K9 tracked
junk.

**K1 name resolver.** Prints every backticked name in `DIR` that no skill, agent, command or folder
defines:

```bash
python3 - "$DIR" <<'EOF'
import os, re, sys
defined = set()
for r, ds, fs in os.walk('.'):
    if '/.git' in r:
        continue
    defined.update(ds)
    for f in fs:
        if not f.endswith('.md'):
            continue
        p = os.path.join(r, f)
        if '/commands/' in p:
            defined.add(f[:-3])
        if f == 'SKILL.md' or '/agents/' in p:
            m = re.search(r'^name:\s*(\S+)', open(p, errors='ignore').read(), re.M)
            if m:
                defined.add(m.group(1))
tok = re.compile(r'`((?:ep|qa|be|fe|design|data|ba|tool|devops|secgov|observability|auth|td|dev)-[a-z0-9-]+)`')
for r, _, fs in os.walk(sys.argv[1]):
    for f in fs:
        p = os.path.join(r, f)
        if f.endswith('.md') and not re.search(r'/ui-ux-pro-max/(data|scripts)/|/vendor/', p):
            for i, line in enumerate(open(p, errors='ignore'), 1):
                for m in tok.finditer(line):
                    if m.group(1) not in defined:
                        print(f"{p}:{i}: {m.group(1)}")
EOF
```

**K7 description report.** Prints each description's length against its budget, and whether it has
a Do-NOT clause. A folded YAML description (`description: >`) prints as `>`; measure those by hand.

```bash
python3 - "$DIR" <<'EOF'
import os, re, sys
for r, _, fs in os.walk(sys.argv[1]):
    for f in fs:
        p = os.path.join(r, f)
        agent = '/agents/' in p and f.endswith('.md')
        if (f == 'SKILL.md' or agent) and not re.search(r'/ui-ux-pro-max/(data|scripts)/|/vendor/', p):
            m = re.search(r'^description:\s*(.*)$', open(p, errors='ignore').read(), re.M)
            if not m:
                print(f"{p}: no description")
                continue
            s = m.group(1).strip().strip('"')
            limit = 650 if agent else 500
            flags = [] if len(s) <= limit else ['over-budget']
            if not re.search(r'Do NOT|Not for|not for', s):
                flags.append('no Do-NOT')
            print(f"{len(s):4}/{limit} {p} {' '.join(flags)}")
EOF
```

### K1 — Every cited name resolves

- **Find:** the first recipe line (removed names) and the K1 resolver.
- **Fix:** point the reference at the real frontmatter `name:`, agent name, command or folder. If the
  thing it names is gone, delete the clause.
- **Keep:** HTML attributes (`data-testid`, `data-theme`, …) and references to a skill folder that
  exists. Known today: §6.1.

### K2 — Agents defer to the task's Gate line

- **Find:** the `green` recipe over `agents/`. Also, every in-scope agent lacks the line today.
- **Fix:** add this line, exactly, to the agent's operating rules (the list that holds its
  commit/async/injection rules). An agent with no such list gets it directly under its Steps table.

```markdown
- **Inside a plan task, the prompt block's `Gate:` line decides what you run.** A `Gate: none` task writes its code and tests and runs no build, test suite, lint or typecheck, whatever an exit criterion below says; only the task that carries the plan's gate runs them.
```

- A skill that tells the session to run checks before claiming it is done (`ep-verify-before-done`)
  gets the same exception in one sentence. A `Gate: none` task reports "written, not run", never
  "passing".
- **Keep:** the exit criteria themselves. They still bind an agent run outside a plan.

### K3 — Workspace and flow match Plan Queue

- **Find:** the branch/worktree recipe.
- **Fix:** any sentence that tells the session to create a branch or worktree, dispatch reviewer
  subagents, run a checkpoint-and-continue loop, or ask "should I continue" is replaced by "Work in
  the checkout you are given — never create a branch or worktree." Plans run through Plan Queue, one
  prompt block per session, each plan in its own worktree.
- **Keep:** domain uses of "branch": a git-branching strategy in a devops skill, CI branch filters,
  branch coverage.

### K4 — Plan vocabulary and plan shape

- **Find:** the phase/slice/stage/milestone recipe.
- **Fix:** where the word names a unit of planned work, it becomes a task, and ids are kept. Examples:
  a plan's "phase 2", a build cut into "slices", a rollout's "milestones". A skill or agent that
  writes a plan emits `engineering-practices/writing-plans/references/plan-format.md`'s shape,
  including `## Close-out — every task` (§7 there).
- **Keep (D8):** CI/CD pipeline stages, expand/contract migration phases, kill-chain phases,
  Redux/state slices, test lifecycle phases, "vertical slice" as an architecture term, and rule text
  that forbids phases.

### K5 — Rule plus reason, no dated emphasis

- **Find:** the emphasis recipe.
- **Fix:** state the rule once, with its reason, in plain sentences. Delete rationalization and
  red-flag tables, "Iron Law" banners, threat words ("lying", "dishonesty"), "Announce at start"
  lines, persona text from upstream authors, unsourced statistics, and `ultrathink`.
- **Keep:** genuine hard safety rules stay bold, stated once, with their reason. Examples: confirmation
  before applying IaC to a live environment, authorization before offensive testing, no secrets in
  code. One bold "never" with a reason is fine; a wall of them is the finding. A design fact the
  vendored corpus settles is not reworded (CLAUDE.md: the corpus wins).

### K6 — Versions follow CLAUDE.md

- **Find:** the version recipe.
- **Fix:** examples and defaults move to the primary version CLAUDE.md names: Node 24, Spring Boot 3.x
  on Java 21, React 19 / Next.js 15, Python 3.13, .NET 10. A CI matrix may keep the supported
  down-level versions (Node 22, .NET 8/9, React 18, Next.js 14).
- **Keep:** migration skills and version-detection lanes that name an old version as the thing being
  migrated from or detected. Where that version is EOL (Node 20), they flag it rather than recommend
  it.

### K7 — Descriptions and packaging

- **Find:** the K7 report, and the folder's entries in `.claude-plugin/marketplace.json`.
- **Fix:** every description does four things:
  1. Opens with the trigger ("Use when…").
  2. Names trigger phrases.
  3. Carries a Do-NOT clause that points at the sibling owning the excluded case.
  4. Fits the budget: ≤ 500 chars for a skill, ≤ 650 for an agent (`tools/token-audit.py`'s limits).
     Trim restated detail, never the Do-NOT clause.
- Every published path exists. A SKILL.md in a published folder that no plugin lists is either listed
  or named in the As built note as deliberately unpublished.
- **Keep:** skill and agent names; renaming breaks installs.

### K8 — The project's own commands

- **Find:** the command recipe. It concerns instructions only.
- **Fix:** an instruction that tells the session what to run names "the project's own install/test
  command, read from the repo" (`package.json` scripts and `packageManager`, the `.sln`, the Gradle
  wrapper), not a default.
- **Keep:** code samples and CI YAML examples. They illustrate a stack.

### K9 — Cleanup

Covered in §5.

## 5. Cleanup rules

| What | Rule |
|---|---|
| A plan whose work landed | `git mv` into `docs/plans/implemented/`, same filename, unedited (D7). Three legacy files share the name `PLAN.md` (`backend/`, `frontend/`, `meta/`); those move as `<folder>-PLAN.md` (`backend-PLAN.md`) so they cannot collide |
| A plan still in progress, or proposed with nothing built | `git mv` into `docs/plans/` if it lives elsewhere, same filename, content untouched |
| A progress, handoff or resume file | If its parent plan is still live, fold any fact the parent lacks into the parent's status line. Then `git rm` it |
| A "moved" stub | Keep it if it documents a contract another repo depends on; otherwise `git rm` |
| Tracked build output, `.DS_Store`, editor or personal files | `git rm` (`--cached` for personal files), and add a `.gitignore` line where the pattern can recur |
| An audit under `docs/audits/` | Keep. Audits are round records |
| A research note under `docs/research/` | Keep it if anything cites it; otherwise list it under "Left for the user" |
| A duplicate template | Keep the one `CONTRIBUTING.md` names; `git rm` the other if nothing references it |

**Deciding "landed":** the plan's own status line says complete or implemented, and a spot check of 2–3
deliverables it names finds them in the repo. Anything else is live.

**Inventory**, with the task that owns each file:

| File | What it is today | Task |
|---|---|---|
| `AGENT-ORIENTATION-CACHE-PLAN.md` | Status: complete 2026-08-01 | G1 |
| `CONFORMANCE-AUDIT-PLAN.md` | Status: in progress (engine, be-dotnet, qa-dotnet built) | G1 |
| `MODEL-PORTABILITY-PLAN.md` | Status: proposed, nothing built | G1 |
| `SECURITY-EXPANSION-PLAN.md` | Status: complete 2026-08-20 | S18 |
| `TOKEN-OPTIMIZATION-PLAN.md` | No status line; its 160 size violations remain | G1 |
| `backend/UNIT-TESTING-PLAN.md` | Status: complete 2026-08-09 | S3 |
| `backend/DOCUMENTER-PLAN.md` | Status: complete 2026-08-02 | S3 |
| `backend/PLAN.md` | Backend audit findings and remediation, 2026-07-26; no status line | S3 |
| `backend/PLANNER-PLAN.md` | Status: complete 2026-08-02 | S2 |
| `frontend/PLAN.md` | Frontend audit and plan, 2026-07-12; "Phase 7 complete for React", cross-stack port remaining | S13 |
| `frontend/react-native/{PLAN,HANDOFF}.md` | Under construction (D5) | leave |
| `meta/PLAN.md` | `meta/` remediation plan; `meta/` is out of scope | G1 |
| `docs/plans/STAGE3-PROGRESS.md` | Build log for SECURITY-EXPANSION Stage 3, marked "not committed" | S18 |
| `docs/plans/design-ux-improvements.md` | Status: T1–T8 executed 2026-08-27 | S14 |
| `docs/plans/fine-tuning-house-models.md` | Research note, nothing built | S15 |
| `docs/plans/planning-lane-rebuild.md` | Status: implemented 2026-08-30 | S2 |
| `docs/plans/token-optimization-progress.md` | Tracker for `TOKEN-OPTIMIZATION-PLAN.md` | G1 |
| `docs/research/ui-ux-practice-2026.md` | Research note | S14 |
| `docs/audits/001-fe-error-resilience-research.md`, `002-security-domain-audit.md` | Audit records | keep |
| `tools/mission-control/.next/server/app/*` (6 files) | Tracked build output of an app that moved to its own repo | G1 |
| `tools/MISSION-CONTROL-MOVED.md` | Documents the catalog contract Mission Control reads from this repo | G1 (keep) |
| `.claude/settings.local.json` | Tracked personal settings | G1 |
| `.agent-template/AGENT.md` | A second agent template beside `.skill-template/agent.md` | S1 |

## 6. Known findings today, by owning task

Measured 2026-09-26 with §4's resolver and `python3 tools/token-audit.py`. A task still runs its
recipes, because these lists are where it starts, not everything it will find.

### 6.1 Unresolved names

| Name | Where | Task |
|---|---|---|
| `qa-dotnet` | `engineering-practices/standards-audit-engine/SKILL.md` (a plugin, cited as a name) | S1 |
| `qa-java-standards-audit` | `backend/java/skills/unit-testing/SKILL.md` | S4 |
| `qa-test-quality-check-typescript` | `backend/node/skills/unit-testing/SKILL.md` ×2 | S4 |
| `qa-api-client-writer` | `qa/dotnet/skills/api-models/SKILL.md` | S5 |
| `qa-db-testing-dotnet` | `qa/dotnet/skills/failure-injection-testing/SKILL.md` ×2 | S5 |
| `qa-ci-pipelines`, `qa-performance-nbomber` | `qa/dotnet/skills/production-uptime-checks/SKILL.md` | S6 |
| `qa-api-client-writer` | `qa/java/skills/api-models/SKILL.md` | S7 |
| `qa-db-testing-java` | `qa/java/skills/failure-injection-testing/SKILL.md` ×2 | S7 |
| `qa-ci-pipelines`, `qa-performance-k6` ×4, `qa-performance-gatling` ×2 | `qa/java/skills/production-uptime-checks/SKILL.md` | S8 |
| `qa-db-testing-typescript` | `qa/typescript/skills/failure-injection-testing/SKILL.md` ×2 | S9 |
| `qa-ci-pipelines`, `qa-performance-k6` ×2 | `qa/typescript/skills/production-uptime-checks/SKILL.md` | S10 |
| `qa-ci-pipelines` | `qa/reporting/{dotnet,java,typescript}/skills/flaky-test-quarantine/` (5 hits) | S12 |
| `qa-test-quality-check-typescript` | `frontend/react/skills/component-testing/SKILL.md` | S13 |
| `design-audit` | `design/agents/design-auditor.md` | S14 |
| `data-modeling` ×2 | `data/agents/data-architect.md` (may be a concept, not a name: judge) | S15 |
| `devops-conformance` | `devops/agents/devops-auditor.md` | S17 |
| `qa-security-testing-permission-testing` | `devops/k8s-security/SKILL.md` | S17 |

Legacy plan files also cite dead names (`be-planner` ×9, `ep-test-driven-development` ×5, `be-node-auth0`, …). They are never edited: §5 moves every one of them out of the scanned folders, which clears those hits. `data-density` in `design/ui-ux-pro-max/references/quick-reference.md` reads as an HTML data attribute (S14 decides; G1 adds it to `ALLOW` if so).

Deliberate examples, not defects: the 18 broken links in the three
`qa/*/skills/mobile-app-crawler/assets/screen-map-template.md`,
`business-analysis/skills/ba-project-memory/SKILL.md` and
`backend/_shared/business-documentation/SKILL.md`.

### 6.2 Description budget violations

| Task | Skills over 500 chars | Agents over 650 chars |
|---|---|---|
| S1 | `brainstorming` 609, `writing-plans` 562 | — |
| S2 | `delivery-plan` 665, `experience-plan` 653, `session-budget` 578 | `solution-planner` 795 |
| S3 | `business-documentation` 709 | `be-feature-documenter` 843, `be-documenter` 735 |
| S4 | `backend/python/skills/`: `sandboxed-worker` 705, `unit-testing` 684, `media-processing` 637, `code-review` 586, `pattern-writer` 572, `pattern-guide` 530 | `be-python` 810 |
| S11 | `qa/_shared/security-testing/`: `mobile-runtime-testing` 881, `mobile-app-scan` 803 | `qa-test-case-designer` 675 |
| S13 | `frontend/react/skills/data-grid` 688 | `fe-react` 663 |
| S14 | `design/`: `ux-patterns` 824, `ui-ux-pro-max` 767 (house-written, not vendored), `visual-identity` 756, `ai-experience` 673, `motion` 667, `ux-review` 657, `landing-patterns` 643, `accessible-by-design` 624, `ethical-patterns` 594 | `design-auditor` 875 |
| S16 | `business-analysis/skills/ba-epic-writer` 515; `tooling/`: `capability-contract` 610, `mcp-builder` 572, `cli-builder` 509 | `requirements-author` 657, `tooling-engineer` 693 |
| S18 | `security/`: `detection-validation` 778, `atomic-simulation` 749, `detection-engineering` 711, `secrets-hardening` 678, `compliance-evidence-mapping` 664, `security-hardening` 654 | `security-architect` 947, `purple-team-engineer` 909 |

### 6.3 Stale versions

| Task | Hits |
|---|---|
| S2/S3 | `backend/_shared`: `Node 20` ×1 |
| S4 | `backend/java`: `Spring Boot 2` ×7, `Java 17` ×3 (5 files); `backend/node`: `Node 20` ×6 (5 files) |
| S5/S6 | `qa/dotnet`: `Node 20` ×8 (7 files) |
| S7/S8 | `qa/java`: `Node 20` ×6 (6 files) |
| S9/S10 | `qa/typescript`: `Node 20` ×86 (44 files), much of it "TypeScript/Node 20" in agent descriptions and titles |
| S11 | `qa/_shared`: `node:20` ×1, `Python 3.10` ×1 |
| S12 | `qa/cicd`: `Node 20` ×2, `node:20` ×4; `qa/reporting`: `Node 20` ×3, `node:20` ×2 |
| S13 | `frontend/react`: `Node 18` ×2, `Node 20` ×2, `React 17` ×1 (check for a migration context) |
| S14 | `observability`: `Node 20` ×4 (3 files) |
| S17 | `devops`: `Node 20` ×8, `Python 3.10` ×1 |

## 7. The gate (G1 only)

Run in this order from the repo root, and fix what fails. A failure may belong to any task above G1.

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` must exit 0.
2. The library check below must print `OK` and exit 0.
3. `python3 tools/token-audit.py`: nothing may be listed under either description heading, and the
   body and file violation counts together must be ≤ 160. The script exits non-zero while any size
   violation remains; that is expected (D6), so read the counts, not the exit code.

An entry added to `ALLOW` or `LINK_EXAMPLES` is justified in G1's `As built` note. These three steps
are also how to re-check the library later.

```python
import json, os, re, sys

SCOPE = ("qa frontend/blazor frontend/react design backend observability data devops security "
         "business-analysis training-data tooling engineering-practices auth/_shared "
         "auth/auth0-blazor auth/auth0-react .skill-template").split()
EXCL = re.compile(r'/ui-ux-pro-max/(data|scripts)/|/vendor/')
ALLOW = {"data-testid", "data-test", "data-theme", "data-table", "data-bs-target", "data-enhance",
         "data-provider-thread-count", "data-access"}
LINK_EXAMPLES = re.compile(r'screen-map-template\.md$|ba-project-memory/SKILL\.md$|business-documentation/SKILL\.md$')
GATE_LINE = "prompt block's `Gate:` line"
CHECKS = {
    "removed name": r"ep-(test-driven-development|worktrees|finish-branch|delegate-to-subagents|requesting-code-review|receiving-code-review|executing-plans)|/dev-build|Task tool|TaskCreate|TaskUpdate|TodoWrite",
    "dated emphasis": r"Iron Law|Violating the letter|HARD-GATE|REQUIRED SUB-SKILL|Announce at start|[Uu]ltrathink|YOU MUST|your human partner",
    "branch/worktree": r"git worktree add|git checkout -b|EnterWorktree|[Ww]ork on a branch",
}

fail = []
market = json.load(open(".claude-plugin/marketplace.json"))
for plugin in market["plugins"]:
    for kind in ("skills", "commands", "agents"):
        for path in plugin.get(kind, []):
            if not os.path.exists(path):
                fail.append(f"marketplace {plugin['name']}: missing {path}")

defined = set()
for root, dirs, files in os.walk("."):
    if "/.git" in root:
        continue
    defined.update(dirs)
    for f in files:
        if not f.endswith(".md"):
            continue
        path = os.path.join(root, f)
        if "/commands/" in path:
            defined.add(f[:-3])
        if f == "SKILL.md" or "/agents/" in path:
            m = re.search(r"^name:\s*(\S+)", open(path, errors="ignore").read(), re.M)
            if m:
                defined.add(m.group(1))

name_token = re.compile(r"`((?:ep|qa|be|fe|design|data|ba|tool|devops|secgov|observability|auth|td|dev)-[a-z0-9-]+)`")
md_link = re.compile(r"\]\((?!https?:|mailto:|#)([^)\s]+?\.md)(?:#[^)]*)?\)")
for top in SCOPE:
    for root, _, files in os.walk(top):
        for f in files:
            path = os.path.join(root, f)
            if not f.endswith(".md") or EXCL.search(path):
                continue
            text = open(path, errors="ignore").read()
            for label, pattern in CHECKS.items():
                for m in re.finditer(pattern, text):
                    fail.append(f"{label}: {path}: {m.group(0)}")
            for m in name_token.finditer(text):
                if m.group(1) not in defined and m.group(1) not in ALLOW:
                    fail.append(f"unresolved name: {path}: {m.group(1)}")
            for m in md_link.finditer(text):
                target = os.path.normpath(os.path.join(root, m.group(1)))
                if not os.path.exists(target) and not LINK_EXAMPLES.search(path):
                    fail.append(f"broken link: {path}: {m.group(1)}")
            if "/agents/" in path and GATE_LINE not in text:
                fail.append(f"agent without the Gate line: {path}")

print("\n".join(fail) or "OK")
sys.exit(1 if fail else 0)
```

Save it outside the repo as `"${TMPDIR:-/tmp}/library-check.py"` and run it from the repo root.

## Decisions

**D1 — Every task runs as `general-purpose`.** No agent in this library owns maintaining the library.
A domain agent (`be-dotnet`, `qa-api-java`, …) builds target projects: it would load that stack's
skill protocol and write an orientation cache into this repo. **Cost:** no skill-loading protocol, so
every prompt block names its full reading list, and the checklist lives in this plan (§3–§5).

**D2 — One stack (`docs`) for every task. Tasks are cut by folder along seams inside that stack and
merged toward ~130k.** **Cost:** 19 sessions. The qa stacks split into two lanes each because one
stack's agents plus its hits exceed a session.

**D3 — Sweeps fix, they do not report.** The record is the task's classed `As built` note plus git; no
`docs/audits/` round is written. **Cost:** no round-over-round audit trail. A formal audit later is a
`code-auditor` engagement.

**D4 — The Gate line is one fixed sentence in every in-scope agent and the agent template. The exit
criteria stay.** **Cost:** one line in each of 54 agents (agent bodies, not the always-on
descriptions). It is the smallest change that makes an agent safe inside a `Gate: none` task and
unchanged outside one.

**D5 — Vendored, unpublished and under-construction trees are excluded** (list in §2). **Cost:** stale
content there stays. The one exception is the `ai-development/claude-api` copy that `training-data`
ships, which S15 refreshes (D11).

| Option | Verdict | Why |
|---|---|---|
| Sweep vendored trees too | Rejected | Edits fork them from upstream; the design corpus is the declared source of truth |
| Exclude them | Chosen | Only the house-written parts reach the prompt surface we own |

**D6 — Description budgets are fixed here; body and file size violations are not.** The 45
description violations are cheap to fix and cost tokens in every session. The 160 body/file
violations mean relocating content to `references/`, which is `TOKEN-OPTIMIZATION-PLAN.md`'s work. That plan
stays live and gets its own numbered plan after this one (O7). **Cost:** `tools/token-audit.py` still exits non-zero after G1.

**D7 — Legacy plans are filed by rule (§5), keep their unnumbered filenames, and are not converted to
the plan format.** Renaming would break every commit message and doc that cites them by name. The one exception is the three files called `PLAN.md`, which gain their folder as a prefix because they would otherwise collide.
`NNN`'s high-water mark counts numbered files only, so this plan is `001`. **Cost:** `docs/plans/`
holds legacy-shaped live plans until each one gets a new plan (O6, O7).

**D8 — Domain uses of phase, stage, slice and milestone stay.** K4 renames only units of planned work.
**Cost:** judgment per hit; the recipe over-reports.

**D9 — §4's recipes are searches every task runs; §7 and `tools/token-audit.py` are the gate, and only
G1 runs them.** **Cost:** no S task can prove its own folder passes. G1 fixes whatever the gate finds,
whichever task caused it.

**D10 — The audit contract copied across `code-auditor`, `spec-vs-code-audit`, `feature-audit` and
`standards-audit-engine` is flagged, not consolidated.** The four copies agree today; merging them is
a refactor with no failing behaviour behind it. **Cost:** they can drift, and a later edit must touch
all four.

**D11 — The shipped `claude-api` copy is replaced wholesale from `anthropics/skills`, then its
description is trimmed back under 500 chars.** Upstream owns every file in it; the description is the
one house fork, because `training-data` pays for it in every session and `tools/token-audit.py`
budgets it. **Cost:** upstream's changes land reviewed only by `git diff --stat` and a skim of
`SKILL.md`, and the description fork has to be re-applied at every refresh.

**D12 (2026-09-26, S1) — Plugin names are written unbackticked; the naming rule is a domain prefix,
not the plugin name.** The plan said "the `qa-dotnet` plugin", but the K1 resolver flags any backticked
`qa-…` token that no skill, agent, command or folder defines, so a backticked plugin name fails §7 as
an unresolved name. S1 wrote "the qa-dotnet plugin" in plain text. Likewise the plan called the naming
rule "plugin prefix plus folder"; the sampled names show a domain prefix (`qa-api-project-setup-dotnet`
lives in the qa-dotnet plugin with the stack as a suffix), and `CONTRIBUTING.md` states that. **Cost:**
plugin names lose code formatting wherever they appear; later tasks must do the same or add the name to
`ALLOW`.

**D13 (2026-09-26, S4) — Old-version lines that only detect or flag stay.** Task S4 read "`Node 20`
×6 → Node 24" and "keep Spring Boot 2 / Java 17 only where they are the migration source". Every hit
was a detection, fallback or EOL-flag line instead ("Node 20 is EOL — flag it", "never use a Java-21
construct on a Java 17 / Spring Boot 2.x project"), which K6's keep clause and the CLAUDE.md version
policy protect. S4 kept all 16 and added the missing EOL flag for Spring Boot 2.x. **Cost:** §7 does
not check versions, so these hits stay in the K6 recipe's output for later readers to re-judge.

**D14 (2026-09-26, S6) — A stale path is fixed wherever it sits in the folder, even in the other
lane's files.** §2 gives S5 the API/BDD/LLM skills, but six stale paths S5's family list did not name
(`performance/nbomber`, `qa/_shared/api-contract-testing`, a missing TypeScript sibling) sat in S5-owned
`qa-api-dotnet.md`, `api-contract-testing`, `failure-injection-testing`, `api-test-author/writer`,
`test-quality-check` and `standards-audit/references/conformance-checklist.md`. S6 fixed them rather
than leave qa/dotnet half-swept. **Cost:** S6's diff touches S5's files; the qa stack pairs (S7/S8,
S9/S10) may do the same, and the As built note names each such file.

**D15 (2026-09-26, S7) — An LLM agent hands a real regression to `qa-test-case-designer`; it does not
load `qa/manual/bug-report-writer`.** `qa-llm-java` forbids `qa/manual/` in its loading protocol and
its own operating rule hands product defects to `qa-test-case-designer`, yet Mode A said "write it up
via `qa/manual/bug-report-writer`". S6 settled the same clash in `qa-performance-dotnet` the other way,
by stating the load as an exception. For the LLM agents the hand-off wins, because the agent's own
operating rule already says so and the other lane agents (`qa-api-*`, `qa-bdd-*`) do the same. S7 also
applied it to `qa-llm-dotnet.md:88`, outside its folder, since S5 had left that copy in place.
**Cost:** two readings coexist: performance agents keep the stated exception (S6, carried into S8/S10),
while LLM agents hand off. `qa-llm-dotnet` is edited by a task that does not own qa/dotnet.

**D16 (2026-09-26, S12) — A gating test step never carries `continue-on-error`; the quarantine lane is
the one stated exception.** `qa-ci-conventions-shared` forbids `continue-on-error` / `allow_failure` on a
test step and says a reference that disagrees is wrong, yet the three `test-reports` skills taught
`continue-on-error: true`, `continueOnError: true` and `|| true` on the test step as the *right* way to
keep publishing, and the three `flaky-test-quarantine` skills wire their non-gating quarantine lane with
`continue-on-error`. Reading one: the conventions win everywhere, so the quarantine lane must find
another mechanism. Reading two (chosen): the conventions win for gating steps — `test-reports` now lets
the test step fail and runs upload/publish with `if: always()` / `condition: succeededOrFailed()` /
`when: always` — and `ci-conventions` names the quarantine lane as the one non-gating exception, because
that lane exists to run and report tests that must not block. **Cost:** the no-green-washing rule now has
an exception a reader must keep narrow; a second "non-gating" lane would need its own justification.

## Answered questions (2026-09-26)

**O1 — How are plans run: through Plan Queue only, one prompt block per session, each plan in its own
worktree.** The inline executor, subagent dispatch, reviewer skills, TDD and the branch skills are
removed (`0eecfce`, `817f7df`).

**O2 — Do agents create branches or worktrees: no.** "Work in the checkout you are given — never create
a branch or worktree."

**O3 — Is the orientation cache gitignored: no.** It stays tracked (`91fc23a` reverted `1f9f190`). No
task touches `docs/agent-context/`.

**O4 — Does each folder task also clean up its old plans and docs: yes.** Per §5; G1 takes the root.

**O5 — The vendored `claude-api` copy: re-vendor it.** S15 refreshes it from `anthropics/skills` (D11).

**O6 — The unbuilt proposals: keep both live.** `MODEL-PORTABILITY-PLAN.md` moves to `docs/plans/`;
`docs/plans/fine-tuning-house-models.md` stays.

**O7 — Next plans: conformance audits and size optimization.** `CONFORMANCE-AUDIT-PLAN.md`'s remaining
stacks and `TOKEN-OPTIMIZATION-PLAN.md`'s 160 size violations each get their own numbered plan after
this one lands. G1 leaves both live in `docs/plans/` and names them as next in the final `Status:`.

**O8 — The unpublished trees: keep them all.** `extras/`, `meta/` and `ai-development/mcp-builder`
stay; D5 still keeps them out of this sweep.

## Open questions

The five raised while writing this plan were answered on 2026-09-26 (O5–O8).

| # | Question | Raised by | Why it needs you |
|---|---|---|---|
| O9 | Should a fallback locator in a generated page object keep its `// TODO: missing data-testid` marker? | S8 (2026-09-26) | CLAUDE.md's Comments rule forbids a `TODO` left behind, and every qa UI agent says "Emit no comments", yet `page-objects-from-url` in all three stacks (and `qa-ui-{dotnet,java,typescript}.md` Live-page step 3) makes the marker "the contract that it gets upgraded". CLAUDE.md lets a skill win for its domain, so both readings hold today. Dropping the marker leaves `missing-testids.md` as the only handshake; keeping it means stating the exception in CLAUDE.md. The text is unchanged until you decide. |

## 8. Tasks

**Because the plan gates once, the tree is not guaranteed green at every task boundary.** Nothing S1–S18
changes is checked until G1 runs §7, so the plan cannot be stopped halfway and trusted. That is the
price of one verify-and-fix loop instead of eighteen. There is no user-facing capability here; each S
task stands alone, and the order is chosen, not required.

**Floor used in every budget:** system prompt and tools 12k, CLAUDE.md files 12k (project 8k, global
4k), no agent definition (D1). That makes 24k.

### S1 — engineering-practices, the templates and CONTRIBUTING

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering-practices/`, `.skill-template/`, `.agent-template/` and `CONTRIBUTING.md`
pass K1–K9: `code-auditor` and the agent template carry the Gate line, `brainstorming`,
`systematic-debugging` and `verify-before-done` state their rules without dated emphasis, and no name
in them is dangling.
**Depends on:** —
**Budget:** ~110k — floor 24k, plan §2–§6 and this block 9k, recipe output 6k, the three ep skills
rewritten in full 7k, `code-auditor` and audit skills around hits 10k, templates and CONTRIBUTING 7k,
~12 files modified 18k, commit read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script; the
repo has no build or suite.

- K1–K8 over `engineering-practices/` per §3. Known today: `brainstorming` names `frontend-design` and
  a "`design` canvas skill" (neither exists: remove them, keep the `Artifact` route);
  `standards-audit-engine` cites the plugin `qa-dotnet` as a name (say "the `qa-dotnet` plugin");
  `agent-orientation-cache`'s `mobile-app-crawler` resolves to the `qa/<stack>/skills/mobile-app-crawler`
  folders, so it stays.
- K2: the Gate line in `agents/code-auditor.md` and `.skill-template/agent.md`; `verify-before-done`
  gets the one-sentence `Gate: none` exception.
- K5: `systematic-debugging` (Iron Law, rationalization and red-flag tables, "95% vs 40%", "Real-World
  Impact", `Ultrathink`); `verify-before-done` ("dishonesty", "lying", Iron Law, rationalization table);
  `brainstorming` (`HARD-GATE`, the "too simple" anti-pattern section, announce line);
  `writing-plans`' announce line; `standards-audit-engine`'s "Half of all false findings" statistic.
- K7: `brainstorming` 609 → ≤ 500, `writing-plans` 562 → ≤ 500.
- `CONTRIBUTING.md:75`: replace "match the folder name" with the real rule, the plugin prefix plus the
  folder (`ep-brainstorming`, `be-shared-delivery-plan`, …). Derive the exact pattern from six existing
  skills before writing it.
- D10: flag the copied audit contract in the As built note; do not merge the files.
- K9: `CONTRIBUTING.md` names `.skill-template/agent.md`. Grep the repo for `.agent-template`; if
  nothing references it, `git rm -r .agent-template`.
- **Not in S1:** other folders' agents (their tasks add the Gate line); README and the catalog (G1).
- **As built (2026-09-26):** `engineering-practices/`, `.skill-template/`, `.agent-template/`, `CONTRIBUTING.md`. Gate line added to 2 agents (`engineering-practices/agents/code-auditor.md` Operating rules, `.skill-template/agent.md` Operating rules; the template's brownfield output contract also gained `Gate: none — written, not run`).
  Data issues: 4 fixed — `brainstorming` no longer names `frontend-design` or the "`design` canvas skill" (Artifact route kept); `standards-audit-engine/SKILL.md:49` names plugins in plain text ("the fe-react, be-dotnet or qa-dotnet plugin") instead of backticked (D12); `CONTRIBUTING.md:75` now states the naming rule derived from ~40 sampled skills (domain prefix + optional stack + folder, e.g. `be-dotnet-pattern-writer`, `qa-api-project-setup-dotnet`, `design-tokens`); `commands/ep-spec-vs-code-audit.md` description no longer ends mid-list.
  Code issues: 12 fixed — `systematic-debugging` (Iron Law, "Violating the letter", red-flag, rationalization and "Signals" sections with `Ultrathink`, "95% vs 40%", "Real-World Impact", "95% of no root cause" folded into rule-plus-reason text); `verify-before-done` (dishonesty/lying, Iron Law, red-flag and rationalization tables, all-caps; the `Gate: none` exception added at `verify-before-done/SKILL.md:14`); `brainstorming` (`HARD-GATE`, the "too simple" section folded into one rule, announce line, "You MUST"/"ONLY"); announce lines removed from `writing-plans`, and — not in the plan's list — from `spec-vs-code-audit` and `feature-audit`, which now say "state the mode in the first line of output"; `standards-audit-engine`'s "Half of all false findings" replaced by its reason; `code-auditor`'s "MANDATORY SECTION" heading suffix dropped; descriptions `brainstorming` 609→470, `writing-plans` 562→475 (K7 report). `writing-plans` body and `plan-format.md` untouched beyond the description and the announce line.
  Logical conflicts: 1 fixed — `CONTRIBUTING.md` said descriptions stay under ~400 chars while `tools/token-audit.py` enforces 500/650; it now states 500/650.
  Cleanup: `git rm -r .agent-template` (only this plan referenced it). No plan/progress files in the S1 folders.
  Flagged (D10): the audit contract (evidence rules, three finding classes, permanent IDs, additive rounds) is copied across `agents/code-auditor.md`, `spec-vs-code-audit`, `feature-audit` and `standards-audit-engine`; the four agree today and were not merged.
  Kept on purpose: `mobile-app-crawler` (resolves to the qa folders); `data-testid` resolver hits (HTML attribute, in `ALLOW`); `root-cause-tracing.md:154`'s single bold "NEVER" with its reason; the template's "Slice scope (extend)" label (brownfield change scope, 7 agents copy it — their tasks judge it under D8); K8 hits are code samples and example cache content.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: nothing.

### S2 — backend/_shared planning lane

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `solution-planner`, `backend/_shared/commands/` and the eight planning-lane skills pass
K1–K9, the plans they produce follow `plan-format.md` including `## Close-out — every task`, and
`docs/plans/planning-lane-rebuild.md` and `backend/PLANNER-PLAN.md` are filed.
**Depends on:** —
**Budget:** ~135k — floor 24k, plan sections 9k, recipe output 6k, `solution-planner` and commands 10k,
`delivery-plan` and `session-budget` read in full 20k, `plan-format.md` 6k, six other planning skills
around hits 12k, descriptions 2k, ~12 files modified 18k, two legacy plan headers 2k, read-back 6k,
churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- Files: `backend/_shared/agents/solution-planner.md`, `backend/_shared/commands/*.md`, and
  `backend/_shared/{solution-blueprint,data-model-plan,experience-plan,api-surface-plan,integration-plan,epic-map,delivery-plan,session-budget}/`.
- K4 plan shape: `delivery-plan` and `session-budget` must produce plans that carry
  `## Close-out — every task` above the prompts and end every prompt block with its close-out line.
  `session-budget`'s "Step 5" duty is that close-out: point at `plan-format.md` §7 instead of
  restating it.
- K2: the Gate line in `solution-planner`.
- K7: `delivery-plan` 665, `experience-plan` 653, `session-budget` 578 → ≤ 500; `solution-planner`
  795 → ≤ 650.
- K9: `docs/plans/planning-lane-rebuild.md` says "implemented 2026-08-30" and `backend/PLANNER-PLAN.md`
  says complete 2026-08-02. Spot-check three deliverables of each; if they hold, `git mv` both into
  `docs/plans/implemented/`.
- **Not in S2:** the documenter and pattern skills in the same folder (S3).
- **As built (2026-09-26):** `backend/_shared/agents/solution-planner.md`, `backend/_shared/commands/`
  (all three read; nothing to fix), and the eight planning-lane skill folders with their `references/`.
  Gate line added to 1 agent (`solution-planner.md` Operating rules, first bullet after "You write
  plans, not code").
  Data issues: 6 fixed — "slice" as a unit of planned work became task/capability at
  `solution-blueprint/SKILL.md:72` and `:212`, `solution-blueprint/references/example-blueprint.md:49`
  and `:126`, `api-surface-plan/SKILL.md:216`; `delivery-plan` Output cited plan format §7 for filing,
  now §8.
  Code issues: 16 fixed — "Announce at start" removed from all 8 skills; `delivery-plan`'s "MUST"
  (Step 3 overlap rule) lower-cased; `solution-planner`'s "— MANDATORY SECTION" heading suffix dropped;
  descriptions `delivery-plan` 665→487, `experience-plan` 653→486, `session-budget` 578→481,
  `solution-planner` 795→619 (K7 report); K3: `solution-planner` Workspace now opens "Work in the
  checkout you are given — never create a branch or worktree.", and `delivery-plan` no longer says a
  plan runs "inline".
  Logical conflicts: 2 fixed — (1) plan-format §6/§7 require `## Close-out — every task` above the
  prompts and a close-out line ending every block, while `delivery-plan`'s template, both golden
  references and `session-budget` Step 4/5 had each block carry its own "Before you stop" list: now
  `delivery-plan` Step 6, template and self-check 12, `example-delivery-plan.md:287` (verbatim §7 copy)
  and its B2 block, `prompts-section-template.md` (template + filled example) and `solution-planner`
  Step 7/8 exit gates and Step 9 item 14 all require the section and the line; (2) `session-budget`
  Step 5 restated the close-out as its own 7-step list — it now points at plan format §7 and keeps only
  what §7 cannot know (which block files the plan, which block writes a `Blocked on` block).
  `solution-planner`'s "two-file closing duty" (a leftover of the removed NEXT-PROMPTS file) now says
  "the same close-out".
  Cleanup: `mkdir -p docs/plans/implemented`; `git mv docs/plans/planning-lane-rebuild.md` and
  `git mv backend/PLANNER-PLAN.md` into it (spot checks: `delivery-plan` "valid serialization" rule =
  its T3; `epic-map` and `session-budget` skills exist; `ba-epic-writer` plain-English §2;
  `validation-catalog.md`, `solution-blueprint`, `data-model-plan` exist per PLANNER-PLAN's shape).
  Nothing else cited either file.
  Kept on purpose: `## For Mission Control` stays after `## Prompts` in `delivery-plan.md` (the MC
  ingestion shape, tools/MISSION-CONTROL-MOVED.md), so the close-out section went between
  `## 6. Decisions` and the prompts — additive, path unchanged; "vertical-slice" (architecture term,
  `solution-planner.md` cache table); rule text forbidding phases/slices; `Node 20` in
  `solution-blueprint` Version policy (flags it as EOL); K8 hits are all example plan content
  (`dotnet build`/`pnpm test` in gate lines); `data-testid` resolver hit. The three commands'
  descriptions have no Do-NOT clause; the K7 report covers skills and agents only, and slash-command
  descriptions are menu text, so they were left.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: nothing.

### S3 — backend/_shared documenter and pattern lane, and backend/dotnet

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `be-documenter`, `be-feature-documenter`, the five remaining `backend/_shared` skills
and all of `backend/dotnet/` pass K1–K9, and `backend/{UNIT-TESTING-PLAN,DOCUMENTER-PLAN,PLAN}.md`
are filed per §5.
**Depends on:** —
**Budget:** ~130k — floor 24k, plan sections 9k, recipe output 6k, the two documenter agents 16k,
`be-dotnet` agent and command 6k, ~9 skills around hits 18k, descriptions 3k, ~14 files modified 21k,
three legacy plans' headers and spot checks 4k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- Files: `backend/_shared/agents/{be-documenter,be-feature-documenter}.md`,
  `backend/_shared/{pattern-guide,code-review,codebase-survey,feature-trace,business-documentation}/`,
  `backend/dotnet/`.
- K2: the Gate line in the three agents. `be-dotnet`'s Step 3 exit criterion ("`dotnet test` green")
  stays.
- K7: `business-documentation` 709 → ≤ 500; `be-feature-documenter` 843 and `be-documenter` 735 →
  ≤ 650.
- `business-documentation`'s link to `areas/identity.md` is a deliberate example; leave it.
- K9: `backend/UNIT-TESTING-PLAN.md` says complete 2026-08-09: confirm the three
  `backend/{dotnet,java,node}/skills/unit-testing/` skills exist, then `git mv` it into
  `docs/plans/implemented/`. `backend/DOCUMENTER-PLAN.md` says complete 2026-08-02: spot-check three
  deliverables, then file it the same way. `backend/PLAN.md` (backend audit, 2026-07-26) has no
  status line: check three of its findings against the skills; if they are fixed it is landed,
  otherwise it moves to `docs/plans/` as live. Either way it moves as `backend-PLAN.md` (§5).
- **Not in S3:** `backend/{java,node,python}` (S4).
- **As built (2026-09-26):** `backend/_shared/agents/{be-documenter,be-feature-documenter}.md`,
  `backend/_shared/{pattern-guide,code-review,codebase-survey,feature-trace,business-documentation}/`,
  `backend/dotnet/` (agent and both commands read in full; the commands needed no change). Gate line
  added to 3 agents, each as the last Operating-rules bullet: `be-documenter.md`,
  `be-feature-documenter.md` and `be-dotnet.md`.
  Data issues: 3 fixed.
  - `be-dotnet.md:23` and `:98` named `_shared/{reference,reviewer}`, which no longer exist. They now
    name `_shared/{pattern-guide,code-review}`, and `:98` lists `be-python` as a sibling.
  - `be-documenter`'s description said ".NET / Java / Node", but the be-python plugin also ships it.
    It now says "… / Python".
  - `be-dotnet.md:84` pointed its closing duty at `be-shared-session-budget` Step 5, which S2 reduced
    to a pointer. It now points at the plan's `## Close-out — every task` section (plan format §7).
  Code issues: 12 fixed.
  - "Announce at start" was removed from `codebase-survey`, `feature-trace` and
    `business-documentation`. In `standards-audit/SKILL.md:12` it became "State the mode … in the
    first line of output".
  - The "— MANDATORY SECTION" heading suffix was dropped from `be-documenter` and `be-dotnet`.
  - Descriptions were trimmed (K7 report): `business-documentation` 709→500, `be-documenter`
    735→622, `be-feature-documenter` 843→641. Every other description in scope already had its
    Do-NOT clause and fit its budget.
  - K3: `be-documenter` Workspace said "committing … on the current branch is fine". It now opens
    "Work in the checkout you are given — never create a branch or worktree." `be-feature-documenter`
    had no workspace rule and gained that line.
  - K2 for skills: one `Gate: none` sentence ("written, not run") each in
    `dotnet/skills/unit-testing` Generation step 6 and `dotnet/skills/pattern-writer` Validation.
  Logical conflicts: 1 fixed. `be-dotnet`'s orientation said "confirm `dotnet build` is green …
  every run", which contradicts a `Gate: none` task. It now reads "every run outside a `Gate: none`
  plan task" (`be-dotnet.md:47`).
  Cleanup (the `docs/plans/implemented/` folder already existed):
  - `git mv backend/UNIT-TESTING-PLAN.md docs/plans/implemented/`: all three
    `backend/{dotnet,java,node}/skills/unit-testing/` exist.
  - `git mv backend/DOCUMENTER-PLAN.md docs/plans/implemented/`. Spot checks: the agent and its
    three skills exist; `feature-trace/references/trace-recipes.md` exists;
    `commands/dev-document-system.md` exists; the business-analysis plugin bundles the agent.
  - `git mv backend/PLAN.md docs/plans/backend-PLAN.md` (**live**). Findings still open:
    - F1: `dotnet/skills/pattern-guide` still has only Strategy, Repository and Mediator cards, plus
      its coverage checklist.
    - F3: `database-code/SKILL.md:79-80` still pairs `[Timestamp]` with `xmin`.
    - F5: `:128` still uses `builder.HasCheckConstraint`.
    - F2 (no `backend/node/skills/auth0`) and F4 (no Version policy in the java auth skills) are also
      open.
  - Nothing outside legacy plans cited the three files. `CONFORMANCE-AUDIT-PLAN.md` cites
    `backend/PLAN.md` as plain text and was left as it is (legacy; noted in G1's prompt).
  Kept on purpose:
  - Every K4 hit is D8 architecture vocabulary ("CRUD slice", "vertical slice", CoR "stage").
  - K8 hits are the .NET CLI inside exit criteria, which the plan keeps, and inside
    code/validation lists.
  - The `data-testid` resolver hit is S2's example plan.
  - `be-dotnet`'s description opens with the role, not "Use when" (S2 did the same for
    `solution-planner`).
  - Recipe fixes F1–F5 in `backend/dotnet/skills/database-code` and `pattern-guide` are outside
    K1–K9. They stay with `backend-PLAN.md`.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: nothing.

### S4 — backend/java, backend/node and backend/python

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `backend/java/`, `backend/node/` and `backend/python/` pass K1–K9: three agents carry
the Gate line, the §6 names and versions for these folders are resolved, and the seven `be-python`
descriptions fit their budgets.
**Depends on:** —
**Budget:** ~145k — floor 24k, plan sections 9k, recipe output 6k, three agents 19k, ~10 skills around
hits 20k, descriptions 6k, ~21 files modified 31k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K1: `qa-java-standards-audit` in `backend/java/skills/unit-testing/SKILL.md` (only `qa-dotnet` has a
  standards audit today: point at the real skill or drop the clause); `qa-test-quality-check-typescript`
  ×2 in `backend/node/skills/unit-testing/SKILL.md` (find the real name under `qa/typescript/skills/`).
- K6: `Spring Boot 2` ×7 and `Java 17` ×3 in five `backend/java` files. Keep them where they are the
  version being migrated from; otherwise move to Spring Boot 3.x on Java 21. `Node 20` ×6 in
  `backend/node` → Node 24.
- K7: `backend/python/skills/`: `sandboxed-worker` 705, `unit-testing` 684, `media-processing` 637,
  `code-review` 586, `pattern-writer` 572, `pattern-guide` 530 → ≤ 500; `be-python` 810 → ≤ 650.
- K2: the Gate line in `be-java`, `be-node` and `be-python`.
- **Not in S4:** `backend/_shared` (S2, S3).
- **As built (2026-09-26):** `backend/java/`, `backend/node/`, `backend/python/` (three agents and
  three commands read in full; the commands needed no change). Gate line added to 3 agents, each as
  the last Operating-rules bullet: `be-java.md:37`, `be-node.md:37`, `be-python.md:40`.
  Data issues: 6 fixed.
  - K1: `qa-java-standards-audit` does not exist (only qa-dotnet has a standards audit), so the
    clause was dropped from `java/skills/unit-testing` (was `:46`).
  - K1: `qa-test-quality-check-typescript` has **no real name** — `qa/typescript/skills/` has no
    mutation-testing skill. `node/skills/unit-testing:43` and `:302` now say no TypeScript peer exists
    yet and cite the real siblings `qa-test-quality-check-java` (PIT) and
    `qa-test-quality-check-dotnet` (Stryker.NET). The stale "tracked in
    `backend/UNIT-TESTING-PLAN.md` §7" pointer went with it (S3 filed that plan). S13's prompt says so.
  - `backend/_shared/{reference,reviewer}` → `{pattern-guide,code-review}` in `be-java.md:21`,
    `:111` and `be-node.md:21`, `:111`; the sibling lines now name `be-python`.
  - The closing duty "per `be-shared-session-budget` Step 5" now points at the plan's
    `## Close-out — every task` section (plan format §7) in all three agents.
  Code issues: 17 fixed.
  - "— MANDATORY SECTION" dropped from the three brownfield headings.
  - K7: `be-python` 810→622; `sandboxed-worker` 705→490, `unit-testing` 684→481, `media-processing`
    637→465, `code-review` 586→475, `pattern-writer` 572→477, `pattern-guide` 530→470. Every other
    description in the three folders already fit its budget and had its Do-NOT clause.
  - K2 for skills: one `Gate: none` sentence ("written, not run") in the `pattern-writer` Validation of
    all three stacks, in the `unit-testing` Verify step of java and node and the `## Gate` list of
    python, and in `python/skills/sandboxed-worker` Validation.
  - K8: `be-node` hardcoded `pnpm` in the orientation pass, Mode A verify and the Step 2/3 exit
    criteria; `node/skills/unit-testing` (`:121`, `:295`) and `node/skills/pattern-writer` Validation
    did too. They now name the project's own scripts, run with its `packageManager`.
  - K6: `be-java.md:17` now flags Spring Boot 2.x as past open-source support (Nov 2023).
  Logical conflicts: 4 fixed. The orientation pass in all three agents said "every run regardless of
  the gate's verdict", which contradicts a `Gate: none` task; it now reads "every run outside a
  `Gate: none` plan task, regardless of the cache gate's verdict". `be-python.md:89` ran the
  `sandboxed-worker` validation list whenever Docker was available; it now excepts `Gate: none` too.
  Cleanup: none — the K9 recipes found no plan, progress or tracked junk file in the three folders,
  and all 18 skills, 3 commands and 3 agents are listed in the marketplace.
  Kept on purpose (D13):
  - `Spring Boot 2` ×7 and `Java 17` ×3 are all version-detection or down-level fallback text
    (`be-java.md:17`, the output contract `:119`/`:132`, and line 12 of `database-code`,
    `code-review`, `pattern-guide`, `pattern-writer`).
  - `Node 20` ×6 are all "Node 20 is EOL — flag it, don't target it" lines.
  - K4 hits are D8 vocabulary ("CRUD slice", "vertical slice", CoR `Stage`, Docker build stage,
    TS stage-3 decorators). K3 hits are code branches; K8's `./gradlew` and `uv run` are the Gradle
    wrapper and the house uv toolchain.
  - The `be-python` hard safety rules (no network, per-job limits, hostile-by-default) stay bold.
  Carried forward: the four recurring agent sentences and the `pnpm` default (K8) are written into
  the S5–S17 prompts as a trap; 28 agents outside backend carry at least one of them.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: nothing.

### S5 — qa/dotnet API, BDD and LLM lanes

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-api-dotnet`, `qa-bdd-dotnet`, `qa-llm-dotnet` and every `qa/dotnet` skill they load
pass K1–K9, and the finding families found here are written into S6–S10 as traps.
**Depends on:** —
**Budget:** ~130k — floor 24k, plan sections 9k, recipe output 6k, three agents 16k, ~10 skills around
hits 20k, descriptions 7k, ~13 files modified 20k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- The lane rule is in §2: the three agents' skill-loading lists decide which skills are yours, and a
  skill both halves load is yours.
- K1: `qa-api-client-writer` in `skills/api-models/SKILL.md`; `qa-db-testing-dotnet` ×2 in
  `skills/failure-injection-testing/SKILL.md`. Find the real frontmatter names under `qa/dotnet/skills/`.
- K2: the Gate line in the three agents; their "green" exit criteria stay.
- K6: `qa/dotnet`'s `Node 20` hits that sit in your skills → Node 24.
- First qa stack task: write the families you found (a renamed skill cited in all stacks, a phrase
  every qa agent copies) into the traps of S6–S10, per Close-out step 3.
- **Not in S5:** the UI, mobile and performance lanes and `qa/dotnet/commands/` (S6).
- **As built (2026-09-26):** `qa/dotnet/agents/{qa-api-dotnet,qa-bdd-dotnet,qa-llm-dotnet}.md` (read in
  full) and the 26 skill folders their loading lists name: `api-project-setup`, `test-login-tokens`,
  `api-models`, `api-client-writer`, `test-data-builder`, `api-test-author/{writer,playwright,graphql,grpc,review}`,
  `data-driven-testing`, `db-testing/{connection,testcontainers,verification-queries}`, `messaging-testing`,
  `file-storage-testing`, `email-testing`, `realtime-stream-testing`, `api-contract-testing`,
  `failure-injection-testing`, `feature-flag-testing`, `test-quality-check`, `standards-audit`,
  `bdd-project-scaffold`, `bdd-reviewer`, `gherkin-step-code`, `page-object-design`,
  `page-objects-from-url`, `ui-test-author/{playwright,appium,review}`, `mobile-screen-objects`,
  `ai-feature-testing`, `ai-answer-quality-testing`. **S6 owns the rest:** `accessibility-testing`,
  `browser-cloud-setup`, `device-cloud`, `inhouse-framework-conventions`, `language-testing`,
  `load-testing`, `mobile-app-crawler`, `mobile-native-features`, `mobile-project-setup`,
  `mobile-screen-explorer`, `network-mocking`, `performance-project-setup`, `production-uptime-checks`,
  `responsive-testing`, `security-testing/*`, `ui-project-setup`, `ui-test-author/selenium`,
  `visual-regression`. Gate line added to 3 agents, each as the last Operating-rules bullet.
  Data issues: 46 fixed.
  - K1: `qa-api-client-writer` → `qa-api-client-writer-dotnet` (`api-models/SKILL.md:20`);
    `qa-db-testing-dotnet` ×2 → `qa-db-testing-testcontainers-dotnet` (`failure-injection-testing/SKILL.md:287`,
    `:318`; both sentences are about the Testcontainers-hosted dependency).
  - **Stale path shorthands** (the resolver cannot see them: they are paths, not prefixed names), 35
    occurrences in 2 agents and 17 skill files. The folders were renamed but the citations were not:
    `api-test-author/generator` → `writer`, `api-test-author/reviewer` → `review`,
    `ui-test-author/reviewer` → `review`, `db-testing/client` → `connection`, `bdd-project-setup` →
    `bdd-project-scaffold`, and `conformance-audit` → `standards-audit` (`qa-api-dotnet.md:78`). Every
    step-table hit in `qa-api-dotnet.md:74–78` and `qa-bdd-dotnet.md:83`, `:87` pointed at a folder that
    does not exist.
  - K6: `Node 20` ×8 in 7 files, all "same skill, Node 20 + TS" sibling lines
    (`realtime-stream-testing/SKILL.md:379`, the four `messaging-testing/references/*`, the two
    `file-storage-testing/references/*`) → Node 24. `realtime-stream-testing:380` names Node 20 as the
    polyfill boundary; it stays and now flags Node 20 as EOL. No `Node 20` hit is left in `qa/dotnet`,
    so S6 has none.
  Code issues: 37 fixed.
  - K7: 15 descriptions gained a Do-NOT clause pointing at the sibling (e.g. `api-client-writer`,
    `page-object-design`, `ui-test-author/{playwright,review}`, `test-login-tokens`, `api-contract-testing`,
    `test-quality-check`, `ai-answer-quality-testing`); `api-test-author/grpc`, `data-driven-testing` and
    `standards-audit` now open with "Use when". All ≤ 500 (largest 483). The three agent descriptions
    already fit (521, 592, 583) and open with the role, as S2/S3 kept.
  - K5: `standards-audit/SKILL.md:12` "Announce at start" → "State the mode … in the first line of
    output"; the all-caps "THE SCOPE FENCE" heading became sentence case.
  - K2 for skills: one `Gate: none` sentence ("written, not run") on the run/verify step of 16 skills
    (`api-models:177`, `api-client-writer:285`, `api-test-author/writer:138`, `…/playwright:250`,
    `ui-test-author/playwright:315`, `…/appium:377`, `page-objects-from-url` §6, `mobile-screen-objects:105`,
    `bdd-project-scaffold:51`, `gherkin-step-code:148`, `test-data-builder:197`, `db-testing/connection:263`,
    `…/testcontainers:269`, `api-contract-testing:244`, `api-project-setup:208`, `test-login-tokens:123`).
  - `qa-llm-dotnet.md` Orientation 2 said "Recover, don't author" twice; merged into one paragraph.
  Logical conflicts: 7 fixed.
  - The operating rule "Run what you write — a step whose code never executed does not pass its gate"
    contradicts a `Gate: none` task; in all three agents it now reads "Run what you write, outside a
    `Gate: none` plan task". **New family** — every qa agent and `fe-blazor`, `fe-react`,
    `tooling-engineer` carry it.
  - The orientation "every run regardless of (the gate's) verdict" now reads "every run outside a
    `Gate: none` plan task, regardless of the cache gate's verdict" (`qa-api-dotnet.md:58`,
    `qa-bdd-dotnet.md:47`, `qa-llm-dotnet.md:70`); `qa-llm-dotnet.md:68`'s "confirm it runs … on
    arrival" got the same exception.
  Cleanup: none. The K9 recipes found no plan, progress or tracked junk file in `qa/dotnet`, and every
  qa/dotnet skill, agent and command is listed in the marketplace.
  Kept on purpose:
  - K4 hits are D8 vocabulary (RAG retrieval/generation "stages", a Pact deploy "stage", Azure block
    staging). K3 hits are code branches, feature-flag branches, Pact `--branch` and "branch coverage".
  - K8 hits are the .NET CLI in exit criteria, procedure steps and checklists. `dotnet test` is the
    project's own command in a .NET suite; `pip install deepteam` is a tool install line.
  - "— MANDATORY SECTION" and the `be-shared-session-budget` Step 5 closing duty do not occur in
    `qa/dotnet`; the `NEVER` in `production-uptime-checks` / `mobile-native-features` code comments is S6's.
  Carried forward: the stale-path family and the "Run what you write" family are traps in S6–S10;
  the stale paths also occur in `qa/_shared` and `qa/manual` (S11), `frontend/blazor/skills/forms`
  (S13) and `data/_shared/slow-query-fixes` (S15), so those blocks carry it too.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: nothing.

### S6 — qa/dotnet UI, mobile and performance lanes

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-ui-dotnet`, `qa-mobile-dotnet`, `qa-performance-dotnet`, `qa/dotnet/commands/` and
every remaining `qa/dotnet` skill pass K1–K9.
**Depends on:** —
**Budget:** ~130k — floor 24k, plan sections 9k, recipe output 6k, three agents and commands 19k, ~10
skills around hits 20k, descriptions 7k, ~13 files modified 20k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- Your skills are the `qa/dotnet/skills/` folders S5 did not own; its As built note lists them.
- K1: `qa-ci-pipelines` and `qa-performance-nbomber` in `skills/production-uptime-checks/SKILL.md`.
- K2: the Gate line in the three agents.
- K6: the remaining `qa/dotnet` `Node 20` hits → Node 24.
- **Not in S6:** S5's lanes.
- **As built (2026-09-26):** `qa/dotnet/agents/{qa-ui-dotnet,qa-mobile-dotnet,qa-performance-dotnet}.md`
  and `qa/dotnet/commands/*.md` (read in full), and the 18 skill folders S5 left to S6. Gate line added
  to 3 agents, each as the last Operating-rules bullet (`qa-ui-dotnet.md:36`, `qa-mobile-dotnet.md:37`,
  `qa-performance-dotnet.md:38`). Six stale paths sat in S5-owned files; S6 fixed them too (D14).
  Data issues: 29 fixed.
  - K1: `production-uptime-checks/SKILL.md:31`, `:360` `qa-performance-nbomber` → `qa-load-testing-dotnet`;
    `:124`, `:362` `qa-ci-pipelines` → `qa-ci-pipelines-dotnet` (the `-github-actions` / `-gitlab-ci`
    names are reference files of that skill, now said so). The resolver prints only `data-testid` /
    `data-test` over `qa/dotnet`.
  - Stale paths: the known seven (`qa-ui-dotnet.md:101` `db-testing/client`, `:102`
    `ui-test-author/reviewer`, `:104` `conformance-audit`; `qa-mobile-dotnet.md:87`, `:88`;
    `qa-performance-dotnet.md:92`; `network-mocking/SKILL.md:3` `api-test-author/generator`). **New
    family:** `performance/nbomber`, a folder that never existed — the NBomber skill is `load-testing`
    (`qa-performance-dotnet.md:91`, `network-mocking/SKILL.md:3`, `failure-injection-testing/SKILL.md:3`,
    `performance-project-setup/SKILL.md:3`, `:100`, `:127`, `standards-audit/references/conformance-checklist.md:18`,
    `api-test-author/writer/SKILL.md:21` `qa/dotnet/skills/performance`). **Second new family:**
    `qa/_shared/api-contract-testing` → `qa/_shared/contract-testing-pact` (`qa-api-dotnet.md:16`, `:76`;
    `api-contract-testing/SKILL.md:8`, `:15`, `:217`, `:254`). `qa-performance-dotnet.md:94` named CI
    hosts as skills; now "read only the `references/<host>.md`". `test-quality-check/SKILL.md:23` cited a
    `qa/typescript/skills/test-quality-check` that does not exist → "no house skill yet".
  - K6: the recipe prints only `realtime-stream-testing/SKILL.md:380`, the flagged EOL line.
  Code issues: 16 fixed.
  - K7: Do-NOT clauses added to `production-uptime-checks`, `load-testing`, `browser-cloud-setup`,
    `ui-test-author/selenium`, `inhouse-framework-conventions`; all ≤ 500 (largest `network-mocking` 487).
    Agent descriptions already fit (622, 594, 549).
  - K5: `qa-dotnet-audit.md:14` "THE SCOPE FENCE" → sentence case, and `:22` "in the announcement" →
    "in the first line of output" (matching S5's `standards-audit` fix); all-caps `NEVER`/`CALLER`/`NOT`
    in `mobile-native-features/SKILL.md:117` and `production-uptime-checks/SKILL.md:167`, `:360`.
  - K2 for skills: the "written, not run" sentence on the run/checklist step of `ui-project-setup`,
    `mobile-project-setup`, `performance-project-setup` and `ui-test-author/selenium:224`.
  - "Recover, don't author" doubled in the Orientation 2 of `qa-ui-dotnet` and `qa-performance-dotnet`;
    merged.
  Logical conflicts: 10 fixed.
  - "Run what you write" gains "outside a `Gate: none` plan task" in all three agents; so do Orientation
    3's "every run regardless of the gate's verdict" and Orientation 2's "confirm it builds/runs on
    arrival".
  - `qa-performance-dotnet`'s Step 6 loads `qa/cicd` / `qa/reporting` skills and its bug-report rule
    loads `qa/manual/bug-report-writer`, while "Related agents" says "do not load their skills"; the three
    exceptions are now stated once under the list.
  Cleanup: none; the K9 recipes find nothing in `qa/dotnet`, and every qa/dotnet skill is published.
  Kept on purpose: K3 hits are Percy/Applitools branch baselines, "code branching", and
  `inhouse-framework-conventions:197`, which describes the Accelerator project's own `/review` command
  rather than instructing the session. K4 hits are a CI gating stage, CDP throttling "phases" and an
  "authorization slice" of a suite (D8). K8 hits are the .NET CLI in exit gates and checklists, and
  `npm install` / `npx` tool installs in code samples (Lighthouse CI, Percy, Appium).
  Carried forward: `performance/<tool>` → `load-testing` and `qa/_shared/api-contract-testing` →
  `contract-testing-pact` into S7–S11, S13 and G1 (catalog `:36`, `:65`, `:66`); production-uptime-checks'
  name mapping into S8 and S10.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: `.NET 8` is written
  as the stack in ~70 headings and "Stack assumptions" lines across qa/dotnet skills (e.g.
  `load-testing/SKILL.md:6`, `:28`, `network-mocking/SKILL.md:6`). The K6 recipe does not match it and
  .NET 8 is a supported version until Nov 2026, so it stays; moving the defaults to ".NET 10 (8–9
  supported)" is a wide rewrite for a later plan to decide.

### S7 — qa/java API, BDD and LLM lanes

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-api-java`, `qa-bdd-java`, `qa-llm-java` and every `qa/java` skill they load pass
K1–K9.
**Depends on:** —
**Budget:** ~130k — floor 24k, plan sections 9k, recipe output 6k, three agents 17k, ~11 skills around
hits 22k, descriptions 6k, ~14 files modified 21k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- The lane rule is in §2.
- K1: `qa-api-client-writer` in `skills/api-models/SKILL.md`; `qa-db-testing-java` ×2 in
  `skills/failure-injection-testing/SKILL.md`.
- K2: the Gate line in the three agents.
- K6: `qa/java`'s `Node 20` hits in your skills → Node 24.
- **Not in S7:** the UI, mobile and performance lanes and `qa/java/commands/` (S8).
- **As built (2026-09-26):** `qa/java/agents/{qa-api-java,qa-bdd-java,qa-llm-java}.md` (read in full)
  and the 27 skill folders their loading lists name: `test-login-tokens`, `api-models`,
  `api-client-writer`, `test-data-builder`, `api-test-author/{writer,playwright,graphql,grpc,review}`,
  `data-driven-testing`, `db-testing/{connection,testcontainers,verification-queries}`,
  `messaging-testing`, `file-storage-testing`, `email-testing`, `realtime-stream-testing`,
  `api-contract-testing`, `failure-injection-testing`, `feature-flag-testing`, `test-quality-check`,
  `bdd-project-scaffold`, `bdd-reviewer`, `gherkin-step-code`, `page-object-design`,
  `page-objects-from-url`, `ui-test-author/{playwright,appium,review}`, `mobile-screen-objects`,
  `ai-feature-testing`, `ai-answer-quality-testing`. qa/java has no `api-project-setup` or
  `standards-audit` folder. **S8 owns the rest:** `accessibility-testing`, `browser-cloud-setup`,
  `device-cloud`, `inhouse-framework-conventions`, `language-testing`, `load-testing`,
  `mobile-app-crawler`, `mobile-native-features`, `mobile-screen-explorer`, `network-mocking`,
  `production-uptime-checks`, `responsive-testing`, `security-testing/*`, `ui-test-author/selenium`,
  `visual-regression`. Gate line added to 3 agents, each as the last Operating-rules bullet
  (`qa-api-java.md:37`, `qa-bdd-java.md:38`, `qa-llm-java.md:73`).
  Data issues: 29 fixed.
  - K1: `api-models/SKILL.md:22` `qa-api-client-writer` → `qa-api-client-writer-java`;
    `failure-injection-testing/SKILL.md:307`, `:340` `qa-db-testing-java` → `qa-db-testing-testcontainers-java`
    (`:340` also listed `qa-messaging-testing-java` twice; one removed). The resolver now prints only
    `data-testid` / `data-test` / `data-provider-thread-count` and S8's `production-uptime-checks` names.
  - Stale paths, 21: `qa/_shared/api-contract-testing` → `contract-testing-pact` (`qa-api-java.md:18`,
    `:140`; `api-contract-testing/SKILL.md:8`, `:26`, `:265`, `:450`); `bdd-project-setup` →
    `bdd-project-scaffold` (`qa-bdd-java.md:103`, a step-table path to a folder that does not exist;
    `gherkin-step-code/SKILL.md:3`, `:8`, `:26`, `:183`; `bdd-project-scaffold/SKILL.md:36`); the skill's
    frontmatter name `qa-bdd-project-setup-java` stays (no renames). `api-test-author/generator` →
    `writer` (`api-test-author/playwright/SKILL.md:3`, `:28`, `:237`; `…/review/SKILL.md:3`);
    `db-testing/client` → `connection` (`db-testing/connection/SKILL.md:23`,
    `file-storage-testing/references/s3.md:24`, `azure-blob.md:25`). `api-contract-testing/SKILL.md:457`
    named three `ci-pipelines/<host>` folders → "`ci-pipelines` (its `references/<host>.md`)";
    `test-quality-check/SKILL.md:22` cited a `qa/typescript/skills/test-quality-check` that does not
    exist → "no house skill yet" (S6's wording). Every `qa/…` path in the S7 files now resolves on disk.
  - K6: `Node 20` ×6, all "same skill, Node 20 + TS" sibling lines in the four
    `messaging-testing/references/*` and two `file-storage-testing/references/*` → Node 24. No `Node 20`,
    `Java 17` or `Spring Boot 2` hit is left in qa/java.
  Code issues: 43 fixed.
  - K7: 25 descriptions rewritten, 24 of them to add a Do-NOT clause naming the sibling (e.g.
    `api-models`, `api-client-writer`, `api-test-author/*`, `db-testing/{connection,testcontainers}`,
    `page-object-design`, `ui-test-author/{playwright,appium,review}`, `ai-feature-testing`,
    `ai-answer-quality-testing`), and `gherkin-step-code` for its stale path. In 12 of them the
    boilerplate "For end-to-end suite work prefer the staged agent … single targeted artifact" gave way
    to the clause; `api-test-author/{graphql,grpc}` and `data-driven-testing` now open with "Use when".
    All ≤ 500 (largest `ai-feature-testing` 495). The agent descriptions already fit (482, 596, 566).
  - K2 for skills: the "written, not run" sentence on the run/verify step of 15 skills (`api-models:159`,
    `api-client-writer:318`, `api-test-author/writer:220`, `…/playwright:246`, `ui-test-author/playwright:346`,
    `…/appium:260`, `page-objects-from-url` §6, `mobile-screen-objects:105`, `bdd-project-scaffold:53`,
    `gherkin-step-code:165`, `test-data-builder:217`, `db-testing/connection:258`, `…/testcontainers:239`,
    `api-contract-testing:440`, `test-login-tokens:119`).
  - "Recover, don't author" doubled in Orientation 2 of all three agents; merged.
  Logical conflicts: 10 fixed.
  - "Run what you write", Orientation 3's "every run regardless of the gate's verdict", and Orientation 2's
    "confirm the suite builds and runs" each gain "outside a `Gate: none` plan task" in all three agents.
  - `qa-llm-java.md` Mode A wrote a real regression up via `qa/manual/bug-report-writer` while the
    loading protocol forbids `qa/manual/` and its own operating rule hands defects to
    `qa-test-case-designer`; it now hands off (D15). Same fix in `qa-llm-dotnet.md:88` (outside qa/java).
  Cleanup: none. The K9 recipes find no plan, progress or tracked junk file in qa/java, and all 61
  qa/java skills, agents and commands are listed in the marketplace.
  Kept on purpose: K3 hits are flag branches, code branching, Pact `--branch` / `mainBranch`, PIT's
  origin branch, Percy/Applitools branch baselines and `inhouse-framework-conventions:220` (S8's; it
  describes the Accelerator's own `/review`). K4 hits are RAG retrieval/generation "stages", Spring
  "slice" tests, a "vertical slice" read, Azure block staging and a Pact deploy "stage" (D8). K5 prints
  only the `NEVER`/`CALLER` code comments in S8's `production-uptime-checks` and `mobile-native-features`.
  K8 hits are `./gradlew test` (the project's own command in a Gradle suite) and `pip install` /
  `npm install` tool-install lines in code samples. "— MANDATORY SECTION" and the
  `be-shared-session-budget` Step 5 duty do not occur in qa/java.
  Carried forward: S8's block now lists its seven Do-NOT gaps, the `…/percy|applitools|lighthouse-ci/SKILL.md`
  paths in `qa-ui-java.md:115`, `network-mocking`'s "`performance` skill", and that K6 is empty; S9's
  block gains the description boilerplate and the `qa-llm-typescript.md:136` hand-off (D15).
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: nothing.

### S8 — qa/java UI, mobile and performance lanes

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-ui-java`, `qa-mobile-java`, `qa-performance-java`, `qa/java/commands/` and every
remaining `qa/java` skill pass K1–K9.
**Depends on:** —
**Budget:** ~130k — floor 24k, plan sections 9k, recipe output 6k, three agents and commands 18k, ~10
skills around hits 20k, descriptions 6k, ~13 files modified 20k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- Your skills are the `qa/java/skills/` folders S7 did not own; its As built note lists them.
- K1: `qa-ci-pipelines`, `qa-performance-k6` ×4 and `qa-performance-gatling` ×2 in
  `skills/production-uptime-checks/SKILL.md`.
- K2: the Gate line in the three agents.
- K6: the remaining `qa/java` `Node 20` hits → Node 24.
- **Not in S8:** S7's lanes.
- **As built (2026-09-26):** `qa/java/agents/{qa-ui-java,qa-mobile-java,qa-performance-java}.md` and
  `qa/java/commands/*.md` (read in full), and the 15 skill folders S7's note left to S8. Gate line added
  to 3 agents, each as the last Operating-rules bullet (`qa-ui-java.md:37`, `qa-mobile-java.md:38`,
  `qa-performance-java.md:35`). The six commands need nothing: each only points at its agent file.
  Data issues: 12 fixed.
  - K1: `production-uptime-checks/SKILL.md:20`, `:35`, `:131`, `:327` `qa-performance-k6` →
    `qa-load-testing-typescript` (k6 is the TypeScript lane's tool, S6's mapping); `:35`, `:329`
    `qa-performance-gatling` → `qa-load-testing-java`; `:117`, `:330` `qa-ci-pipelines` →
    `qa-ci-pipelines-java` (`:330` now "its GitLab CI, GitHub Actions and Azure Pipelines references";
    the stray `(#?)` at `:327` removed). The resolver now prints only `data-testid` / `data-test` /
    `data-provider-thread-count` over qa/java.
  - Stale paths: `qa-ui-java.md:114` `…/percy/SKILL.md`, `…/applitools/SKILL.md`, `…/lighthouse-ci/SKILL.md`
    → "its `references/percy.md`" etc.; `network-mocking/SKILL.md:3` "the `performance` skill" →
    `qa-load-testing-java`; `qa-performance-java.md:87` bare `test-reports` (which resolves to no
    qa/java skill) → `qa/reporting/java/skills/test-reports/SKILL.md`, and its "house default" CI note →
    S6's "read only the `references/<host>.md`"; `load-testing/SKILL.md:363`
    `ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` (reference files, not folders) → "its
    `references/<host>.md`"; `browser-cloud-setup/SKILL.md:8` `ui-test-author/{playwright,appium}/java`
    → `…/{playwright,appium}`. Every `qa/…` path in the S8 files now resolves on disk.
  - K6: nothing; the recipe prints no hit in qa/java.
  Code issues: 14 fixed.
  - K7: Do-NOT clauses added to the seven — `browser-cloud-setup`, `inhouse-framework-conventions`,
    `ui-test-author/selenium`, `device-cloud`, `production-uptime-checks`, `mobile-native-features`,
    `load-testing` — each naming the sibling by frontmatter name; the staged-agent boilerplate is gone
    from the three that had it. All ≤ 500 (largest `network-mocking` 487, `production-uptime-checks` 468).
    Agent descriptions already fit (639, 559, 518).
  - K5: all-caps `NEVER` in `production-uptime-checks/SKILL.md:161` and `NEVER`/`CALLER` in
    `mobile-native-features/SKILL.md:126` → lower case.
  - K2 for skills: the "written, not run" sentence on the run step of `ui-test-author/selenium:221`,
    `browser-cloud-setup:115`, `device-cloud:212` and `load-testing:353`.
  - "Recover, don't author" doubled in the Orientation 2 of `qa-ui-java` and `qa-mobile-java`; merged
    into S7's one-sentence form.
  - `qa-mobile-java.md` had its "Emit no comments" bullet stranded after the "Live-app exploration"
    subsection; moved into the Operating-rules list.
  Logical conflicts: 10 fixed.
  - "Run what you write", Orientation 3's "every run regardless of the gate's verdict" (worded
    "regardless of verdict" in `qa-performance-java`) and Orientation 2's "confirm it builds/runs on
    arrival" each gain "outside a `Gate: none` plan task" in all three agents.
  - `qa-performance-java`'s Step 6 loads `qa/cicd` / `qa/reporting` skills and its bug-report rule loads
    `qa/manual/bug-report-writer`, while "Related agents" says "do not load their skills"; the three
    exceptions are now stated once under the list (S6's reading, kept for performance agents).
  Cleanup: none. The K9 recipes find nothing in qa/java, and every qa/java skill, agent and command is
  listed in the marketplace.
  Kept on purpose: K3 hits are Percy/Applitools branch baselines, flag and code branching, Pact
  `--branch`, and `inhouse-framework-conventions:220` (the Accelerator's own `/review` command). K4 hits
  are the CI "gating stage", CDP throttling "phases", a "slice" of a suite, Spring slice tests, Azure
  block staging and RAG stages (D8). K8 hits are `./gradlew test` / `gatlingRun` (the Gradle suite's own
  command) and `npm install` / `pip install` tool installs in code samples (Lighthouse CI, Percy,
  DeepEval, Ragas). The mobile-app-crawler screen-map template's three broken links are deliberate
  examples (§6.1). "— MANDATORY SECTION" and the `be-shared-session-budget` Step 5 duty do not occur.
  Carried forward: S10's block gains the same three copied defects in its agents
  (`qa-ui-typescript.md:115` reference paths, `qa-mobile-typescript.md:51` stranded bullet,
  `qa-performance-typescript.md:107` CI note) and the description boilerplate.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: O9 — the
  `// TODO: missing data-testid` marker that `page-objects-from-url` and the UI agents prescribe against
  CLAUDE.md's no-`TODO` rule; the text is unchanged.

### S9 — qa/typescript API, BDD and LLM lanes

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-api-typescript`, `qa-bdd-typescript`, `qa-llm-typescript` and every `qa/typescript`
skill they load pass K1–K9, including the move off Node 20 in those files.
**Depends on:** —
**Budget:** ~140k — floor 24k, plan sections 9k, recipe output 6k, three agents 18k, ~8 skills around
non-version hits 16k, ~14 version-only files reviewed as a diff 7k, descriptions 6k, files modified
24k (the version edits are one substitution, reviewed in the diff), read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- The lane rule is in §2.
- K6: `qa/typescript` holds 86 `Node 20` hits in 44 files, many of them "TypeScript/Node 20" in agent
  descriptions and titles. Change your lanes' files with one substitution to Node 24, then read the
  diff: keep any hit that names Node 20 as a detected or EOL version, and reword those to flag it.
- K1: `qa-db-testing-typescript` ×2 in `skills/failure-injection-testing/SKILL.md`.
- K2: the Gate line in the three agents.
- **Not in S9:** the UI, mobile and performance lanes and `qa/typescript/commands/` (S10).
- **As built (2026-09-26):** `qa/typescript/agents/{qa-api-typescript,qa-bdd-typescript,qa-llm-typescript}.md`
  (read in full) and the 28 skill folders their loading lists name: `test-login-tokens`, `api-models`,
  `api-client-writer`, `test-data-builder`, `api-test-author/{writer,playwright,graphql,grpc,review}`,
  `data-driven-testing`, `db-testing/{connection,testcontainers,verification-queries}`, `messaging-testing`,
  `file-storage-testing`, `email-testing`, `realtime-stream-testing`, `api-contract-testing`,
  `failure-injection-testing`, `feature-flag-testing`, `bdd-project-scaffold`, `bdd-reviewer`,
  `gherkin-step-code`, `page-object-design`, `page-objects-from-url`, `ui-test-author/{playwright,appium,review}`,
  `mobile-screen-objects`, `ai-feature-testing`, `ai-answer-quality-testing` (56 `.md` files). qa/typescript has
  no `api-project-setup`, `standards-audit` or `test-quality-check` folder. **S10 owns the rest:**
  `accessibility-testing`, `browser-cloud-setup`, `device-cloud`, `inhouse-framework-conventions`,
  `language-testing`, `load-testing`, `mobile-app-crawler`, `mobile-native-features`, `mobile-screen-explorer`,
  `network-mocking`, `production-uptime-checks`, `responsive-testing`, `security-testing/*`,
  `ui-test-author/selenium`, `visual-regression`. Gate line added to 3 agents, each as the last
  Operating-rules bullet (`qa-api-typescript.md:37`, `qa-bdd-typescript.md:40`, `qa-llm-typescript.md:72`).
  Data issues: 85 fixed.
  - K6: one substitution over the 56 files changed 63 `Node 20` hits in 30 files to Node 24 (agent
    descriptions, titles and role lines; the "Node 20 + TypeScript" stack lines; the email, messaging and
    file-storage references). The diff review reworded 9 of them in `realtime-stream-testing/SKILL.md:64–68`,
    `:283`, `:332` and `references/details.md:42–55`, where Node 20 was the native-`WebSocket`/`EventSource`
    boundary: those now describe Node 22/24 as having the globals and flag a detected Node 20 as EOL. The K6
    recipe over the S9 files prints only those four flag lines; the 23 `Node 20` hits left in qa/typescript
    are all S10's. `api-client-writer/SKILL.md:8` "(Node 24+)" for native `fetch` → "(built into Node 22 and 24)".
  - K1: `failure-injection-testing/SKILL.md:312`, `:345` `qa-db-testing-typescript` →
    `qa-db-testing-testcontainers-typescript` (`:345` also listed `qa-messaging-testing-typescript` twice;
    one removed). The resolver prints only `data-testid` / `data-test` over the S9 files.
  - Stale paths, 20: `qa/_shared/api-contract-testing` → `contract-testing-pact` (`qa-api-typescript.md:18`,
    `:140`; `api-contract-testing/SKILL.md:8`, `:15`, `:213`, `:251`); `bdd-project-setup` →
    `bdd-project-scaffold` (`qa-bdd-typescript.md:105`, a step-table path to a folder that does not exist;
    `gherkin-step-code/SKILL.md:3`, `:8`, `:82` and both references ×2; `bdd-project-scaffold/SKILL.md:47`);
    the frontmatter name `qa-bdd-project-setup-typescript` stays. `api-test-author/generator` → `writer`
    (`api-test-author/playwright/SKILL.md:3`, `:29`, `:233`; `…/review/SKILL.md:3`); `db-testing/client` →
    `connection` (`db-testing/connection/SKILL.md:23`, `file-storage-testing/references/s3.md:25`,
    `azure-blob.md:13`, `:26`); `api-contract-testing/SKILL.md:256` `ci-pipelines/{github-actions,…}` →
    "`ci-pipelines` (its `references/<host>.md`)". Every `qa/…` path in the S9 files now resolves on disk.
  Code issues: 51 fixed.
  - K7: 23 skill descriptions rewritten, 22 of them to add a Do-NOT clause naming the sibling by frontmatter
    name (e.g. `api-models`, `api-client-writer`, `api-test-author/*`, `db-testing/connection`,
    `page-object-design`, `ui-test-author/{playwright,appium,review}`, `ai-feature-testing`,
    `ai-answer-quality-testing`; `api-test-author/review` swapped its path pointer for the name). In 12 the
    staged-agent boilerplate gave way to the clause; `api-test-author/{graphql,grpc}`, `data-driven-testing`
    and `realtime-stream-testing` now open with "Use when". All ≤ 500 (largest `ai-answer-quality-testing`
    499). Agent descriptions fit (524, 640, 574); "TypeScript/Node 20" → "Node 24" in two of them.
  - K2 for skills: the "written, not run" sentence on the run/verify step of 15 skills (`api-models:158`,
    `api-client-writer:320`, `api-test-author/writer:196`, `…/playwright:243`, `ui-test-author/playwright:264`,
    `…/appium:245`, `page-objects-from-url` §6, `mobile-screen-objects:100`, `bdd-project-scaffold:64`,
    `gherkin-step-code:60`, `test-data-builder:242`, `db-testing/connection:284`, `…/testcontainers:229`,
    `api-contract-testing:242`, `test-login-tokens:112`).
  - K8: hardcoded `pnpm exec tsc` / `pnpm test` / `npm run typecheck` / `pnpm exec eslint` in those run steps
    (`api-models`, `api-client-writer` ×2, `api-test-author/{writer,playwright}`, `test-data-builder`,
    `db-testing/connection`, `api-contract-testing:242`) and in the orientation's "how it is invoked" line of
    `qa-api-typescript` and `qa-llm-typescript` → the project's own script, run with the package manager
    `packageManager` names.
  - "Recover, don't author" doubled in Orientation 2 of all three agents; merged into S7's one-sentence form.
  Logical conflicts: 10 fixed.
  - "Run what you write", Orientation 3's "every run regardless of the gate's verdict" and Orientation 2's
    "confirm it builds/runs" each gain "outside a `Gate: none` plan task" in all three agents.
  - `qa-llm-typescript.md:135` wrote a real regression up via `qa/manual/bug-report-writer` against its own
    loading protocol; it now hands off to `qa-test-case-designer` (D15).
  Cleanup: none. The K9 recipes find no plan, progress or tracked junk file in qa/typescript, and every
  qa/typescript skill, agent and command is listed in the marketplace.
  Kept on purpose: K3 hits are the fixed workspace sentence, flag branches, GraphQL envelope branches, Pact
  `--branch` / `mainBranch` and POM "branching" review rows. K4 hits are RAG retrieval/generation "stages",
  a Pact deploy "stage", Azure block staging, a "vertical slice" read, an inbox "slice" and a
  "test-token slice" (D8). K8 hits left are `pip install` tool installs in the DeepEval/Ragas references and
  the `pnpm --filter … test` lines in `api-contract-testing`'s CI YAML samples. The exit-gate commands
  (`npx vitest run`, `npx tsc --noEmit`, `npx bddgen && npx playwright test`) stay as exit criteria. K5 and
  "— MANDATORY SECTION" / the `be-shared-session-budget` Step 5 duty do not occur in the S9 files.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: nothing.

### S10 — qa/typescript UI, mobile and performance lanes

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-ui-typescript`, `qa-mobile-typescript`, `qa-performance-typescript`,
`qa/typescript/commands/` and every remaining `qa/typescript` skill pass K1–K9, with no `Node 20`
default left in `qa/typescript/`.
**Depends on:** —
**Budget:** ~140k — floor 24k, plan sections 9k, recipe output 6k, three agents and commands 19k, ~8
skills around non-version hits 16k, ~14 version-only files reviewed as a diff 7k, descriptions 6k,
files modified 24k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- Your skills are the `qa/typescript/skills/` folders S9 did not own; its As built note lists them.
- K6: the same substitution and diff review as S9, over your files.
- K1: `qa-ci-pipelines` and `qa-performance-k6` ×2 in `skills/production-uptime-checks/SKILL.md`.
- K2: the Gate line in the three agents.
- **Not in S10:** S9's lanes.
- **As built (2026-09-26):** `qa/typescript/agents/{qa-ui-typescript,qa-mobile-typescript,qa-performance-typescript}.md`
  and `qa/typescript/commands/*.md` (read in full), and the 15 skill folders S9's note left to S10 (41 `.md`
  files). Gate line added to 3 agents, each as the last Operating-rules bullet (`qa-ui-typescript.md:37`,
  `qa-mobile-typescript.md:38`, `qa-performance-typescript.md:39`). The six commands need nothing: each only
  points at its agent file.
  Data issues: 34 fixed.
  - K6: the same one-pass substitution over the S10 files moved the 23 remaining `Node 20` hits to Node 24 (the
    ui and mobile agents' descriptions, titles, role lines and mobile's "Appium/TS on Node 20"; the "Node 20 +
    TypeScript" stack lines of 11 skills and references; `inhouse-framework-conventions/SKILL.md:8`, whose
    description already said Node 24). The diff review reworded one feature boundary:
    `device-cloud/SKILL.md:16` global `fetch` + `FormData` + `Blob` "(Node 20)" → "(built into Node 22 and 24)".
    Also `security-testing/dependency-scan/SKILL.md:232` CI YAML `node-version: 20` → 24. The K6 recipe over
    qa/typescript now prints only S9's four flagged EOL lines in `realtime-stream-testing`.
  - K1: `production-uptime-checks/SKILL.md:29`, `:344` `qa-performance-k6` → `qa-load-testing-typescript`;
    `:346` `qa-ci-pipelines` → `qa-ci-pipelines-typescript` ("its GitHub Actions, Azure Pipelines and GitLab CI
    references"). The resolver prints only `data-testid` / `data-test` over qa/typescript.
  - Stale paths, 7: `qa-ui-typescript.md:114` `…/percy/SKILL.md`, `…/applitools/SKILL.md`, `…/lighthouse-ci/SKILL.md`
    → "its `references/percy.md`" etc.; `browser-cloud-setup/SKILL.md:8` `ui-test-author/{playwright,appium}/typescript`
    → `…/{playwright,appium}`; `load-testing/SKILL.md:21` `api-test-author/writer/<stack>` → `…/writer` and
    `ui-test-author/<stack>` → `<tool>`; `:326` `ci-pipelines/{github-actions,…}` → "`ci-pipelines` (its
    `references/<host>.md`)". Every other `qa/…` path in the S10 files resolves on disk or is a stated glob.
  Code issues: 27 fixed.
  - K7: Do-NOT clauses added to the eight — `browser-cloud-setup`, `inhouse-framework-conventions`,
    `ui-test-author/selenium`, `language-testing`, `device-cloud`, `production-uptime-checks`,
    `mobile-native-features`, `load-testing` — each naming the sibling by frontmatter name (S8's Java pairs,
    with `fe-react-languages` for localization wiring); the staged-agent boilerplate is gone from the three
    that had it. All ≤ 500 (largest `language-testing` 491). Agent descriptions fit (616, 597, 544).
  - K5: all-caps `NEVER` in `production-uptime-checks/SKILL.md:186`, `references/details.md:25` and
    `NEVER`/`CALLER` in `mobile-native-features/SKILL.md:116` → lower case.
  - K2 for skills: the "written, not run" sentence on the run step of `ui-test-author/selenium:233`,
    `browser-cloud-setup:114`, `device-cloud:378`, `load-testing:315` and `network-mocking/references/{cdp:310,proxy:339,playwright-routes:328}`.
  - K8: `ui-test-author/selenium:233` `npm test`, `load-testing:313` `npm run build:perf`, and the ui and mobile
    agents' "how the suite is invoked" line → the project's own script, run with the package manager
    `packageManager` names.
  - "Recover, don't author" doubled in Orientation 2 of all three agents; merged into the one-sentence form.
  - `qa-mobile-typescript.md` "Emit no comments" bullet moved from after the "Live-app exploration" subsection
    into the Operating-rules list, with the Gate line after it.
  - `qa-performance-typescript.md:106` "house default — switch to …" CI note → "read only the
    `references/<host>.md` … matching the project's existing CI".
  Logical conflicts: 10 fixed.
  - "Run what you write", Orientation 3's "every run regardless of the gate's verdict" and Orientation 2's
    "confirm it builds/runs on arrival" each gain "outside a `Gate: none` plan task" in all three agents.
  - `qa-performance-typescript`'s Step 6 loads `qa/cicd` / `qa/reporting` skills and its bug-report rule loads
    `qa/manual/bug-report-writer`, while "Related agents" says "do not load their skills"; the three exceptions
    are stated once under the list (`:115`, S6's reading).
  Cleanup: none. The K9 recipes find nothing in qa/typescript, and every qa/typescript skill, agent and command
  is listed in the marketplace.
  Kept on purpose: K3 hits are the fixed workspace sentence, Percy/Applitools branch baselines and
  `inhouse-framework-conventions:209` (the Accelerator's own `/review` command). K4 hits are k6 `stages:`, the
  CI "gating stage" / "perf-gate stage", CDP throttling "phases" and an "authorization slice" of a suite (D8).
  K8 hits left are `npm install` tool installs and `npm run start` / `npm ci` in code and CI YAML samples. The
  `green` hits are exit criteria (K2 keep). `ci-pipelines/*` cross-links stay as globs. "— MANDATORY SECTION"
  and the `be-shared-session-budget` Step 5 duty do not occur.
  Carried forward: the Node-20 feature-boundary trap (and CI `node-version: 20`) into the S12, S13, S14 and
  S17 blocks, whose folders still hold `Node 20` hits.
  Unverified: nothing was run beyond §4's searches (Gate: none). Left for the user: O9 also covers
  `qa-ui-typescript.md:45` (the `// TODO: missing data-testid` marker); the text is unchanged.

### S11 — qa/_shared and qa/manual

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/_shared/` and `qa/manual/` pass K1–K9: `qa-security`, `qa-test-case-designer` and
`qa-test-planner` carry the Gate line, and the two over-budget mobile security descriptions fit.
**Depends on:** —
**Budget:** ~120k — floor 24k, plan sections 9k, recipe output 6k, three agents and commands 19k, ~8
skills around hits 16k, descriptions 7k, ~11 files modified 17k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K7: `qa/_shared/security-testing/mobile-runtime-testing` 881 and `mobile-app-scan` 803 → ≤ 500;
  `qa-test-case-designer` 675 → ≤ 650.
- K6: `node:20` ×1 and `Python 3.10` ×1 in `qa/_shared` → the primary versions.
- K5: `qa-security` is an offensive-adjacent lane; its authorization and scope rules are hard safety
  rules and stay bold.
- K2: the Gate line in every agent under both folders.
- **Not in S11:** the per-stack qa folders (S5–S10) and `qa/cicd`, `qa/reporting` (S12).
- **As built (2026-09-26):** `qa/_shared/` and `qa/manual/`; the three agents and nine commands read in full.
  Gate line added to 3 agents, each as the last Operating-rules bullet (`qa-security.md:47`,
  `qa-test-case-designer.md:37`, `qa-test-planner.md:34`). The nine commands need nothing: each only points at
  its agent or skill file.
  Data issues: 27 fixed.
  - K6: `image-infra-scan/SKILL.md:9` `node:20-slim` → `node:24-slim`; `certificate-scan/SKILL.md:65` sslyze
    install comment "Python 3.10+" → "Python 3.13".
  - Stale paths, 20: `api-test-author/generator/<stack>` → `…/writer` and `ui-test-author/<stack>` → `…/<tool>` in
    `performance:168`, `contract-testing-pact:169`, `:170`, `:179`, `exploratory-charter-writer:256` and
    `test-strategy:21`, `:160`, `:161`, `:201`, `:202`; `test-strategy:22` `…/reviewer` → `…/review` (both);
    `test-strategy:25` and `performance:8` `skills/performance/…` → `skills/load-testing`;
    `feature-file-writer:3`, `:21`, `:155` `bdd-project-setup` → `bdd-project-scaffold` (the folder);
    `ci-pipelines/{github-actions,…}` and `ci-pipelines/<ci>` → "`ci-pipelines` (its `references/<host>.md`)" in
    `code-scan:318`, `performance:90`, `:182`, `contract-testing-pact:181`; `performance:183`
    `test-reports/<stack>` → `test-reports`; `contract-testing-pact:180` `api-models/<stack>` → `api-models`;
    `security/SETUP.md:184` put `ci-pipelines` and `test-reports` under `qa/cicd/<stack>` and
    `qa/reporting/<stack>`, where they live.
  - Stale plan stages: SECURITY-EXPANSION-PLAN's "(Stage 2/3/5/6)" and "forthcoming" labels dropped where the
    lane has landed (`penetration-testing`, `initial-access`, `security-hardening` all exist):
    `qa-security.md:26`, `:27`, `:115`, `:116`; `exploit-validation:80`, `:207`; `client-side-security:18`,
    `:161`, `:178`; `vuln-reachability:21`.
  - `python-web-testing:3`, `:11` "the library's one/single Python skill" → "qa's" (backend/python ships more).
  - `qa-security.md:55` "a changed the CI config / …" → "a change to the CI config, … or the dependency manifests".
  Code issues: 20 fixed.
  - K7: `mobile-runtime-testing` 881 → 499, `mobile-app-scan` 803 → 493, `qa-test-case-designer` 675 → 631 (both
    manual agents now open with "Use when"; `qa-test-planner` 636). Do-NOT clauses added to the nine that lacked
    one — `known-vuln-scan` (476), `secrets-scan`, `api-fuzzing`, `quality-metrics`, `test-design-techniques`,
    `exploratory-charter-writer`, `bug-report-writer`, `requirements-breakdown`, `test-strategy` — each naming the
    sibling. Every description in both folders now fits and carries one.
  - K4: `qa-test-planner` description trigger "plan the testing for this slice" → "this story";
    `requirements-breakdown:43` "one slice" → "one part of it".
  - K5: `active-scan:74`, `:241` `NEVER` → never (the bold hard rule at `:73` stays, once);
    `code-scan:152` `ALWAYS`; `python-web-testing:18` "DO NOT read the source … abslutely necessary" → one plain
    sentence, `:64` `CRITICAL:` code comment → lower case.
  - K8 and K2 for skills: `security/SETUP.md:132` "`npx vitest` / `dotnet test` / `./gradlew test`" → the project's
    own test command (the `package.json` script run with the package manager `packageManager` names, the
    `.sln`, the Gradle wrapper), plus the "written, not run" sentence.
  - `qa-security.md` Orientation 2 said "Recover, don't author" twice; merged into one sentence.
  Logical conflicts: 2 fixed.
  - `qa-security.md:59` Orientation 3 "check it every run regardless of the gate's verdict" gains "outside a
    `Gate: none` plan task".
  - `qa-security`'s Steps 1 and 6 load `qa/manual/` and `qa/cicd/` skills while "Related agents" says "never load
    their skills"; the exception is stated once under that heading (S6's reading).
  Cleanup: none. The K9 file recipe hits only `qa-test-planner.md` and the `qa-test-plan-writer` / `qa-test-planner`
  commands (names, not plans); no tracked junk; every SKILL.md, agent and command in both folders is listed in the
  marketplace and every listed path exists.
  Kept on purpose: K3 hits are the fixed workspace sentence, Pact `--branch` / `mainBranch`, KEV "OR-branch" and
  branch coverage. K4 hits are pipeline/enrichment "stages", the test-strategy "Stage" column, "the relevant slice"
  of logs and OWASP-category "slices" (D8). K8 hits left are `pip install` tool installs and the `dotnet test
  --collect` coverage sample. The `green` hits are exit criteria or "green ≠ secure" rule text (K2 keep).
  qa-security's authorization and scope rules stay bold (K5 keep). `qa-test-case-designer` and `qa-test-planner`
  Orientation 3 run a read-only consistency check, not a build, so they need no Gate qualifier. The skills' own
  scan-run instructions got no "written, not run" sentence: the scanners are loaded through `qa-security`, whose
  Gate line covers them. "— MANDATORY SECTION" and the `be-shared-session-budget` Step 5 duty do not occur.
  Carried forward: the "(Stage N, forthcoming)" family into the S17 and S18 blocks (`devops/` and `security/`
  still carry it).
  Unverified: nothing was run beyond §4's searches (Gate: none).

### S12 — qa/cicd and qa/reporting

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/cicd/` and `qa/reporting/` pass K1–K9: all six agents carry the Gate line,
`qa-ci-pipelines` is resolved in the three `flaky-test-quarantine` skills, and no Node 20 default
remains.
**Depends on:** —
**Budget:** ~155k, over target. Floor 24k, plan sections 9k, recipe output 6k, six agents 27k, ~13
skills around hits 26k, descriptions 3k, ~19 files modified 28k, read-back 6k, churn ×1.2. The natural
split is between the two folders; the task stays whole because both folders share one finding family
(`qa-ci-pipelines`).
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K1: `qa-ci-pipelines` in `qa/reporting/{dotnet,java,typescript}/skills/flaky-test-quarantine/` (5
  hits), probably the `qa-cicd-<stack>` agents under an old name. Confirm against `qa/cicd/agents/`.
- K4: pipeline and job "stages" here are CI vocabulary (D8), so they stay.
- K6: `Node 20` ×5 and `node:20` ×6 across both folders → Node 24; a CI matrix may keep Node 22.
- K5: `qa/cicd` has 6 all-caps rule words; restate them.
- K2: the Gate line in the three `qa-cicd-*` and three `qa-reporting-*` agents.
- **Not in S12:** `qa/_shared` and `qa/manual` (S11).
- **As built (2026-09-26):** `qa/cicd/` and `qa/reporting/`, one session, not split; the six agents and six
  commands read in full. Gate line added to 6 agents, each as the last Operating-rules bullet
  (`qa-cicd-{dotnet,java,typescript}.md:37`, `qa-reporting-{dotnet,java,typescript}.md:37`). The six commands
  need nothing: each only points at its agent file. 26 files changed.
  Data issues: 44 fixed.
  - K1, 6 hits (the plan counted 5): `qa-ci-pipelines` → `qa-ci-pipelines-<stack>`, matching S6/S8/S10, in
    `flaky-test-quarantine` dotnet `:176`, `:345`, java `:330`, `references/details.md:36`, typescript `:129`,
    `:275`; the trailing "(github-actions / … references)" now reads "(its GitHub Actions, Azure Pipelines and
    GitLab CI references)". The resolver now prints nothing for both folders.
  - K6 Node: `Node 20` ×5 → Node 24 (`ci-pipelines/references/{github-actions,gitlab-ci}.md:3` typescript,
    `flaky-test-quarantine` typescript `:6`, `:48`, `test-reports` typescript `:8`); `node:20` ×6 → `node:24`
    (typescript `gitlab-ci.md:50`, `:51`, `:71`, dotnet `gitlab-ci.md:221`, `test-reports` typescript `:264`,
    `:278`); plus pins the recipe misses: `NODE_VERSION` `'20'`/`"20"` (typescript `github-actions.md:74`,
    `gitlab-ci.md:83`), `'20.x'` (typescript `azure-pipelines.md:58`, `test-reports` typescript `:236`),
    `node-version: '20'` (`test-reports` typescript `:209`). None was a feature boundary.
  - K6 .NET (the recipe misses it): `.NET 8` defaults → .NET 10 (8/9 supported) in `qa-cicd-dotnet` and
    `qa-reporting-dotnet` (description, title, intro), the dotnet `ci-pipelines` and `flaky-test-quarantine`
    titles and stack line; `8.0.x` → `10.0.x`, `sdk:8.0` → `sdk:10.0` and `net8.0/` → `net10.0/` in the three
    dotnet CI references and `test-reports` dotnet. The TFM detection lists (`net8.0/9.0/10.0`) stay.
  - Stale paths: the earlier path rewrite collapsed `ci-pipelines/<host>` into `ci-pipelines`, so 18 "GitHub
    Actions / Azure Pipelines / GitLab CI equivalent → `qa/cicd/<stack>/skills/ci-pipelines`" lines and 9
    "port of / ports from" lines pointed at their own skill; they now name `references/<host>.md`. The same
    rewrite turned the SSM parameter `/qa/api-base-url` into `/qa/<stack>/skills/api-base-url` in the three
    `gitlab-ci.md` files (6 hits); restored. `ci-conventions:8`, `:93` and the three `test-reports` handoffs
    `ci-pipelines/{github-actions,…}` → "`ci-pipelines` (its `references/<ci>.md`)"; `test-reports:20`
    `ui-test-author/<stack>/<stack>` → `ui-test-author/<tool>`; the reporting agents' Step 2 cited a
    `@known-flaky` label no skill defines → "its quarantine tag/category convention".
  Code issues: 22 fixed.
  - K7: Do-NOT clauses added to all 9 skills that lacked one (three `ci-pipelines`, three
    `flaky-test-quarantine`, three `test-reports`), each naming the sibling; the six reporting skills now open
    with "Use when". Longest now: `ci-conventions` 494, `ci-pipelines` 490; agents 537–587.
  - K5: `MUST` ×6 (YAML comments in the three `github-actions.md`) and `NEVER` ×3 (code comments in the three
    `flaky-test-quarantine`) → lower case. No `— MANDATORY SECTION` or `be-shared-session-budget` duty occurs.
  - K8: `qa-cicd-typescript` Step 1 "`npx tsc --noEmit`" and "Node + npm/pnpm", `qa-reporting-typescript`
    Step 1 "`npx vitest run`" → the project's own scripts, run with the package manager `packageManager` names.
  - "written, not run": one sentence in each `ci-pipelines` SKILL.md's shared rules (covers the nine
    references' Generation steps) and before each `test-reports` Handoffs (its smoke step).
  - `qa-cicd-*` Orientation 2 said "Recover, don't author" twice; merged.
  Logical conflicts: 5 fixed.
  - The three `qa-cicd-*` agents said "GitHub Actions by the library default … Gradle Kotlin DSL for new
    projects" while `ci-pipelines` calls Azure Pipelines the house default (CLAUDE.md) and `ci-conventions`
    lets the project's CI decide; now "the project's existing CI host decides — Azure Pipelines is the house
    default for a new pipeline". The Gradle clause is gone from the dotnet and typescript agents too.
  - `test-reports` ×3 put `continue-on-error` / `continueOnError` / `|| true` on the test step and recommended
    it in "What NOT to do", against `ci-conventions`; the test step now fails the build, and the GitHub publish
    step gains `always() &&`, Azure `PublishHtmlReport` gains `condition: succeededOrFailed()` and the GitLab
    publish rule gains `when: always` so the report still publishes. `ci-conventions:46`, `:83` state the
    quarantine lane as the one non-gating exception (D16).
  - "Run what you write" (`qa-reporting-*:33`) and "Validate what you write" (`qa-cicd-*:35`) gain "outside a
    `Gate: none` plan task"; Orientation 3's "every run regardless of the (gate's) verdict" gains the same in
    all six.
  Cleanup: none. The K9 file recipe finds nothing; no tracked junk; every SKILL.md, agent and command in both
  folders is listed in the marketplace and every listed path exists.
  Kept on purpose: K3 hits are the fixed workspace sentence and CI branch filters / `gh-pages`. K4 hits are
  pipeline stages (D8), Gradle/NUnit shard "slices" and Allure's "user-story slice". K8 hits left are CI YAML
  samples (`dotnet test`, `./gradlew test`, `pnpm install --frozen-lockfile`, `npm ci`) and the
  "never bare `npm install` in CI" rules. `green` hits are exit criteria, gate-evidence examples and
  anti-green-washing rule text (K2 keep). The qa agent descriptions still open with the role, like every
  qa-* agent S5–S11 left.
  Carried forward: the .NET 8 default family into S13, S14 and S17, and the `continue-on-error` family into
  S13 and S17.
  Unverified: nothing was run beyond §4's searches and the K1/K7 scripts (Gate: none).

### S13 — frontend and auth

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `frontend/blazor/`, `frontend/react/` (not `vendor/`) and the three published `auth/`
folders pass K1–K9: `fe-blazor` and `fe-react` carry the Gate line, and `fe-react` and `data-grid` fit
their description budgets, and `frontend/PLAN.md` is filed per §5.
**Depends on:** —
**Budget:** ~145k — floor 24k, plan sections 9k, recipe output 6k, two agents and commands 16k, ~13
skills around hits 26k, descriptions 13k, ~15 files modified 23k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K1: `qa-test-quality-check-typescript` in `frontend/react/skills/component-testing/SKILL.md` (same
  target as S4's; its As built note has the real name).
- K6: `Node 18` ×2, `Node 20` ×2 and `React 17` ×1 in `frontend/react`. `fe-react-migration`
  legitimately names React 17 and 18 as sources; keep those.
- K7: `frontend/react/skills/data-grid` 688 → ≤ 500; `fe-react` 663 → ≤ 650.
- K5: the frontend rules in CLAUDE.md (RSC by default, one styling authority, three-state regions)
  are house rules, not dated emphasis. Keep them bold where the skill states them.
- `data-testid` and the other `data-*` tokens are HTML attributes, not names.
- K9: `frontend/PLAN.md` (2026-07-12) says "Phase 7 complete for React" with a cross-stack port
  remaining. Check whether the Blazor port landed: if so it is landed, otherwise it moves to
  `docs/plans/` as live. Either way it moves as `frontend-PLAN.md` (§5). `frontend/react-native/{PLAN,HANDOFF}.md` stay (D5).
- **Not in S13:** `auth/cognito-*` (under construction, D5); `design/` (S14).
- **As built (2026-09-26):** `frontend/blazor/`, `frontend/react/` (not `vendor/`), `auth/_shared/`,
  `auth/auth0-blazor/`, `auth/auth0-react/`. The two agents and three commands were read in full; the
  commands needed no change. Gate line added to 2 agents, each as the last Operating-rules bullet
  (`fe-blazor.md:40`, `fe-react.md:40`). 43 files changed plus the plan move.
  Data issues: 10 fixed.
  - K1: `qa-test-quality-check-typescript` → `react/skills/component-testing:243` now says no TypeScript
    mutation-testing skill exists and cites `qa-test-quality-check-java` (PIT) and
    `qa-test-quality-check-dotnet` (Stryker.NET), as `backend/node/skills/unit-testing` does. The resolver
    now prints only HTML attributes (`data-testid`, `data-theme`, `data-table`, `data-bs-target`,
    `data-enhance`, all already in §7's `ALLOW`).
  - Stale paths (6): `blazor/skills/forms:201`, `:387` `qa/api-test-author/generator/dotnet` →
    `qa/dotnet/skills/api-test-author/writer`; `blazor/skills/performance:3` qa `performance/nbomber` →
    `qa-load-testing-dotnet`; `blazor/skills/component-writer:423` `qa/api-models/dotnet` →
    `qa/dotnet/skills/api-models`; `auth0-blazor:357` and `auth0-react:389` `qa/ui-test-author/playwright`
    → `qa/{dotnet,typescript}/skills/ui-test-author/playwright`. A script that checks every cited repo path
    in the five folders now finds none missing.
  - K6 .NET (the recipe misses it): `auth/auth0-blazor:8`, `:12` "target .NET 8" → .NET 10 (8/9
    supported); `:33` "Interactive Auto in .NET 8" → ".NET 8+". The `.NET 8/9/10` ranges in every Blazor
    description stay (they are the supported lanes, not a default).
  Code issues: 51 fixed.
  - K7: `fe-react` 663→649 (dropped "/ RSC" from the stack line and "page or" from a trigger);
    `data-grid` 688→495 (feature list condensed, two trigger phrases cut; Do-NOT clause kept). Every
    other description in the five folders already fit its budget and had its Do-NOT clause.
  - K5: "Announce at start" dropped from `react/skills/standards-audit:14`; `ALWAYS` ×4 and `MUST` ×1 in
    code comments lowercased (`blazor/skills/realtime:67`, `react/skills/{component-testing:97,realtime:85,routing:145,seo:63}`).
    No "— MANDATORY SECTION" occurs in either agent.
  - K2 for skills: the "written, not run" sentence after `## Validation` in all 32 frontend SKILL.md
    files that have one, in `react/skills/migration`'s Verification, and "Outside a `Gate: none` plan
    task" on the build step of both `test-ids` Procedures.
  - K8: `pnpm tsc`/`pnpm lint`/`pnpm test`/`pnpm build`/`pnpm dev` in the Validation lists of
    `react/skills/{component-writer,component-library,styling,realtime,data-fetching,project-setup}` and
    `test-ids` step 4 → the project's own scripts, run with the package manager `packageManager` names.
  - K4: `react/skills/standards-audit:188` "EXTEND (a slice)" → "(a missing capability)".
  Logical conflicts: 5 fixed. "Run what you write" and Orientation 3's "every run regardless of the
  verdict" gain "outside a `Gate: none` plan task" in both agents; the closing duty "per
  `be-shared-session-budget` Step 5" now points at the plan's `## Close-out — every task` section in both.
  `react/skills/migration:10`, `:31`, `:149` told the session to work "on its own branch" (K3); now "as its
  own change", with the fixed workspace sentence, and `fe-react.md:17` matches. `migration:33` recommended
  Node 18 as React 19's floor; it now names Node 22/24 as the house floor and flags 18/20 as EOL.
  Cleanup: `frontend/PLAN.md` → `docs/plans/frontend-PLAN.md` (live). Its Phase 7 Blazor port has not
  landed: `blazor/skills/error-handling` has no stale state or failure scoping, `test-ids` has no
  `<Region>.Stale`, and there is no `blazor/skills/standards-audit`. No tracked junk. Every SKILL.md,
  agent and command in the five folders is listed in the marketplace and every listed path exists.
  `frontend/_shared/product-analytics` is deliberately unpublished (no plugin lists it, §2 does not
  scope it).
  Kept on purpose: the K6 hits in `frontend/react` are flag lines (`standards-audit` checklist A6 flags
  Node 20 and React 17 as EOL; `migration:33` names the upstream Node floor) — D13. K3 hits are code
  branches and the audit report's `**Branch:**` field; K4 hits are "model slice", Zustand slices, a
  `Stage` field and "vertical slice" (D8). Remaining `pnpm add`/`pnpm create`/`pnpm dlx` lines are install
  samples. `green` hits are exit criteria, "contract test green" validation rows and the colour green.
  `ui-rules` ×2 and `standards-audit` open with "Use on"/"Use to", a trigger, so they stay.
  `oidc-concepts:3` still points at `auth/cognito-*`, a folder that exists but is under construction.
  Legacy files still cite `frontend/PLAN.md` (`CONFORMANCE-AUDIT-PLAN.md:45`,
  `docs/plans/implemented/UNIT-TESTING-PLAN.md:126`, `frontend/react-native/PLAN.md:68`); per D7 they are
  not edited.
  Carried forward: nothing new. Unverified: nothing was run beyond §4's searches, the K1/K7 scripts and
  a path-existence script (Gate: none). Left for the user: nothing.

### S14 — design and observability

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `design/` (not the vendored corpus) and `observability/` pass K1–K9: nine design
descriptions and `design-auditor` fit their budgets, four agents carry the Gate line, and
`docs/plans/design-ux-improvements.md` and `docs/research/ui-ux-practice-2026.md` are filed per §5.
**Depends on:** —
**Budget:** ~135k — floor 24k, plan sections 9k, recipe output 6k, four agents and design commands
25k, ~5 skills around hits 10k, descriptions 6k, ~17 files modified 26k, the design plan and research
note headers 5k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- D5: `design/ui-ux-pro-max/data/` and `scripts/` are vendored; never edit them.
  `design/ui-ux-pro-max/SKILL.md` is house-written (`design/ATTRIBUTIONS.md`, "SKILL.md rewritten in
  house style"), so its description is yours to trim.
- K7: `ux-patterns` 824, `ui-ux-pro-max` 767, `visual-identity` 756, `ai-experience` 673, `motion` 667,
  `ux-review` 657, `landing-patterns` 643, `accessible-by-design` 624, `ethical-patterns` 594 → ≤ 500;
  `design-auditor` 875 → ≤ 650.
- K1: `design-audit` in `design/agents/design-auditor.md`.
- K5: never reword a design fact the corpus settles.
- K6: `Node 20` ×4 in `observability/` (3 files) → Node 24.
- K2: the Gate line in `design-auditor` and the three `observability-engineer-*` agents.
- K9: `docs/plans/design-ux-improvements.md` says T1–T8 executed 2026-08-27. Spot-check three of its
  deliverables, then file it. `docs/research/ui-ux-practice-2026.md` stays if anything cites it.
- **Not in S14:** frontend (S13).

### S15 — data and training-data

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `data/` and `training-data/` pass K1–K9 with three agents carrying the Gate line;
`ai-development/claude-api` matches `anthropics/skills` `skills/claude-api` at the current `main`
except for a description of ≤ 500 chars; `docs/plans/fine-tuning-house-models.md` is filed per §5.
**Depends on:** —
**Budget:** ~140k — floor 24k, plan sections 9k, recipe output 6k, three agents 16k, ~11 skills around
hits 22k, descriptions 5k, ~13 files modified 20k, the research note header 2k, the re-vendor (clone,
`git diff --stat`, a skim of the new `SKILL.md`, the description fork) 8k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K1: `data-modeling` ×2 in `data/agents/data-architect.md`. Decide whether it is a skill name or a
  concept; only a name needs resolving.
- K4: expand/contract migration "phases" are domain vocabulary (D8), so they stay.
- K5: `data/` has 10 all-caps rule words. Keep migration-safety rules (online-safe DDL, never drop
  before backfill) as hard rules with their reason.
- D11 re-vendor: shallow-clone `https://github.com/anthropics/skills`, replace
  `ai-development/claude-api/` with its `skills/claude-api/` (`rsync -a --delete`), then put the
  description back under 500 chars. Start from today's house description (`fc94a9a`); keep upstream's
  trigger phrases and Do-NOT scope. Record the upstream commit SHA and date, the file count changed and
  the new "cached:" date in the As built note, so G1 can update README's attribution row.
- K9: `docs/plans/fine-tuning-house-models.md` is a research note with nothing built. It stays in
  `docs/plans/` (O6).
- K2: the Gate line in `data-architect` and both `training-data` agents.
- **Not in S15:** `business-analysis`, `tooling` (S16).

### S16 — business-analysis and tooling

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `business-analysis/` and `tooling/` pass K1–K9: three agents carry the Gate line, and
the six over-budget descriptions fit.
**Depends on:** —
**Budget:** ~135k — floor 24k, plan sections 9k, recipe output 6k, three agents and commands 19k, ~9
skills around hits 18k, descriptions 3k, ~18 files modified 27k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K7: `ba-epic-writer` 515, `tooling/_shared/capability-contract` 610, `tooling/skills/mcp-builder` 572,
  `tooling/skills/cli-builder` 509 → ≤ 500; `requirements-author` 657 and `tooling-engineer` 693 →
  ≤ 650.
- K4: business-analysis uses "phase" 17 times. Keep it where it describes a business process;
  rename it where it names planned work.
- `ba-project-memory`'s links (`areas/ordering.md`, `entities/order.md`, …) are deliberate examples;
  leave them.
- K2: the Gate line in `business-analyst`, `requirements-author` and `tooling-engineer`.
- **Not in S16:** the planning lane (S2), which `requirements-author` hands to.

### S17 — devops

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `devops/` passes K1–K9: `devops-engineer`, `devops-auditor` and `infra-security-tester`
carry the Gate line, the two dangling names are resolved, and no Node 20 or Python 3.10 default remains.
**Depends on:** —
**Budget:** ~135k — floor 24k, plan sections 9k, recipe output 6k, three agents and commands 21k, ~11
skills around hits 22k, descriptions 4k, ~14 files modified 21k, read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K1: `devops-conformance` in `devops/agents/devops-auditor.md`; `qa-security-testing-permission-testing`
  in `devops/k8s-security/SKILL.md`.
- K6: `Node 20` ×8 across the deployment, pipeline and docker skills → Node 24 (a matrix may keep 22);
  `Python 3.10` in `cloud-posture` → 3.13. The version-policy note in CLAUDE.md applies: managed
  runtimes lag, so pin the newest runtime the platform offers and say so.
- K4: pipeline stages are CI vocabulary (D8), so they stay.
- K5: "Never apply IaC to a live environment without explicit confirmation" is a hard safety rule;
  keep it bold, stated once.
- K3: git-branching guidance inside a CI skill is domain content, so it stays.
- **Not in S17:** `security/` (S18).

### S18 — security

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `security/` passes K1–K9: four agents carry the Gate line, the six over-budget skill
descriptions and two agent descriptions fit, `SECURITY-EXPANSION-PLAN.md` is filed and
`docs/plans/STAGE3-PROGRESS.md` is removed.
**Depends on:** —
**Budget:** ~135k — floor 24k, plan sections 9k, recipe output 6k, four agents and commands 29k, ~3
skills around hits 6k, descriptions 4k, ~14 files modified 21k, the two legacy files' headers 3k,
read-back 6k, churn ×1.2
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py` or §7's script.

- K7: `detection-validation` 778, `atomic-simulation` 749, `detection-engineering` 711,
  `secrets-hardening` 678, `compliance-evidence-mapping` 664, `security-hardening` 654 → ≤ 500;
  `security-architect` 947 and `purple-team-engineer` 909 → ≤ 650.
- K5: rules of engagement, written authorization, scope files and production sign-off are hard safety
  rules. Keep them bold, once each, with their reason.
- K4: kill-chain "phases" are domain vocabulary (D8), so they stay.
- K9: `SECURITY-EXPANSION-PLAN.md` says complete 2026-08-20. Confirm the `penetration-testing` and
  `security-governance` plugins exist in `marketplace.json`, then `git mv` it into
  `docs/plans/implemented/`. `docs/plans/STAGE3-PROGRESS.md` is that plan's uncommitted build log:
  `git rm` it. `docs/audits/002-security-domain-audit.md` stays.
- K2: the Gate line in all four agents.
- **Not in S18:** `devops/`'s infra-security skills (S17).

### G1 — root cleanup, the docs, and the gate

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** §7 passes: the marketplace parses, the library check prints `OK`, and
`tools/token-audit.py` lists no description violation with body and file violations ≤ 160. The root
and `docs/plans/` are filed per §5, and README, `docs/skills-catalog.md` and CLAUDE.md match what S1–S18
landed.
**Depends on:** S1–S18 (every As built note).
**Budget:** ~120k — floor 24k, plan §5, §7, this block and all As built notes 16k, six legacy plan
headers 6k, README and catalog around the changed names 22k, ~20 moves, removals and doc edits 20k,
the gate and its fix loop 12k, churn ×1.2
**Gate:** the plan's only gate, §7, in run order:

```bash
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
python3 "${TMPDIR:-/tmp}/library-check.py"
python3 tools/token-audit.py
```

Fix what it finds rather than handing it back; a failure may belong to any S task, so attribute it in
the As built note.

- §5 root inventory:
  - `AGENT-ORIENTATION-CACHE-PLAN.md` → `docs/plans/implemented/`.
  - `CONFORMANCE-AUDIT-PLAN.md`, `MODEL-PORTABILITY-PLAN.md` and `TOKEN-OPTIMIZATION-PLAN.md` →
    `docs/plans/` (live).
  - `docs/plans/token-optimization-progress.md`: fold today's token-audit counts into
    `TOKEN-OPTIMIZATION-PLAN.md`'s status, then `git rm` the tracker.
  - `meta/PLAN.md`: file it as `docs/plans/implemented/meta-PLAN.md` only if its own status says
    complete; otherwise leave it and list it.
  - `git rm -r tools/mission-control/.next` and add `tools/mission-control/` to `.gitignore`.
    `tools/MISSION-CONTROL-MOVED.md` stays.
  - `git rm --cached .claude/settings.local.json` and add it to `.gitignore`.
- Docs: grep README, `docs/skills-catalog.md` and CLAUDE.md for every name, count and path the As
  built notes say changed, and fix those places only. The catalog is 175 KB; do not read it whole.
- README's attribution row for `ai-development` gets the upstream SHA and date S15 recorded.
- Record in the As built note the gate output lines and every `ALLOW`/`LINK_EXAMPLES` addition with its
  reason. The final `Status:` names the next two plans (O7): conformance audits from
  `CONFORMANCE-AUDIT-PLAN.md` and size optimization from `TOKEN-OPTIMIZATION-PLAN.md`.
- This task deletes the last prompt block, so Close-out step 6 files this plan into
  `docs/plans/implemented/`.

## Close-out — every task

Before you stop, in this order, in this file:

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
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them in order, one Plan Queue session each; every block is complete on its own. Only G1 runs the
gate (§7). No other block runs `tools/token-audit.py` or §7's script. No block renames a skill or
agent, edits a vendored tree (D5), or touches `docs/agent-context/`.

Two traps S1 hit that apply to every block. **Unattended sessions deny some shell forms:** a Bash
command with brace expansion or `$VAR` expansion, running a `.sh` file, and writing outside the
worktree (including `/tmp`) were all refused. What worked: save §4's resolver and K7 report as `.py`
files in an untracked scratch folder inside the worktree, run them with `python3 <file> <dir>…`, run the
greps as plain single `grep -rEn … <dirs>` commands, and delete the scratch folder before committing.
**Never backtick a plugin name** (`qa-dotnet`, `devops`, …) that is not also a skill, agent or folder
name: the K1 resolver flags it (D12).

| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| S1 | `docs` | `general-purpose` | — | ~110k |
| S2 | `docs` | `general-purpose` | — | ~135k |
| S3 | `docs` | `general-purpose` | — | ~130k |
| S4 | `docs` | `general-purpose` | — | ~145k |
| S5 | `docs` | `general-purpose` | — | ~130k |
| S6 | `docs` | `general-purpose` | — | ~130k |
| S7 | `docs` | `general-purpose` | — | ~130k |
| S8 | `docs` | `general-purpose` | — | ~130k |
| S9 | `docs` | `general-purpose` | — | ~140k |
| S10 | `docs` | `general-purpose` | — | ~140k |
| S11 | `docs` | `general-purpose` | — | ~120k |
| S12 | `docs` | `general-purpose` | — | ~155k |
| S13 | `docs` | `general-purpose` | — | ~145k |
| S14 | `docs` | `general-purpose` | — | ~135k |
| S15 | `docs` | `general-purpose` | — | ~140k |
| S16 | `docs` | `general-purpose` | — | ~135k |
| S17 | `docs` | `general-purpose` | — | ~135k |
| S18 | `docs` | `general-purpose` | — | ~135k |
| G1 | `docs` | `general-purpose` | S1–S18 | ~120k |

S1 to S13 have landed, and their prompts are deleted; the 6 prompts from S14 to G1 are live.

---

### S14 — design and observability (general-purpose, docs)

````
You are `general-purpose`. Task S14 of docs/plans/001-library-conformance-sweep.md: bring design/ (not
the vendored corpus) and observability/ in line with the plan's checks K1–K9.

Deliverable: design/ (not the vendored corpus) and observability/ pass K1–K9: nine design descriptions
and design-auditor fit their budgets, four agents carry the Gate line, and
docs/plans/design-ux-improvements.md and docs/research/ui-ux-practice-2026.md are filed per §5.

Read, in this order:
1. CLAUDE.md, especially "When uncertain" (the design corpus wins on design facts).
2. The plan: §2, §3, §4, §5, §6 (the S14 rows), D1–D11, task S14.
3. design/ATTRIBUTIONS.md.
4. CONTRIBUTING.md.
5. design/agents/*.md, design/commands/*.md and observability/agents/*.md in full.
6. The plan's "Close-out — every task".

Do:
- Run §4's recipes with DIR=design, then DIR=observability.
- K7: the nine design skills in §6.2 → ≤ 500; design-auditor 875 → ≤ 650.
  design/ui-ux-pro-max/SKILL.md is house-written, so trim it too.
- K1: `design-audit` in design/agents/design-auditor.md.
- K6: Node 20 ×4 in observability → Node 24.
- K2: the Gate line in design-auditor and the three observability-engineer agents.
- K9: spot-check three deliverables of docs/plans/design-ux-improvements.md, then file it per §5.
  docs/research/ui-ux-practice-2026.md stays if anything cites it; otherwise list it for the user.

Traps:
- Agent sentences S3/S4 fixed in backend recur in 28 agents across S5–S17; fix them where your
  agents carry them:
  - "— MANDATORY SECTION" on the brownfield heading is dropped (K5).
  - The orientation pass's "every run regardless of the gate's verdict" (the cache gate) gains
    "outside a `Gate: none` plan task".
  - A closing duty "per `be-shared-session-budget` Step 5" now reads "per the plan's
    `## Close-out — every task` section (plan format §7)".
  - A skill's Validation / Verify list gets one sentence: inside a `Gate: none` plan task it runs
    none of the checks and reports "written, not run".
  - K8: a hardcoded `pnpm …` / `npm …` in an instruction becomes the project's own script, run with
    the package manager `packageManager` names.
- Never edit design/ui-ux-pro-max/data/ or scripts/.
- A trimmed description keeps the Do-NOT clause that routes between the 16 design skills; those
  clauses are what stop them colliding.
- (S9/S10) Node 20 is sometimes a feature boundary, not a default (native `WebSocket`/`EventSource`,
  global `fetch`/`FormData`/`Blob`): such a line says Node 22/24 have the feature and flags a detected
  Node 20 as EOL, rather than reading "Node 24" after the substitution. A CI `node-version: 20` moves to 24.
- (S12) K6's recipe does not catch .NET 8 defaults (observability-engineer-dotnet): grep
  `\.NET 8\b|8\.0\.x|sdk:8\.0|net8\.0/` too. A default or sample moves to .NET 10; a TFM detection list
  (`net8.0/9.0/10.0`) stays.

Gate: none — this plan gates once, in G1. Do not run tools/token-audit.py or §7's script.

Commit: `chore(sweep S14): design and observability`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S15 — data and training-data (general-purpose, docs)

````
You are `general-purpose`. Task S15 of docs/plans/001-library-conformance-sweep.md: bring data/ and
training-data/ in line with the plan's checks K1–K9.

Deliverable: `data/` and `training-data/` pass K1–K9 with three agents carrying the Gate line;
`ai-development/claude-api` matches `anthropics/skills` `skills/claude-api` at the current `main`
except for a description of ≤ 500 chars; `docs/plans/fine-tuning-house-models.md` is filed per §5.

Read, in this order:
1. CLAUDE.md, especially the data-engine versions in the version policy.
2. The plan: §1 (the claude-api row), §2, §3, §4, §5, §6 (the S15 rows), D1–D11, O5–O6, task S15.
3. CONTRIBUTING.md.
4. data/agents/*.md and training-data/agents/*.md in full.
5. The plan's "Close-out — every task".

Do:
- Run §4's recipes with DIR=data, then DIR=training-data.
- K1: `data-modeling` ×2 in data/agents/data-architect.md. Resolve it only if it is meant as a skill
  name.
- K5: restate data/'s 10 all-caps rule words; migration-safety rules stay hard rules with their
  reason.
- D11 re-vendor, from the repo root:
    git clone --depth 1 https://github.com/anthropics/skills "${TMPDIR:-/tmp}/anthropic-skills"
    rsync -a --delete "${TMPDIR:-/tmp}/anthropic-skills/skills/claude-api/" ai-development/claude-api/
  Then restore a ≤ 500-char description in ai-development/claude-api/SKILL.md: start from today's
  house description (git show fc94a9a) and keep upstream's trigger phrases and Do-NOT scope. Record the
  upstream SHA and date, `git diff --stat` totals and the new "cached:" date in the As built note.
- K9: docs/plans/fine-tuning-house-models.md stays in docs/plans/ (O6).
- K2: the Gate line in data-architect and both training-data agents.

Traps:
- Agent sentences S3/S4 fixed in backend recur in 28 agents across S5–S17; fix them where your
  agents carry them:
  - "— MANDATORY SECTION" on the brownfield heading is dropped (K5).
  - The orientation pass's "every run regardless of the gate's verdict" (the cache gate) gains
    "outside a `Gate: none` plan task".
  - A closing duty "per `be-shared-session-budget` Step 5" now reads "per the plan's
    `## Close-out — every task` section (plan format §7)".
  - A skill's Validation / Verify list gets one sentence: inside a `Gate: none` plan task it runs
    none of the checks and reports "written, not run".
  - K8: a hardcoded `pnpm …` / `npm …` in an instruction becomes the project's own script, run with
    the package manager `packageManager` names.
- Stale path (S5): `data/_shared/slow-query-fixes/SKILL.md:117` cites
  `qa/<stack>/skills/api-test-author/reviewer`; the folder is `…/api-test-author/review`.
- Expand/contract "phases" are domain vocabulary (D8).
- Never up-level a data engine version in a probe-first recipe. The recipes are keyed to the live
  server's version.
- The re-vendored files are upstream's (D11): do not apply K1–K9 to them, and do not edit anything
  but the description. The marketplace path `./ai-development/claude-api` must still exist afterwards.
- If the clone fails (no network), keep the prompt block with a `Blocked on network` line and your
  other work landed (Close-out step 4), rather than hand-copying files.

Gate: none — this plan gates once, in G1. Do not run tools/token-audit.py or §7's script.

Commit: `chore(sweep S15): data and training-data`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S16 — business-analysis and tooling (general-purpose, docs)

````
You are `general-purpose`. Task S16 of docs/plans/001-library-conformance-sweep.md: bring
business-analysis/ and tooling/ in line with the plan's checks K1–K9.

Deliverable: business-analysis/ and tooling/ pass K1–K9: three agents carry the Gate line, and the six
over-budget descriptions fit.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3, §4, §6 (the S16 rows), D1–D11, task S16.
3. CONTRIBUTING.md.
4. business-analysis/agents/*.md, business-analysis/commands/*.md and tooling/agents/*.md in full.
5. The plan's "Close-out — every task".

Do:
- Run §4's recipes with DIR=business-analysis, then DIR=tooling.
- K7: ba-epic-writer 515, tooling/_shared/capability-contract 610, tooling/skills/mcp-builder 572,
  tooling/skills/cli-builder 509 → ≤ 500; requirements-author 657 and tooling-engineer 693 → ≤ 650.
- K4: 17 "phase" hits in business-analysis. Keep business-process phases; rename planned-work phases
  to tasks.
- K2: the Gate line in business-analyst, requirements-author and tooling-engineer.

Traps:
- Agent sentences S3/S4 fixed in backend recur in 28 agents across S5–S17; fix them where your
  agents carry them:
  - "— MANDATORY SECTION" on the brownfield heading is dropped (K5).
  - The orientation pass's "every run regardless of the gate's verdict" (the cache gate) gains
    "outside a `Gate: none` plan task".
  - A closing duty "per `be-shared-session-budget` Step 5" now reads "per the plan's
    `## Close-out — every task` section (plan format §7)".
  - A skill's Validation / Verify list gets one sentence: inside a `Gate: none` plan task it runs
    none of the checks and reports "written, not run".
  - K8: a hardcoded `pnpm …` / `npm …` in an instruction becomes the project's own script, run with
    the package manager `packageManager` names.
  - The operating rule "Run what you write — a step whose code never executed does not pass its
    gate" becomes "Run what you write, outside a `Gate: none` plan task — …" (S5; every qa agent
    carries it).
- ba-project-memory's links (areas/ordering.md, entities/order.md, …) are deliberate examples.
- requirements-author hands off to /dev-plan-solution (S2's lane). Keep that handoff name exact.

Gate: none — this plan gates once, in G1. Do not run tools/token-audit.py or §7's script.

Commit: `chore(sweep S16): business-analysis and tooling`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S17 — devops (general-purpose, docs)

````
You are `general-purpose`. Task S17 of docs/plans/001-library-conformance-sweep.md: bring devops/ in
line with the plan's checks K1–K9.

Deliverable: devops/ passes K1–K9: devops-engineer, devops-auditor and infra-security-tester carry the
Gate line, the two dangling names are resolved, and no Node 20 or Python 3.10 default remains.

Read, in this order:
1. CLAUDE.md, especially the version policy's DevOps note (managed runtimes lag the language).
2. The plan: §2, §3, §4, §6 (the S17 rows), D1–D11, task S17.
3. CONTRIBUTING.md.
4. devops/agents/*.md and devops/commands/*.md in full.
5. The plan's "Close-out — every task".

Do:
- Run §4's recipes with DIR=devops.
- K1: `devops-conformance` (devops/agents/devops-auditor.md),
  `qa-security-testing-permission-testing` (devops/k8s-security/SKILL.md).
- K6: Node 20 ×8 → Node 24, or the newest runtime the platform offers, said so; Python 3.10 in
  cloud-posture → 3.13.
- K2: the Gate line in all three agents.

Traps:
- Agent sentences S3/S4 fixed in backend recur in 28 agents across S5–S17; fix them where your
  agents carry them:
  - "— MANDATORY SECTION" on the brownfield heading is dropped (K5).
  - The orientation pass's "every run regardless of the gate's verdict" (the cache gate) gains
    "outside a `Gate: none` plan task".
  - A closing duty "per `be-shared-session-budget` Step 5" now reads "per the plan's
    `## Close-out — every task` section (plan format §7)".
  - A skill's Validation / Verify list gets one sentence: inside a `Gate: none` plan task it runs
    none of the checks and reports "written, not run".
  - K8: a hardcoded `pnpm …` / `npm …` in an instruction becomes the project's own script, run with
    the package manager `packageManager` names.
- Pipeline "stages" and git-branching guidance inside CI skills are domain content (D8, K3 keep).
- "Never apply IaC to a live environment without explicit confirmation" stays bold, once.
- (S9/S10) Node 20 is sometimes a feature boundary, not a default (native `WebSocket`/`EventSource`,
  global `fetch`/`FormData`/`Blob`): such a line says Node 22/24 have the feature and flags a detected
  Node 20 as EOL, rather than reading "Node 24" after the substitution. A CI `node-version: 20` moves to 24.
- (S11) SECURITY-EXPANSION-PLAN's "Stage N" / "(Stage N, forthcoming)" labels name units of planned work
  (K4) and point at lanes that have since landed. Drop the label and keep the lane name, after checking
  the named skill, agent or plugin exists (e.g. S11 made "`penetration-testing` *(Stage 3, forthcoming)*"
  read "`penetration-testing`"). Known hits: `devops/agents/infra-security-tester.md`,
  `devops/commands/infra-security-tester.md` and eight devops skills or references.
- (S12) K6's recipe does not catch .NET 8 defaults: grep `\.NET 8\b|8\.0\.x|sdk:8\.0|net8\.0/` too. A
  default, CI pin or sample path moves to .NET 10 (`10.0.x`, `sdk:10.0`); a TFM detection list stays, and
  a managed runtime that lags stays pinned to the newest one the platform offers (CLAUDE.md).
- (S12) A CI sample that puts `continue-on-error` / `continueOnError` / `allow_failure` / `|| true` on a
  gating test step lets a red suite pass; the test step fails the build and the upload/publish steps run
  with `if: always()` / `condition: succeededOrFailed()` / `when: always`.

Gate: none — this plan gates once, in G1. Do not run tools/token-audit.py or §7's script.

Commit: `chore(sweep S17): devops`.
Close out per the plan's "Close-out — every task" before you stop.
````

### S18 — security (general-purpose, docs)

````
You are `general-purpose`. Task S18 of docs/plans/001-library-conformance-sweep.md: bring security/ in
line with the plan's checks K1–K9 and file its legacy plan.

Deliverable: security/ passes K1–K9: four agents carry the Gate line, the six over-budget skill
descriptions and two agent descriptions fit, SECURITY-EXPANSION-PLAN.md is filed and
docs/plans/STAGE3-PROGRESS.md is removed.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §3, §4, §5, §6 (the S18 rows), D1–D11, task S18.
3. CONTRIBUTING.md.
4. security/agents/*.md and security/commands/*.md in full.
5. The plan's "Close-out — every task".

Do:
- Run §4's recipes with DIR=security.
- K7: the six security skills in §6.2 → ≤ 500; security-architect 947 and purple-team-engineer 909 →
  ≤ 650.
- K2: the Gate line in all four agents.
- K9: confirm penetration-testing and security-governance are in .claude-plugin/marketplace.json, then
  `git mv SECURITY-EXPANSION-PLAN.md docs/plans/implemented/` and
  `git rm docs/plans/STAGE3-PROGRESS.md`. docs/audits/002-security-domain-audit.md stays.

Traps:
- Rules of engagement, written authorization, scope files and production sign-off are hard safety
  rules. Keep them bold, once each, with their reason; K5 must not soften them.
- Kill-chain "phases" are domain vocabulary (D8).
- (S11) SECURITY-EXPANSION-PLAN's "Stage N" / "(Stage N, forthcoming)" labels name units of planned work
  (K4) and point at lanes that have since landed. Drop the label and keep the lane name, after checking
  the named skill, agent or plugin exists. Known hits: `security/agents/{penetration-tester,security-architect}.md`,
  `security/commands/security-test-planner.md`, `initial-access`, `detection-engineering`,
  `security-hardening`, `pentest-reporting`. SECURITY-EXPANSION-PLAN itself is filed unedited (D7).
- `docs/plans/implemented/` already exists (S2 created it).

Gate: none — this plan gates once, in G1. Do not run tools/token-audit.py or §7's script.

Commit: `chore(sweep S18): security`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — root cleanup, the docs, and the gate (general-purpose, docs)

````
You are `general-purpose`. Task G1 of docs/plans/001-library-conformance-sweep.md: file the root's old
plans, reconcile README, the catalog and CLAUDE.md with what S1–S18 landed, and run the plan's only
gate, fixing what it finds.

Deliverable: §7 passes: the marketplace parses, the library check prints `OK`, and
tools/token-audit.py lists no description violation with body and file violations ≤ 160. The root and
docs/plans/ are filed per §5, and README, docs/skills-catalog.md and CLAUDE.md match what S1–S18
landed.

Read, in this order:
1. CLAUDE.md.
2. The plan: §5, §7, D1–D11, O5–O8, task G1, every As built note on S1–S18.
3. The first 15 lines of each root legacy plan: AGENT-ORIENTATION-CACHE-PLAN.md,
   CONFORMANCE-AUDIT-PLAN.md, MODEL-PORTABILITY-PLAN.md, TOKEN-OPTIMIZATION-PLAN.md, meta/PLAN.md.
4. The plan's "Close-out — every task".

Do:
- §5 root inventory:
  - `git mv AGENT-ORIENTATION-CACHE-PLAN.md docs/plans/implemented/`.
  - `git mv CONFORMANCE-AUDIT-PLAN.md MODEL-PORTABILITY-PLAN.md TOKEN-OPTIMIZATION-PLAN.md docs/plans/`.
  - Fold today's token-audit counts into TOKEN-OPTIMIZATION-PLAN.md's status, then
    `git rm docs/plans/token-optimization-progress.md`.
  - meta/PLAN.md: file it as docs/plans/implemented/meta-PLAN.md only if its own status says complete.
  - `git rm -r tools/mission-control/.next`; add `tools/mission-control/` to .gitignore; keep
    tools/MISSION-CONTROL-MOVED.md.
  - `git rm --cached .claude/settings.local.json`; add it to .gitignore.
- Docs: grep README.md, docs/skills-catalog.md and CLAUDE.md for every name, count and path the As
  built notes changed, and fix those places. Grep for root plan filenames too; they moved. README's
  ai-development attribution row gets the upstream SHA and date from S15's As built note.
- Final Status (Close-out steps 5–6) names the next plans (O7): conformance audits and size
  optimization.
- Gate, in run order. Save §7's script as "${TMPDIR:-/tmp}/library-check.py", then:
    python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
    python3 "${TMPDIR:-/tmp}/library-check.py"
    python3 tools/token-audit.py
  Fix what it finds. A failure may belong to any S task; attribute it in your As built note. The last
  command exits non-zero while size violations remain; judge it by the two description headings
  (empty) and the body + file counts (≤ 160).

Traps:
- docs/skills-catalog.md is 175 KB. Grep it; do not read it whole.
- S2 replaced the planning lane's per-block "closing duty" with the plan's `## Close-out — every task`
  section (plan-format §7) plus one close-out line per block; docs/skills-catalog.md's session-budget
  entry (line ~207) still says "the closing duty". Reword it.
- Stale skill paths in docs/skills-catalog.md (S6): `performance/nbomber` at ~:36 and
  `performance/{nbomber,k6,gatling}` at ~:66 → each stack's `load-testing`;
  `qa/_shared/api-contract-testing` at ~:65 → `qa/_shared/contract-testing-pact`.
- Any entry you add to ALLOW or LINK_EXAMPLES needs a one-line reason in the As built note.
- CONFORMANCE-AUDIT-PLAN.md and README cite each other; fix the README link after the move.
- CONFORMANCE-AUDIT-PLAN.md cites `backend/PLAN.md` (F2, F3) as plain text, not a link. S3 moved that
  file to docs/plans/backend-PLAN.md (live). The plan is legacy text, so leave it as it is.
- `docs/plans/backend-PLAN.md` joins the live legacy plans. Its F1–F5 are still open in the skills
  (S3 checked them). Name it beside O7's two plans in the final Status.
- You delete the last prompt block, so Close-out step 6 files this plan into docs/plans/implemented/.
- Writing to "${TMPDIR:-/tmp}" may be refused in an unattended session (S1 hit it). If so, save the
  script in an untracked scratch folder inside the worktree, run it from the repo root, and delete the
  folder before committing — it must not be scanned as part of the tree when it holds `.md` files.
- The resolver's prefix list has no `pentest` or `purpleteam`, so those skill names are never checked;
  CONTRIBUTING.md (S1) lists both as prefixes. Adding them to both §4 and §7 is your call; record it.

Commit: `chore(sweep G1): file legacy plans, reconcile docs, pass the gate`.
Close out per the plan's "Close-out — every task" before you stop.
````
