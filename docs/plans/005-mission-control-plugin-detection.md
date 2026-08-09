# 005 — Mission Control: plugin detection on project link

**Status:** planned 2026-08-09
**Scope:** `tools/mission-control`
**Goal:** when a project is linked, inspect the repo, propose the `skills-library` plugins its stack actually needs, block on a human confirmation that can add or remove rows, then write the confirmed set into the repo's own `.claude/settings.json`.

---

## Why

Linking a project today registers a path and nothing else. The library ships **11 marketplace plugins** and a repo needs some small subset of them — picking that subset by hand means knowing the whole catalog, and getting it wrong is quiet: a missing plugin means an agent is simply never available, and an unnecessary one loads dozens of skills into every session in that repo for nothing.

The repo itself already carries the answer. A `*.csproj` with a TFM, a `prisma/schema.prisma`, a `.github/workflows/`, a `react` dependency — each is unambiguous evidence for exactly one plugin. This is a detection problem, not a judgement problem, right up until the point where evidence is thin, which is what the confirmation gate is for.

### The mechanism is already proven in this repo

`.claude/settings.json` **in a project** takes `enabledPlugins`, keyed `"<plugin>@<marketplace>"`. This very repository does it:

```json
{
  "enabledPlugins": {
    "frontend-design@claude-plugins-official": true,
    "skill-creator@claude-plugins-official": true,
    "code-simplifier@claude-plugins-official": true
  }
}
```

`~/.claude/plugins/installed_plugins.json` confirms plugins install with `scope: "project"` against a `projectPath`, and `known_marketplaces.json` shows `skills-library` resolving to `github:akotrulev/SkillsLibrary`. So the write target is well-defined and portable — the marketplace source is a GitHub repo, not a machine-local path.

---

## Design decisions

### D1 — Deterministic detection, evidence per row

File-pattern probes, not an LLM pass. Detection here is genuinely mechanical, and a deterministic detector is instant, free, unit-testable, and — most importantly — can show *why*: every proposed plugin carries the path that triggered it.

An optional LLM tie-break can be added later for genuinely ambiguous repos, but it must never be the primary path: a proposal a human cannot audit is worse than no proposal.

### D2 — Mirror the `devops-engineer` confirmation gate

The library already has the right pattern for this exact shape of decision, and CLAUDE.md describes it for `devops-engineer`: **Phase 0 Discover** (read-only inspection) → **Phase 1 Confirm** (a proposal table with every row marked `detected` / `stated` / `proposed`, blocking on the human's answer) → act.

Reuse it verbatim, including the proportionality rule: a repo where every row is `detected` gets a one-click confirmation, not an interrogation.

| Plugin | Verdict | Evidence |
|---|---|---|
| `be-dotnet` | detected | `src/Api/Api.csproj` — `net10.0` |
| `qa-dotnet` | detected | `tests/Api.Tests/Api.Tests.csproj` — NUnit |
| `devops` | detected | `.github/workflows/ci.yml`, `Dockerfile` |
| `data` | proposed | `src/Api/Migrations/` — EF Core migrations present |
| `business-analysis` | proposed | no evidence; offered because the repo has no `docs/business-model/` |

### D3 — The rule table is keyed to `marketplace.json`, never hardcoded

Plugin names come from `<LIBRARY_ROOT>/.claude-plugin/marketplace.json`, which MC already has on disk. The signal→plugin rules live in a table, but every plugin name in that table is validated against the marketplace file at load, and an unknown name is a loud startup error.

Without this, MC drifts the moment a plugin is renamed or a twelfth is added — and the failure would be silent, which is the worst kind.

**Only the 11 marketplace plugins are proposable.** `ep-*`, `design/*` and `observability/*` are bundled inside those plugins per CLAUDE.md and are not separately installable; proposing them would produce settings keys that resolve to nothing.

### D4 — Detection rules

| Plugin | Signals |
|---|---|
| `be-dotnet` | `*.csproj` / `*.sln` / `global.json`; non-test project; TFM read from the csproj |
| `qa-dotnet` | `*.Tests.csproj`, or NUnit/xUnit/MSTest package references |
| `be-java` | `pom.xml`, `build.gradle(.kts)`, `src/main/java` |
| `qa-java` | `src/test/java`, TestNG/JUnit dependencies |
| `be-node` | `package.json` with NestJS/Express/Fastify and no React |
| `qa-typescript` | Playwright/Vitest/Jest dependencies, `playwright.config.*` |
| `fe-react` | `react` in dependencies (`next` additionally selects the App Router lane) |
| `fe-blazor` | `*.razor`, or Blazor package references |
| `devops` | `Dockerfile`, `.github/workflows/`, `azure-pipelines.yml`, `.gitlab-ci.yml`, `*.tf`, `*.bicep`, `helm/`, `k8s/` |
| `data` | EF `Migrations/`, `prisma/schema.prisma`, Flyway `db/migration/`, a database service in `docker-compose.yml` |
| `business-analysis` | `docs/business-model/`, or requirements/epic documents — weakest signal, usually `proposed` |

A monorepo legitimately trips several stacks at once; multiple selections are the correct answer, not a conflict to resolve. But when more than three plugins are proposed, say so — every enabled plugin loads its skills into every session in that repo, and the gate is the right place to make that cost visible.

### D5 — MC manages `@skills-library` keys only

A repo's settings may already enable plugins from other marketplaces — `playwright@claude-plugins-official` is exactly the case that exists on this machine today. MC reads them, displays them as context, and **never adds, removes or reorders them**. Its write scope is precisely the `@skills-library`-suffixed keys.

That single rule makes the deselect path safe: an unchecked row removes a key MC is entitled to manage, and cannot touch anything else.

### D6 — `settings.local.json` by default, `settings.json` on request

`settings.json` is committed and team-shared; `settings.local.json` is gitignored. Linking a project should not dirty someone's working tree without being asked, so the default write target is `settings.local.json`, with a **"commit for the team"** toggle in the gate that switches to `settings.json`.

When writing the shared file, also write `extraKnownMarketplaces` for `skills-library` — pointing at the GitHub source, which is portable — so a teammate who has never registered the marketplace gets working config rather than dangling keys.

### D7 — Merge, never rewrite

Parse the existing file, mutate only the owned keys, re-serialise with 2-space indent. An unparseable settings file aborts with the parse error shown — never overwritten, never "repaired". No file is written at all if the confirmed set is identical to what is already there.

### D8 — MC configures; it does not install

Writing `enabledPlugins` enables a plugin; Claude Code fetches it on next use in that directory. The gate's completion message must say exactly that, rather than implying an install happened. Overstating what a step did is how a tool loses trust the first time something doesn't work.

---

## Phases

### Phase 1 — Detector

- [ ] `src/lib/plugin-detect.ts`: `detectPlugins(dir) → { plugin, verdict, evidence[] }[]`, bounded-depth walk skipping `node_modules`, `bin`, `obj`, `.git`, `dist`
- [ ] `src/lib/marketplace.ts`: parse `<LIBRARY_ROOT>/.claude-plugin/marketplace.json` for names + descriptions; validate the rule table against it on load
- [ ] Fixture-based unit tests: a .NET API + tests + CI repo; a Next.js + Prisma repo; a Spring Boot repo; a mixed monorepo; an empty directory (proposes nothing, does not error)

**Acceptance:** run against this library's own `tools/mission-control` and it detects `be-node` + `qa-typescript` + `fe-react` with the `package.json` paths as evidence.

### Phase 2 — Settings writer

- [ ] `src/lib/claude-settings.ts`: read/merge/write `.claude/settings.json` and `settings.local.json` per D5–D7
- [ ] Preserve unrelated keys and non-`skills-library` plugins byte-for-byte where the serialiser allows
- [ ] Write `extraKnownMarketplaces` only when targeting the shared file
- [ ] Create `.claude/` when absent; add `settings.local.json` to `.gitignore` if it is missing there
- [ ] Tests: no existing file · existing file with foreign plugins · unparseable file aborts · no-op when the set is unchanged

**Acceptance:** enabling two plugins in a repo that already has `playwright@claude-plugins-official` leaves that key untouched and adds exactly two.

### Phase 3 — The gate

- [ ] Run detection after the project's workspace is prepared — for `git` projects that means after `ensureWorkspace()`, for `local` projects immediately
- [ ] Confirmation UI: the D2 table, checkboxes pre-set from the verdicts, every unproposed plugin listed underneath as an addable row with its marketplace description
- [ ] Show the current `enabledPlugins` state so the diff is legible on a re-run
- [ ] Warn above three selections, naming the context cost
- [ ] Write target toggle (D6), defaulting to local
- [ ] **Skip** is a first-class option — a project may legitimately want no plugin config from MC
- [ ] Completion message states what was written, to which file, and that Claude Code installs on next use (D8)

**Acceptance:** linking a project cannot write settings without an explicit confirmation, and Skip leaves the repo untouched.

### Phase 4 — Re-detection

- [ ] A **Re-check plugins** action per project in `ProjectsPanel`
- [ ] Present it as drift: `detected but not enabled` / `enabled but no longer detected` / `unchanged`
- [ ] Never auto-apply — same gate, same confirmation

**Acceptance:** adding a `Dockerfile` to a linked repo and re-checking proposes `devops` as newly detected, with the other rows unchanged.

---

## Interaction with the other plans

- **002 (local runtime)** — detection reads the linked repo directly; no path mapping, no container mount, so it just works natively.
- **002 Phase 3 (worktrees)** — linking happens *before* any run exists, so this writes to the project's real working tree, not a worktree. That is why D6 defaults to the gitignored file: a link should not produce a diff the user has to explain.
- **004 B2 (catalog validation)** — related but distinct. That validates agent/skill names *inside a plan* against the indexed catalog; this validates *plugin* names against the marketplace and writes repo config. Shared plumbing: both read `LIBRARY_ROOT`.

## Effort

Phase 1 a day with fixtures. Phase 2 half a day. Phase 3 a day for the UI and the wiring. Phase 4 a few hours. **Roughly two and a half days.**
