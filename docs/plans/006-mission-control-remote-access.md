# 006 — Mission Control: run it on `shanks`, reach it from anywhere

**Status:** planned 2026-08-09
**Scope:** `tools/mission-control`, plus host configuration on the homelab box
**Goal:** move the Mission Control server off the Mac onto the always-on Linux box, publish it on the public internet over HTTPS, and put a real authentication layer in front of it — one that is deny-by-default today with one user, and becomes a small allowlist when there are more.

> **Relationship to plan 002.** 002 chose a *native, single-user, loopback-bound* deployment on the Mac. This plan keeps the native runtime and the loopback bind and **supersedes 002's D5** ("no authentication — correctly, for a single-user tool"): the moment the listener is reachable from outside the host, absence of authentication stops being a defensible default. 002's D2 (no LLM credential configuration) is **host-specific reasoning that does not survive the move** — see F3. Everything else in 002 — the worktree isolation, the deleted credential subsystem, the `agent-env.ts` allowlist — carries over unchanged and is, if anything, more load-bearing here.

---

## Why

Two motivations, one of which is not about convenience.

**Availability.** The Mac is a laptop: it sleeps, it travels, and a run that takes forty minutes wants a host that does not. `shanks` is already the always-on box — it runs the tcms stack, microk8s, and the self-hosted CI runner.

**Reach.** Access should not be conditional on being on the LAN or on having an SSH session open. The target is: open a browser on any device, anywhere, and get the board.

The second motivation is what makes this a security document rather than a deployment note.

### The threat model is unusual, and it drives every decision below

Mission Control is not a dashboard. `dispatchTask` (`src/lib/dispatcher.ts:92-110`) runs an agent with `Bash` in its tool set, `permissionMode: "acceptEdits"`, and `maxTurns: 200`, in a working directory that is a real checkout, on a host that holds a working `gh auth git-credential` helper.

So the honest statement of what a session grants is: **arbitrary code execution on the homelab box as `akotrulev`, with push access to the GitHub account.** Not "read some run logs."

Three consequences, and they are the reason the rest of this plan looks heavier than "put a password on it":

1. **Authentication must be terminated before the request reaches the app.** An app-level check that runs after Next.js has routed is one middleware bug away from exposing an RCE surface. The auth layer is a separate process that either passes a request through or refuses it.
2. **It must be deny-by-default and allowlisted by identity** — not "anyone with a valid GitHub account", which is everyone.
3. **It must cover `/api/*` and the SSE stream**, not just pages. `src/app/api/runs/route.ts` creates and starts runs; `.../runs/[runId]/control/route.ts` drives them. A page-only guard protects nothing.

### What the host survey found (2026-08-09)

Read on the box; all of it changes the shape of the work.

| Finding | Detail |
|---|---|
| **F1 — Tailscale is installed and Funnel is already on** | `tailscale 1.102.2`; the node is `clearstep` on tailnet `tailffde84.ts.net`. `tailscale funnel status` shows **`tcp://clearstep.tailffde84.ts.net:443` funnelled to `127.0.0.1:443`** — in raw TCP mode, and **nothing is listening on `127.0.0.1:443`**. It is currently a no-op, but it is a loaded no-op: the day something binds that port it is published to the internet with no further action. |
| **F2 — Caddy is installed** (`v2.11.4`) | A TLS-terminating reverse proxy with automatic certificates is already on the box. No nginx, no `cloudflared`. |
| **F3 — there is no Claude credential on the box** | `~/.claude/` holds `settings.json`, `plugins/`, `backups/` and **no `.credentials.json`**; `ANTHROPIC_API_KEY` is unset. 002's D2 relied on the Mac's keychain login, which does not exist here. The SDK will fail to authenticate until this is fixed — it is a prerequisite, not an afterthought. |
| **F4 — the git credential path already works** | `credential.https://github.com.helper=!gh auth git-credential`, and `git ls-remote` authenticates. 002's D3 reasoning holds unchanged on this host. |
| **F5 — the toolchain is partial** | `java` (Temurin 21), `node` (24.19.0), `python3`, `git`, `docker` are present. **`ripgrep` is absent** (the SDK's search tooling prefers it) and **`dotnet` is absent** — so a `be-dotnet` task would fail at its first build. |
| **F6 — port 8080 and 5432 are taken** | The tcms backend and Postgres. 4300 is free. |

---

## Design decisions

### D1 — The app keeps binding loopback; a reverse proxy is the only listener

`next start -H 127.0.0.1 -p 4300` on `shanks`, exactly as 002 Phase 1 specifies. Caddy binds `:443` and proxies to it. The app is never directly reachable, from the LAN or from the internet, in any configuration.

This is what makes edge-terminated auth actually edge-terminated: there is no second door. It also means an auth misconfiguration fails *closed* (Caddy refuses) rather than *open* (Caddy bypassed).

### D2 — Two front doors, one app: tailnet for your devices, Funnel for the public one

The two access paths answer different questions and it is worth being explicit that they are not redundant:

- **Tailnet (`https://clearstep.tailffde84.ts.net` from a device running Tailscale)** — device-level identity, no browser login, nothing exposed to the internet. This should be the path you actually use daily, on the Mac and on your phone.
- **Funnel (the same hostname, from anywhere, no client)** — a public HTTPS endpoint for the case the tailnet path cannot serve: a borrowed machine, a device you will not enrol, someone you have not onboarded.

Funnel is already enabled (F1), which removes the two things that usually make "expose it publicly" a project: **no router port-forwarding and no dynamic DNS**, because the tunnel is outbound, and **no certificate management**, because the `ts.net` name gets a real Let's Encrypt certificate.

**The critical property to encode: Funnel traffic is anonymous.** Tailscale `serve` adds identity headers (`Tailscale-User-Login`) for tailnet requests; Funnel requests arrive from the public internet carrying no identity at all. So the auth layer in D3 is not optional decoration on top of Tailscale — for the public path it is the *entire* control.

### D3 — Authentication: GitHub OAuth, terminated in `oauth2-proxy`, allowlisted by login

**Recommendation.** Put [`oauth2-proxy`](https://github.com/oauth2-proxy/oauth2-proxy) between Caddy and the app, configured against a GitHub OAuth app, with `--github-user=akotrulev` (an explicit login allowlist). Caddy's `forward_auth` sends every request — pages, `/api/*`, SSE — to it first; unauthenticated requests get redirected to GitHub, and only a request bearing a valid session cookie is proxied to `127.0.0.1:4300`.

Why this one:

- **You already have the identity provider.** GitHub is the account that matters here — it is the same account whose push credential the box holds. Access to Mission Control and access to the repositories collapse to one identity, which is the correct relationship rather than a coincidence.
- **The allowlist is the whole policy.** `--github-user=akotrulev` today; add a login when you add a person. Multi-user later is a config line, not a feature. (`--github-org`/`--github-team` exist if it ever becomes an organisation rather than a list.)
- **It is a cookie session, which SSE needs.** `src/app/api/runs/[runId]/events/route.ts` is consumed by `EventSource`, which **cannot set request headers** — so any scheme built on an `Authorization` header breaks live updates. A cookie is sent automatically on the SSE request, and this is a genuine constraint, not a preference.
- **It terminates before the app**, satisfying the first consequence in the threat model.

**Configuration specifics that matter:**

- `--cookie-secure=true`, `--cookie-samesite=lax`, `--cookie-expire` on the order of 12h with `--cookie-refresh` shorter. `lax` (not `strict`) so the OAuth redirect back from GitHub carries the cookie; combined with the origin check in D4 it is sufficient against CSRF.
- `--email-domain=*` is **wrong here** — the policy is the user allowlist, and leaving the email domain open with no user allowlist authenticates the entire internet.
- `--skip-auth-routes` should be **empty**. There is no public endpoint on this app.
- `--reverse-proxy=true`, and Caddy must set `X-Forwarded-*` (it does by default), so redirect URLs are built against the public hostname.
- The upstream request carries `X-Forwarded-User`; D4 consumes it.

**Alternative if you would rather not self-host the auth proxy:** Cloudflare Tunnel + Cloudflare Access, with GitHub as the IdP and an email allowlist policy. Strictly more capable — MFA, device posture, a real audit log, and the block happens at Cloudflare's edge so probes never reach your line. The costs are that it needs a domain on Cloudflare, a `cloudflared` daemon (not currently installed), and it replaces the Funnel path rather than sitting beside it. If this becomes a tool other people rely on, this is the upgrade; for one user it is more moving parts than the problem needs.

**Rejected — a custom login (password or magic link) implemented in the app.** Hand-rolled session handling is a reasonable thing to build in front of a CRUD app and an unreasonable thing to build in front of remote code execution. It also lands *inside* Next.js, violating the first consequence of the threat model, and it makes you the maintainer of session fixation, timing-safe comparison, cookie flags, and lockout — all of which `oauth2-proxy` has already got wrong once and fixed.

**Rejected — HTTP Basic auth at Caddy.** One shared secret, no revocation, no per-person identity, and it is typed into a browser prompt on whatever machine you happen to be borrowing. Acceptable for a static page; not for this.

**Rejected — tailnet-only, no public path.** It is the most secure option and it does not meet the requirement as stated ("every device, not only on the same network"). It stays available as the daily path under D2, which captures most of its benefit.

### D4 — Defence in depth: the app refuses requests that did not come through the proxy

The proxy is the control; the app should still not be credulous. Two cheap additions in Next middleware:

1. **A shared proxy secret.** Caddy injects a header with a high-entropy value from the environment; middleware rejects any request without it. This makes a direct hit on `127.0.0.1:4300` — from another process on the box, from a future container, from a misconfigured `serve` — fail closed. It is not a substitute for D3; it closes the "someone bypassed the front door" case.
2. **An origin check on state-changing requests.** `POST`/`DELETE` to `/api/*` must carry an `Origin` matching the public hostname. Cookie-based auth plus `SameSite=Lax` already blocks the classic cross-site POST; this is the belt to that pair of braces.

Middleware also becomes the place to surface *who* is acting, from `X-Forwarded-User` — which D7 needs.

### D5 — The credential problem is a prerequisite, not a phase-5 detail

F3: the box has no Claude credential, so the very first dispatch fails until one exists. Two options, in preference order:

1. **`claude setup-token` on the box** — a long-lived OAuth token bound to your subscription, exported as `CLAUDE_CODE_OAUTH_TOKEN` in the service's environment. `agent-env.ts`'s `CLAUDE_` prefix rule already forwards it to agent subprocesses.
2. **`ANTHROPIC_API_KEY`** — separately metered, and 002 D2 removed it from the documented path for good reasons that still apply. Use it only if the token path does not work out.

Whichever is chosen, it lives in the systemd unit's environment file with `0600` permissions, **not** in the repo and not in a shell profile. Note the tension with `agent-env.ts` and accept it consciously: agents *must* receive the credential to work at all, so an agent can always read the credential that pays for it. That is inherent, unchanged by this plan, and is exactly why the identity allowlist in D3 is the real boundary.

### D6 — Stale Funnel configuration is cleaned up before anything binds 443

F1 is a live hazard: Funnel is publishing `127.0.0.1:443` in raw TCP mode today. Configuring Caddy to listen on 443 would publish it *instantly*, before `oauth2-proxy` exists — a window in which an unauthenticated Mission Control is on the public internet.

So the order is fixed and non-negotiable: **turn Funnel off first**, build the whole chain behind loopback, verify auth locally over SSH, and turn Funnel back on last as the final step of Phase 4. Additionally, replace the raw-TCP funnel with the HTTPS form (`tailscale serve --https=443` + `tailscale funnel 443 on`) so Tailscale terminates TLS and the tailnet path gets its identity headers.

### D7 — Multi-user is an allowlist today and a data model later

The requirement says "I will be the only one using it for now, but there may be others." Those are two different amounts of work, and it is worth naming the gap rather than implying D3 closes it.

**What D3 gives you:** authentication and authorisation for *access*. Adding a person is one config line.

**What it does not give you:** Mission Control has **no user model**. Runs and projects (`src/lib/store.ts`, `src/lib/projects.ts`) are global, unattributed, and mutable by anyone who is in. Two people on this instance share one board and one set of execution switches, and the run log will not say who started what.

For a second trusted collaborator, that is tolerable. Before it is more than that, it needs: a `startedBy` on `Run` fed from `X-Forwarded-User`, that identity shown in the UI, and a decision about whether project execution switches are per-user. Phase 5 does the cheap half (attribution); the rest is deferred and stated as deferred.

---

## Phases

Ordered so that nothing is publicly reachable until the layer that protects it is verified.

### Phase 0 — Prerequisites on the host

- [ ] `tailscale funnel --https=443 off` (and clear the raw-TCP serve entry) — **before any other step**, per D6
- [ ] Install `ripgrep` (F5)
- [ ] Establish the Claude credential per D5; verify with a one-shot `claude -p 'say ok'` as the service user
- [ ] Decide on `dotnet` (F5): install it, or accept that `be-dotnet` tasks cannot run on this host and note it in the README
- [ ] Clone the library to a fixed path on the box and confirm `LIBRARY_ROOT`'s two-levels-up default resolves

**Acceptance:** `tailscale funnel status` reports nothing on; `claude -p` returns a completion as the service user.

### Phase 1 — The app runs as a service, on loopback

- [ ] `package.json`: `"start": "next start -p 4300 -H 127.0.0.1"` (shared with 002 Phase 1)
- [ ] `systemd` unit for the app: `Restart=on-failure`, `EnvironmentFile=` the `0600` credential file, `WorkingDirectory=` the checkout, journald for logs
- [ ] `MISSION_CONTROL_DATA_DIR` to a path outside the checkout so `.data` survives a `git clean`
- [ ] Confirm `next.config.mjs`'s `proxyTimeout` (1h) is not undercut by anything new in the chain

**Acceptance:** `curl -s localhost:4300` from an SSH session returns the board; `curl` from the Mac to the LAN IP is refused.

### Phase 2 — Authentication in front

- [ ] Create the GitHub OAuth app; callback `https://clearstep.tailffde84.ts.net/oauth2/callback`
- [ ] `oauth2-proxy` as a second systemd unit, on loopback, with the cookie and allowlist settings from D3 — `--github-user=akotrulev`, empty `--skip-auth-routes`
- [ ] Caddyfile: `:443` → `forward_auth` to `oauth2-proxy` → `reverse_proxy 127.0.0.1:4300`, with the D4 proxy-secret header injected
- [ ] Verify SSE survives the chain — Caddy must not buffer `text/event-stream`, and the cookie must ride the `EventSource` request
- [ ] Confirm long-running requests are not cut by a proxy read timeout (a dispatch can hold a connection for many minutes)

**Acceptance, all over the tailnet or an SSH tunnel, still not public:** an unauthenticated `GET /` redirects to GitHub; an unauthenticated `POST /api/runs` is refused (**not** redirected — assert the status, since a 302 on an API call reads as success to some clients); a signed-in browser gets the board and a run's log updates live.

### Phase 3 — App-side hardening

- [ ] Next middleware: reject any request missing the D4 proxy secret
- [ ] Origin check on state-changing `/api/*` requests
- [ ] Read `X-Forwarded-User` into a request-scoped identity
- [ ] Confirm the failure mode is a clean 403 page, not a stack trace

**Acceptance:** `curl 127.0.0.1:4300/api/runs` on the box, bypassing Caddy, returns 403.

### Phase 4 — Go public

- [ ] `tailscale serve --https=443` → `127.0.0.1:443`, then `tailscale funnel 443 on`
- [ ] Verify from a device with **no** Tailscale client and on a **different** network — phone on cellular is the honest test
- [ ] Re-run the full Phase 2 acceptance list from that device
- [ ] Note the tailnet path still works and is the recommended daily route

**Acceptance:** the board is reachable from cellular after a GitHub login, and only after it.

### Phase 5 — Attribution and operations

- [ ] `startedBy` on `Run`, populated from the identity in Phase 3, shown in the run header and the runs list
- [ ] A visible "signed in as" and a sign-out link (`/oauth2/sign_out`)
- [ ] Back up `.data` (runs, projects, worktree metadata) — a laptop being the host was its own backup story; a headless box is not
- [ ] A short runbook section in `tools/mission-control/README.md`: the two units, where logs go, how to revoke access (remove the login from the allowlist, restart), how to take it off the internet in one command (`tailscale funnel 443 off`)

**Acceptance:** a run started from the phone shows the right `startedBy` on the Mac; `funnel off` makes the public URL dead while the tailnet URL keeps working.

---

## Effort

Phase 0 is an hour, mostly waiting on installs. Phase 1 is half a day. **Phase 2 is the real work** — a day, and the SSE-through-`forward_auth` verification is where the surprises live. Phase 3 is half a day. Phase 4 is an hour if Phase 2 was done honestly. Phase 5 is a day. Call it **three to four focused days**.

## Deferred

- **Real multi-tenancy.** Per-user projects, per-user execution switches, and an authorisation model finer than "in or out". Blocked on the same thing 002 deferred: `dispatchTask` runs an agent with `Bash` and `acceptEdits` on the host, contained only by `agent-env.ts`. That is sound for a small allowlist of people you trust with an SSH key to the same box, and it is **not** a tenancy boundary. Anyone added to the allowlist should be understood as being handed shell access.
- **Cloudflare Access.** The D3 alternative; revisit if the user count grows past a handful or an audit log becomes a requirement.
- **Rate limiting and fail2ban on the public listener.** Funnel's hostname is not guessable and `oauth2-proxy` refuses everything unauthenticated, so this is hygiene rather than a gap — but it should exist before the endpoint is shared with anyone.
