# Skill, agent and rule-file mechanics

The branch of the standard that applies when the document is a skill, an agent or a rule file: its frontmatter, whether the model sees it, its description, its shape and its name. The writing levers and the rule table are in `../SKILL.md`; the rule ids below point into that table.

## Frontmatter

| File | Keys | Notes |
|---|---|---|
| Skill (`SKILL.md`) | `name`, `description`, and `disable-model-invocation: true` unless the skill is a front door | R1, R2, R3, R5. The description is a plain scalar, so it holds no colon followed by a space |
| Agent (`<domain>/agents/<name>.md`) | `name` (matches the file name), `description`, `tools` (only what the agent uses), `model: inherit` | R2. The `tools:` list is sent with the description on every request |
| Command (`<domain>/commands/<name>.md`) | `description`, `disable-model-invocation: true` | R5. A command is typed by a person; the model reaches the same workflow through the agent |
| Rule file | `paths:` globs | Loaded automatically once a session reads, writes or edits a matching file |

## Front door or hidden

A **front door** is a skill listed to the model: its description goes out with every request, and a session can load it on a description match. Every other registered skill is **hidden** (`disable-model-invocation: true`). A hidden skill is still typed as `/<plugin>:<name>`, and agents and commands still `Read` it by path.

**Make a skill a front door only when** a main session must reach it on its own trigger and no agent or command reaches it: a plugin's `rules` skill (a model runs it while setting a project up), a workflow skill a person starts with no agent behind it, a skill no agent step loads. Each front door costs about 50 tokens in every session of every project that enables the plugin, and the listing has a budget of about 1% of the context window; past it, Claude Code drops the least-used descriptions and those skills stop triggering. The list is `FRONT_DOORS` in `tools/plugin-surface-check.py`, and the checker fails on a listed skill outside it and on a hidden one inside it (R5).

What follows from the choice:

- **A hidden skill is reached by path.** An agent's `Load` cell, a command or another skill names the path to `Read`. The Skill tool refuses a hidden skill, so no line tells a model to invoke one through it (R12).
- **A hidden skill carries no routing sections.** Its agent's Steps table picks it, so `When to use`, `When NOT to use`, `Handoffs` and `Related` would be read on every load and decide nothing (R6). A rule about which of two skills owns a decision is content: it goes under `Rules`.
- **A front door carries `When to use` and `When NOT to use`** (R7), because a session chooses it from its description and needs the fences once loaded.
- **A pointer a main session follows names the agent** (R22). A front door and a rule file are read by sessions holding the Skill tool, where a bare hidden `plugin:name` is something the model cannot act on. Write "delegate to the `business-analyst` agent, which loads it, or type `/product:conflict-check`". Inside a hidden skill the bare form is fine: its reader is an agent that loads by path.
- **A hidden skill cannot be preloaded** through an agent's `skills:` frontmatter. Agents here load by path, so nothing depends on it.

## The description

For a front door the description is the pointer that decides whether the skill is ever loaded; for a hidden skill it is the line a person reads in the `/` menu. Both take the same shape.

**Shape (R3):** `Use when <the situation>.` then `Triggers "a", "b".` then `Not for <the confusable case> (<sibling>).`

- **Lead with the situation.** "Use when" plus the key case, in the words a user types. Name the stack or tool when the skill is specific to one: those words do the matching.
- **One or two triggers**, quoted, after the word `Triggers` and a space. A colon after it, or a colon and a space anywhere in the line, makes the frontmatter invalid YAML, and `plugin-surface-check` fails on it.
- **One `Not for` clause** naming the closest sibling a model could confuse it with, in the same plugin.
- **When, not how** (R4). At most one clause on what the skill produces. A description that summarises the workflow becomes the workflow: the model follows the summary and skips the body. "Use when executing plans; dispatches a subagent per task with a review between tasks" ran one review where the body required two; cut to the situation, the body's two reviews ran.
- **Describe the problem, in the third person.** "Use when tests pass and fail on the same code" beats "Use when tests call `sleep`" (a symptom) and "I can help with flaky tests" (first person, sent as system text).
- **Leave lists to the body**: enumerations, version lists and scope prose.
- **Sizes (R2):** a skill description ≤ 200 characters; an agent description ≤ 360, saying what the agent does and for which stack, two triggers, and the two or three closest siblings.

Good:

> Use when deriving formal manual test cases from requirements, stories or ACs. Triggers "write test cases for X", "derive scenarios from these ACs". Not for exploratory charters (exploratory-charter-writer).

Bad, and why:

> Helps with test cases.

No situation, no trigger, no sibling: it matches everything about tests and nothing in particular.

> Use for TDD. Write the test first, watch it fail, write the minimal code, refactor.

The workflow in the description (R4): the model runs these four words and never reads the body.

## Skill body

In the SkillsLibrary repo, copy the matching file from `.skill-template/` (`CONTRIBUTING.md`, "The three-layer model", says which). The outline: **Inputs needed** → **Procedure** (numbered steps, each ending on its done-when, R15) → **Output format** (the exact shape produced) → **Examples**.

- **One excellent example** beats several thin ones. Write it in the stack the skill serves, as runnable code that obeys the house code, comment and test rules (R21). A story about one past session is not an example: write the general case.
- **Reference that only some branches reach** goes to `references/<topic>.md`, behind a pointer naming its condition (R16). A reference file over 300 lines opens with a contents list (R9).
- **A skill points at a rule file and never restates it** (R17). A stack's do/don't standards live in its rule files; the skill's `## Rules` section is a pointer, and a reviewer skill's checklist is the rule files.

## Agents: thin routers

An agent says in what order to work and where its boundaries are. The standards live in the plugin's rule files, the know-how in its skills, and a plan task's close-out in the plan. Copy `.skill-template/agent.md` and keep its skeleton:

1. a role paragraph;
2. invariants, only where the domain has real ones no rule file states;
3. **Every run, before writing anything**: read the rule files, run the orientation-cache gate, detect versions, confirm green on arrival, read two or three representative files;
4. **Steps**: `| # | Step | Load | Done when |` (R13), then one paragraph on fix and extend;
5. **Boundaries**: the peer fences; in a plan task the prompt block, the plan's close-out and its `Gate:` line decide; acceptance tests are read-only;
6. the orientation-cache update;
7. one **Report** template with a `Mode: BUILD | FIX | EXTEND` line (R13).

An agent restates no rule file, no plan-execution protocol and no list of related agents (R17). Reference: `backend/java/agents/be-java.md`.

**A step loads by condition.** A skill costs 2–5k tokens each time an agent reads it, so a `Load` cell holds two groups split by a `·`: the skills every task entering the step needs, then `<what the task contains> → <skill>` for the rest. Keep the first group to what no task in that step can do without. A form, an API call, a new route, motion, translated text and each platform feature are conditions. A condition names something visible in the task or the code (R14). Measured on `fe-react` (2026-11-20): a task entering steps 2 to 5 read about 72k tokens of skills unconditionally, and 30k plus its conditions once the cells were split.

**Brownfield is part of every agent.** It orients in an existing codebase before changing it; it fixes (reproduce → triage → smallest correct change → verify → sweep the class, loading `engineering:debugging` and `engineering:verify`); it extends (re-enter only the touched step, reuse the seams orientation found).

**Vocabulary is fixed** (R11, R20). An agent's own procedure is numbered in **steps**. The work items of a plan it writes are **tasks**: flat, ordered, ids prefixed by the family of work (`C1`, `B1…Bn`, `F1…Fn`), one deliverable each.

## Rule files

A stack's do/don't standards are Claude Code rule files with `paths:` globs, installed into a project's `.claude/rules/<plugin>/` by the plugin's `rules` skill (`CONTRIBUTING.md`, "Code standards are rules, installed per project", covers the install).

- **Split by path**, so a session loads only what its files need: a core file for the stack's source files, plus one each for persistence, tests, config or whatever the stack has. The core file is ≤ 6,000 characters and every other file ≤ 2,500 (R23).
- **Each file opens** with its `paths:`, an HTML version comment and the one-line severity scale; the core file adds "the codebase wins" and version detection. Each rule is one bullet ending in its review severity tag.
- **Pointers, not content** (R23). A rule file is always loaded once its glob matches, so a procedure or a template goes in a skill it points at, and the pointer names the agent (R22).
- **Two plugins loading on the same file never contradict.** Each rule file says which side it owns: a `be-*` persistence file owns the ORM and the driver, `data` owns the engine and the schema; the QA CI file owns test jobs, `devops` owns build, deploy and infra-gate jobs.
- **A non-stack plugin writes rules only where earned**: it holds standards for files at stable project paths (migrations, Dockerfiles, CI files, `docs/plans/**`, `docs/business-model/**`, dataset files) that a session outside the plugin's agent edits. A document rule holds the document's standards, never its template or procedure.

## Names

- **Folders are kebab-case.** A stack-specific skill carries its stack in the path (`auth/auth0-react`, not `auth/react`).
- **`name:` is the topic only** (R1). The plugin namespace already says the domain and the stack, so a name carries no domain prefix (`be-`, `fe-`, `qa-`, `mobile-`, `ba-`, `ep-`, `td-`, `tool-`, `secgov-`, `pentest-`, `purpleteam-`, `auth-`, `be-shared-`, `mobile-shared-`) and no stack or `-shared` suffix. The forms skill of `fe-react` is `forms`, typed `/fe-react:forms`.
- **Unique per plugin, counting commands**: skills and commands share one slash namespace per plugin. A name is never a Claude Code built-in (the reserved list is in `CONTRIBUTING.md`, "Names and registration").
- **One meaning per word** (R20): `-setup` creates a project, `-review` reviews, `audit` is a saved read-only sweep, `concepts` explains how a framework works.
- **Folders stay put when a skill is renamed.** Agents load skills by path and about 140 files cite those paths, so `name:` may differ from its folder.
- **Commands:** a plugin's front-door agent command is the plugin's name (`/fe-react`, `/data`); every read-only conformance audit is `audit`; every other command is a short role or topic. Agent identifiers never change, because plans' `Agent:` lines bind on them.
