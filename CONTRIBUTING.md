# Contributing to SkillsLibrary

This guide covers how to add a new skill so that Claude actually triggers it correctly and the output stays consistent across the library.

## The three-layer model

For most domains, a skill comes in one of three shapes:

- **reference** — answers conceptual questions. No code is generated, no files are touched.
- **generator** — scaffolds code into the active repo. Asks at most 2–3 clarifying questions.
- **reviewer** — reads existing code and returns findings. Does not rewrite.

If a domain is procedural (Auth0 setup, pipeline YAML) one combined skill is fine.

## File layout

Each skill lives in its own directory and contains a single `SKILL.md`:

```
qa/test-case-writer/SKILL.md
backend/dotnet/skills/pattern-writer/SKILL.md
```

Supporting templates or examples go alongside:

```
qa/test-case-writer/
├── SKILL.md
├── templates/
│   ├── functional-test-case.md
│   └── api-test-case.md
└── examples/
    └── login-test-cases.md
```

## SKILL.md structure

Every skill follows the same outline. Copy the right file from `.skill-template/`.

1. **YAML frontmatter** — `name`, `description`. The description is what Claude uses to decide whether to load this skill.
2. **When to use** — concrete trigger phrases.
3. **When NOT to use** — explicit disambiguation from sibling skills.
4. **Inputs needed** — what Claude should know before generating output.
5. **Procedure** — numbered steps Claude follows.
6. **Output format** — exact shape of what gets produced.
7. **Examples** — at least one good example, ideally one bad example with rationale.

## Agent structure

Step-by-step orchestrator agents live in `<domain>/agents/<name>.md`. Copy `.skill-template/agent.md` and keep its section skeleton: role + **two-modes note** → Skill-loading protocol → Operating rules → **Working on existing \<X\> (brownfield)** → Steps → Related agents → Output contract (both shapes) → When uncertain. Keep the template's `Gate:` line in Operating rules verbatim: inside a plan task it overrides the agent's own exit criteria.

**Vocabulary is fixed.** An agent's own operating procedure is numbered in **steps** (`## Steps`, `| # | Step | Goal | …`); the work items any plan it writes hands out are **tasks** (flat and ordered, ids prefixed by the family of work — `C1`, `B1…Bn`, `F1…Fn` — one deliverable each) — see the Planning rules in `CLAUDE.md`. Never call either a *phase* or a *slice*, in a heading, a table, or prose.

**The brownfield structure is mandatory.** Every agent must be able to orient in an existing codebase/suite/schema, fix (Mode A: reproduce → triage → smallest correct change → verify → sweep the class), and extend (Mode B: reuse existing seams, re-enter only the touched steps) — not just author from zero. That means: the two-modes note up top, the four-part `## Working on existing <X> (brownfield)` section, the `Mode: FIX | EXTEND` brownfield output contract, and the `dev:*` loading sentence (or the inlined-discipline variant when the agent's plugin doesn't depend on `dev` — see `data-architect`). An agent PR without this section is incomplete.

## Writing a good `description`

This is the highest-leverage line in the whole skill. Claude reads only descriptions when deciding which skills are relevant — if the description is vague, the skill won't trigger; if it's too broad, it'll trigger for the wrong things.

Rules:
- Start with "Use when..." and list concrete trigger phrases.
- Include the stack/language if the skill is stack-specific.
- Include an explicit "Do NOT use for..." clause to disambiguate from siblings.
- Stay within ≤ 500 characters for a skill and ≤ 650 for an agent — `tools/token-audit.py` enforces both. Trim restated detail, never the Do-NOT clause.

Good:
> Use when the user asks to write, derive, or generate formal test cases from requirements, user stories, or acceptance criteria. Triggers: "write test cases for X", "derive test scenarios from these ACs". Do NOT use for exploratory test charters (use qa/exploratory-charter-writer) or for writing automation code (use qa/api-test-author or qa/ui-test-author).

Bad:
> Helps with test cases.

## Naming conventions

- Folders: `kebab-case`
- Stack-specific skills: include the stack in the path (`auth/auth0-react`, not `auth/react`)
- Folders do not move when a skill is renamed — paths are how agents load skills, and about 140 files cite them. A `name:` may differ from its folder.

## Names and registration

**Bundle within a category, depend across categories.** One plugin per category is installed per project (`qa-*`, `fe-*`, `mobile-*`, `be-*` are the categories with several stacks; every other plugin is its own). Sharing inside a category is bundled and duplicates nothing. Anything used by more than one category is registered in exactly one plugin (`dev`, `design`) and the others declare it in `dependencies` by bare name. A skill folder or agent file is never registered by plugins of two categories. Internals loaded by path (`engineering-practices/{agent-orientation-cache,code-comments,standards-audit-engine}`, `auth/_shared/*`) are not registered.

**Skills**
- `name:` is the topic only. The plugin namespace already carries the domain and the stack, so a name never starts with the plugin's name or a domain prefix (`be-`, `fe-`, `qa-`, `mobile-`, `ba-`, `ep-`, `td-`, `tool-`, `secgov-`, `pentest-`, `purpleteam-`, `auth-`, `be-shared-`, `mobile-shared-`) and never ends in a stack token or `-shared`. The forms skill of `fe-react` is named `forms` and typed `/fe-react:forms`.
- Unique within every plugin that registers it, counting command names too: skills and commands share one slash namespace per plugin.
- One meaning per word: `-setup` creates a project, `-review` reviews, `audit` is a saved read-only sweep, `concepts` explains how a framework works.

**Commands**
- A plugin's front-door agent command is the plugin's name (`/fe-react`, `/be-java`, `/data`, `/devops`).
- Every read-only conformance audit is `audit` (`/be-dotnet:audit`, `/design:audit`, `/dev:audit`).
- Every other command is a short role or topic (`/qa-java:api`, `/penetration-testing:pentest`).
- Agent identifiers do not change (`code-auditor`, `solution-planner`, `devops-engineer`); plans' `Agent:` lines bind on them. Only command file names change.

**Reserved names.** No skill name or command stem may equal a Claude Code built-in (list as of 2026-10-11): `add-dir agents artifacts bug clear claude-api code-review compact config context cost dataviz doctor effort exit export fast feedback fewer-permission-prompts focus help hooks ide init install-github-app keybindings-help login logout loop mcp memory migrate-installer model output-style permissions plan plugin plugin-authoring pr-comments privacy-settings release-notes resume review rewind run schedule security-review simplify status statusline terminal-setup todos update-config upgrade usage vim workflow-authoring`.

**Before a commit that touches `.claude-plugin/marketplace.json` or a `name:`**, `python3 tools/plugin-surface-check.py` must print `OK`; it enforces unique names per plugin, the reserved list, no prefixes, one category per skill and agent, resolvable dependencies with no cycle, and that every registered path exists. Rename a skill only with the references that cite it, and record it in the plan that renamed it.

## Testing a new skill

Before merging:

1. Use the skill in a real conversation with Claude Code or Claude Desktop.
2. Try at least three different trigger phrases.
3. Try one phrase that should NOT trigger it — make sure it doesn't.
4. If it's a generator, run the generated code.
5. If it's a reviewer, point it at code with known issues and verify it catches them.

## Versioning

Skills are versioned via git. If you make a breaking change to a skill's output format, call it out in the commit message.

## Pull request checklist

- [ ] New skill follows the template
- [ ] Description starts with "Use when..." and includes a "Do NOT use for..." clause
- [ ] At least one full example in the skill
- [ ] Tested with 3+ trigger phrases
- [ ] Listed in the appropriate section of the root `README.md` status table
- [ ] `name:` is the topic only and `python3 tools/plugin-surface-check.py` prints `OK`
