# 010 — One neutral source, built for Claude Code and Codex — plan (2026-11-07)

**Goal:** The library is written once, in a format neither tool owns, and a build script turns it into a
Claude Code plugin marketplace and a Codex plugin marketplace. A team using Codex (GPT) installs the same
22 plugins and gets the same skills, with agents and commands turned into skills, as a team using Claude.

**Status:** Planned 2026-11-07. Already done before the plan: the global rules moved to `AGENTS.md`,
and `CLAUDE.md` is now just the line `@AGENTS.md` (commit `0ebd5e3`). Next: H0 (the user installs `uv`),
then C1. Nothing else is built. This plan replaces Track A of `docs/plans/MODEL-PORTABILITY-PLAN.md`
(D1). Track B of that plan (small-model hardening) is untouched. Metered: only H1 runs Codex against a
model, and the user starts it.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| One instruction file both tools read in this repo | `AGENTS.md` holds the rules; `CLAUDE.md` is `@AGENTS.md` (`0ebd5e3`) | None |
| Skill frontmatter both tools accept | 532 `SKILL.md`, all with `name` + `description`; 21 also carry the Claude-only `disable-model-invocation` | A neutral way to say "only when asked for", turned into each tool's form |
| File references that work in any install | 167 files use `${CLAUDE_PLUGIN_ROOT}/…`, 21 use `${CLAUDE_SKILL_DIR}`, many add "fall back to `<path>` inside the SkillsLibrary repo" or use bare library paths | One token for "a file in this library", resolved per tool at build time |
| A record of what is in each plugin that is not Claude's format | `.claude-plugin/marketplace.json`: 22 entries, every one `source: "./"`, `strict: false`, with skill, agent and command lists | A neutral `plugins.json` from which both marketplaces are built |
| Claude packages | The whole repo is every plugin's root (`source: "./"`), so every install copies all of it | One built package per plugin under `dist/claude/` |
| Codex packages and a Codex marketplace | None | `dist/codex/<plugin>/` + `.agents/plugins/marketplace.json` |
| Agents on Codex | 63 `agents/*.md` with Claude `tools:` lists (42 share `Read, Write, Edit, Bash, Glob, Grep, WebSearch`; 12 add MCP tools) and `model: inherit` | Each agent built as a Codex skill (D5) |
| Commands on Codex | 67 `commands/*.md` using `$ARGUMENTS`; 10 share a name with an agent (`fe-react`, `be-dotnet`, …) | Each command built as a Codex skill; the 10 that only route to their agent are dropped on Codex (D5) |
| Plugin dependencies on Codex | 17 plugins depend on `dev` and/or `design`; Codex has no `dependencies` | Files a package reads are copied into it; the README says to install `dev`/`design` too (D6) |
| Path-scoped rules in a target project | 20 `rules` skills copy rule files into `.claude/rules/<plugin>/`; 320 files cite that path | Rules installed for Codex too, with an `AGENTS.md` index (D8) |
| Instruction-file name in skill prose | 195 files say `CLAUDE.md` | They say `AGENTS.md`; skills that create one write `AGENTS.md` + a `CLAUDE.md` that imports it |
| Tool names in prose | `Claude Code` in 42 files, `` `Read` `` in 75, `` `Write` `` in 26, Agent/Task tool or `subagent_type` in 17, `TaskCreate`/`AskUserQuestion`/… in 3 | Plain verbs, or a marked Claude-only/Codex-only block (§3) |
| Checks | `tools/plugin-surface-check.py` and `tools/token-audit.py` read the Claude marketplace; the reserved list is Claude's built-ins only | Both read `plugins.json`; Codex's built-in skill names reserved too; a check that `dist/` is up to date and the source is neutral |
| Docs | README installs for Claude only; `CONTRIBUTING.md` describes the Claude format | Codex install, the neutral format, the build step |

## 2. What Codex reads (checked 2026-11-07)

Codex CLI `0.167.0` is installed at `~/.local/bin/codex`. Sources: OpenAI's skills, plugins, subagents
and Claude-plugin conversion pages (links in §9).

| Thing | Codex | Claude Code |
|---|---|---|
| Instruction file | `AGENTS.md`, root and nested | `CLAUDE.md`; `@AGENTS.md` imports it. Third-party reports say Claude Code reads `AGENTS.md` itself only when there is no `CLAUDE.md`. Not verified, so the import stays |
| Skill | `SKILL.md`, only `name` + `description` documented; repo `.agents/skills/`, user `~/.agents/skills/` | `SKILL.md` |
| "Only when asked for" | `agents/openai.yaml` → `policy.allow_implicit_invocation: false` | `disable-model-invocation: true` |
| Skill's own folder | No variable. The model is given each skill's file path, so relative paths work | `${CLAUDE_SKILL_DIR}` |
| Plugin root | No variable for skills (`PLUGIN_ROOT` only reaches hook commands) | `${CLAUDE_PLUGIN_ROOT}` |
| Plugin manifest | `.codex-plugin/plugin.json` (what the scaffold writes) or a root `plugin.json`; skills found under `skills/` | `.claude-plugin/plugin.json` or the marketplace entry |
| Marketplace | `$REPO_ROOT/.agents/plugins/marketplace.json`; each entry needs `policy.installation`, `policy.authentication`, `category`, and a `./` relative `source.path` | `.claude-plugin/marketplace.json` |
| Subagents | `.codex/agents/*.toml`; plugins cannot ship them | `agents/*.md` in plugins |
| Commands | None. OpenAI's conversion guide: "Turn each Markdown command into a skill" | `commands/*.md`, `$ARGUMENTS` |
| Plugin dependencies | None | `dependencies` |

## 3. The neutral source format

Every file a plugin ships is written in this format. The build (§4) is the only thing that writes either
tool's format, and `--check` (§4.4) rejects any Claude or Codex form in the source.

| Element | Neutral source | Built for Claude | Built for Codex |
|---|---|---|---|
| Skill frontmatter | `name`, `description`; optional `license`, `metadata` (string → string) | Same, plus `disable-model-invocation: true` when `metadata.invocation: explicit`; that key removed | `name`, `description` only; `agents/openai.yaml` with `policy.allow_implicit_invocation: false` when `metadata.invocation: explicit` |
| "Only when asked for" | `metadata.invocation: explicit` | as above | as above |
| A file in this library | `{{lib}}/<path from the repo root>` | `${CLAUDE_PLUGIN_ROOT}/<path>` | the path relative to the built file's own location (§4.2) |
| A file in this skill's folder | `{{skill}}/<path>` | `${CLAUDE_SKILL_DIR}/<path>` | `./<path>` |
| An installed rule file in the target project | `{{rules}}/<plugin>/<file>` | `.claude/rules/<plugin>/<file>` | `.agents/rules/<plugin>/<file>` |
| A command's arguments | `{{arguments}}` | `$ARGUMENTS` | `the scope the user gave with the request` |
| Command frontmatter | `description`, optional `argument-hint` | as is | skill `name` = file stem, `description`; `allow_implicit_invocation: false` |
| Agent frontmatter | `name`, `description`, `capabilities:` from `read, search, edit, shell, web, fetch`, optional `mcp:` map `server: [tool, …]` | `tools:` (read→`Read`; search→`Glob, Grep`; edit→`Write, Edit`; shell→`Bash`; web→`WebSearch`; fetch→`WebFetch`; each MCP tool → `mcp__<server>__<tool>`) and `model: inherit` | a skill (§4.3) |
| A passage only one tool needs | `{{claude}} … {{/claude}}` or `{{codex}} … {{/codex}}`, each on its own line | Claude blocks kept (markers removed), Codex blocks removed | the reverse |
| The project's instruction file, in prose | `AGENTS.md` | as written | as written |
| Tools, in prose | plain verbs: "read", "search", "edit", "run", "ask the user", "hand the work to a subagent" | as written | as written |

Rules for authors:

- `{{lib}}` is only for files of this library. Paths in the **target project** (`docs/plans/`,
  `docs/audits/`, `src/`) are written plainly, never with a token.
- The "fall back to `<path>` inside the SkillsLibrary repo" sentences go away: `{{lib}}` is resolved for
  every install, and an agent working in this repo reads the source path directly.
- Conditional blocks are for passages that are genuinely different, such as how to spawn a subagent or
  which file holds the user's global rules (`~/.claude/CLAUDE.md` vs `~/.codex/AGENTS.md`). A sentence
  both tools can follow is written once.

## 4. The build: `tools/build_targets.py`

Python ≥ 3.12, run with `uv run tools/build_targets.py` (a PEP 723 header names `pyyaml>=6`). Tests in
`tools/tests/`, run with pytest.

```
uv run tools/build_targets.py                       # build every plugin into dist/
uv run tools/build_targets.py --plugin tooling --out <dir>
uv run tools/build_targets.py --check               # dist/ up to date + source is neutral (§4.4)
uv run tools/build_targets.py --check-prose [--scope <dir> …]   # no tool names in prose (§4.4)
```

### 4.1 Input: `plugins.json`

At the repo root. Today's marketplace with the Claude-only fields taken out:

```json
{
  "name": "skills-library",
  "owner": { "name": "Aleksandar Kotrulev", "email": "alexandur.kotrulev@gmail.com" },
  "description": "<today's metadata.description>",
  "version": "4.0.0",
  "plugins": [
    { "name": "dev", "description": "…", "author": {…}, "license": "MIT", "keywords": […],
      "category": "development", "skills": ["engineering-practices/brainstorming", …],
      "agents": ["engineering-practices/agents/code-auditor.md", …],
      "commands": ["engineering-practices/commands/plan-feature.md", …],
      "dependencies": [] }
  ]
}
```

Paths are repo-relative with no leading `./`.

### 4.2 Output layout

```
dist/claude/<plugin>/
  .claude-plugin/plugin.json     name, description, version, author, license, keywords,
                                 skills / agents / commands lists (repo-relative paths)
  <repo-relative tree>           the plugin's skill folders, agents and commands, and every file
                                 they reach through {{lib}} (the closure, below)
dist/codex/<plugin>/
  .codex-plugin/plugin.json      name, version, description, author, license, keywords, skills: "./skills/"
  skills/<name>/                 each skill folder; each agent (§4.3); each command (§4.3)
  lib/<repo-relative path>       every file the closure reaches that is not inside an emitted skill
.claude-plugin/marketplace.json  today's top level; entries: source "./dist/claude/<plugin>",
                                 description, category, keywords, dependencies — no lists
.agents/plugins/marketplace.json name "skills-library", interface.displayName, one entry per plugin
                                 with source.path "./dist/codex/<plugin>", policy, category
```

- **The closure.** Starting from the plugin's skills, agents and commands, follow every `{{lib}}/<path>`
  in every file copied, until nothing new is reached. A path that is a folder copies the folder. A
  missing target fails the build. This is what replaces `source: "./"`: today `qa-java` can read a
  `dev` file because every plugin holds the whole repo; after the build it holds exactly what it reads.
- **Codex paths.** A `{{lib}}` reference resolves to where the target landed in this package: inside
  `skills/<name>/` when it is a skill, agent or command this plugin emits, otherwise `lib/<path>`. The
  written path is relative to the referring file's own built location
  (`../../lib/engineering-practices/standards-audit-engine/SKILL.md`). A reference to an agent file
  resolves to that agent's built skill, `skills/<agent>/SKILL.md`.
- **Codex marketplace values** (`policy.installation`, `policy.authentication`, `source` shape) are taken
  from OpenAI's plugin build page (§9), never guessed; C1 records the values and the page in `As built`.
- Every file in `dist/` is written by the build. Nobody edits it.

### 4.3 Agents and commands on Codex

- **Agent → skill** `skills/<agent>/SKILL.md`: frontmatter `name` and `description` from the agent,
  then this preamble, then the agent's body:

  > Built from the `<name>` agent. In Codex it runs in the current session, not as a separate
  > subagent. The agent was limited to: <capabilities, in words, and each MCP server>. <When `edit` is
  > absent: **Read-only. Never create or change a file.**>

  When the agent has `mcp:`, `agents/openai.yaml` lists each server under `dependencies.tools`.
- **Command → skill** `skills/<stem>/SKILL.md`, with `allow_implicit_invocation: false`. A command whose
  stem equals an agent name in the same plugin is **not** built on Codex: those 10 commands only say
  "adopt this agent" and the agent's skill already is that.
- **Names are unique per Codex package** across skills, agents and commands; a clash fails the build.

### 4.4 Checks

| Flag | Fails on |
|---|---|
| `--check` | `dist/` differs from a fresh build into a temporary folder; in any source file a plugin reaches: `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}`, `$ARGUMENTS`, `.claude/rules/`, `disable-model-invocation`, an agent `tools:` or `model:` key, a capability outside §3's list, a `{{lib}}` target that does not exist, an unclosed or nested conditional block |
| `--check-prose` | Outside a conditional block, in source a plugin reaches: `Claude Code`; `` `Read` ``, `` `Write` ``, `` `Edit` ``, `` `Glob` ``, `` `Grep` ``, `` `Bash` ``, `` `WebSearch` ``, `` `WebFetch` ``; `Agent tool`, `Task tool`, `subagent_type`, `TaskCreate`, `TodoWrite`, `EnterWorktree`, `AskUserQuestion`, `ExitPlanMode`; a line naming `CLAUDE.md` without naming `AGENTS.md`. Exceptions go in `tools/prose-allowlist.txt` as `<path>  <regex>  # <reason>`; the file starts empty. `--scope` limits it to source files under the given folders |

Both print one line per failure (`path:line: <what>`) and exit 1, or print `OK` and exit 0.

### 4.5 What stays out

Folders no plugin reaches (`meta/`, `extras/`, `ai-development/`, `communication/`,
`auth/cognito-*`, `docs/`) are not converted and not checked. The under-construction folders stay
unpublished, as `AGENTS.md` already says.

## 5. Rules in a target project, for both tools

A `rules` skill (20 of them, one per plugin that has rules) installs its rule files where each tool
reads them, asking which tools the project uses when it cannot tell (a `.claude/` folder means Claude;
`.codex/` or an `AGENTS.md` without `CLAUDE.md` means Codex):

- **Claude:** `.claude/rules/<plugin>/<file>` as today. Claude loads each by its `paths:` frontmatter.
- **Codex:** `.agents/rules/<plugin>/<file>`, plus one managed block in the project's `AGENTS.md`,
  between `<!-- rules:<plugin> -->` and `<!-- /rules:<plugin> -->`:

  ```markdown
  <!-- rules:dev -->
  Before reading or editing a file matching one of these patterns, read the rule file beside it:
  | Files | Rule |
  |---|---|
  | `docs/plans/*.md`, `docs/plans/*/delivery-plan.md` | `.agents/rules/dev/plans.md` |
  <!-- /rules:dev -->
  ```

  The table comes from each rule file's `paths:`. Re-running the skill replaces the block. Codex reads
  the whole `AGENTS.md` every session, so the block is short and names files instead of copying them.
- Both: the existing `cmp`/`diff`/ask-before-replacing step applies to each copy.

## 6. Decisions

**D1 — The source is neutral and both tools' formats are built from it (the user, 2026-11-07).**
This reverses principle 1 of `MODEL-PORTABILITY-PLAN.md` ("the repo stays authored for Claude Code"),
so that plan's Track A is replaced by this one. Cost: every change needs `build_targets.py` run and
`dist/` committed; the source is no longer a working Claude plugin by itself.

| Option | Verdict | Why |
|---|---|---|
| Claude format stays the source, Codex built from it | Rejected by the user | Codex would always be the translated copy |
| Install script that links skills into `~/.agents/skills` | Rejected | No plugins, no marketplace, nothing for agents or commands |
| Neutral source, both built | Chosen | Neither tool is the translation |

**D2 — `AGENTS.md` is the instruction file; `CLAUDE.md` holds only `@AGENTS.md`** (done, `0ebd5e3`).
Projects the library sets up get the same pair. Cost: one extra file. It could go if Claude Code's own
`AGENTS.md` reading is confirmed (O-open 1).

**D3 — File references are template tokens, not bare paths.**

| Option | Verdict | Why |
|---|---|---|
| Bare repo paths, the build guesses which are library files | Rejected | `docs/plans/` is both a library folder and a target-project folder; a guess would rewrite the wrong ones |
| `{{lib}}`, `{{skill}}`, `{{rules}}`, `{{arguments}}` | Chosen | Unambiguous, and `--check` can prove none is left unresolved |

Cost: the source is a little less readable to someone browsing the repo.

**D4 — One package per plugin holding exactly the files it reads (the closure, §4.2).** Cost: a file
read by several plugins is copied into each package. Gain: a Claude install no longer copies the whole
repo, and a Codex package works on its own.

**D5 — On Codex, agents and commands become skills (the user, 2026-11-07).** Cost, stated once: on Codex
an agent runs in the main session, with no separate context, no tool limit and no model of its own; the
preamble (§4.3) states its limits instead. The 10 commands that only adopt their same-named agent are
not built on Codex, so their "no task given → run orientation" fallback is lost there.

**D6 — Codex has no plugin dependencies, so `dev` and `design` are installed explicitly on Codex.**
Files a package reads still arrive through the closure; what a Codex user misses without `dev` is
`dev`'s own skills and commands. Cost: one more install line in the README.

**D7 — `dist/` is committed, and a root `.ignore` lists it.** Both marketplaces install from git, so the
built packages must be in the repo. ripgrep (used by both tools' search) skips paths in `.ignore`, so a
search of this repo is not tripled. Cost: a larger repo and a second commit-time step.

**D8 — Rules install for both tools, with an `AGENTS.md` index for Codex (§5).** Codex has no
path-scoped rules, and nested `AGENTS.md` files cannot match patterns like `**/*.swift`. Cost: Codex
users pay a few hundred tokens per session for the index.

**D9 — The build is Python 3.12+ run by `uv`, owned by `be-python`.** System Python here is 3.9.6 and
`uv` is not installed, so H0 installs it. `be-python` is chosen for its toolchain (uv, ruff, mypy
`--strict`, pytest), not its upload-worker domain. The existing checkers stay plain `python3`.

**D10 — Codex packages use `.codex-plugin/plugin.json`.** It is what Codex's own scaffold writes. A root
`plugin.json` is OpenAI's newer portable form, but it would sit beside nothing else in our packages and
gains nothing yet.

## 7. Questions

**Answered (2026-11-07)**

- **O1 — Which tool counts as "GPT"?** Codex (CLI, IDE extension, desktop), the one with skills and plugins.
- **O2 — How do Codex users get the skills?** From a Codex marketplace of built packages (D1).
- **O3 — Agents on Codex?** Built as skills (D5).
- **O4 — Move the root file before the plan?** Yes; done in `0ebd5e3`.

**Open**

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| 1 | Does Claude Code read `AGENTS.md` itself, so the `CLAUDE.md` shim could go? | Keep the shim · drop it once confirmed in Anthropic's changelog | Nothing | the user |
| 2 | Does the Codex desktop app, which also reads `.claude-plugin/marketplace.json`, list our Claude packages as well? | Accept · rename one marketplace | Nothing; H1 looks | the user |

## 8. Tasks

What a halfway stop leaves: each landed task's own checks green, but the whole set (X1's gate) has not
run. Between C2 and X1, `dist/` is rebuilt by every task, so the published packages are always the
current source.

### H0 — install uv

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** `uv --version` prints a version in a new terminal.
**Depends on:** —
**Budget:** none.
**Gate: none** — a machine setup step.

- `brew install uv`.

### C1 — the build script, proven on a small fixture library

**Stack:** `be` · **Agent:** `be-python`
**Deliverable:** `uv run tools/build_targets.py` turns the fixture library in
`tools/tests/fixtures/lib/` into the expected Claude and Codex trees in
`tools/tests/fixtures/expected/`, and `tools/tests/` covers ≥ 80% of `build_targets.py`'s branches.
**Depends on:** H0 (uv).
**Budget:** ~135k — AGENTS.md + system 25k; this plan §2–§4 and D3–D7, D9–D10 15k; patterns
`tools/plugin-surface-check.py` 5k, `.claude-plugin/marketplace.json` 12k, one skill, one agent, one
command 10k; OpenAI's plugin build page 5k; writes `build_targets.py` ~15k, tests ~12k, fixtures ~8k;
test, ruff and mypy output 10k; × 1.2.
**Gate: own tests** — `uv run --with pytest --with pytest-cov --with pyyaml pytest tools/tests --cov=tools --cov-branch --cov-report=`,
`uv run --with coverage coverage json --include=tools/build_targets.py -o .coverage.json` (branch % =
`totals.covered_branches ÷ totals.num_branches`, ≥ 0.80), `uvx ruff check tools/build_targets.py tools/tests`,
`uv run --with mypy --with types-PyYAML mypy --strict tools/build_targets.py`. Do not run the build on the real repo.

- `tools/build_targets.py` with the PEP 723 header (`requires-python = ">=3.12"`,
  `dependencies = ["pyyaml>=6"]`). A `ROOT` argument (default: the repo root) so tests point it at the
  fixture; `--out` (default `<ROOT>/dist`); `--plugin`; `--check`; `--check-prose` with `--scope`.
  `main()` is the only function that touches `sys.argv`, the process exit code or the console.
- Everything in §3 and §4: frontmatter in and out, the four tokens, conditional blocks, the closure,
  Codex path rewriting (including agent-file references → the agent's built skill), agent and command
  → skill (§4.3), both `plugin.json` forms, both marketplaces, `agents/openai.yaml`, the uniqueness
  check, `--check` and `--check-prose` with `tools/prose-allowlist.txt` (created empty).
- Fixture library: two plugins. `alpha` has a skill with `metadata.invocation: explicit`, a `{{skill}}`
  reference and a `{{rules}}` reference; an agent with `capabilities: [read, search]` and an `mcp:` map;
  an agent with `edit`; a command using `{{arguments}}`; a command with the same stem as an agent; a
  `{{lib}}` reference into `beta`'s skill. `beta` depends on `alpha` and has one skill with a
  `{{claude}}` and a `{{codex}}` block. Expected trees are written by hand from §3–§4, never by
  copying the script's output.
- Tests, one per branch the script has: each token per target, each capability mapping, each
  `--check` failure and each `--check-prose` failure (one fixture file per failure, made on the fly in
  `tmp_path`), the allowlist, a missing `{{lib}}` target, a name clash, a nested block.
- Codex marketplace field values from https://developers.openai.com/plugins/build/plugins, cited in
  `As built`.
- Add `.coverage`, `.coverage.json` and `.pytest_cache/` to `.gitignore`.
- **Not in C1:** changing any real skill, agent, command or marketplace (C2); the prose (C3, C4).

### C2 — the real library made neutral, built, and published to both marketplaces

**Stack:** `be` · **Agent:** `be-python`
**Deliverable:** Every file the 22 plugins reach is in the neutral format; `plugins.json` replaces the
Claude marketplace as the source; `dist/claude/` and `dist/codex/` hold all 22 packages;
`.claude-plugin/marketplace.json` points at `dist/claude/*` and passes `claude plugin validate`; Codex
lists the 22 plugins from `.agents/plugins/marketplace.json`; `build_targets.py --check` prints `OK`.
**Depends on:** C1 (the build script).
**Budget:** ~150k — AGENTS.md + system 25k; this plan §3–§5 and D3–D7 15k; `build_targets.py` 15k;
both checkers 10k; the sweep script ~8k; sweep output and diff sampling ~35k; hand fixes ~15k;
validate and `--check` output 10k; × 1.1. If it runs over, the seam is: leave the `{{rules}}` rewrite to
C3 and C4 and allowlist `.claude/rules/` in `--check` until X1.
**Gate: own tests** — `uv run tools/build_targets.py --check`; `python3 tools/plugin-surface-check.py`;
`python3 tools/token-audit.py --violations-only | grep 'budget violations'` (same counts as before the
sweep); `claude plugin validate .`; `for d in dist/claude/*/; do claude plugin validate "$d" || exit 1; done`;
`codex plugin marketplace add <repo root>` then `codex plugin list` showing all 22; C1's pytest command
with the coverage line. Do not run `--check-prose` (C3, C4).

- A one-off sweep script in the session's scratchpad (not committed) that, over every file the
  marketplace's 22 plugins list, plus `.skill-template/`:
  - `${CLAUDE_PLUGIN_ROOT}/<path>` → `{{lib}}/<path>`; `${CLAUDE_SKILL_DIR}/<path>` → `{{skill}}/<path>`;
    `.claude/rules/<plugin>/<file>` → `{{rules}}/<plugin>/<file>`; `$ARGUMENTS` → `{{arguments}}`;
  - drops each "(fall back to `<path>` …SkillsLibrary repo…)" clause;
  - turns a bare backticked path into `{{lib}}/<path>` only when its first segment is a top-level
    library folder **other than `docs/`** and the path exists in the repo;
  - `disable-model-invocation: true` → `metadata.invocation: explicit` (merging into an existing
    `metadata`); agent `tools:` → `capabilities:` + `mcp:` by §3's map; drops `model: inherit`. Any
    other `model:` value or an unmapped tool stops the sweep and is reported.
- Read the sweep's diff on a sample per folder, fix by hand what it got wrong, then
  `git grep -n 'CLAUDE_PLUGIN_ROOT\|CLAUDE_SKILL_DIR'` over the reached files until empty.
- `plugins.json` from today's marketplace (§4.1); version `4.0.0`.
- `plugin-surface-check.py` and `token-audit.py` read `plugins.json`. Add Codex's built-in skill names
  `skill-creator` and `skill-installer` to the checker's reserved list, dated 2026-11-07.
  Each changed function gets a test in `tools/tests/` (load the hyphenated scripts with `importlib`).
- Build: `uv run tools/build_targets.py`. Root `.ignore` with `dist/`.
- The switch is one commit: sweep, `plugins.json`, `dist/`, both marketplaces, the checkers. A commit
  with the sweep but the old marketplace would publish packages that read `{{lib}}` literally.
- `codex plugin marketplace add` changes `~/.codex/config.toml`; say so in the final message, with the
  remove command.
- **Not in C2:** prose wording (C3, C4); the `rules` skills' procedure (C3, C4); README and
  CONTRIBUTING (X1).

### C3 — prose and rules installers, outside `qa/`, `frontend/` and `mobile/`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `uv run tools/build_targets.py --check-prose --scope <every reached folder except qa frontend mobile> .skill-template`
prints `OK`, and the 12 `rules` skills in those folders install for both tools as §5 says.
**Depends on:** C2 (the neutral source and the build).
**Budget:** ~145k — AGENTS.md + system 25k; this plan §3, §4.4, §5, D2, D8 10k; `--check-prose` output
8k; ~130 files edited from `grep -n -C2` context, ~0.6k each, 80k; one `rules` skill read whole 4k;
rebuild and check output 5k; × 1.05.
**Gate: own tests** — the deliverable's `--check-prose` command; `uv run tools/build_targets.py`;
`uv run tools/build_targets.py --check`; `python3 tools/plugin-surface-check.py`.

- Folders: `engineering-practices/`, `backend/`, `observability/`, `business-analysis/`, `data/`,
  `design/`, `devops/`, `security/`, `tooling/`, `training-data/`, the `auth/` skills a plugin lists,
  `.skill-template/`.
- `CLAUDE.md` → `AGENTS.md` where a skill reads or cites the project's instruction file. Where a skill
  **creates** one (scaffolds, `init`-style steps), it writes `AGENTS.md` and a `CLAUDE.md` holding
  `@AGENTS.md`. The planning skills' budget floor ("CLAUDE.md 25k") becomes `AGENTS.md`.
- Tool names → plain verbs (§3). Spawning a subagent, the Claude task list, and the user's global rules
  file go in `{{claude}}`/`{{codex}}` blocks.
- A passage about Claude Code itself (a skill that configures Claude hooks or settings) goes in a
  `{{claude}}` block, or into `tools/prose-allowlist.txt` with its reason when the whole skill is about
  Claude.
- The 12 `rules` skills (`engineering-practices/rules`, `backend/{dotnet,java,node,python,rust}/skills/rules`,
  `business-analysis/skills/rules`, `data/rules`, `design/rules`, `devops/rules`, `tooling/skills/rules`,
  `training-data/skills/rules`): procedure per §5. Write the first one fully, then give the others the
  same wording with their own plugin name and table.
- **Not in C3:** `qa/`, `frontend/`, `mobile/` (C4).

### C4 — prose and rules installers in `qa/`, `frontend/` and `mobile/`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `uv run tools/build_targets.py --check-prose` (whole library) prints `OK`, and the 8
`rules` skills in `qa/`, `frontend/` and `mobile/` install for both tools as §5 says.
**Depends on:** C3 (the `rules` wording to copy; both rebuild `dist/`).
**Budget:** ~140k — AGENTS.md + system 25k; this plan §3, §4.4, §5 8k; `engineering-practices/rules/SKILL.md`
as C3 left it 4k; `--check-prose` output 8k; ~120 files from `grep -n -C2` context 75k; rebuild and
check output 5k; × 1.1.
**Gate: own tests** — `uv run tools/build_targets.py --check-prose`; `uv run tools/build_targets.py`;
`uv run tools/build_targets.py --check`; `python3 tools/plugin-surface-check.py`.

- Folders: `qa/`, `frontend/`, `mobile/`. Same rules as C3's bullets: instruction file, tool names,
  conditional blocks, allowlist with reasons.
- The 8 `rules` skills (`qa/{java,dotnet,typescript}/skills/rules`, `frontend/{blazor,react}/skills/rules`,
  `mobile/{react-native,ios,android}/skills/rules`): C3's wording, their own plugin and table.
- **Not in C4:** README, CONTRIBUTING, catalog (X1).

### X1 — docs, the whole set, and the close-out

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** README tells a Codex user how to install the plugins; `AGENTS.md` and `CONTRIBUTING.md`
describe the neutral format and the build step; the whole set below is green, with ≥ 80% branch coverage
over the Python the plan wrote.
**Depends on:** C4 (and through it C1–C3).
**Budget:** ~120k — AGENTS.md + system 25k; this plan whole 20k; README, CONTRIBUTING and the catalog's
affected sections 25k; edits 15k; gate output 20k; 2k per earlier task 8k; × 1.05.
**Gate (this is the last runnable task, so it runs the whole set once more across the plan, in run order):**

```bash
uv run --with pytest --with pytest-cov --with pyyaml pytest tools/tests --cov=tools --cov-branch --cov-report=
uv run --with coverage coverage json --include=tools/build_targets.py,tools/plugin-surface-check.py,tools/token-audit.py -o .coverage.json
uvx ruff check tools/build_targets.py tools/tests
uv run --with mypy --with types-PyYAML mypy --strict tools/build_targets.py
uv run tools/build_targets.py --check
uv run tools/build_targets.py --check-prose
python3 tools/plugin-surface-check.py
python3 tools/qa-version-check.py
python3 tools/token-audit.py --violations-only | grep 'budget violations'
claude plugin validate . && for d in dist/claude/*/; do claude plugin validate "$d" || exit 1; done
codex plugin list
```

Branch coverage ≥ 0.80 over `build_targets.py`, and over the functions C2 changed in the two checkers
(read from `coverage html`, `plan-format.md` §5). Fix what it finds by the fix loop (`plan-format.md` §5).

- `README.md`: an install section per tool. Codex: `codex plugin marketplace add <git URL>`, then
  `codex plugin add <plugin>`, plus `dev` (and `design` for `fe-*`/`mobile-*`), since Codex has no
  dependencies (D6). What differs on Codex: agents and commands are skills invoked with `$<name>` (D5).
- `AGENTS.md`: a short "Authoring format" section: the source is neutral (§3, condensed), `dist/` is
  built, never edited, and `uv run tools/build_targets.py` then `--check` run before every commit that
  touches a plugin's files. Repository map row for `tools/`.
- `CONTRIBUTING.md`: the same, replacing the Claude-format instructions; the commit checklist gets
  `--check` and `--check-prose`.
- `docs/skills-catalog.md`: the scope paragraph (built packages, Codex marketplace); the
  `${CLAUDE_PLUGIN_ROOT}` mentions.
- `docs/plans/MODEL-PORTABILITY-PLAN.md`: one line under its header — Track A replaced by plan 010 (D1);
  Track B stands.
- **Not in X1:** a Codex run against a model (H1).

### H1 — try it in Codex and in Claude

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** In a scratch project, Codex runs one built skill, one built agent and one built
command from this marketplace; Claude, after `/plugin marketplace update skills-library`, runs the
same three.
**Depends on:** X1 (pushed to `master`).
**Budget:** Codex and Claude subscription usage.
**Gate: none** — a manual check.

- Codex: `codex plugin marketplace add <git URL>`, `codex plugin add dev`, then in a new session
  `$plan-feature`, `$code-auditor` and `$audit` (`be-dotnet`) on a small repo.
- Claude: reinstall `dev` and `be-dotnet`, run `/dev:plan-feature` and `/be-dotnet:audit`.
- Look at the Codex desktop app's plugin list for duplicates (open question 2).
- Write what you saw under H1's `As built`, then delete H1's prompt and file the plan (§7 step 8 of
  `plan-format.md`).

## 9. Sources

- OpenAI, Codex skills — https://learn.chatgpt.com/docs/build-skills (moved from developers.openai.com/codex/skills)
- OpenAI, plugin build — https://developers.openai.com/plugins/build/plugins
- OpenAI, submitting a Claude Code plugin — https://developers.openai.com/plugins/guides/submit-claude-plugin
- OpenAI, subagents — https://learn.chatgpt.com/docs/agent-configuration/subagents
- On Claude Code reading `AGENTS.md` (third-party, unverified) — https://www.developersdigest.tech/blog/claude-code-agents-md-support

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
6. **Merge, last task only** — if this plan runs on its own branch, merge the default branch into it
   now, resolve every conflict by keeping both sides' rows, re-run the failing suites if code conflicted,
   and commit the merge, so the plan merges back cleanly.
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

Run them in order, one session each; each block is complete on its own. Every gate runs locally in the
session running the task. Tasks commit and push straight to `master` (this repo's rule). No prompt may run Codex
or Claude against a model: H1 is the user's. Nothing runs in parallel: C1 → C2 → C3 → C4 → X1 each
rebuild or read `dist/` and the build script.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| H0 | `human` | **the user** | none | — | none |
| C1 | `be` | `be-python` | H0 | — | ~135k |
| C2 | `be` | `be-python` | C1 | — | ~150k |
| C3 | `docs` | `general-purpose` | C2 | — | ~145k |
| C4 | `docs` | `general-purpose` | C3 | — | ~140k |
| X1 | `docs` | `general-purpose` | C4 | — | ~120k |
| H1 | `human` | **the user** | X1 | — | subscription usage |

All prompts are live; none has landed.

---

### H0 — install uv (human, human)

````
Depends on: none
Agent: human · Stack: human

The user runs `brew install uv`, then `uv --version` in a new terminal. When it prints a version,
delete this block and commit `docs: delete H0's prompt (010)`.
````

### C1 — the build script, proven on a small fixture library (be-python, be)

````
Depends on: H0
Agent: be-python · Stack: be

You are `be-python`. Task C1 of docs/plans/010-agents-md-dual-harness.md: write
`tools/build_targets.py`, which turns this library's neutral source into a Claude Code plugin
marketplace and a Codex plugin marketplace, and prove it on a fixture library. You do not touch the
real library.

Read, in this order:
1. AGENTS.md.
2. The plan: §2, §3, §4 (all of it), D3–D7, D9, D10, task C1, and "Close-out — every task".
3. `tools/plugin-surface-check.py` — the house style for a repo tool (one `main`, plain output, exit 1
   on failure).
4. `.claude-plugin/marketplace.json` — the first two plugin entries only, for the fields `plugins.json`
   keeps.
5. One real file of each kind, to shape the fixture: `engineering-practices/rules/SKILL.md`,
   `engineering-practices/agents/code-auditor.md` (frontmatter and first 20 lines),
   `backend/dotnet/commands/audit.md`, `frontend/react/commands/fe-react.md`.
6. https://developers.openai.com/plugins/build/plugins — the marketplace entry fields and their
   allowed values (`policy.installation`, `policy.authentication`, `source`) and the
   `.codex-plugin/plugin.json` fields.

Build:
- `tools/build_targets.py`: PEP 723 header (`requires-python = ">=3.12"`, `dependencies = ["pyyaml>=6"]`),
  a `ROOT` argument (default the repo root), `--out` (default `<ROOT>/dist`), `--plugin`, `--check`,
  `--check-prose`, `--scope`. Everything in §3 and §4: frontmatter in and out, `{{lib}}` `{{skill}}`
  `{{rules}}` `{{arguments}}`, `{{claude}}`/`{{codex}}` blocks, the closure, Codex path rewriting
  (relative to each built file; an agent-file reference resolves to `skills/<agent>/SKILL.md`), agent
  and command → skill with the §4.3 preamble, the 10-command same-name rule, both `plugin.json` forms,
  both marketplaces, `agents/openai.yaml`, the per-package name check, `--check` and `--check-prose`
  exactly as §4.4 lists, `tools/prose-allowlist.txt` created empty.
- `tools/tests/conftest.py` (puts `tools/` on `sys.path`), `tools/tests/test_build_targets.py`,
  `tools/tests/fixtures/lib/` (two plugins `alpha` and `beta`, exactly as task C1's fixture bullet
  says) and `tools/tests/fixtures/expected/{claude,codex}/`.
- One test per branch: each token per target, each capability mapping, MCP tools, each `--check` and
  `--check-prose` failure (made in `tmp_path`), the allowlist, `--scope`, a missing `{{lib}}` target,
  a name clash, a nested block, the closure following a folder and a chain of two files.
- `.gitignore`: `.coverage`, `.coverage.json`, `.pytest_cache/`.

Traps:
- Write the expected trees by hand from §3–§4. Expected output copied from the script proves nothing.
- `docs/` is both a library folder and a target-project folder; `{{lib}}` is the only thing that marks
  a library path. Never infer one.
- The closure follows `{{lib}}` inside every copied file, not only the plugin's own files, and a
  folder target copies the whole folder.
- Codex has no plugin-root variable for skills: every Codex path is relative to the file it is written
  in, so the same target gets different strings in `skills/a/SKILL.md` and `skills/a/references/x.md`.
- Take the Codex marketplace values from the page in item 6 and cite them; do not guess enum values.

Gate:
  uv run --with pytest --with pytest-cov --with pyyaml pytest tools/tests --cov=tools --cov-branch --cov-report=
  uv run --with coverage coverage json --include=tools/build_targets.py -o .coverage.json
  (branch coverage = totals.covered_branches / totals.num_branches, must be >= 0.80)
  uvx ruff check tools/build_targets.py tools/tests
  uv run --with mypy --with types-PyYAML mypy --strict tools/build_targets.py
Do not run the build on the real repo; its source is not neutral until C2.

Commit: `feat(tools): build_targets.py builds Claude and Codex packages from neutral source (010 C1)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### C2 — the real library made neutral, built, and published to both marketplaces (be-python, be)

````
Depends on: C1
Agent: be-python · Stack: be

You are `be-python`. Task C2 of docs/plans/010-agents-md-dual-harness.md: convert every file the 22
plugins reach into the neutral format, replace the Claude marketplace with `plugins.json` as the
source, build `dist/`, and switch both marketplaces to the built packages, in one commit.

Read, in this order:
1. AGENTS.md.
2. The plan: §1, §3, §4.1, §4.2, §4.4, §4.5, D3–D7, task C2, C1's `As built` notes, and
   "Close-out — every task".
3. `tools/build_targets.py` and its `--help`, as C1 left it.
4. `tools/plugin-surface-check.py` and `tools/token-audit.py` — both read
   `.claude-plugin/marketplace.json` today.
5. `.claude-plugin/marketplace.json`.

Build:
- Record `python3 tools/token-audit.py --violations-only | grep 'budget violations'` before you change
  anything; the gate compares against it.
- A one-off sweep script in your scratchpad (not committed), over every file the marketplace's
  plugins list plus `.skill-template/`: `${CLAUDE_PLUGIN_ROOT}/x` → `{{lib}}/x`; `${CLAUDE_SKILL_DIR}/x`
  → `{{skill}}/x`; `.claude/rules/<plugin>/<file>` → `{{rules}}/<plugin>/<file>`; `$ARGUMENTS` →
  `{{arguments}}`; drop each "fall back to `<path>` … SkillsLibrary repo" clause; a bare backticked path
  becomes `{{lib}}/<path>` only when its first segment is a top-level library folder other than `docs/`
  and the path exists; `disable-model-invocation: true` → `metadata.invocation: explicit` (merge into an
  existing `metadata`); agent `tools:` → `capabilities:` + `mcp:` by §3's map; drop `model: inherit`.
  Stop and report any other `model:` value or an unmapped tool.
- Read the diff on a sample from every top-level folder; fix what the sweep got wrong by hand.
- `plugins.json` (§4.1, version `4.0.0`) from today's marketplace.
- Both checkers read `plugins.json`. Reserved list: add `skill-creator` and `skill-installer` (Codex
  built-ins), dated 2026-11-07. Each function you change gets a test in `tools/tests/`
  (load the hyphenated scripts with `importlib`).
- `uv run tools/build_targets.py`; root `.ignore` containing `dist/`.

Traps:
- One commit for the switch. A commit with the sweep and the old marketplace would publish packages
  that read `{{lib}}` literally to every Claude user of this marketplace.
- `docs/plans/`, `docs/audits/` in a skill are the target project's folders. Leave them plain.
- 10 commands share a stem with their plugin's agent (`fe-react`, `be-dotnet`, …): the build drops
  them on Codex, so do not rename them.
- `codex plugin marketplace add` writes `~/.codex/config.toml`. Check its `--help` for whether it takes
  a path or a git URL; name the remove command in your final message.
- Leave the prose (`CLAUDE.md` mentions, tool names) for C3 and C4; do not run `--check-prose`.

Gate:
  uv run tools/build_targets.py --check
  python3 tools/plugin-surface-check.py
  python3 tools/token-audit.py --violations-only | grep 'budget violations'   (same counts as recorded)
  claude plugin validate .
  for d in dist/claude/*/; do claude plugin validate "$d" || exit 1; done
  codex plugin marketplace add <repo root>   then   codex plugin list   (all 22 listed)
  uv run --with pytest --with pytest-cov --with pyyaml pytest tools/tests --cov=tools --cov-branch --cov-report=
  uv run --with coverage coverage json --include=tools/build_targets.py -o .coverage.json   (>= 0.80)

Commit (add by path, never `git add -A`):
`refactor(plugins): neutral source; Claude and Codex marketplaces built into dist/ (010 C2)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### C3 — prose and rules installers, outside qa, frontend and mobile (general-purpose, docs)

````
Depends on: C2
Agent: general-purpose · Stack: docs

You are a skills-library author. Task C3 of docs/plans/010-agents-md-dual-harness.md: make the prose
neutral, and the `rules` skills install for both Claude and Codex, in every reached folder except
`qa/`, `frontend/` and `mobile/`.

Read, in this order:
1. AGENTS.md.
2. The plan: §3, §4.4, §5, D2, D8, task C3, C2's `As built` notes, and "Close-out — every task".
3. `uv run tools/build_targets.py --check-prose --scope engineering-practices backend observability business-analysis data design devops security tooling training-data auth .skill-template`
   — the list of lines to fix.
4. `engineering-practices/rules/SKILL.md` in full.

Do:
- Work from the `--check-prose` list with `grep -n -C2`, not by reading whole files.
- `CLAUDE.md` → `AGENTS.md` where a skill reads or cites the project's instruction file. A skill that
  creates one writes `AGENTS.md` and a `CLAUDE.md` holding `@AGENTS.md`. The planning skills' budget
  floor ("CLAUDE.md 25k") becomes `AGENTS.md`.
- Tool names → plain verbs. Spawning a subagent, the task list, and the user's global rules file
  (`~/.claude/CLAUDE.md` vs `~/.codex/AGENTS.md`) go in `{{claude}}` / `{{codex}}` blocks, each marker
  on its own line.
- A passage about Claude Code itself goes in a `{{claude}}` block; a skill that is wholly about Claude
  gets a line in `tools/prose-allowlist.txt` with the reason.
- The 12 `rules` skills (`engineering-practices/rules`, `backend/{dotnet,java,node,python,rust}/skills/rules`,
  `business-analysis/skills/rules`, `data/rules`, `design/rules`, `devops/rules`,
  `tooling/skills/rules`, `training-data/skills/rules`): the procedure in §5 — ask which tools when it
  cannot tell, Claude copy, Codex copy plus the managed `AGENTS.md` block built from each rule file's
  `paths:`, the cmp/diff/ask step for each copy. Write `engineering-practices/rules` first, then give
  the others the same wording with their own plugin name and table.
- Rebuild: `uv run tools/build_targets.py`.

Traps:
- "AGENTS.md (or CLAUDE.md where the project has only that)" passes the check and is often the honest
  wording for a skill that reads a project's rules.
- `{{rules}}/<plugin>/…` is already in place from C2; do not write `.claude/rules/` back in.
- Edit the source only. Never edit `dist/`.

Gate:
  uv run tools/build_targets.py --check-prose --scope engineering-practices backend observability business-analysis data design devops security tooling training-data auth .skill-template
  uv run tools/build_targets.py
  uv run tools/build_targets.py --check
  python3 tools/plugin-surface-check.py

Commit (add by path): `refactor(skills): neutral prose and dual-tool rules installers outside qa/fe/mobile (010 C3)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### C4 — prose and rules installers in qa, frontend and mobile (general-purpose, docs)

````
Depends on: C3
Agent: general-purpose · Stack: docs

You are a skills-library author. Task C4 of docs/plans/010-agents-md-dual-harness.md: make the prose
neutral in `qa/`, `frontend/` and `mobile/`, and give their 8 `rules` skills the dual-tool install,
so the whole library passes `--check-prose`.

Read, in this order:
1. AGENTS.md.
2. The plan: §3, §4.4, §5, task C4, C3's `As built` notes, and "Close-out — every task".
3. `engineering-practices/rules/SKILL.md` as C3 left it — the wording to copy.
4. `uv run tools/build_targets.py --check-prose --scope qa frontend mobile` — the lines to fix.

Do:
- Same rules as C3: work from `grep -n -C2`; `CLAUDE.md` → `AGENTS.md` (a skill that creates one writes
  both, `CLAUDE.md` holding `@AGENTS.md`); tool names → plain verbs; harness-specific passages in
  `{{claude}}` / `{{codex}}` blocks; whole-Claude skills in `tools/prose-allowlist.txt` with a reason.
- The 8 `rules` skills (`qa/{java,dotnet,typescript}/skills/rules`, `frontend/{blazor,react}/skills/rules`,
  `mobile/{react-native,ios,android}/skills/rules`): C3's wording, their own plugin name and table.
- Rebuild: `uv run tools/build_targets.py`.

Traps:
- The QA skills name MCP tools (`mcp__playwright__…`, `mcp__appium-mcp__…`). Those are MCP names both
  tools share, not Claude tool names; leave them.
- The mobile skills mention `Info.plist`, `BuildConfig`, Xcode: platform names, not tool names.
- Edit the source only. Never edit `dist/`.

Gate:
  uv run tools/build_targets.py --check-prose
  uv run tools/build_targets.py
  uv run tools/build_targets.py --check
  python3 tools/plugin-surface-check.py

Commit (add by path): `refactor(skills): neutral prose and dual-tool rules installers in qa/fe/mobile (010 C4)`.
Close out per the plan's "Close-out — every task" before you stop.
````

### X1 — docs, the whole set, and the close-out (general-purpose, docs)

````
Depends on: C4
Agent: general-purpose · Stack: docs

You are a skills-library author. Task X1 of docs/plans/010-agents-md-dual-harness.md, the last
runnable task: document the neutral format and the Codex install, run the whole set once more, fix
what it finds, and close the plan out up to H1.

Read, in this order:
1. AGENTS.md.
2. The plan, whole, including every `As built` note and `## Decisions`.
3. `README.md` (install and rules sections), `CONTRIBUTING.md`, and in `docs/skills-catalog.md` the
   scope paragraph and every `${CLAUDE_PLUGIN_ROOT}` mention.

Write:
- README: an install section for each tool. Codex: `codex plugin marketplace add <git URL>`,
  `codex plugin add <plugin>`, plus `dev` (and `design` for `fe-*`/`mobile-*`) because Codex has no
  dependencies (D6); agents and commands are skills invoked as `$<name>` there (D5).
- AGENTS.md: a short "Authoring format" section — the neutral source (§3, condensed), `dist/` is built
  and never edited, run `uv run tools/build_targets.py` then `--check` before every commit touching a
  plugin's files — and the Repository map's `tools/` mention.
- CONTRIBUTING.md: the same, replacing the Claude-format instructions; the commit checklist gets
  `--check` and `--check-prose`.
- docs/skills-catalog.md: the scope paragraph (built packages, Codex marketplace) and the
  `${CLAUDE_PLUGIN_ROOT}` mentions.
- docs/plans/MODEL-PORTABILITY-PLAN.md: one line under its header — Track A replaced by plan 010 (D1);
  Track B stands.

Traps:
- AGENTS.md is read by both tools every session: keep the new section short and point at
  CONTRIBUTING for detail.
- A failure in the gate may belong to C1–C4; fix it here, and name the task in `As built`.
- H1 still holds a block, so the plan does not move to `docs/plans/implemented/` in this task. Say so
  in `Status`, and that H1 files it.

Gate (this is the last runnable task, so it runs the whole set once more across the plan, in run order):
  uv run --with pytest --with pytest-cov --with pyyaml pytest tools/tests --cov=tools --cov-branch --cov-report=
  uv run --with coverage coverage json --include=tools/build_targets.py,tools/plugin-surface-check.py,tools/token-audit.py -o .coverage.json
  uvx ruff check tools/build_targets.py tools/tests
  uv run --with mypy --with types-PyYAML mypy --strict tools/build_targets.py
  uv run tools/build_targets.py --check
  uv run tools/build_targets.py --check-prose
  python3 tools/plugin-surface-check.py
  python3 tools/qa-version-check.py
  python3 tools/token-audit.py --violations-only | grep 'budget violations'
  claude plugin validate . && for d in dist/claude/*/; do claude plugin validate "$d" || exit 1; done
  codex plugin list
Branch coverage >= 0.80 over build_targets.py, and over the functions C2 changed in the two checkers
(read from `coverage html`). Fix loop: the whole set once; each failure reproduced and fixed with the
narrowest command; only the failed rerun; the whole set once more to close.

Commit (add by path): `docs: neutral source and Codex install documented; plan 010 gate green (010 X1)`,
then push to master.
Finish with the exact commands the user runs for H1.
Close out per the plan's "Close-out — every task" before you stop.
````

### H1 — try it in Codex and in Claude (human, human)

````
Depends on: X1
Agent: human · Stack: human

The user, in a scratch project:
- Codex: `codex plugin marketplace add <git URL>`, `codex plugin add dev`, `codex plugin add be-dotnet`;
  in a new session run `$plan-feature`, `$code-auditor` and `$audit` on a small repo.
- Claude: `/plugin marketplace update skills-library`, reinstall `dev` and `be-dotnet`, run
  `/dev:plan-feature` and `/be-dotnet:audit`.
- Look at the Codex desktop app's plugin list for duplicate entries (open question 2).
Then write what you saw under H1's `As built`, rewrite `Status` one final time, delete this block,
`git mv` the plan into `docs/plans/implemented/`, and commit `docs: delete H1's prompt (010)`.
````
