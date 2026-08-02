# 001 — Mission Control: per-project GitHub key

**Status:** implemented 2026-08-01 (all four phases). Phase 4 was done first, as the credential exposure it closes predated this feature.
**Scope:** `tools/mission-control`
**Goal:** each git-backed project carries its own GitHub credential, so one Mission Control instance can push to repos across different owners/orgs without a single process-wide token.

---

## Why

Today `gitToken()` (`src/lib/git.ts:45`) reads one process-wide value:

```ts
process.env.MISSION_CONTROL_GIT_TOKEN || process.env.GITHUB_TOKEN || process.env.GH_TOKEN
```

Three consequences:

1. **One credential for every project.** Adding a repo under a different owner means restarting the container with a different env var.
2. **Broadest-scope token wins.** The single token needs write access to every repo you ever add, which is the opposite of least privilege.
3. **Every implementer agent can read it.** `dispatchTask` (`src/lib/dispatcher.ts:91`) passes no `env` to the SDK, so the agent subprocess inherits the server's environment. `Bash` is in `IMPLEMENTER_TOOLS`, so a task can run `env` or `echo $GITHUB_TOKEN` and print a live credential into its own task log. **This is a live issue independent of this feature** — see Phase 4, which should arguably land first.

---

## Design decisions

### D1 — Where the token lives: encrypted in the project record

`.data/projects.json` is plain JSON on a volume. A PAT must not sit there in cleartext.

**Decision:** AES-256-GCM (`node:crypto`) with a key derived from `MISSION_CONTROL_SECRET`, stored as `{ ciphertext, iv, tag }` on the project. If `MISSION_CONTROL_SECRET` is unset, per-project tokens are **disabled** with an explicit UI message rather than silently degrading to plaintext.

Rejected alternatives:
- *Plaintext with `0600`* — the file is on a shared docker volume; permissions don't survive that boundary meaningfully.
- *Env-var reference per project* (`tokenEnv: "GITHUB_TOKEN_ACME"`) — no secret at rest, but adding a repo needs a container restart, which defeats the point of adding projects from the UI. Keep as a documented power-user override, not the primary path.

### D2 — Resolution order

```
project token (decrypted)  →  MISSION_CONTROL_GIT_TOKEN / GITHUB_TOKEN / GH_TOKEN  →  none
```

Env stays as the fallback so existing setups keep working untouched. `gitToken()` becomes `gitTokenFor(project)`; the no-arg form remains for non-project call sites.

### D3 — The token is write-only across the API

No response body ever contains a token. `GET` returns a **descriptor**:

```jsonc
{ "source": "project" | "env" | "none", "hint": "…ab12", "canPush": true }
```

`hint` is the last 4 characters, enough to tell two tokens apart and useless on its own.

### D4 — The token never reaches an agent

Git commands get the credential; agent subprocesses do not. Two mechanisms, both required:
- the token is injected per git invocation into the remote URL (already how `withToken` works) and never written to `.git/config` (already true);
- `dispatchTask` passes an **explicitly constructed `env`** to the SDK rather than inheriting `process.env`.

### D5 — Scope guidance, not enforcement

The UI states the expected shape — a fine-grained PAT with **Contents: read/write** on that repo only — but the app cannot verify scopes without an API call. The "Test access" button (Phase 3) is the practical check.

---

## Phases

### Phase 1 — Storage and resolution (no UI)

- [x] `src/lib/secrets.ts`: `encrypt(plaintext)` / `decrypt(record)` using AES-256-GCM, key = SHA-256 of `MISSION_CONTROL_SECRET`. Export `secretsEnabled()`.
- [x] `Project` gains `tokenCipher?: { ciphertext: string; iv: string; tag: string }` and `tokenHint?: string`. Both optional — existing records load unchanged.
- [x] `setProjectToken(id, token | null)` in `projects.ts`, serialised through the existing write chain.
- [x] `gitTokenFor(project)` in `git.ts` implementing D2; `withToken`/`pushBranch`/`ensureWorkspace` take the resolved token as an argument instead of calling `gitToken()` internally.
- [x] Unit tests: encrypt/decrypt round-trip; wrong key fails closed; resolution precedence (project > env > none); `redact()` still strips a project-sourced token from an error string.

### Phase 2 — API surface

- [x] `PUT /api/projects/[projectId]/token` — body `{ token: string }`, stores encrypted, returns the D3 descriptor.
- [x] `DELETE /api/projects/[projectId]/token` — clears it, falls back to env.
- [x] `GET /api/projects/[projectId]/git` — add the descriptor to the existing status payload.
- [x] Reject with 409 + actionable message when `MISSION_CONTROL_SECRET` is unset.
- [x] Test: no response body on any route contains the token string.

### Phase 3 — UI section

In `ProjectsPanel.tsx`, per git-backed project, a **GitHub access** block:

- [x] Status chip: `Project token ·  …ab12` / `Using environment token` / `No token — push disabled`.
- [x] Password field + **Save** (`type="password"`, `autoComplete="off"`), **Clear** when a project token exists.
- [x] **Test access** → `git ls-remote` against the repo with the resolved token; reports reachable / unauthorized / not found, never echoing the credential.
- [x] Helper text naming the expected scope (D5) and linking to GitHub's fine-grained PAT page.
- [x] Push button surfaces the specific failure (`401` → "token rejected", `403` → "token lacks Contents: write").

### Phase 4 — Contain the credential (do this first if anything slips)

- [x] `dispatchTask` builds an explicit `env` for the SDK: `PATH`, `HOME`, `LANG`, the Anthropic auth vars, and nothing else. Verify with a task whose only job is to run `env`.
- [x] Same treatment for the planner `query` call.
- [x] Confirm `redact()` is applied on every path that can carry a git error into a task log or an API response.
- [x] README: a "Credentials" section covering per-project vs env, `MISSION_CONTROL_SECRET`, and the explicit statement that agents cannot read either.

---

## Out of scope

- GitHub App / OAuth device flow instead of PATs (better long-term; much larger).
- SSH key management — the URL path already passes SSH through untouched.
- Per-project *Anthropic* keys.
- Rotation reminders or expiry tracking.

## Risks

| Risk | Mitigation |
|---|---|
| `MISSION_CONTROL_SECRET` lost → every stored token is undecryptable | Fail closed with a clear "re-enter the token" state; never crash the project list |
| Token in a git error reaching a task log | `redact()` on every git error path, covered by a Phase 1 test |
| Agent exfiltrates the token via `Bash` | Phase 4 explicit `env`; this is the one that actually closes the hole |
| Secret written to the docker volume | Encrypted at rest; the key stays in env, never on the volume |

## Implementation notes

- `checkAccess` originally used `git ls-remote`, which **passes on a public repo
  with no credential at all** — a junk token looked valid. It now prefers a
  dry-run push from the workspace (real authorization on the same path a real
  push takes) and falls back to `ls-remote` only pre-clone, reporting
  `verified: "read"` so the UI never overstates what was checked.
- Credential helpers are disabled (`-c credential.helper=`) on authenticated
  commands, so a cached OS-keychain entry cannot mask a bad token.
- `EnvLike` (`agent-env.ts`) replaced `NodeJS.ProcessEnv` in signatures; the
  latter requires `NODE_ENV` and made the env maps in tests untypable.

## Verification

- `npm test` green, including the new secrets and resolution tests.
- Manual: two projects under different owners, each with its own token, both push successfully in one session.
- Manual: a task running `env` shows no `GITHUB_TOKEN` and no `ANTHROPIC_API_KEY` beyond what the SDK needs.
