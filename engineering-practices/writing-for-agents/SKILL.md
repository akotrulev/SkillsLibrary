---
name: writing-for-agents
description: Use when writing or editing a skill, agent, rule file or CLAUDE.md. Triggers "write a skill", "tighten this CLAUDE.md". Not for plan documents (plan-feature).
---

# Writing for agents

The house standard for every document a model reads: a skill, an agent, a rule file, a `CLAUDE.md`, and any file one of them points at. A model runs such a document many times, and the aim is that it takes the same path through it every time. The levers below decide that path. The rule table at the end gives each checkable part an id that the lint, the audit and a review cite.

When the document is a skill, an agent or a rule file, also read `references/skill-mechanics.md`: frontmatter, front door or hidden, the description shape, the agent template, rule files and names.

## Procedure

1. **List the branches.** A branch is one distinct case the document handles: a front door or a hidden skill, a new feature or a shaped one, a .NET 8 project or a .NET 10 one. Done when each branch has a one-line name.
2. **Place every piece on the hierarchy** (below): steps first, then the reference every branch needs, then a pointer to each piece only some branches reach. Done when nothing inline is used by one branch alone.
3. **End each step on its completion criterion.** Done when every step has a `Done when` a reader can check.
4. **Prune** with the four tests under Pruning. Done when every sentence has passed the no-op test.
5. **Check against the rule table.** Run the enforcers on the file (in the SkillsLibrary repo: `python3 tools/skill-lint.py <path>`, `python3 tools/token-audit.py --violations-only`, `python3 tools/plugin-surface-check.py`), then read the file once per judgment rule. Done when every enforcer is clean for the file and every judgment rule is marked pass or not applicable.

## Pointers

A **pointer** is a line in context that names material outside it and says when to fetch it: a skill's description, an agent's `Load` cell, a `CLAUDE.md` line naming a doc, "read X when Y". The pointer's wording, not the material behind it, decides how often the model fetches it. When must-have material is fetched only some of the time, sharpen the pointer's condition first, and inline the material only if the sharper pointer still misses.

A pointer carries two things: what the material is, and each branch that should fetch it.

- **Lead with the trigger word.** The first words of a pointer do the matching.
- **One condition per branch.** Three synonyms for one case are one condition; keep the word a user would type.
- **Name a visible condition.** "a form in the task → `forms`" fires on something the model can see. "When relevant" leaves the fetch to chance (R14).
- **Leave the detail to the target.** What the material contains belongs in the material.

## The two loads

Every line spends one of two budgets.

- **Context load** is what sits in the window on every turn: a `CLAUDE.md`, a rule file once loaded, every listed description. It is paid whether the line fires or not, and it thins attention for everything beside it.
- **Cognitive load** is what a person has to remember: which skills exist, which command to type. A hidden skill moves its whole cost here, so it costs no context, and someone has to know it exists.

Material behind a pointer costs only the pointer. So always-loaded text carries pointers, not content (R23), and each listed description is a deliberate purchase (R5).

## Information hierarchy

A document mixes **steps**, the actions taken in order, with **reference**, the facts, rules and definitions consulted on demand. Each piece sits on one of three rungs, by how soon the model needs it:

1. **an in-file step**, the main line;
2. **in-file reference**, under its own heading after the steps;
3. **disclosed reference**, a file under `references/` or anywhere else, behind a pointer that names its condition.

**Disclose by branch** (R16). What every branch needs stays inline; what only some branches reach moves down a rung. Reference left between the steps buries them, and a buried step is followed at random. Disclosing past need hides what the model must have. The decision is the balance between the two.

**Co-locate.** Once a piece has its rung, keep its definition, its rules and its exceptions under one heading. A concept gathered under one heading is read whole; one scattered across a file is read in fragments. Scattering splits one meaning across places; duplication repeats it (R17). Both are defects.

**Sprawl** is a file too long even when every line is live: attention spreads thin over the surplus. Cure it with the hierarchy. Disclose, or split.

## Completion criteria

Every step ends on a **done when**: the state that tells the model the step is finished (R15). Two properties make it work.

- **Checkable.** Done is distinguishable from not done. "Understand the module" ends whenever the model feels ready to move on; "every public method listed with its callers" ends when it is true. A vague criterion with later steps in view pulls the model forward early: **premature completion**. Sharpen the criterion first. Only when it cannot be sharpened and the rush is observed, put the later steps behind a real context boundary: a subagent, a hand-off, a separate session. A later step in the same context stays in view.
- **Exhaustive where thoroughness matters.** "Every changed endpoint accounted for" drives the digging; "list the changes" does not. The same bar binds reference: "every rule in the table applied" makes a checklist exhaustive.

## When to split

A split adds a file and a pointer, so it spends a load. Split when the cut earns that.

- **By sequence:** a run of steps whose visible successors tempt the model to rush the current one. Merging two sequences has the opposite effect.
- **By invocation:** a part that must be reached on its own trigger, by a session with no agent behind it, becomes its own front door (`references/skill-mechanics.md`, "Front door or hidden").
- **By path:** a rule file splits by `paths:`, so a session loads only what its files need.

## Leading words

A **leading word** is one compact concept the model already knows, used as a token wherever the idea recurs: *tight* for a fast, deterministic loop, *red* for a gate that fails on the bug, *front door* for a listed skill. Repeated, it collects a definition from its uses and anchors a whole behaviour in one token. In a pointer, the same word in the user's prompts, the docs and the code makes the match reliable.

- **One concept, one word** (R20). The house vocabulary is fixed: *task*, *step*, *deliverable*, *front door*, *gate*, *done when*. A paraphrase such as "work item", "stage" or "check" reads as a different concept.
- **Prefer a known word to a coined one.** A coined word pays for its definition in tokens; a known word arrives with its meaning.
- **Collapse restatements.** A triad spelled out at three sites, or a sentence gesturing at one idea, is usually one word waiting to be used.
- **Pick a word strong enough to move the default.** "Be careful" changes nothing; name the check instead.

## Positive targets

State the behaviour wanted (R18). A prohibition names the unwanted behaviour and puts it in context, and the model reads the concept more strongly than the negation around it. "Write a one-line doc comment" lands; "avoid long comments" mostly says "long comments". Keep a prohibition for a hard guardrail only, and pair it with the target in the same sentence: "Commit on the current branch; never check out the default branch."

## Pruning

- **One meaning, one place** (R17). A rule lives in one file and everything else points at it. A copy costs tokens, drifts on the next edit, and raises the rule's weight past its rank. A leading word repeats a token on purpose; duplication repeats a meaning.
- **The environment is a source.** `package.json`, config files, the folder layout and `--help` answer for themselves. A document that restates them is a cache that goes stale. Cache only what no lookup reveals: the unwritten convention, the reason for a choice, the trap the config does not show.
- **Relevance.** Each line bears on what the document makes the model do. A line that never did, or one describing a world that has since moved, is **sediment**: it settles because adding feels safe and deleting feels risky. Delete it.
- **No-ops** (R19). Test each sentence: does it change what the model does, compared with its default? When it does not, delete the whole sentence rather than trimming words from it. A disagreement about a no-op is a disagreement about the default, settled by running the document.

## The rules

Each rule has an id that the lint, the audit and a review cite. **Enforced by** names the one tool that checks it, in the SkillsLibrary repo; *judgment* rules are checked in review, and outside this repo every rule is checked in review. Severities follow the review scale in `CLAUDE.md`. An id is never renumbered; a retired rule keeps its number.

| Rule | Applies to | Enforced by | Severity |
|---|---|---|---|
| **R1** — frontmatter has `name` and `description`; `name` is kebab-case and the topic only | skills | `plugin-surface-check` for registered skills (prefix, suffix, uniqueness) · `skill-lint` for presence and kebab-case on every skill | major |
| **R2** — size budgets: skill description ≤ 200 chars, body ≤ 16,000; agent description ≤ 360, file ≤ 14,000 | skills, agents | `token-audit` | major |
| **R3** — description shape: starts `Use when`, then `Triggers "a"` or `Triggers "a", "b".`, ends `Not for <case> (<sibling>).`; never `Triggers:` | skills | `skill-lint` | minor |
| **R4** — a description says *when*, plus at most one clause of *what*; never a summary of the workflow (the model follows the summary and skips the body) | skills | judgment | major |
| **R5** — listed to the model only when a front door | skills, commands | `plugin-surface-check` | major |
| **R6** — a hidden skill has no `When to use`, `When NOT to use`, `Handoffs` or `Related` heading | skills | `skill-lint` | minor |
| **R7** — a front door has `When to use` and `When NOT to use` | skills | `skill-lint` | minor |
| **R8** — pointers resolve: every relative Markdown link, and every backticked path under `references/`, `scripts/`, `templates/` or `examples/` in a skill or agent, exists relative to that file's folder; a path holding a placeholder (`<`, `{`, `*` or `…`) is a pattern and is skipped | skills, agents | `skill-lint` | major |
| **R9** — a reference file over 300 lines opens with a contents list of its `##` headings, before its first `##` | skill `references/*.md` | `skill-lint` | minor |
| **R10** — no placeholders: `TODO`, `TBD`, `FIXME`, `XXX` outside a code fence or an inline code span, and no `@path` force-load links | skills, agents | `skill-lint` | major |
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

## When to use

- Writing or editing a skill, an agent, a rule file, a `CLAUDE.md`, or a file one of them points at.
- Reviewing one of those: each finding cites its rule id.
- Cutting always-loaded text that has grown, or a description that no longer triggers.

## When NOT to use

- A plan document: `plan-feature` and the plan format own its shape.
- The contributor workflow around a skill in the SkillsLibrary repo (file layout, registration, testing, the PR checklist): `CONTRIBUTING.md`.
- Documentation written for people: delegate to the `be-documenter` agent.
