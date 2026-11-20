# Contributing to SkillsLibrary

This guide covers the contributor workflow: where a skill goes, how it is registered and tested, and the PR checklist. **How to write anything an agent reads** (skills, agents, rule files, `CLAUDE.md`) is the house standard, [`engineering/writing-for-agents/SKILL.md`](engineering/writing-for-agents/SKILL.md), with the skill, agent and rule-file mechanics in its [`references/skill-mechanics.md`](engineering/writing-for-agents/references/skill-mechanics.md). Its rules carry ids, `R1`–`R23`, which the checklist below, `tools/skill-lint.py` and every review cite.

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

Copy the right file from `.skill-template/` and keep its outline: frontmatter, **Inputs needed**, **Procedure**, **Output format**, **Examples**. How to fill it in, which sections a hidden skill and a front door carry (R6, R7), and what an example must obey (R21) are in `engineering/writing-for-agents/references/skill-mechanics.md`, "Skill body".

## Agent structure

Agents live in `<domain>/agents/<name>.md`. Copy `.skill-template/agent.md`; the reference agent is `backend/java/agents/be-java.md`. The skeleton, the conditional `Load` cells, the `Mode:` line and the fixed vocabulary are in `engineering/writing-for-agents/references/skill-mechanics.md`, "Agents: thin routers" (R11, R13, R14).

## Code standards are rules, installed per project

A stack's do/don't standards are **Claude Code rules**, not skill sections: files with `paths:` glob frontmatter that Claude Code loads automatically once a session (or a subagent) reads, writes or edits a matching file. Plugins cannot ship rules, so each stack plugin carries an install skill, `<stack dir>/skills/rules/`, invoked as `/<plugin>:rules` by a person or as `<plugin>:rules` by a model setting a project up (so it never carries `disable-model-invocation`), which copies its rule files into the project's `.claude/rules/<plugin>/`. Its `Run by a person or by a model` section is the same in every plugin: the `replace | keep | beside` argument, and what an unattended run does when a step needs an answer.

- Where a file extension is shared with another stack in a monorepo (TypeScript, C#, Kotlin), the default globs stay narrow and the install skill finds where this stack's code really lives and proposes globs for it.
- Prove new globs before merging: a scratch project with the rule files installed and an `InstructionsLoaded` hook logging to a file, then `claude -p "Read <sample files>"`; each file must load for its sample and not for a non-matching file. Reference: `backend/java/skills/rules/`.

How a rule file is written (split by path, sizes, its opening lines, which side it owns, when a non-stack plugin earns one) is in `engineering/writing-for-agents/references/skill-mechanics.md`, "Rule files" (R23).

## Front doors: which skills the model sees

**A skill is listed to the model only when it is a front door** (R5). Every other registered skill carries `disable-model-invocation: true`; a person can still type `/<plugin>:<name>`, and agents and commands `Read` it by path. Every command carries it too.

The list is `FRONT_DOORS` in `tools/plugin-surface-check.py`. The checker fails when a skill outside it is listed, when a front door is hidden, and when a command is listed. When a skill earns a front door, and what follows from the choice (no routing sections in a hidden skill, pointers by path, pointers that name the agent), is in `engineering/writing-for-agents/references/skill-mechanics.md`, "Front door or hidden".

## Writing a good `description`

The shape (R3), the when-not-how rule (R4), the sizes (R2) and the good and bad examples are in `engineering/writing-for-agents/references/skill-mechanics.md`, "The description". `tools/token-audit.py` enforces the sizes, and `tools/plugin-surface-check.py` fails on a colon followed by a space in the line.

## Names and registration

**Bundle within a category, depend across categories.** One plugin per category is installed per project (`qa-*`, `fe-*`, `mobile-*`, `be-*` are the categories with several stacks; every other plugin is its own). Sharing inside a category is bundled and duplicates nothing. Anything used by more than one category is registered in exactly one plugin (`engineering`, `design`) and the others declare it in `dependencies` by bare name. `product` (planning, documentation, requirements, business analysis) is the opposite case: it depends on `engineering`, no stack plugin depends on it, and a project enables it itself, so a stack file that hands off to a `product` skill or command names the plugin and stops when it is off. A skill folder or agent file is never registered by plugins of two categories. Internals loaded by path (`engineering/{agent-orientation-cache,code-comments,standards-audit-engine}`, `auth/_shared/*`) are not registered.

Name rules for skills and commands (topic only, no prefix or suffix, unique per plugin, one meaning per word, folders stay put on a rename) are in `engineering/writing-for-agents/references/skill-mechanics.md`, "Names" (R1).

**Reserved names.** No skill name or command stem may equal a Claude Code built-in (list as of 2026-10-11): `add-dir agents artifacts bug clear claude-api code-review compact config context cost dataviz doctor effort exit export fast feedback fewer-permission-prompts focus help hooks ide init install-github-app keybindings-help login logout loop mcp memory migrate-installer model output-style permissions plan plugin plugin-authoring pr-comments privacy-settings release-notes resume review rewind run schedule security-review simplify status statusline terminal-setup todos update-config upgrade usage vim workflow-authoring`.

**Before a commit that touches `.claude-plugin/marketplace.json` or a skill's frontmatter**, `python3 tools/plugin-surface-check.py` must print `OK`; it enforces unique names per plugin, the reserved list, no prefixes, one category per skill and agent, resolvable dependencies with no cycle, that every registered path exists, that only front doors are listed to the model, that every command is hidden from it, and that no skill description holds an unquoted colon and space. Rename a skill only with the references that cite it, and record it in the plan that renamed it.

## Testing a new skill

Before merging:

1. Use the skill in a real conversation with Claude Code or Claude Desktop: a hidden skill through its agent or by typing `/<plugin>:<name>`, a front door by description.
2. For a front door, try at least three different trigger phrases.
3. For a front door, try one phrase that should NOT trigger it — make sure it doesn't.
4. If it's a generator, run the generated code.
5. If it's a reviewer, point it at code with known issues and verify it catches them.

## Versioning

Skills are versioned via git. If you make a breaking change to a skill's output format, call it out in the commit message.

## Pull request checklist

Each item cites its rule in `engineering/writing-for-agents`.

- [ ] The skill copies its `.skill-template/` file and keeps its outline
- [ ] Description: ≤ 200 characters (R2), `Use when` … `Triggers "a", "b".` … `Not for <case> (<sibling>).` (R3), the situation and never the workflow (R4)
- [ ] `disable-model-invocation: true` is set, unless the skill is a front door added to `FRONT_DOORS` (R5)
- [ ] A hidden skill has no routing sections (R6); a front door has `When to use` and `When NOT to use` (R7)
- [ ] Every pointer resolves, no placeholder is left, and no line invokes a hidden skill through the Skill tool (R8, R10, R12)
- [ ] Every step ends on a checkable done-when (R15)
- [ ] At least one full example, obeying the house code, comment and test rules (R21)
- [ ] An agent: a Steps table with `Load` and `Done when`, a Report with a `Mode:` line (R13), and a visible condition in every `Load` cell (R14)
- [ ] Tested through its agent or typed name; a front door with 3+ trigger phrases
- [ ] Listed in the appropriate section of the root `README.md` status table
- [ ] `name:` is the topic only (R1); `python3 tools/plugin-surface-check.py` prints `OK`, and `python3 tools/skill-lint.py <path>` and `python3 tools/token-audit.py --violations-only` report nothing for the files touched
