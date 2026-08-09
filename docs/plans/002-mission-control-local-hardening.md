# 002 — Mission Control: local-deployment hardening

**Status:** planned 2026-08-09
**Scope:** `tools/mission-control`
**Goal:** make the existing Docker image safe and predictable as a **local, single-user** deployment — not reachable off-box, not serving stale catalog data, not silently corrupting state across a version bump, and backed up.

**Explicitly out of scope:** multi-tenancy, auth/registration, sandboxed execution, billing. Those belong to a hosted product; see the evaluation summary in *Why*. This plan assumes exactly one user, on one machine, running their own agents against their own repos.

---

## Why

The container story is essentially finished already. `Dockerfile` is a clean three-stage build (deps → build → `node:22-bookworm-slim` runtime with `git` + `ripgrep`, which agents shell out to), `MISSION_CONTROL_DATA_DIR=/data` is backed by the named volume `mission-control-data`, `VOLUME ["/data"]` is declared so even a bare `docker run` keeps state, and every mutation is written through immediately. Restart recovery is already correct: `reconcile()` (`src/lib/store.ts:56`) requeues orphaned `in_progress` tasks and demotes a `running` run to `paused`, so a restart never silently resumes writing to your code.

State survives `stop`/`start`, `down`/`up`, and image rebuilds. It does **not** survive `down -v` or `docker volume prune`.

Four gaps remain between that and something safe to leave running day to day.

1. **`4300:4300` publishes on every interface** (`docker-compose.yml:22`) and there is **no authentication anywhere in the app**. On any shared network, that is an unauthenticated agent with `Bash` and write access to the mounted repos, exposed to the LAN. Blocker-class.
2. **The catalog cache never invalidates.** `getCatalog()` (`src/lib/catalog.ts:207`) serves the in-memory copy, then `/data/catalog.json`, and only rebuilds when `force` is set — and **nothing in the UI ever sets it**: the sole call site is `fetch("/api/catalog")` (`src/app/page.tsx:71`), with no `?refresh=1`. So the cache is permanent until someone deletes the file by hand. Since this library is under active development, a newly authored agent is invisible to the planner, and `dispatchTask` hard-fails a task whose agent is absent (`src/lib/dispatcher.ts:76`).
3. **No schema versioning on persisted state.** `store.ts:76`, `store.ts:137`, `projects.ts:60` and `catalog.ts:184` all `JSON.parse(...) as T` — a bare cast, no validation. Fine for stop/start of one version; the failure mode is a **redeploy across versions**, where a renamed or added field silently deserializes to `undefined` and surfaces as confusing UI rather than a clean error. Zod is already a dependency.
4. **Uncommitted agent work has a single point of failure.** Git-backed projects check out under `.data/workspaces/<id>` (`src/lib/git.ts:10`), which is on the volume — so it survives restarts, but it is a *working tree*. Edits an agent has made but not pushed exist in exactly one place: a Docker volume with no backup and a one-flag destruction path.

---

## Design decisions

### D1 — Bind to loopback, do not add auth

The fix is `127.0.0.1:4300:4300`, not a login screen. Adding users/sessions to a single-user local tool is the first step down the multi-tenant road this deployment deliberately isn't taking, and loopback binding is strictly stronger than a password against the actual threat (someone else on the same wifi). Anyone needing off-box access uses an SSH tunnel, which is documented rather than built.

Rejected: *bind to the LAN and add basic auth* — more code, weaker guarantee, and invites the assumption that the tool is safe to expose.

### D2 — Invalidate the catalog on library mtime, keep the cache

The cache exists for a good reason: a cold index is ~25s over a bind-mounted volume. So keep it and add a cheap staleness probe — walk the library for the newest `.md` mtime and compare against `indexedAt`. The walk is `stat`-only (no file reads), which is the fast half of indexing; `collect()` (`src/lib/catalog.ts:36`) already does exactly this traversal and can be reused.

Rejected: *a filesystem watcher* — the library is a read-only bind mount, and inotify across that boundary is unreliable on Docker Desktop. Rejected: *TTL expiry* — either too short (pays 25s for nothing) or too long (still stale); mtime answers the actual question.

### D3 — Version the persisted shape, fail loud on mismatch

Add `schemaVersion: number` to `Run` and the projects file, validate on load with Zod, and on a version the running code doesn't understand **refuse the record and say so** rather than best-effort casting it. A quarantine rename (`<runId>.json.v1.bak`) keeps the data recoverable.

`catalog.json` is exempt — it is a derived cache, so the correct response to an unreadable one is to rebuild, which `readCacheFile()` already does by returning null.

Rejected: *migration functions per version* — premature for one user and one writer; loud refusal plus a preserved file is enough, and migrations can be added later at the same seam.

### D4 — Host bind mount as the default, named volume as the fallback

Switch `docker-compose.yml` to `./.data:/data`. `.data/` is already in `.gitignore` (`tools/mission-control/.gitignore:3`) and already in `.dockerignore`, so nothing leaks into the repo or the image. The payoff is that state becomes an ordinary directory the user can inspect, back up, and copy — and the `down -v` footgun disappears entirely.

The cost is UID ownership on Linux: the container runs as root by default (deliberately — see the `Dockerfile` comment on bind-mounted host directories), so it would leave root-owned files in the tree. Document `--user "$(id -u):$(id -g)"` alongside it. On macOS, where this is actually run, the issue doesn't arise.

---

## Phases

Independent of each other; ordered by risk. Each is self-contained and shippable.

### Phase 1 — Close the network exposure

- [ ] `docker-compose.yml:22` → `- "127.0.0.1:4300:4300"`
- [ ] `README.md`: state plainly that the app has **no authentication** and must not be published on a routable interface; give the SSH-tunnel one-liner (`ssh -L 4300:localhost:4300 <host>`) as the remote-access path
- [ ] Add a startup log line naming the bound address, so a misconfiguration is visible at boot

**Acceptance:** `curl http://<host-lan-ip>:4300` from another machine on the LAN is refused; `curl http://localhost:4300` on the host succeeds.

### Phase 2 — Make the catalog self-invalidate

- [ ] `catalog.ts`: extract the `stat`-only traversal from `collect()` into `newestLibraryMtime(): Promise<number>`
- [ ] `getCatalog()`: after loading from memory or disk, compare `newestLibraryMtime()` against `indexedAt`; rebuild when the library is newer. Keep `force` for a manual override
- [ ] Guard the probe with a short in-process throttle (≥10s) so a page with several catalog reads doesn't re-walk the tree per request
- [ ] Wire a **Refresh** control in the header next to the `40 agents · 333 skills` count, calling `/api/catalog?refresh=1` — the endpoint supports it (`src/app/api/catalog/route.ts:8`) and has no caller
- [ ] Surface `indexedAt` in the header as a relative time, so staleness is legible

**Acceptance:** add a new `SKILL.md` under the library, reload the page without restarting the container, and the skill count increases. Touching nothing and reloading does **not** trigger a rebuild (verify via the absence of the ~25s index).

### Phase 3 — Version the persisted state

- [ ] Add `schemaVersion` to `Run` (`src/lib/types.ts`) and to the projects file; define `CURRENT_SCHEMA_VERSION`
- [ ] Zod schemas for `Run` and `Project`; validate in `loadRun`, `loadRunUncached` (`store.ts:76,137`) and `readAll` (`projects.ts:60`)
- [ ] On a version or shape mismatch: log it, rename the file to `<name>.v<n>.bak`, and omit the record from the listing rather than crashing the whole list — matching the existing `decryptSecret` posture of degrading rather than throwing (`src/lib/secrets.ts:70`)
- [ ] Treat a missing `schemaVersion` as version 1 and stamp it on next write, so existing `.data/` upgrades cleanly
- [ ] Surface quarantined runs in the UI as a one-line notice, so a silent disappearance is impossible
- [ ] Unit tests: current shape loads; unknown-future version quarantines; missing field is caught by Zod, not by `undefined` reaching a component

**Acceptance:** hand-edit a run file's `schemaVersion` to `999`; the board still renders every other run and shows the notice. Revert, and it loads normally.

### Phase 4 — Durable state and backups

- [ ] `docker-compose.yml`: replace `mission-control-data:/data` with `./.data:/data`; drop the now-unused `volumes:` block
- [ ] `README.md` → *Persistence*: document the bind mount, the Linux `--user "$(id -u):$(id -g)"` note, and the migration for anyone on the old named volume:
      `docker run --rm -v mission-control-data:/data -v "$PWD/.data:/out" alpine cp -a /data/. /out/`
- [ ] Document the backup one-liner and the durability boundary in one sentence: **pushed commits are safe; anything uncommitted in `.data/workspaces/<id>` lives in one place only**
- [ ] Consider (do not build yet) a `git push` of the work branch at end-of-run as the real fix for that boundary — noted here so Phase 4 doesn't get mistaken for having solved it

**Acceptance:** `docker compose down && docker compose up` preserves all runs and projects with `.data/` visible on the host; a `tar` of `.data/` restored into a fresh checkout reproduces the board.

---

## Effort

Roughly one focused day for all four: Phase 1 is minutes, Phase 2 and 4 an hour or two each, Phase 3 the bulk of it because of the tests.

## Notes for a future session

The larger question that produced this plan — extracting Mission Control as a multi-tenant hosted product — was evaluated and **deferred**. The blocking item is execution isolation: `dispatchTask` runs `query()` as a host subprocess with `Bash` and `permissionMode: "acceptEdits"` for up to 200 turns (`src/lib/dispatcher.ts:91-108`), contained only by the env allowlist in `agent-env.ts`. That is sound for a single trusted user and is not a multi-tenant boundary; a hosted version needs one ephemeral microVM per run with allowlisted egress, which is where the majority of that project's cost sits. The intermediate step, if demand appears, is a **single-tenant self-hosted** distribution — which is what this plan produces.
