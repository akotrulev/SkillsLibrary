# 014 — Authoring standard, domain language, `dev:feature`, `design:prototype` — plan (2026-11-20)

**Goal:** Give the library one written standard for anything an agent reads (skills, agents, rule
files, `CLAUDE.md`), enforce its mechanical half with `tools/skill-lint.py`, and audit every skill
against it. Merge `dev:design` and `dev:decision-interview` into one front door, `dev:feature`: you
describe a feature, it interviews you in rounds, then writes the spec. Add a project glossary and
ADRs that the interview writes while it runs. Add `design:prototype`, which renders 2–5 structurally
different variants of a screen in the project's design language. When the project has no design
language, it first interviews you on style through the `ui-ux-pro-max` corpus.

**Status:** Not started. Nothing is built. Next: A1. After A1, tasks A2, B1 and P1 run side by side.

**Test design:** none. The plan serves no stories. Its only code is `tools/skill-lint.py`, which A2
covers with unit tests.
**Documentation task:** none. This is the skills library. Its documentation is the catalog,
`README.md` and `CONTRIBUTING.md`, and R1 updates those as part of registering what A1, B1 and P1
wrote. No product behaviour changes for a `be-documenter` to trace.
**Telemetry smoke:** none. No service is built.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| One authoring standard for agent-read documents | `CONTRIBUTING.md` holds the description shape, front doors, hidden skills, agent shape and naming (`CONTRIBUTING.md` "SKILL.md structure" … "Names and registration"). `meta/writing-skills/SKILL.md` (654 lines, an unregistered superpowers port) contradicts it on descriptions (`meta/PLAN.md` Phase 1, never executed) | No standard covers *how to write* (pointers, hierarchy, completion criteria, leading words, pruning). Two sources disagree. Rules carry no ids, so neither a lint nor an audit can cite them |
| Mechanical rules checked by a script | `tools/plugin-surface-check.py` checks registration, names, front-door listing and description YAML. `tools/token-audit.py` checks size budgets | Nothing checks description shape, routing sections in hidden skills, dangling `references/` links, placeholders, agent template shape or Load-cell conditions |
| Every skill audited against the standard | — | No audit has been run. 612 `SKILL.md` files exist (587 registered, 37 listed to the model) plus 66 agents |
| A feature front door that interviews, then specs | `dev:design` (`engineering-practices/brainstorming/SKILL.md`) asks one question per message, proposes approaches and writes `docs/specs/NNN-*-design.md`. `dev:decision-interview` (`engineering-practices/decision-interview/SKILL.md`) closes the decision tree of a shaped design, also one question per message | Two front doors overlap on the questioning loop. Asking one question per message costs a turn each. Neither uses a multiple-choice tool, records terms, or records decisions outside the spec |
| A project glossary the agents use | `docs/business-model/glossary.md`: its format is in `business-analysis/skills/ba-project-memory/SKILL.md` "glossary.md and active-context.md format". `be-documenter` writes it per `backend/_shared/business-documentation/references/glossary.md` | Only BA and documenter runs write it. The interview never adds a term. No agent reads it before naming code. No `Avoid` column, so a synonym is never ruled out |
| ADRs | Plans carry `D<n>` (plan-format §2). The BA KB carries business `DEC-` files in `docs/business-model/decisions/` | No home for a hard-to-reverse technical decision that outlives its plan. No rule for when one is written |
| See a screen before building it | `dev:design` "Showing something visual" (`brainstorming/SKILL.md:151`) uses the Artifact tool ad hoc. `design:visual-identity` and `design:brand-import` produce tokens, not screens | No skill renders variants of a screen, detects the project's design language, or falls back to a corpus-led style interview |

## 2. What is taken from `mattpocock/skills`, and what is not

Upstream: `mattpocock/skills@5863806dd4e15c63174bee4e7515a4256792ecfa` (MIT), read 2026-11-20. Every
idea is **rewritten in house words**, and no upstream text is copied. That matches commit `e7c353f3`,
which dropped provenance and licence notes from adapted skills (D8).

| Upstream | Taken | Left |
|---|---|---|
| `productivity/writing-for-agents` + `SKILL-MECHANICS.md` | Context pointers and their wording; the two loads (context load and cognitive load); the information hierarchy (in-file steps → in-file reference → disclosed reference); completion criteria (clarity and demand); leading words; prompting the positive target over the negation; single source of truth; environment as source of truth (don't cache a cheap lookup); no-ops; sediment; model-invoked vs user-invoked skills | Router skills (`ask-matt`): a separate decision, not in scope |
| `productivity/grilling` | The **frontier**: every open decision whose prerequisites are settled, asked as one round. A recommended answer on each question, worded so "yes" accepts it. Fact lookups that block only the questions downstream of them. "Done when the frontier is empty and the user confirms" | Free-text rounds where a multiple-choice tool exists |
| `engineering/domain-modeling` + `GLOSSARY-FORMAT.md` + `ADR-FORMAT.md` | Challenge a term against the glossary; sharpen a fuzzy term into a canonical one; probe edge cases with concrete scenarios; check the code against what the user said; write the glossary *inline*, never batched; the `Avoid` list; offer an ADR only when the **three tests** hold (hard to reverse, surprising without context, the result of a real trade-off); one-paragraph ADRs; lazy creation | A root `GLOSSARY.md` and `GLOSSARY-MAP.md`. We already keep one glossary (D4) |
| `engineering/prototype` + `UI.md` | Throwaway code that answers one question; 3 variants by default, capped at 5; variants that are **structurally** different (layout, hierarchy, primary affordance), never recoloured; a floating switcher; `?variant=`; in-app variants preferred over a vacuum *when built in-app*; state surfaced; the verdict captured | `LOGIC.md` (state-model prototypes): not asked for. A throwaway git branch: the verdict lives in the spec instead (D11) |

## 3. The authoring standard

A1 writes it as `engineering-practices/writing-for-agents/SKILL.md`, registered in `dev` as a front
door (D2), with the skill-specific mechanics in `references/skill-mechanics.md`. It becomes **the**
authority. `CONTRIBUTING.md` keeps only the contributor workflow (file layout, registration,
testing, PR checklist) and points to the standard for every writing rule, so each rule lives in one
place. Every rule has an id, so `skill-lint` and the audit can cite it. The enforcer column names
the one tool that checks it. Nothing is checked twice.

| Rule | Applies to | Enforced by | Severity |
|---|---|---|---|
| **R1** — frontmatter has `name` and `description`; `name` is kebab-case and the topic only | skills | `plugin-surface-check` for registered skills (prefix, suffix, uniqueness) · `skill-lint` for presence and kebab-case on every skill | major |
| **R2** — size budgets: skill description ≤ 200 chars, body ≤ 16,000; agent description ≤ 360, file ≤ 14,000 | skills, agents | `token-audit` | major |
| **R3** — description shape: starts `Use when`, then `Triggers "a"` or `Triggers "a", "b".`, ends `Not for <case> (<sibling>).`; never `Triggers:` | skills | `skill-lint` | minor |
| **R4** — a description says *when*, plus at most one clause of *what*; never a summary of the workflow (the model follows the summary and skips the body) | skills | judgment | major |
| **R5** — listed to the model only when a front door | skills, commands | `plugin-surface-check` | major |
| **R6** — a hidden skill has no `When to use`, `When NOT to use`, `Handoffs` or `Related` heading | skills | `skill-lint` | minor |
| **R7** — a front door has `When to use` and `When NOT to use` | skills | `skill-lint` | minor |
| **R8** — pointers resolve: every relative Markdown link, and every backticked `references/…`, `scripts/…`, `templates/…` or `examples/…` path in a skill or agent, exists relative to that file's folder | skills, agents | `skill-lint` | major |
| **R9** — a reference file over 300 lines opens with a contents list of its `##` headings, before its first `##` | skill `references/*.md` | `skill-lint` | minor |
| **R10** — no placeholders: `TODO`, `TBD`, `FIXME`, `XXX` outside a code fence, and no `@path` force-load links | skills, agents | `skill-lint` | major |
| **R11** — vocabulary: `Phase`, `Slice` or `Milestone` never appears in a heading or a table header row | skills, agents | `skill-lint` | minor |
| **R12** — no line tells a model to invoke a hidden skill through the Skill tool; it names the path to `Read`, or the agent | skills, agents | `skill-lint` | major |
| **R13** — agent shape per `.skill-template/agent.md`: a `## Steps` table whose header has `Load` and `Done when`, and a `## Report` section holding a `Mode:` line | agents | `skill-lint` | major |
| **R14** — a `Load` cell names a visible condition, and never says "when relevant", "if relevant", "as needed" or "if needed" | agents | `skill-lint` | minor |
| **R15** — every step ends on a completion criterion that is checkable (done is distinguishable from not done) and exhaustive where thoroughness matters ("every X accounted for") | skills, agents | judgment | major |
| **R16** — information hierarchy: what every branch needs stays inline; what only some branches reach moves to `references/` behind a pointer that names the condition | skills | judgment | minor |
| **R17** — one meaning, one place: a rule in a rule file or `CLAUDE.md` is pointed at, never restated; a fact one command or one file away (scripts, config, layout) is looked up, not cached | skills, agents, rule files | judgment | major |
| **R18** — state the target behaviour. A prohibition appears only as a hard guardrail, and is paired with the positive target | skills, agents, rule files | judgment | minor |
| **R19** — no no-ops: a sentence that does not change behaviour against the model's default is deleted whole | skills, agents, rule files | judgment | minor |
| **R20** — leading words: one concept, one word, reused as a token; the house vocabulary (task, step, deliverable, front door, gate) is never paraphrased | skills, agents | judgment | minor |
| **R21** — examples obey the house code, comment and test rules (`CLAUDE.md`) | skills | judgment | major |
| **R22** — a pointer a main session follows (in a front door or a rule file) names the agent that loads a hidden skill or runs a command | front doors, rule files | judgment | major |
| **R23** — always-loaded text (a `CLAUDE.md`, a rule file, a front-door description) carries pointers, not content. A rule file is ≤ 6,000 chars for the core file and ≤ 2,500 for each other file | `CLAUDE.md`, rule files | judgment | major |

A1 may add, merge or reword rules. When it does, it rewrites §3, §4 and A2's prompt in place (D1).
It never renumbers a rule that A2 already implements.

## 4. `tools/skill-lint.py`

A Python 3.9 script using only the standard library: the system interpreter here is 3.9.6, so no
`match` statements and no `X | None` hints. It sits beside its two peers and follows their shape:
module docstring as usage, `ROOT` from `__file__`, one line per failure.

```
python3 tools/skill-lint.py                  # every in-scope skill, agent and rule file
python3 tools/skill-lint.py <path> [<path>…] # only these: a SKILL.md, a skill folder, an agent .md, a rule file
python3 tools/skill-lint.py --json …         # a JSON array of {path, line, rule, severity, message}
```

- **Output:** `<path>:<line>: <severity> <rule> <message>`, paths relative to the repo root, sorted.
  This is `kb-lint.py`'s shape (`business-analysis/skills/ba-project-memory/scripts/kb-lint.py`).
  Exit `0` clean, `1` on findings, `2` on a usage error.
- **Scope of the no-argument run:** every `SKILL.md` under the repo; every agent file listed in
  `.claude-plugin/marketplace.json`; every rule file beside a `rules/SKILL.md`. **Excluded by
  name:** `auth/cognito-*/`, `communication/`, `extras/`, `meta/skill-creator/`, `**/vendor/**`,
  `.skill-template/`.
- **Front door:** a skill whose frontmatter lacks `disable-model-invocation: true`. That is the
  same test `plugin-surface-check.py` rule 7 uses, so the two tools never disagree.
- **Checks:** R1 (presence, kebab-case), R3, R6, R7, R8, R9, R10, R11, R12, R13, R14. **R12** builds
  the set of hidden registered names per plugin from `marketplace.json`. It flags a line that holds
  `Skill tool` or a verb from `invoke|call|run` together with `<plugin>:<name>`, where that name is
  hidden.
- **Code fences are skipped** for R10, R11 and R12. A fence shows text; it is not an instruction.
- **Tests:** `tools/test_skill_lint.py`, pytest, loading the hyphenated script through
  `importlib.util` the way `test_kb_lint.py` loads `kb-lint.py`. Fixtures under
  `tools/fixtures/skill-lint/`: one clean skill, one clean agent, and per rule one file that breaks
  it on purpose. Branch coverage of `tools/skill-lint.py` must reach ≥ 80%.

## 5. `dev:feature`: one front door, interview first

`dev:design` and `dev:decision-interview` merge into one skill (D3). The folder
`engineering-practices/brainstorming/` stays, `name:` becomes `feature`, and
`engineering-practices/decision-interview/` is removed (D5).

**Two entry modes, chosen from the input:**

| Mode | Input | Output |
|---|---|---|
| **NEW** | You describe a feature | the interview → 2–3 approaches → the design, section by section → `docs/specs/NNN-<feature>-design.md` → `dev:plan-feature` |
| **SHAPED** | A spec, a design or a plan with open questions | the interview only. Each answer is written back into the document it came from (a plan's `## Answered questions (YYYY-MM-DD)`, a spec's decisions list) |

A loose or multi-capability ask still goes to the `requirements-author` agent (`/dev:refine`). The
fence table in today's `brainstorming/SKILL.md` stays, with `dev:feature` in its first column.

**The interview** (adapted from grilling; it replaces both skills' one-question loops):

1. **Orient.** Read the files, docs and recent commits; `docs/business-model/glossary.md` and the
   titles in `docs/adr/` when they exist. Draw the decision tree.
2. **Ask the frontier as one round.** The frontier is every open decision whose prerequisites are
   settled. When the session has a multiple-choice question tool (AskUserQuestion), each round goes
   through it: at most 4 questions, 2–4 options each, the recommended option first and labelled
   `(Recommended)`. A larger frontier is split across consecutive rounds, the decisions that unblock
   the most going first. Without the tool, a round is numbered text: `**Q1 — <title>:** <body>`, then
   `➡️ <recommended answer>`, worded so "yes" accepts it.
3. **Facts are yours to find.** Look up anything the repo, the docs or a tool can tell you. A slow
   lookup runs as a read-only subagent where the session allows one. Only the questions downstream
   of it wait, and the rest of the frontier is asked now.
4. **Restate and redraw.** After each round, one line per answer: the branch it closes, and the
   branches it opens. A contradiction with an earlier answer is a new question.
5. **Domain language, inline** (loads `engineering-practices/domain-modeling`): challenge a term
   that conflicts with the glossary; turn a fuzzy term into a canonical one; probe a boundary with a
   concrete scenario; check the code against what you were told. Write each resolved term to the
   glossary the moment it is settled. Offer an ADR when, and only when, the three tests hold.
6. **Done when** the frontier is empty and you confirm that nothing is left assumed. NEW then
   continues to approaches, the design and the spec, as `dev:design` does today. The spec gains a
   `## Decisions from the interview` list (question → answer → branches closed).

**Showing something visual** becomes a pointer: when you ask to *see* a screen, type
`/design:prototype` when the `design` plugin is enabled; otherwise the Artifact tool, as today.

Draft description (A1's R3 governs, so it may change):
`Use when describing a new feature or closing a plan's open questions. Triggers "I want to add X", "grill me on this". Not for a loose multi-capability ask (requirements-author).`

## 6. Domain language: one glossary, and ADRs

**The glossary is `docs/business-model/glossary.md`** (D4). There is one, shared by the BA
knowledge base, `be-documenter` and now the interview. Its format moves to
`engineering-practices/domain-modeling/references/glossary-format.md`, which becomes the single
source. `ba-project-memory/SKILL.md` and `business-documentation/references/glossary.md` point to
it instead of carrying their own copy. Both of those plugins depend on `dev`.

```markdown
| Term (client) | Means | Avoid | Called in code | Where the client sees it | Notes |
|---|---|---|---|---|---|
| Order | A confirmed purchase, from placement to delivery | Purchase, transaction | `Order` | order confirmation email | `#confirmed` |
| Customer | **Drift:** the person (E1, US4) · the billing entity (E3, US21) | — | — | — | CONF-004, open |
```

- **Synonyms are ruled out; drift is a finding.** Two words for one concept: pick one and list the
  other under `Avoid`. One word for two concepts: keep both meanings, mark it **Drift**, and leave
  it to the `business-analyst` agent. Today's rule stands.
- **Only this project's terms.** General programming concepts never get a row.
- **Created lazily.** With no knowledge base, `domain-modeling` creates `glossary.md` alone. KB
  init (`ba-project-memory` "init", step 2) **adopts** an existing `glossary.md` rather than
  creating a new one.
- **Read before naming.** `engineering-practices/agent-orientation-cache` (every agent loads it on
  every run) gains one orientation line: when they exist, read the glossary and the ADR titles;
  names follow the glossary; an ADR is respected or explicitly superseded. One edit reaches all 66
  agents.

**ADRs are `docs/adr/NNNN-<slug>.md`** (D6). Four digits, the next free number, the folder created
lazily. Format in `engineering-practices/domain-modeling/references/adr-format.md`. Default is one
paragraph (context, decision, why). `Status` (`proposed | accepted | superseded by NNNN`), `Considered
options` and `Consequences` are added only when they earn their place.

- **Written only when all three tests hold**: hard to reverse, surprising without context, the
  result of a real trade-off. Qualifying examples go in the reference file: architectural shape,
  integration style between areas, lock-in technology, ownership boundaries, deliberate deviations,
  constraints invisible in the code.
- **Kept apart from the BA `DEC-` files.** `decisions/` in the KB holds business decision tables;
  `docs/adr/` holds technical decisions.
- **Writers:** `dev:feature` during the interview; the `solution-planner` blueprint step; and any
  plan task. Plan-format §2 gains one sentence: a `D<n>` that passes the three tests also gets an
  ADR, written by the task that records it, citing the plan.

## 7. `design:prototype`

`design/prototype/SKILL.md`, `name: prototype`, registered in `design` as a front door (D9). It
renders **2–5 structurally different variants** of one screen or flow so you can pick before
anything is built. The default output is **one self-contained HTML file** (D10).

1. **The question.** Which screen or flow, what it must let a person do, and how many variants
   (3 by default, 5 at most). It writes the plan in one line at the top of the file:
   "Three variants of the booking list, states loaded / empty / failed, desktop and phone."
2. **Detect the design language,** in this order, and stop at the first source that answers each
   part (palette, type, spacing, radius, elevation, components, iconography):
   1. `design-system/<slug>/MASTER.md` (+ `pages/<page>.md`) persisted by `ui-ux-pro-max`
   2. tokens: `tailwind.config.*` or a Tailwind v4 `@theme` block, CSS custom properties on `:root`,
      `components.json` (shadcn), an MUI / Mantine / Chakra theme file, `*.tokens.json` (Style
      Dictionary), a Blazor component-library theme, SwiftUI asset-catalogue colours and `Font`
      extensions, Compose `ui/theme/{Color,Type,Theme}.kt`, a WinUI `ResourceDictionary`
   3. the component library and one or two existing screens, for density, spacing and layout habits
   4. `docs/plans/<NNN>-*/experience-plan.md` for the screen's purpose and states; a brand book →
      `design:brand-import`'s intake

   It shows the result as a **design-language block** (each part with the file it came from) before
   building. When only some parts are missing, it asks only for those.
3. **No design language → a style interview,** in rounds like §5 step 2. Round one asks product type
   and audience, mood words, density, and light / dark. Then it runs
   `search.py "<product> <industry> <mood>" --design-system` with `--variance/--motion/--density`
   from the answers, and offers **2–3 directions** as one question. Each option cites its corpus
   style, palette and font-pairing rows. The chosen direction is the language for this prototype.
   Turning it into the project's real tokens is `design:visual-identity`'s job, offered and never
   done here.
4. **Build** `docs/prototypes/<slug>/index.html` to the shell contract in
   `design/prototype/references/html-shell.md`:
   - inline CSS and JS; tokens as custom properties on `:root`, light and dark where the language
     has both; Google Fonts the only network request
   - variants as `<section data-variant="A">`, each different in layout, hierarchy or primary
     affordance, never only in colour
   - every data region in each state the house rules require: loaded, loading, empty, and failed
     with its persistent notification
   - realistic data taken from the project's seeds, fixtures, OpenAPI examples or stories; never
     lorem ipsum
   - a floating switcher bar for variant, state, theme and viewport (desktop / tablet / phone, or
     the device frame of a mobile or desktop target). Keys `1`–`5` pick the variant and `s` cycles
     states. `?variant=B&state=failed&theme=dark` round-trips
   - semantic HTML, and contrast checked against the corpus rule
5. **Show.** It opens the file (`open` on macOS, `xdg-open` on Linux). On request it takes a
   Playwright screenshot of every variant × state into `docs/prototypes/<slug>/screenshots/`, or
   publishes the page with the Artifact tool when the session has it.
6. **Verdict.** You pick a variant, or combine parts of several. The verdict (which variant, and
   why) is written into the spec when `dev:feature` called it, and as a line at the top of the file
   in every case.
7. **In-app, on request only.** The variants are built on a `?variant=` switch inside the existing
   route (a new throwaway route only when no host page exists). They are built by **the stack
   agent** (`fe-react`, `fe-blazor`, `mobile-*`, `desktop-*`), using the HTML prototype and §7 as
   its brief. `design/` never writes app code.

Draft description: `Use when a screen should be seen before it is built; renders variants in the
project's design language. Triggers "prototype this screen", "show me options". Not for a full
identity (visual-identity).` This draft must be cut to fit R2's 200 characters.

## 8. The audit

Round 1 of a saved, read-only conformance audit, `docs/audits/<NNN>-skill-authoring-r1.md`, using
the next free `NNN` in `docs/audits/`. It runs after G1, so it sees the library this plan leaves
behind.

- **The lint, over everything.** Counts per plugin and per rule from
  `python3 tools/skill-lint.py --json`, plus `token-audit.py --violations-only`.
- **Judgment (R4, R15–R23)** on every listed front door (A3), on each plugin's front-door agent,
  and on one hidden skill sampled per top-level domain folder (A4), with the sample's paths named.
  Every finding uses the house review table (`| Severity | Location | Issue | Suggested fix |`) and
  cites its rule id.
- **Findings are classed** under three headings, all present in every round (`None.` when empty).
  **Data issues** are wrong facts in the text: a stale version, a dead tool, a wrong path in prose.
  **Code issues** are text that breaks a rule. **Logical conflicts** are two skills, or a skill and
  a rule file, that cannot both hold; the owner decides.
- **A5 turns it into the remediation plan**: the next free number in `docs/plans/`, its own plan
  file, written per plan-format. This plan fixes nothing outside its own files (D7).

## 9. Decisions

**D1 — The standard is a skill with numbered rules, and every rule names one enforcer.** Mechanical
rules go to a script; judgment rules go to review. That makes the lint and the audit cite the same
ids. Cost: `CONTRIBUTING.md` loses its writing rules to a pointer, and anyone used to reading them
there follows one link.

**D2 — `writing-for-agents` is a `dev` front door.** Target projects write `CLAUDE.md` files and
rule files too, so a main session needs to reach it without an agent. Cost: about 50 tokens in every
session of every project that enables `dev`.

**D3 — `dev:design` and `dev:decision-interview` become one skill, `dev:feature`** (the user's ask,
2026-11-20). Both ran the same questioning loop. Only `design` proposed approaches and wrote the
spec. Cost: anyone who types `/dev:design` or `/dev:decision-interview` must learn `/dev:feature`.
R1 renames every reference.

| Option | Verdict | Why |
|---|---|---|
| Merge into `dev:feature` with NEW and SHAPED modes | **chosen** | One front door, one loop, and the spec still has one writer |
| `dev:feature` interviews, then hands to `dev:design` | rejected | Two front doors would still overlap on the first step |
| Keep both, fence harder | rejected | The overlap is the loop itself, which a fence cannot remove |

**D4 — One glossary: `docs/business-model/glossary.md`, gaining an `Avoid` column** (answered
2026-11-20). Its format moves into `dev` as the single source. Cost: three writers to update in B1,
and the `kb-lint` fixture's header changes.

**D5 — The folder `engineering-practices/brainstorming/` keeps its name; only `name:` changes.**
That is `CONTRIBUTING.md`'s rule ("Folders do not move when a skill is renamed"). Cost: a folder
whose name does not match its skill.

**D6 — ADRs live in `docs/adr/NNNN-<slug>.md`**, kept apart from the BA `DEC-` files (answered
2026-11-20). Four digits, the common ADR convention. Cost: a second numbering width beside plans'
and specs' three.

**D7 — The audit lints everything, judges the front doors, the front-door agents and a sample, and
writes a separate remediation plan** (answered 2026-11-20). A full judgment read would take about
8–10 sessions. Cost: hidden skills outside the sample are covered by the lint only, until the
remediation plan or a later round reaches them.

**D8 — Upstream ideas are rewritten in our own words, with no copied text and no provenance note.**
This follows `e7c353f3`. Cost: no in-file link back to the upstream; this plan's §2 is the record.

**D9 — `prototype` is a `design` front door.** A main session reaches it from "show me what this could
look like" with no agent behind it, and `dev:feature` points to it. Cost: about 50 tokens per session
in projects that enable `design`, plus a new `design` key in `FRONT_DOORS`.

**D10 — Renders are one self-contained HTML file by default; in-app variants only on request, and
built by the stack agent** (answered 2026-11-20). No app has to run and no lane is crossed. Cost:
HTML variants approximate the real component library rather than run it.

**D11 — Prototypes live in `docs/prototypes/<slug>/`, not on a throwaway branch.** The spec links to
them. Cost: throwaway files in the tree until someone deletes them.

**D12 — `meta/writing-skills/` is removed and `meta/PLAN.md` is marked superseded by 014.** The new
standard replaces its unique content: the description trap is R4, and pressure-testing is
`CONTRIBUTING.md`'s "Testing a new skill". Cost: its rationalization tables are gone, and are still
in git history.

## 10. Answered questions (2026-11-20)

**O1 — Where do the glossary and ADRs live:** the existing BA glossary, extended, plus `docs/adr/` (D4, D6).
**O2 — Merge `dev:design` and `dev:decision-interview`:** yes, into `dev:feature` (D3).
**O3 — What is a render:** one self-contained HTML file; in-app on request (D10).
**O4 — How deep is the audit:** lint everything, judge front doors and a sample, separate remediation plan (D7).

## 11. Tasks

### A1 — `writing-for-agents`: the house authoring standard

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering-practices/writing-for-agents/SKILL.md` states every rule of §3 with its
id, enforcer and severity. `CONTRIBUTING.md` points there for every writing rule. `meta/writing-skills/`
is gone.
**Depends on:** —
**Budget:** ~115k. `CLAUDE.md` 25k, this plan §2–§3 and §9 10k, `CONTRIBUTING.md` 20k,
`.skill-template/*` 8k, upstream `writing-for-agents` + `SKILL-MECHANICS.md` 9k, the headers of
`plugin-surface-check.py` and `token-audit.py` 3k, `meta/writing-skills/SKILL.md` skimmed for
anything unique 10k, writes ~25k, review 5k.
**Gate: none.** The deliverable is text. G1 runs `skill-lint` over it once A2 exists.

- `SKILL.md` (front door, `name: writing-for-agents`), in house words: context pointers; the two
  loads; the information hierarchy and progressive disclosure; co-location; completion criteria;
  splitting by sequence; leading words; positive targets; pruning (single source of truth,
  environment as source, relevance, sediment, no-ops). Then **the rule table of §3**, copied with
  its ids. It ends with `When to use` / `When NOT to use`, as a front door.
- `references/skill-mechanics.md`: frontmatter; front door vs hidden (`disable-model-invocation`,
  `FRONT_DOORS`); the description shape (R3) with the good and bad examples moved from
  `CONTRIBUTING.md`; agents as thin routers with conditional `Load` cells; rule files (`paths:`,
  sizes); naming.
- `CONTRIBUTING.md`: "SKILL.md structure", "Agent structure", "Front doors" and "Writing a good
  `description`" each shrink to their contributor-facing facts plus a pointer to the standard. The
  PR checklist cites rule ids.
- `git rm -r meta/writing-skills`. Add a first line to `meta/PLAN.md`: `**Superseded by
  docs/plans/014-authoring-standard-domain-language-feature-prototype.md (D12).**`
- **Not in A1:** registration and `FRONT_DOORS` (R1); the lint (A2).

### A2 — `tools/skill-lint.py`: the mechanical half of the standard

**Stack:** `infra` · **Agent:** `general-purpose`
**Deliverable:** `python3 tools/skill-lint.py` checks R1, R3, R6–R14 as §4 specifies. Every rule
has a fixture that trips it. `tools/test_skill_lint.py` passes, with ≥ 80% branch coverage of the
script.
**Depends on:** A1 (the final rule ids and wording).
**Budget:** ~110k. `CLAUDE.md` 25k, this plan §3–§4 8k, the standard's rule table 4k,
`plugin-surface-check.py` 8k (frontmatter parsing and the marketplace walk, as patterns),
`kb-lint.py` + `test_kb_lint.py` heads 8k, writes ~40k (script ~450 lines, tests, fixtures), test
and coverage output 10k, fixes 7k.
**Gate: own tests.** `python3 -m pytest tools/test_skill_lint.py -q`,
`python3 -m coverage run --branch -m pytest tools/test_skill_lint.py -q && python3 -m coverage report --include=tools/skill-lint.py`
(≥ 80% branch), and `python3 tools/skill-lint.py tools/fixtures/skill-lint/clean-skill tools/fixtures/skill-lint/clean-agent.md`
(exit 0). Do not run the no-argument library sweep as a gate; A3 owns that.

- Parse frontmatter the way `plugin-surface-check.py` does, so the two tools agree on the same files.
- One function per rule, each returning findings; `main()` is the only function that touches argv
  or the process.
- Fixtures: `clean-skill/` (a front door and a hidden variant), `clean-agent.md`, and one breaking
  file per rule (`r3-no-triggers/`, `r8-dangling-ref/`, …).
- **Not in A2:** registration (R1 owns `plugin-surface-check.py`), and any fix to an existing skill.

### B1 — `dev:feature` and `domain-modeling`: the merged front door, the glossary and ADRs

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering-practices/brainstorming/SKILL.md` is `name: feature` and runs §5's NEW
and SHAPED modes. `engineering-practices/domain-modeling/` holds §6's skill and two formats.
`decision-interview/` is removed. The glossary format has one source, and the KB lint fixtures still
pass.
**Depends on:** A1 (the standard it is written to).
**Budget:** ~120k. `CLAUDE.md` 25k, this plan §2, §5, §6 and D3–D6 12k, the standard 8k,
`brainstorming/SKILL.md` 9k, `decision-interview/SKILL.md` 3k, `ba-project-memory/SKILL.md` (the
glossary format and init sections) 6k, `business-documentation/references/glossary.md` 2k,
`agent-orientation-cache/SKILL.md` 7k, plan-format §2 3k, writes ~30k, test output 3k, review 12k.
**Gate: own tests.** `python3 -m pytest business-analysis/skills/ba-project-memory/scripts/test_kb_lint.py -q`.
`skill-lint` runs over these files in G1.

- Rewrite `brainstorming/SKILL.md` as `name: feature`: §5's modes, interview, restate step,
  approaches → design → spec, the fence table, and the visual pointer. `## Decisions from the
  interview` is added to the spec outline. Keep what still holds in today's approval gate and
  self-review.
- `domain-modeling/SKILL.md`, hidden (`disable-model-invocation: true`), loaded by path:
  challenge, sharpen, scenarios, cross-check against code, write the glossary inline, offer an ADR
  under the three tests. `references/glossary-format.md` (§6 table and rules);
  `references/adr-format.md` (template, optional sections, numbering, what qualifies).
- `ba-project-memory/SKILL.md`: the glossary table moves to a pointer at `glossary-format.md`;
  init step 2 adopts an existing `glossary.md`. `scripts/fixtures/clean-kb/glossary.md` gains the
  `Avoid` column.
- `business-documentation/references/glossary.md`: its table becomes the pointer, plus the
  documenter's own notes (where `Called in code` comes from).
- `agent-orientation-cache/SKILL.md`: the one orientation line from §6.
- `writing-plans/references/plan-format.md` §2: the ADR sentence from §6.
- `git rm -r engineering-practices/decision-interview`.
- **Not in B1:** `marketplace.json`, `FRONT_DOORS`, renaming references in agents, the catalog
  and README (R1).

### P1 — `design:prototype`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `design/prototype/SKILL.md` and `references/{design-language.md,html-shell.md}` run
§7 end to end: detection or style interview, then a self-contained variant file, the verdict, and
the in-app hand-off.
**Depends on:** A1 (the standard it is written to).
**Budget:** ~105k. `CLAUDE.md` 25k, this plan §2, §7, D9–D11 8k, the standard 8k,
`design/ui-ux-pro-max/SKILL.md` 10k, `visual-identity/SKILL.md` 6k, `brand-import/SKILL.md` 5k,
`design-tokens/SKILL.md` head 3k, writes ~30k (skill, two references with an HTML shell skeleton),
review 10k.
**Gate: none.** The deliverable is text. G1 lints it. Building a sample prototype is the trigger
smoke recorded as unverified in `Status:`.

- `SKILL.md` (front door): §7's steps 1–7, `When to use` / `When NOT to use` (visual-identity,
  brand-import, ux-review, the stack agents).
- `references/design-language.md`: §7 step 2's detection order, per stack, with what each source
  yields; the design-language block's shape; the partial-language rule; §7 step 3's interview and
  its exact `search.py` invocation (`${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py`;
  inside this repo, `design/ui-ux-pro-max/scripts/search.py`).
- `references/html-shell.md`: the file contract of §7 step 4 and an HTML skeleton of the switcher
  bar and the variant/state/theme/viewport wiring. Under ~120 lines of markup; its script obeys the
  house comment rules.
- **Not in P1:** registration and `FRONT_DOORS` (R1). It writes no stack's app code, ever.

### R1 — Register, rename and point

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `writing-for-agents`, `feature` and `prototype` are registered front doors, and
`domain-modeling` is registered hidden. `decision-interview` is gone from every list.
`plugin-surface-check.py` prints `OK`. No live file outside `docs/plans/implemented/` names
`dev:design`, `/dev:design`, `decision-interview` or `meta/writing-skills`.
**Depends on:** A1, A2, B1, P1. They wrote the files this task registers; A1 and R1 both edit
`CONTRIBUTING.md`; R1's gate runs A2's lint.
**Budget:** ~105k. `CLAUDE.md` 25k, this plan §5–§7 and §9 8k, `marketplace.json` (the `dev` and
`design` entries, read by line range) 8k, `CONTRIBUTING.md` 15k, `README.md` and
`docs/skills-catalog.md` (the dev, design and BA sections) 18k, the three agents' Steps tables 6k,
writes ~15k, tool output 5k, review 5k.
**Gate: own tests.** `python3 tools/plugin-surface-check.py` (prints `OK`);
`python3 tools/skill-lint.py engineering-practices/writing-for-agents engineering-practices/brainstorming engineering-practices/domain-modeling design/prototype`
(exit 0); `grep -rnE "dev:design|decision-interview|meta/writing-skills" --exclude-dir=.git . | grep -v docs/plans/implemented | grep -v docs/plans/014-`
(prints nothing).

- `marketplace.json`: `dev.skills` adds `./engineering-practices/writing-for-agents` and
  `./engineering-practices/domain-modeling`, and drops `./engineering-practices/decision-interview`;
  `design.skills` adds `./design/prototype`. Each plugin's `description` names the new skills.
- `tools/plugin-surface-check.py` `FRONT_DOORS`: `dev` swaps `design decision-interview` for
  `feature writing-for-agents`; a new `"design": frozenset(("prototype",))`.
- References: `requirements-author.md`, `business-analyst.md`, `solution-planner.md` (also gains
  the conditional `Load` → `engineering-practices/domain-modeling` for a blueprint decision that
  passes the three ADR tests), `CONTRIBUTING.md` front-door list, `README.md`,
  `docs/skills-catalog.md` (the dev chain, the design catalog, counts, the slash-surface count in
  `CLAUDE.md`'s pointer line if it changes).
- **Not in R1:** any change to a skill's body beyond a renamed reference.

### G1 — Gate: the whole set once more

**Stack:** `infra` · **Agent:** `general-purpose`
**Deliverable:** every check below passes on this plan's files. `tools/skill-lint.py` is at ≥ 80%
branch coverage. `Status:` names what is unverified.
**Depends on:** R1, A2.
**Budget:** ~85k. `CLAUDE.md` 25k, this plan 12k, tool output 15k, fixes ~25k, plan edits 8k.
**Gate (this is the last runnable task, so it runs the whole set once more across the plan, in
order):**

```bash
python3 tools/plugin-surface-check.py
python3 -m pytest tools/test_skill_lint.py business-analysis/skills/ba-project-memory/scripts/test_kb_lint.py -q
python3 -m coverage run --branch -m pytest tools/test_skill_lint.py -q && python3 -m coverage report --include=tools/skill-lint.py
python3 tools/skill-lint.py engineering-practices/writing-for-agents engineering-practices/brainstorming engineering-practices/domain-modeling design/prototype
python3 tools/token-audit.py --violations-only | grep -E "writing-for-agents|brainstorming|domain-modeling|prototype"   # must print nothing
git diff --name-only "$(git log --diff-filter=A --format=%h -1 -- docs/plans/014-authoring-standard-domain-language-feature-prototype.md)" HEAD
```

- Fix what fails by the fix loop (plan-format §5): the whole set once; each failure with its
  narrowest command; only the failed rerun; the whole set once more.
- The last command lists the plan's files. Read each changed skill once for broken cross-references
  that the lint cannot see (a pointer to a renamed section).
- `token-audit.py` already exits non-zero on violations that predate this plan (e.g.
  `security-governance`). Only a line naming this plan's files is a failure.
- **Not in G1:** the library-wide sweep (A3), and any feature work.

### A3 — Audit round 1: the lint sweep and the front doors

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `docs/audits/<NNN>-skill-authoring-r1.md` holds the lint counts per plugin and
rule, and a judgment finding table for every listed front door, classed per §8.
**Depends on:** G1.
**Budget:** ~140k. `CLAUDE.md` 25k, this plan §3, §8 6k, the standard 8k, lint and token-audit
output summarised by script (never pasted whole) 10k, the 38 listed front doors read once each
(~75k; the `rules` skills share one shape, so they are read as a group), writes ~16k.
**Gate: own tests.** `python3 tools/skill-lint.py --json > /tmp/skill-lint-r1.json; test $? -le 1`.
Findings are expected; exit 2 is a defect in the lint, which this task fixes in `tools/skill-lint.py`
and reruns `python3 -m pytest tools/test_skill_lint.py -q`.

- List the front doors from `marketplace.json` plus the `disable-model-invocation` test. Record the
  list in the report.
- A lint finding that is a false positive is a lint defect: fix it in the script with a fixture that
  pins it, and say so in `As built`.
- **Not in A3:** agents and hidden skills (A4); fixing any skill (the remediation plan).

### A4 — Audit round 1: the agents and the sample

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** the same report gains a judgment table for each plugin's front-door agent (the one
its plugin-name command runs) and for one hidden skill per top-level domain folder (paths named),
then its summary: totals by severity and class, and the top five rules by count.
**Depends on:** A3 (the same report file).
**Budget:** ~145k. `CLAUDE.md` 25k, this plan §8 3k, the standard 8k, the report so far 12k, ~24
front-door agents (~60k), ~14 sampled skills (~30k), writes ~7k.
**Gate: none.** The deliverable is a report; the lint ran in A3.

- Pick the sample by size: the largest hidden skill in each domain folder, since sediment collects
  there.
- **Not in A4:** fixing anything.

### A5 — The remediation plan, and filing 014

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `docs/plans/<next>-skill-authoring-remediation.md` exists in plan format: one task
per cluster of findings (by plugin, filling sessions up to ~150k), each with a gate of
`skill-lint` over its paths plus `plugin-surface-check.py`, then a gate task and its prompts. This
plan is filed.
**Depends on:** A4.
**Budget:** ~110k. `CLAUDE.md` 25k, plan-format 20k, the audit report 25k, this plan's header and
§8 4k, writes ~30k, review 6k.
**Gate: none.** It writes a plan document.

- The next free number spans `docs/plans/` and `docs/plans/implemented/`.
- Mechanical findings batch by rule across a plugin; judgment findings go with the skill they name.
- **Not in A5:** fixing any skill.

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

Run them in order, one session each. Each block is complete on its own. Every gate runs locally, in
the session that runs the task. No prompt fixes a skill outside its own deliverable. The remediation
is the next plan's. **After A1, A2, B1 and P1 run side by side** (disjoint files); R1 waits for all
three; then G1, A3, A4 and A5 run in sequence.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| A1 | `docs` | `general-purpose` | none | — | ~115k |
| A2 | `infra` | `general-purpose` | A1 | B1, P1 | ~110k |
| B1 | `docs` | `general-purpose` | A1 | A2, P1 | ~120k |
| P1 | `docs` | `general-purpose` | A1 | A2, B1 | ~105k |
| R1 | `docs` | `general-purpose` | A1, A2, B1, P1 | — | ~105k |
| G1 | `infra` | `general-purpose` | R1, A2 | — | ~85k |
| A3 | `docs` | `general-purpose` | G1 | — | ~140k |
| A4 | `docs` | `general-purpose` | A3 | — | ~145k |
| A5 | `docs` | `general-purpose` | A4 | — | ~110k |
| — | try `/dev:feature`, `/design:prototype` in a real project | **the user** | G1 | — | — |

No prompt has landed yet; all nine are live.

---

### A1 — writing-for-agents, the house authoring standard (general-purpose, docs)

````
Depends on: none
Agent: general-purpose · Stack: docs

Task A1 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: write the
library's one authoring standard for anything an agent reads, as a `dev` front door, and make
CONTRIBUTING.md point to it.

Read, in this order:
1. CLAUDE.md (repo root).
2. The plan: §1, §2, §3, D1, D2, D8, D12, task A1, and "Close-out — every task".
3. CONTRIBUTING.md: "SKILL.md structure" through "Names and registration", and the PR checklist.
4. .skill-template/{reference,generator,reviewer}.SKILL.md and .skill-template/agent.md.
5. Upstream, for ideas only (rewrite in your own words, copy no sentence):
   https://raw.githubusercontent.com/mattpocock/skills/5863806dd4e15c63174bee4e7515a4256792ecfa/skills/productivity/writing-for-agents/SKILL.md
   https://raw.githubusercontent.com/mattpocock/skills/5863806dd4e15c63174bee4e7515a4256792ecfa/skills/productivity/writing-for-agents/SKILL-MECHANICS.md
6. The docstrings of tools/plugin-surface-check.py and tools/token-audit.py (what they already enforce).
7. meta/writing-skills/SKILL.md, skimmed for anything not covered by §3 (D12).

Write:
- engineering-practices/writing-for-agents/SKILL.md: frontmatter `name: writing-for-agents`, no
  `disable-model-invocation` (front door). Draft description, ≤ 200 chars, shape R3:
  `Use when writing or editing a skill, agent, rule file or CLAUDE.md. Triggers "write a skill", "tighten this CLAUDE.md". Not for plan documents (plan-feature).`
  Body: the writing levers (pointers, two loads, hierarchy, co-location, completion criteria,
  splitting, leading words, positive targets, pruning), then §3's rule table with ids, enforcer and
  severity, then When to use / When NOT to use.
- engineering-practices/writing-for-agents/references/skill-mechanics.md: frontmatter, front door
  vs hidden, the description shape with CONTRIBUTING's good/bad examples, agents as thin routers
  with conditional Load cells, rule files (paths:, sizes), naming.
- CONTRIBUTING.md: the four writing sections shrink to contributor facts plus a pointer; the PR
  checklist cites rule ids.
- `git rm -r meta/writing-skills`; first line of meta/PLAN.md:
  `**Superseded by docs/plans/014-authoring-standard-domain-language-feature-prototype.md (D12).**`

Traps:
- The standard must obey itself: front-loaded leading words, no no-op sentences, positive targets.
  Keep SKILL.md under 16,000 characters; anything only one branch needs goes to references/.
- If you add, merge or reword a rule, rewrite §3, §4 and the A2 prompt block below in place. Never
  renumber a rule id.
- Don't register the skill or touch FRONT_DOORS. That is R1.
- No colon followed by a space in the description line.

Gate: none. The deliverable is text; G1 lints it.

Commit: `feat(dev): writing-for-agents, the house authoring standard (014 A1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A2 — tools/skill-lint.py, the mechanical half of the standard (general-purpose, infra)

````
Depends on: A1
Agent: general-purpose · Stack: infra

Task A2 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: build
tools/skill-lint.py, which checks the standard's mechanical rules R1, R3, R6–R14, with pytest tests
and fixtures.

Read, in this order:
1. CLAUDE.md (repo root).
2. The plan: §3, §4, task A2, and "Close-out — every task".
3. engineering-practices/writing-for-agents/SKILL.md: the rule table (A1 may have reworded a rule;
   the table wins over this prompt).
4. tools/plugin-surface-check.py: frontmatter parsing, the marketplace walk, FRONT_DOORS. Reuse
   its frontmatter rules so the two tools agree.
5. business-analysis/skills/ba-project-memory/scripts/kb-lint.py (output shape) and
   test_kb_lint.py (how a hyphenated script is loaded with importlib.util in tests).

Build:
- tools/skill-lint.py per §4: CLI (no args = library sweep; paths; --json), output
  `<path>:<line>: <severity> <rule> <message>`, exit 0/1/2, exclusions by name, one function per
  rule, main() the only function touching argv.
- tools/test_skill_lint.py + tools/fixtures/skill-lint/: a clean front door, a clean hidden skill,
  a clean agent, and one fixture per rule that breaks it. A test per branch.

Traps:
- The interpreter is Python 3.9.6: no `match`, no `X | None` hints, nothing newer than 3.9.
  Stdlib only.
- Skip fenced code blocks for R10, R11 and R12. A Rust skill legitimately says "slice" in prose;
  R11 checks headings and table header rows only.
- R12 needs the hidden-name set per plugin from .claude-plugin/marketplace.json; a name hidden in
  one plugin and absent from another is only hidden where registered.
- Do not run the no-argument sweep as your gate, and fix no existing skill. A3 owns the sweep.

Gate (own tests):
  python3 -m pytest tools/test_skill_lint.py -q
  python3 -m coverage run --branch -m pytest tools/test_skill_lint.py -q && python3 -m coverage report --include=tools/skill-lint.py
  python3 tools/skill-lint.py tools/fixtures/skill-lint/clean-skill tools/fixtures/skill-lint/clean-agent.md
Branch coverage ≥ 80%; the clean fixtures exit 0.

Commit: `feat(tools): skill-lint, the mechanical half of the authoring standard (014 A2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### B1 — dev:feature and domain-modeling, the merged front door, glossary and ADRs (general-purpose, docs)

````
Depends on: A1
Agent: general-purpose · Stack: docs

Task B1 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: merge dev:design
and dev:decision-interview into `dev:feature`, add the hidden `domain-modeling` skill with the
glossary and ADR formats, and make the glossary format a single source.

Read, in this order:
1. CLAUDE.md (repo root).
2. The plan: §1, §2, §5, §6, D3–D6, task B1, and "Close-out — every task".
3. engineering-practices/writing-for-agents/SKILL.md (the standard you write to).
4. engineering-practices/brainstorming/SKILL.md and engineering-practices/decision-interview/SKILL.md.
5. business-analysis/skills/ba-project-memory/SKILL.md: "glossary.md and active-context.md format"
   and the init procedure only.
6. backend/_shared/business-documentation/references/glossary.md (the "## Glossary" part).
7. engineering-practices/agent-orientation-cache/SKILL.md, the orientation-pass section.
8. engineering-practices/writing-plans/references/plan-format.md §2 ("## Decisions" bullet).
9. Upstream ideas, rewritten in your own words:
   https://raw.githubusercontent.com/mattpocock/skills/5863806dd4e15c63174bee4e7515a4256792ecfa/skills/productivity/grilling/SKILL.md
   https://raw.githubusercontent.com/mattpocock/skills/5863806dd4e15c63174bee4e7515a4256792ecfa/skills/engineering/domain-modeling/SKILL.md
   (and its GLOSSARY-FORMAT.md, ADR-FORMAT.md beside it)

Write:
- engineering-practices/brainstorming/SKILL.md → `name: feature`, front door, draft description:
  `Use when describing a new feature or closing a plan's open questions. Triggers "I want to add X", "grill me on this". Not for a loose multi-capability ask (requirements-author).`
  Body: §5's two modes, the round-based interview (AskUserQuestion when present, ≤ 4 questions,
  recommended option first; numbered text rounds otherwise), restate-and-redraw, domain language
  inline via engineering-practices/domain-modeling, then approaches → design → spec (with
  `## Decisions from the interview`) → dev:plan-feature. Keep the fence table and the approval gate.
  "Showing something visual" becomes the /design:prototype pointer.
- engineering-practices/domain-modeling/SKILL.md (hidden: `disable-model-invocation: true`) +
  references/glossary-format.md (§6 table, synonyms vs drift, only project terms, lazy creation,
  KB adoption) + references/adr-format.md (docs/adr/NNNN-<slug>.md, one paragraph default,
  optional sections, the three tests, what qualifies).
- ba-project-memory/SKILL.md: glossary table → pointer to glossary-format.md; init adopts an
  existing glossary.md. scripts/fixtures/clean-kb/glossary.md gains the Avoid column.
- business-documentation/references/glossary.md: table → pointer; keep the documenter's own notes.
- agent-orientation-cache/SKILL.md: one orientation line (read glossary + ADR titles when present;
  names follow the glossary; respect or explicitly supersede an ADR).
- plan-format.md §2: one sentence (a D<n> passing the three tests also gets an ADR, written by the
  task that records it, citing the plan).
- `git rm -r engineering-practices/decision-interview`.

Traps:
- dev depends on nothing in business-analysis; business-analysis and be-* depend on dev. So the
  format lives in dev and the BA/documenter files point to it, never the reverse.
- Drift (one word, two meanings) is still a finding left to the business-analyst agent; only
  synonyms are ruled out with Avoid. Do not merge the two rules.
- The folder stays `brainstorming/` (D5). Do not touch marketplace.json, FRONT_DOORS, agents,
  README or the catalog. That is R1.
- domain-modeling is hidden, so nothing may tell a model to invoke it through the Skill tool (R12):
  write "Read engineering-practices/domain-modeling/SKILL.md".

Gate (own tests):
  python3 -m pytest business-analysis/skills/ba-project-memory/scripts/test_kb_lint.py -q

Commit: `feat(dev): dev:feature merges design and decision-interview; domain-modeling, glossary and ADRs (014 B1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P1 — design:prototype (general-purpose, docs)

````
Depends on: A1
Agent: general-purpose · Stack: docs

Task P1 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: write
`design:prototype`, which renders 2–5 structurally different variants of a screen as one
self-contained HTML file in the project's design language, or, when it has none, after a style
interview through the ui-ux-pro-max corpus.

Read, in this order:
1. CLAUDE.md (repo root), especially the React and Mobile "data region" rules (states and the
   persistent failure notification).
2. The plan: §2, §7, D9–D11, task P1, and "Close-out — every task".
3. engineering-practices/writing-for-agents/SKILL.md (the standard you write to).
4. design/ui-ux-pro-max/SKILL.md (the query contract, --design-system, --persist layout, dials).
5. design/visual-identity/SKILL.md and design/brand-import/SKILL.md (what they own; prototype
   never writes token files).
6. design/design-tokens/SKILL.md, its first section only.
7. Upstream ideas, rewritten in your own words:
   https://raw.githubusercontent.com/mattpocock/skills/5863806dd4e15c63174bee4e7515a4256792ecfa/skills/engineering/prototype/SKILL.md
   https://raw.githubusercontent.com/mattpocock/skills/5863806dd4e15c63174bee4e7515a4256792ecfa/skills/engineering/prototype/UI.md

Write:
- design/prototype/SKILL.md: `name: prototype`, front door (no disable-model-invocation), a
  description ≤ 200 chars in R3's shape (§7 has a draft that is too long); §7 steps 1–7; When to
  use / When NOT to use (visual-identity, brand-import, ux-review, the stack agents).
- design/prototype/references/design-language.md: the detection order per stack, what each source
  yields, the design-language block, the partial-language rule, and the style interview with its
  exact search.py command (plugin path and in-repo path).
- design/prototype/references/html-shell.md: the file contract and an HTML skeleton (≤ ~120 lines)
  of the switcher bar and the variant / state / theme / viewport wiring with URL round-trip.

Traps:
- design/ never writes app code: the in-app branch hands the variants to the stack agent
  (fe-react, fe-blazor, mobile-*, desktop-*) as a brief.
- Variants differ in structure, never only colour; all variants share one design language.
- Never `--persist --force` the corpus output (ui-ux-pro-max forbids it without the user's say-so).
- The skeleton's script obeys the house comment rules: no inline comments.
- Don't register the skill or touch FRONT_DOORS. That is R1.

Gate: none. The deliverable is text; G1 lints it. Building a real prototype is the user's trigger
smoke, recorded as unverified.

Commit: `feat(design): prototype, variant renders in the project's design language (014 P1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### R1 — register, rename and point (general-purpose, docs)

````
Depends on: A1, A2, B1, P1
Agent: general-purpose · Stack: docs

Task R1 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: register the new
skills, update FRONT_DOORS, and rename every live reference to dev:design, decision-interview and
meta/writing-skills.

Read, in this order:
1. CLAUDE.md (repo root).
2. The plan: §5–§7, §9, task R1, the As built notes of A1, A2, B1, P1, and "Close-out — every task".
3. .claude-plugin/marketplace.json: the `dev` and `design` entries only (find them with grep -n,
   read those line ranges).
4. tools/plugin-surface-check.py: FRONT_DOORS.
5. The list from:
   grep -rnE "dev:design|decision-interview|meta/writing-skills|brainstorming" --exclude-dir=.git . | grep -v docs/plans/implemented
   and each hit's surrounding lines only.
6. The Steps tables of backend/_shared/agents/solution-planner.md,
   business-analysis/agents/requirements-author.md, business-analysis/agents/business-analyst.md.

Do:
- marketplace.json: dev adds ./engineering-practices/writing-for-agents and
  ./engineering-practices/domain-modeling, drops ./engineering-practices/decision-interview;
  design adds ./design/prototype; both plugin descriptions name the new skills.
- FRONT_DOORS: dev swaps `design decision-interview` for `feature writing-for-agents`; add
  `"design": frozenset(("prototype",))`.
- Every hit from step 5 renamed to dev:feature / writing-for-agents as fits; solution-planner gains
  the conditional Load (a blueprint decision passing the three ADR tests →
  engineering-practices/domain-modeling).
- CONTRIBUTING.md front-door list, README.md, docs/skills-catalog.md (dev chain, design catalog,
  skill counts, front-door counts), and CLAUDE.md's catalog pointer line if a count in it changed.

Traps:
- Skills share one slash namespace with commands per plugin: `feature` must not collide with a
  command stem in dev (today: refine, plan-system, document-system, document-feature, audit).
- A pointer a main session follows names the agent (R22), not a bare hidden plugin:name.
- Change no skill body beyond a renamed reference.

Gate (own tests):
  python3 tools/plugin-surface-check.py
  python3 tools/skill-lint.py engineering-practices/writing-for-agents engineering-practices/brainstorming engineering-practices/domain-modeling design/prototype
  grep -rnE "dev:design|decision-interview|meta/writing-skills" --exclude-dir=.git . | grep -v docs/plans/implemented | grep -v docs/plans/014-
The first prints OK, the second exits 0, the third prints nothing.

Commit: `feat(dev, design): register writing-for-agents, feature, domain-modeling and prototype (014 R1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — gate, the whole set once more (general-purpose, infra)

````
Depends on: R1, A2
Agent: general-purpose · Stack: infra

Task G1 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: the plan's gate.
Run the whole set once more across the plan, fix what fails, and record what is unverified.

Read, in this order:
1. CLAUDE.md (repo root).
2. The plan: header, §3, §4, task G1, every As built note, and "Close-out — every task".
3. engineering-practices/writing-plans/references/plan-format.md §5, "The last task's fix loop".

Gate (this is the last runnable task, so it runs the whole set once more across the plan, in order):
  python3 tools/plugin-surface-check.py
  python3 -m pytest tools/test_skill_lint.py business-analysis/skills/ba-project-memory/scripts/test_kb_lint.py -q
  python3 -m coverage run --branch -m pytest tools/test_skill_lint.py -q && python3 -m coverage report --include=tools/skill-lint.py
  python3 tools/skill-lint.py engineering-practices/writing-for-agents engineering-practices/brainstorming engineering-practices/domain-modeling design/prototype
  python3 tools/token-audit.py --violations-only | grep -E "writing-for-agents|brainstorming|domain-modeling|prototype"
  git diff --name-only "$(git log --diff-filter=A --format=%h -1 -- docs/plans/014-authoring-standard-domain-language-feature-prototype.md)" HEAD
Expect: OK; all pass; branch ≥ 80%; exit 0; nothing printed; the plan's file list.

Then read each changed SKILL.md once for cross-references the lint cannot see (a pointer to a
section that moved or was renamed).

Traps:
- token-audit exits non-zero for violations that predate this plan; only a line naming this plan's
  files fails the gate.
- Fix by the fix loop: the narrowest command per failure, then only the failed rerun, then the
  whole set once more. A failure may belong to A1–R1; fix it and name the task in As built.
- Do not run the no-argument library sweep; A3 owns it.

Record in Status (built but unverified): /dev:feature and /design:prototype untried in a real
project session; trigger phrases untested.

Commit: `chore: 014 gate, the whole set green (014 G1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A3 — audit round 1, the lint sweep and the front doors (general-purpose, docs)

````
Depends on: G1
Agent: general-purpose · Stack: docs

Task A3 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: start the
read-only skill-authoring audit. Sweep the whole library with the lint, then judge every listed
front door against the standard's judgment rules.

Read, in this order:
1. CLAUDE.md (repo root): "Review behavior" (the findings table and severities).
2. The plan: §3, §8, D7, task A3, and "Close-out — every task".
3. engineering-practices/writing-for-agents/SKILL.md, the rule table.
4. Then the front doors themselves, one at a time, as you judge them.

Do:
- `python3 tools/skill-lint.py --json > /tmp/skill-lint-r1.json` and `python3 tools/token-audit.py --violations-only`;
  summarise counts per plugin × rule with a short python one-off. Never paste the raw JSON into
  the report.
- List the listed front doors (registered skills without `disable-model-invocation: true`) and
  write the list into the report.
- Judge each against R4 and R15–R23. Read the `rules` skills as a group; they share one shape.
- Write docs/audits/<NNN>-skill-authoring-r1.md (next free NNN in docs/audits/): scope, the lint
  summary, the front-door list, findings under Data issues / Code issues / Logical conflicts (each
  heading present, `None.` when empty), house review table rows citing rule ids.

Traps:
- A lint false positive is a lint defect: fix tools/skill-lint.py, add a fixture that pins it,
  rerun its tests, and say so in As built.
- Read-only for every skill: fix nothing outside tools/ and the report.

Gate (own tests):
  python3 tools/skill-lint.py --json > /tmp/skill-lint-r1.json; test $? -le 1
  python3 -m pytest tools/test_skill_lint.py -q   (only if you changed the lint)

Commit: `docs(audits): skill-authoring audit r1, lint sweep and front doors (014 A3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A4 — audit round 1, the agents and the sample (general-purpose, docs)

````
Depends on: A3
Agent: general-purpose · Stack: docs

Task A4 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: finish the audit
report A3 started. Judge each plugin's front-door agent and one sampled hidden skill per domain
folder, then write the summary.

Read, in this order:
1. CLAUDE.md (repo root): "Review behavior".
2. The plan: §3, §8, task A4, A3's As built, and "Close-out — every task".
3. engineering-practices/writing-for-agents/SKILL.md, the rule table; .skill-template/agent.md.
4. The report A3 wrote in docs/audits/.

Do:
- Front-door agents: for each plugin in marketplace.json, the agent its plugin-name command runs
  (read the command file to find it). Judge against R13–R23.
- The sample: the largest hidden SKILL.md in each top-level domain folder (qa, frontend, desktop,
  mobile, design, backend, observability, data, devops, security, business-analysis,
  training-data, tooling, engineering-practices). Name the paths in the report.
- Append the findings in the same three classes, then the summary: totals by severity and class,
  and the five rules with the most findings.

Traps:
- An agent file can be 14k characters; read one, write its rows, then move on. Do not hold all of
  them before writing.
- Read-only: fix nothing.

Gate: none. The deliverable is the report; the lint ran in A3.

Commit: `docs(audits): skill-authoring audit r1, agents and sample (014 A4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### A5 — the remediation plan, and filing 014 (general-purpose, docs)

````
Depends on: A4
Agent: general-purpose · Stack: docs

Task A5 of docs/plans/014-authoring-standard-domain-language-feature-prototype.md: turn the audit
into the remediation plan, then file this plan as its last task.

Read, in this order:
1. CLAUDE.md (repo root): "Planning".
2. engineering-practices/writing-plans/references/plan-format.md, all of it.
3. The audit report in docs/audits/ (<NNN>-skill-authoring-r1.md).
4. This plan: header, §8, task A5, and "Close-out — every task".

Write docs/plans/<next>-skill-authoring-remediation.md, with the next free number across
docs/plans/ and docs/plans/implemented/:
- §1 Need | Today | Gap from the report's findings.
- Tasks: stack docs, agent general-purpose, one per cluster of findings by plugin, merged until a
  session would pass ~150k. Mechanical findings batch by rule; judgment findings go with their
  skill. Each gate: `python3 tools/skill-lint.py <its paths>` + `python3 tools/plugin-surface-check.py`.
- A gate task that sweeps every touched path, and its prompts, the close-out section and the task
  table per plan-format.
- Header: `Documentation task: none — <why>` and `Test design: none — <why>`.

Traps:
- Fix no skill here.
- Every remediation prompt names the exact paths and rule ids it fixes; never "the findings in the
  report".

Gate: none. It writes a plan document.

Commit: `docs(plans): <next> skill-authoring remediation, from the 014 audit (014 A5)`.
You delete the last prompt block, so you file this plan (close-out step 8).
Close out per the plan's "Close-out — every task" before you stop.
````
