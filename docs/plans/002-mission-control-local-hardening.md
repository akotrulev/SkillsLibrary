# 002 — Mission Control: local single-user deployment

**Status:** planned 2026-08-09
**Scope:** `tools/mission-control`
**Goal:** tailor Mission Control to what it actually is — a **single-user tool running natively on one Mac** — by deleting the credential and container machinery that only a hosted deployment needs, and adding per-run worktree isolation so agents never edit a tree you have open.

> Supersedes the Docker-oriented first draft of this plan (same number, replaced 2026-08-09). The four gaps that draft identified are still real; two of them are dissolved by the runtime change rather than fixed, and the surviving two are Phase 5 here.

---

## Why

Three questions drove this: does a local deployment need an LLM token, does it need a git token, and how do multiple project directories get configured. Investigating them on the actual machine produced a fourth answer that reframes all three.

### The LLM token is a Docker artifact

The Agent SDK resolves credentials `ANTHROPIC_API_KEY` → `ant auth login` → the local Claude Code login. On this machine there is **no `ANTHROPIC_API_KEY`** and **no `~/.claude/.credentials.json`** — macOS keeps the Claude Code login in the **keychain**.

A container cannot reach the keychain, so the commented-out `~/.claude` mount in `docker-compose.yml` does not work on macOS. Docker therefore forces a separate metered API key. Run the app natively and the SDK picks up the existing login with zero configuration.

### The git token is mostly a Docker artifact too

`credential.helper` is `store` on this machine, so `~/.git-credentials` already answers non-interactively. `withToken()` (`src/lib/git.ts:60`) passes a URL through untouched when no token is configured, and `GIT_ASKPASS=echo` / `GIT_TERMINAL_PROMPT=0` (`git.ts:22`) suppress *prompting* without blocking the helper — so a native process pushes successfully with no token of its own.

That makes the encrypted per-project PAT store from plan 001 redundant here: it protects a credential that already sits in plaintext two directories away in `~/.git-credentials`. Its **other** purpose survives untouched and is not affected by this plan — `agent-env.ts` keeping the credential out of agent subprocesses is still exactly right, because an agent with `Bash` should not be able to read your environment regardless of who is using the tool.

### Toolchains are the decisive argument

The `Dockerfile` says it plainly: agents run unit tests inside the container, so *"whatever your target project needs must exist there."* The image carries `node`, `git` and `ripgrep`. This library's agents target .NET 10, Java 21, Node 24 and React — and this machine already has `dotnet`, `java`, `node` and `python3` installed. Containerising means baking every toolchain into one image and keeping it aligned with each project's detected version lane, permanently, for no benefit a single user receives.

### Multiple project directories already work

`projects.json` + `ProjectsPanel` already hold N projects, each with its own absolute `targetDir` and an independent execution switch. The only constraint is Docker's `MC_PROJECTS_ROOT`, which mounts **one** parent directory at an identical host/container path and so forces every project under a single root. Native has no such limit — any absolute path works and the paths agents log back are real.

**Conclusion: run it natively, delete the container, delete both credential paths.**

---

## Design decisions

### D1 — Native process, no container

`npm run build && npm run start`, wrapped in a launchd agent for start-on-login. Deletes `Dockerfile`, `docker-compose.yml`, `.dockerignore`, the `MC_PROJECTS_ROOT` path-mapping concept, and the toolchain-extension section of the README.

Rejected: *a container with the toolchains baked in* — see above; it is a standing maintenance cost that buys a single user nothing. Rejected: *keeping the container as an optional path* — two supported runtimes doubles the documentation and the failure modes for a tool with one user.

### D2 — No LLM credential configuration

The SDK's own resolution order is the feature. Remove `ANTHROPIC_API_KEY` from the setup instructions and let the host login serve. `agent-env.ts` already forwards `ANTHROPIC_*` and `CLAUDE_*` prefixes, so an API key still works for anyone who prefers one — it just stops being a documented prerequisite.

### D3 — No credential store; git uses the host helper

Delete `secrets.ts` (+ `secrets.test.ts`), `MISSION_CONTROL_SECRET`, the token API routes, and the token half of `GitHubAccess.tsx`. Two call sites change behaviour rather than disappearing:

- `pushBranch()` (`git.ts:174`) drops its "no git token for this project" precondition and simply pushes, letting the helper authenticate.
- `checkAccess()` (`git.ts:230`) stops forcing `credential.helper=`. That flag exists so a cached keychain entry cannot mask a bad *supplied* token — with no supplied token there is nothing to mask, and forcing it empty would make the check fail where the real push succeeds. The dry-run-push-over-`ls-remote` reasoning in that function is sound and stays.

Keep the repo-access check itself: "can I push to this remote" is still worth answering before a run, and it now verifies the helper rather than a stored PAT.

### D4 — Both project sources stay; isolation is a per-run worktree

`local` (a path to a repo you already have) and `git` (a managed clone under `.data/workspaces/<id>`) both remain. On top of either, every run gets its own **`git worktree`**:

```
.data/worktrees/<runId>   ← branch mc/<runId>, cut from the project's base branch
```

`run.targetDir` becomes that worktree path, which is what `dispatchTask` already passes as `cwd` (`dispatcher.ts:93`) — so nothing downstream changes. The properties that make this the right primitive locally:

- `git worktree add` works fine against a repo with a dirty main tree, so a run never disturbs the checkout you have open in an editor;
- it shares the object store, so there is no duplicated history and no second fetch;
- the result is an ordinary branch in your own repo — review with `git diff`, merge or delete, no push required and no remote involved for `local` projects;
- `CLAUDE.md`, `.claude/` and `docs/agent-context/` come along in the worktree, so agents keep their orientation cache and project conventions.

**Fallback:** a `local` project that is not a git repository gets no worktree and is edited directly, with the UI saying so. Silently doing nothing would be worse than the honest downgrade.

### D5 — Bind to loopback; keep the env allowlist

> **→ superseded in part by plan 006** (2026-08-09), which moves the server to the homelab box and publishes it. The loopback bind survives — it is what makes an edge-terminated auth layer the only door — but "the app has no authentication, correctly, for a single-user tool" does not survive the host being reachable from outside. 006 D3 is the replacement.

`next start` binds `0.0.0.0` by default, and the app has no authentication — correctly, for a single-user tool. Set `HOSTNAME=127.0.0.1` so it is not reachable off-box. `agent-env.ts` stays byte-for-byte: an agent with `Bash` reading the server's environment is a bad idea at any tenancy count.

---

## Phases

Ordered by dependency: 1 and 2 shrink the surface, 3 is the one real feature, 4–5 are ergonomics and durability.

### Phase 1 — Native runtime

- [ ] Delete `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- [ ] `package.json`: `"start": "next start -p 4300 -H 127.0.0.1"`
- [ ] Add `launchd/com.mission-control.plist` + a `README` section for start-on-login (`launchctl load`), logging to `.data/mission-control.log`
- [ ] Default `MISSION_CONTROL_DATA_DIR` to `./.data` (already the code default via `config.ts:16`) and confirm `LIBRARY_ROOT`'s two-levels-up default resolves correctly outside a container
- [ ] README rewrite: prerequisites become *Node 22+, a Claude Code login, git* — no API key, no `MC_PROJECTS_ROOT`, no toolchain-extension section

**Acceptance:** `npm run start` on a machine with no `ANTHROPIC_API_KEY` plans and dispatches a run successfully. `curl http://<lan-ip>:4300` from another machine is refused.

### Phase 2 — Delete the credential subsystem

- [ ] Remove `src/lib/secrets.ts`, `src/lib/secrets.test.ts`, `src/app/api/projects/[projectId]/token/route.ts`
- [ ] `projects.ts`: drop `tokenCipher`, `tokenHint`, `secretsEnabled` and the token-resolution path; keep `gitTokenFromEnv()` as an unadvertised override for a repo the helper cannot serve
- [ ] `git.ts`: relax `pushBranch()`'s token precondition; stop forcing `credential.helper=` in `gitAuthed()`
- [ ] `GitHubAccess.tsx` → a read-only **Repo access** panel: remote, base branch, and the result of the access check
- [ ] Migration for the existing `.data/projects.json`: strip `tokenCipher`/`tokenHint` on load, no user action needed
- [ ] Remove `MISSION_CONTROL_SECRET` and `MISSION_CONTROL_GIT_TOKEN` from all documentation

**Acceptance:** a `git` project clones, commits and pushes with no token configured anywhere in Mission Control. `rg -i "MISSION_CONTROL_SECRET|tokenCipher"` returns nothing outside this plan and plan 001.

### Phase 3 — Per-run worktree isolation

- [ ] `git.ts`: `createWorktree(baseDir, runId, baseBranch)` → `.data/worktrees/<runId>` on branch `mc/<runId>`; `removeWorktree(runId)` doing `git worktree remove` + `git worktree prune`
- [ ] `isGitRepo(dir)` probe; a non-repo `local` project skips the worktree and is flagged in the UI
- [ ] Run creation: build the worktree, set `run.targetDir` to it, record `baseDir` + `workBranch` on the run
- [ ] Extend `reconcile()` (`store.ts:56`) to survive a worktree that vanished under a stopped process — a run whose `targetDir` no longer exists must fail loudly, not dispatch into a missing directory
- [ ] Run detail UI: branch name, changed-file count (reuse `workspaceStatus`), a copyable `git diff mc/<runId>` line, and **Discard** (remove worktree + branch) / **Keep** (remove worktree, keep branch)
- [ ] Never auto-delete a worktree with uncommitted changes — `hasChanges()` already answers this
- [ ] Retention: prune worktrees for runs finished more than N days ago, branches kept

**Acceptance:** start a run against a `local` project with a deliberately dirty working tree; the tree is untouched throughout, the work lands on `mc/<runId>`, and `git worktree list` is clean after Discard.

### Phase 4 — Project configuration ergonomics

- [ ] Validate on add: path exists, is a directory, is readable, and report whether it is a git repo — instead of silently registering anything typed
- [ ] Reject duplicate `targetDir` registrations (normalise trailing slashes and symlinks via `fs.realpath`)
- [ ] Show base branch and repo-clean state per project row in `ProjectsPanel`
- [ ] Recently-used paths in the target-directory field, sourced from existing projects

**Acceptance:** adding a path that does not exist produces an inline error, not a project row that fails at dispatch.

### Phase 5 — Carried over from the superseded draft

Both survive the runtime change untouched.

- [ ] **Catalog self-invalidation.** `getCatalog()` (`catalog.ts:207`) serves the cache unconditionally and `?refresh=1` **has no caller** — the sole fetch is `src/app/page.tsx:71` — so a newly authored agent stays invisible, and `dispatchTask` hard-fails a task naming it (`dispatcher.ts:76`). Add a `stat`-only newest-mtime probe over `LIBRARY_ROOT` compared against `indexedAt`, throttled to ~10s, plus a Refresh control and a relative `indexedAt` in the header.
- [ ] **Schema versioning.** `store.ts:76,137` and `projects.ts:60` are bare `JSON.parse(...) as T` casts. Add `schemaVersion`, validate with Zod (already a dependency), and on mismatch quarantine the file to `<name>.v<n>.bak` and omit the record with a UI notice rather than letting `undefined` reach a component. Missing version reads as 1. `catalog.json` is exempt — it is derived, and rebuilding is the correct response.

**Acceptance:** adding a `SKILL.md` to the library makes the skill count rise on reload without a restart; a run file with `schemaVersion: 999` is quarantined while every other run still renders.

---

## What this deletes

`Dockerfile` · `docker-compose.yml` · `.dockerignore` · `secrets.ts` · `secrets.test.ts` · the token route · the token half of `GitHubAccess.tsx` · `MISSION_CONTROL_SECRET` · `MISSION_CONTROL_GIT_TOKEN` (as a documented path) · `MC_PROJECTS_ROOT` and all host↔container path mapping.

Plan 001 is **partly reverted by design**: its D1–D3 (encrypted per-project token, resolution order, write-only API) are hosted-deployment concerns that a native single-user process does not have. Its **D4 is untouched and remains load-bearing** — the token never reaching an agent subprocess, via the `agent-env.ts` allowlist.

## Effort

Phase 1 and 2 are half a day each and mostly deletion. Phase 3 is the real work — call it two days with the UI and the reconcile edge cases. Phases 4 and 5 are a day together. Roughly **four focused days** for all five.

## Deferred

The hosted multi-tenant product remains out of scope. Its blocking item is execution isolation: `dispatchTask` runs `query()` as a host subprocess with `Bash` and `permissionMode: "acceptEdits"` for up to 200 turns (`dispatcher.ts:91-108`), contained only by the `agent-env.ts` allowlist. Sound for one trusted user; not a tenancy boundary. A hosted version needs one ephemeral microVM per run with allowlisted egress, which is where the majority of that project's cost sits.
