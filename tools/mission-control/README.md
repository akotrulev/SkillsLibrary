# Mission Control

Plan-driven agent orchestration over the SkillsLibrary. You give it a plan and a
directory; it splits the plan into phased tasks, assigns a library agent to each,
and runs them — sequentially where order matters, in parallel where it is safe.

---

## Getting started

### Prerequisites

- **Node 22+** (`node -v`)
- **Model credentials.** The agents run through the Claude Agent SDK, which
  resolves credentials in this order — the first one found wins:
  1. `ANTHROPIC_API_KEY` in the environment
  2. an `ant auth login` profile
  3. the credentials your local Claude Code is already logged in with

  If you already use Claude Code on this machine, there is nothing to set up.
  Otherwise: `export ANTHROPIC_API_KEY=sk-ant-...`

### Install and start

```bash
cd tools/mission-control
npm install
npm run dev
```

Open **http://localhost:4300**.

The first page load indexes the library (~25s, agents + skills) and caches the
result to `.data/catalog.json`; later starts are instant. The header shows the
count — if it reads *40 agents · 333 skills*, the catalog is healthy.

To run it as a background service instead:

```bash
npm run build && npm run start        # same port, production build
```

Stop it any time with `Ctrl-C`. Nothing is lost — see [Persistence](#persistence).

---

## Using it

### 1. Point it at a project

Paste the **absolute path** of the repository you want worked on into *Target
directory* (e.g. `/Users/you/code/my-api`). The directory is registered as a
project automatically, so it gets an execution switch and shows up in the
**Projects** panel from then on.

> The agents write to this directory. Use a repo under version control, ideally
> on a scratch branch.

### 2. Paste a plan and press *Plan this run*

The plan is free-form prose or markdown — phases, features, constraints,
whatever you have. It does not need a particular structure. For example:

```markdown
Add rate limiting to the public API.

Phase 1 — foundations
- Redis-backed token bucket, shared config, typed settings

Phase 2 — apply it
- /auth endpoints: 10 req/min per IP
- /search endpoints: 60 req/min per API key
- /admin endpoints: 5 req/min per user

Constraints: no breaking changes to existing routes; Postgres stays the
system of record.
```

Planning takes a few minutes: the planner reads both your plan **and the target
repo** so its tasks match the code that actually exists. It is read-only — it
cannot modify your project. When it finishes you land on the board.

### 3. Answer the open questions

Anything the planner could not settle appears at the top in **Open questions**,
each with concrete options (its own pick marked *Recommended*) and a
*Something else…* free-text box. Select answers and press **Save answers**.

Questions that gate specific tasks keep those tasks blocked, and the **Start**
button stays disabled until they are answered. Your answers are handed to every
implementer as decisions already made.

### 4. Review the plan, then press *Start*

Before starting, skim the board:

- **Phase lanes** run strictly top to bottom.
- The **`sequential` / `parallel` chip** on each phase shows how its tasks will
  run — hover it to read the planner's justification.
- **Details** on any card shows the intent, acceptance criteria, target files,
  and dependencies.
- The **agent name** on each card is the library agent that will do the work.

Press **Start**. Cards move Ready → In progress → Done, streaming the agent's
live tool activity, and each finished task posts a short summary on its card.

### 5. Steer it while it runs

| Control | Effect |
|---|---|
| **Pause** | Stops at the next task boundary; state kept. **Resume** continues. |
| **Cancel** | Aborts in-flight agents and returns unfinished tasks to backlog. |
| **Retry** (on a blocked card) | Requeues that task. |
| **Skip** (on a blocked/ready card) | Marks it skipped so dependents can proceed. |
| **Project switch** (home page) | Off = stop and dispatch nothing, keep all state. |

A failed task turns **Blocked** with the error on the card; the rest of the phase
continues where dependencies allow. Fix the cause, then **Retry** and **Resume**.

### 6. When it finishes

Every card carries its summary — what was built, what was tested, and the
mutation-testing result. Review the diff in your repo as you would any change.

Implementers write unit tests but deliberately **do not** run live/E2E tests or
start servers; that is a separate pass. Run your own integration suite, or hand
the repo to a `qa-*` agent, once the code is in.

### Running several projects

Add as many projects as you like via **Add project**. Each has its own switch, so
you can leave one running and hold others off. Click a project to filter the run
list to it; click again to clear. Runs from different projects are independent
and can be active at the same time.

---

## How it works

1. **Catalog** — indexes every `*/agents/*.md` and `**/SKILL.md` in the library
   (40 agents, 333 skills) and caches the result in `.data/catalog.json`.
2. **Planner** — a read-only agent pass. Reads your plan *and the target repo*,
   then emits a task graph: phases, tasks, per-task agent + skills, dependencies,
   and open questions. It cannot write to your code.
3. **Board** — Kanban, one lane per phase, columns Backlog → Ready → In progress
   → Done / Blocked. Task cards stream the agent's live activity.
4. **Orchestrator** — phases run strictly in order. Within a phase, tasks run one
   at a time unless the planner marked the phase parallel-safe, in which case
   they run concurrently up to `maxParallel`.
5. **Implementers** — each task runs with its assigned library agent, `cwd` set
   to your target directory.

## The implementer contract

Every implementer is held to this, on top of its own agent definition:

- **Implement only.** No live/E2E/integration tests, no starting servers, no
  manual verification — a separate testing pass owns that.
- **Unit tests are required**, in the project's existing framework. Running unit
  tests is allowed and expected.
- **Mutation testing verifies test strength** (Stryker.NET / StrykerJS / PIT).
  Surviving mutants mean missing assertions. If no tool can be run, the agent
  must say so in its summary rather than skip silently.
- **Stay in scope** — another agent may be working in the same repo concurrently.
- **Post a short summary** on completion, shown verbatim on the task card.

## Parallel safety

The planner decides per phase and must justify the call (hover the
`parallel`/`sequential` chip to read its rationale). Foundational work —
scaffolding, shared types, schema, config, auth — is essentially never
parallel-safe; independent feature slices on a stable base usually are.

There is a second line of defence at dispatch: two tasks that declare
overlapping `files` will not run concurrently even inside a parallel-safe phase.

## Open questions

Anything the planner could not settle appears in the **Open questions** panel with
concrete options (its own pick marked *Recommended*) plus a free-text option. A
question can gate specific tasks; those tasks stay blocked and the run will not
start until it is answered. Answers are passed to every implementer as decisions
already made.

## Projects and the execution switch

Each working directory is a **project**. Planning a run registers its directory
automatically; you can also add one manually.

Every project has an execution switch:

- **On** — runs may dispatch agents.
- **Off** — any running work is stopped at the next task boundary and nothing
  further dispatches. All plans, tasks, summaries and answers are kept exactly
  as they were. Flip it back on and press Resume to continue.

Selecting a project filters the run list to it.

## GitHub credentials

Git-backed projects clone, commit and push on your behalf, which needs a
credential. There are two places to put one, and the **project token wins**:

| Source | Scope | Where |
|---|---|---|
| Project token | That one project | The **GitHub access** section on the project row (key icon) |
| Environment token | Every project without its own | `MISSION_CONTROL_GIT_TOKEN`, `GITHUB_TOKEN` or `GH_TOKEN` |

### Per-project tokens

Open a git project's key icon, paste a token, press **Save**. Use a
[fine-grained personal access token](https://github.com/settings/personal-access-tokens)
scoped to that repository with **Contents: read and write**.

Storing a token requires **`MISSION_CONTROL_SECRET`** — a passphrase used to
encrypt it (AES-256-GCM) in `projects.json`. Without that variable the section
says so and the field is disabled; a token is never written unencrypted. Change
or lose the passphrase and stored tokens become unreadable: the UI flags them
and you re-enter them.

**Test access** verifies the credential against the real remote. Once the
workspace is cloned it runs a dry-run push, so it proves *write* access — a
plain reachability check would pass on any public repo even with a junk token.
Before the first clone it can only confirm the repo is reachable, and says so.

### What agents can see: nothing

Credentials are the server's, not the agents'. Two mechanisms:

- The token is injected into the remote URL **per git command** and never
  written to `.git/config` inside a workspace an agent can read.
- Agent subprocesses get an **explicitly built environment** (`src/lib/agent-env.ts`)
  rather than inheriting the server's. It is an allowlist — process plumbing plus
  Anthropic auth — so `GITHUB_TOKEN`, `MISSION_CONTROL_SECRET` and any future
  secret are excluded by default.

Git errors are redacted before they reach a log or the UI, since a failing
command can echo the remote URL back.

## Persistence

All state lives on disk under `.data/` and is written on every mutation:

```
.data/
  catalog.json          # indexed agents + skills
  projects.json         # projects, execution switches, encrypted tokens
  runs/<runId>.json     # plan, phases, tasks, statuses, summaries, logs
```

Stopping the tool is safe. On restart:

- Plans, tasks, statuses, summaries, answers and projects are restored.
- A task left `in_progress` by a stopped process is **requeued to `ready`** — its
  agent subprocess did not survive, so nothing was driving it.
- A run left `running` is demoted to `paused`. Restarting never silently resumes
  dispatching against your code; you press Resume.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MISSION_CONTROL_LIBRARY_ROOT` | `../..` | SkillsLibrary root |
| `MISSION_CONTROL_DATA_DIR` | `./.data` | State directory |
| `MISSION_CONTROL_PLANNER_MODEL` | `claude-opus-5` | Planner model |
| `MISSION_CONTROL_IMPLEMENTER_MODEL` | `claude-opus-5` | Implementer model |
| `MISSION_CONTROL_MAX_PARALLEL` | `3` | Concurrency in a parallel-safe phase |
| `MISSION_CONTROL_SECRET` | — | Passphrase encrypting per-project tokens; without it they cannot be stored |
| `MISSION_CONTROL_GIT_TOKEN` | — | Fallback git credential for projects with no token of their own |

Set these in `.env.local`, or export them before `npm run dev`.

## Troubleshooting

**"Planning failed" immediately.**
Usually credentials. Check `echo $ANTHROPIC_API_KEY`, or that `claude` is logged
in on this machine. The error text from the SDK is shown on the form.

**Header shows 0 agents / far fewer than 40.**
The catalog could not read some files. Re-index with
`curl 'localhost:4300/api/catalog?refresh=1'` and check the server console — it
lists any file it gave up on after 3 attempts. On slow or network-backed volumes,
lower `READ_CONCURRENCY` in `src/lib/catalog.ts`.

**Catalog is stale after editing an agent or skill.**
The index is cached. Refresh it:
`curl 'localhost:4300/api/catalog?refresh=1'`, or delete `.data/catalog.json`.

**Start button is disabled.**
Either an open question still gates a task (answer it), or the project's
execution switch is off (turn it on in the Projects panel).

**A task sits in Blocked with no error.**
It is waiting on an unanswered question — check the Open questions panel.

**Run says "Execution is turned off for this project".**
Flip that project's switch on, then press **Resume**.

**Board stops updating; "Live connection lost".**
The SSE stream dropped. Reload the page — state is on disk, nothing is lost.

**A task claims it could not run mutation testing.**
Expected when the project has no mutation tool configured. The implementer is
instructed to say so explicitly rather than skip silently; configure
Stryker/PIT in the project if you want it enforced.

## Notes

- Implementers run with `permissionMode: "acceptEdits"` and an explicit tool
  allowlist, so they do not block on prompts. They write to the directory you
  point them at — use version control.
- The planner is read-only (`Read`, `Glob`, `Grep` only) and cannot modify your
  project.
- The library's frontmatter is parsed by `src/lib/frontmatter.ts`, not a YAML
  engine: descriptions contain unquoted colons and quotes that js-yaml both
  rejects and backtracks catastrophically on (tens of seconds per file).
- Prompts live in `src/lib/prompts.ts` — edit them to tune the planner's task
  splitting or the implementer's test discipline and summary format.
