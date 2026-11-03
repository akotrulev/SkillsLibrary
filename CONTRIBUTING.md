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

Agents live in `<domain>/agents/<name>.md` and are **thin routers**: they say in what order to work and where the boundaries are, and nothing else. The standards live in the plugin's rule files, the know-how in its skills, and a plan task's close-out in the plan itself (`plan-format.md` §7). Copy `.skill-template/agent.md` and keep its skeleton: role paragraph → invariants (only where the domain has real ones) → **Every run, before writing anything** (read the rule files, orientation-cache gate, version detection, green build first, read 2–3 representative files) → **Steps** (`| # | Step | Load | Done when |`) plus one paragraph on fix and extend → **Boundaries** (peer fences; in a plan task the prompt block, the plan's `## Close-out — every task` and its `Gate:` line decide; acceptance tests are read-only) → cache update → one **Report** template. An agent does not restate a rule file, the plan-execution protocol, or a list of related agents. Reference: `backend/java/agents/be-java.md`.

**Vocabulary is fixed.** An agent's own operating procedure is numbered in **steps** (`## Steps`, `| # | Step | Goal | …`); the work items any plan it writes hands out are **tasks** (flat and ordered, ids prefixed by the family of work — `C1`, `B1…Bn`, `F1…Fn` — one deliverable each) — see the Planning rules in `CLAUDE.md`. Never call either a *phase* or a *slice*, in a heading, a table, or prose.

**Brownfield is still mandatory, in less space.** Every agent orients in an existing codebase before changing it, fixes (reproduce → triage → smallest correct change → verify → sweep the class, loading `dev:debugging` and `dev:verify`) and extends (re-enter only the touched step, reuse the seams orientation found). Its report template has a `Mode: BUILD | FIX | EXTEND` line.

## Code standards are rules, installed per project

A stack's do/don't standards are **Claude Code rules**, not skill sections: files with `paths:` glob frontmatter that Claude Code loads automatically once a session (or a subagent) reads, writes or edits a matching file. Plugins cannot ship rules, so each stack plugin carries an install skill, `<stack dir>/skills/rules/`, invoked as `/<plugin>:rules` (`disable-model-invocation: true`), which copies its rule files into the project's `.claude/rules/<plugin>/`.

- **Split by path, so a session loads only what its files need**: a core file for the stack's source files, plus persistence, tests, config or whatever the stack needs. Core ≤ 6k characters, every other file ≤ 2.5k.
- Each file opens with its `paths:`, an HTML version comment, the one-line severity scale, and (core file) "the codebase wins" plus version detection. Each rule is one bullet ending in its review severity tag.
- Where a file extension is shared with another stack in a monorepo (TypeScript, C#, Kotlin), the default globs stay narrow and the install skill finds where this stack's code really lives and proposes globs for it.
- A skill does not restate a rule: its `## Rules` section points at the rule file. The reviewer skill's checklist **is** the rule files. Provider- or tool-specific configuration rules (an auth provider, an exporter) stay in their skill.
- Prove new globs before merging: a scratch project with the rule files installed and an `InstructionsLoaded` hook logging to a file, then `claude -p "Read <sample files>"`; each file must load for its sample and not for a non-matching file. Reference: `backend/java/skills/rules/`.

## Writing a good `description`

This is the highest-leverage line in the whole skill. Claude reads only descriptions when deciding which skills are relevant — if the description is vague, the skill won't trigger; if it's too broad, it'll trigger for the wrong things.

Every enabled skill's description is sent on every request, inside a listing budget of about 1% of the context window. When the listing overflows, Claude Code drops descriptions, starting with the least-used skills. Those skills then show as bare names and never trigger. A project enables several plugins with about 200 skills between them, so the budget per skill is small.

Rules:
- **≤ 200 characters for a skill** and ≤ 650 for an agent. `tools/token-audit.py` enforces both.
- Start with "Use when..." and the key use case. Name the stack or tool if the skill is stack-specific, since those words drive matching.
- Then one or two quoted trigger phrases, written `Triggers "a", "b".` Never write `Triggers:`. A colon followed by a space breaks a plain YAML scalar.
- End with one "Not for X (sibling)." clause naming the closest confusable sibling in the same plugin.
- Leave enumerations, version lists and scope prose to the body.

Good:
> Use when deriving formal manual test cases from requirements, stories or ACs. Triggers "write test cases for X", "derive scenarios from these ACs". Not for exploratory charters (exploratory-charter-writer).

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
- [ ] Description is ≤ 200 characters, starts with "Use when..." and ends with a "Not for..." clause
- [ ] At least one full example in the skill
- [ ] Tested with 3+ trigger phrases
- [ ] Listed in the appropriate section of the root `README.md` status table
- [ ] `name:` is the topic only and `python3 tools/plugin-surface-check.py` prints `OK`
