---
name: plan-blueprint
description: Use when writing a system plan's §3, the thin skeleton every feature binds to (stack, architecture, areas, auth, entities). Triggers "plan the skeleton". Not for a feature's design (plan-data-model).
disable-model-invocation: true
---

# Solution Blueprint — the system plan's skeleton

Writes **§3 of a system plan, `## 3. The skeleton`**, and nothing else: the decisions every feature
binds to, made once, so that no feature makes a system decision alone. Stack and versions,
architecture style, functional areas with their file trees and agents, auth, the shared entities and
the cross-cutting conventions.

It is thin on purpose. Each feature's data model, API, screens, key flows and integrations are
designed in that feature's own spec, by `/product:plan-feature`. A skeleton that designs a feature
designs it twice, and the two copies drift.

## Output

§3 of `docs/plans/<NNN>-<system>-system.md`, in the shape of
[`references/skeleton-template.md`](references/skeleton-template.md). The file around it is defined by
[`references/system-plan-format.md`](references/system-plan-format.md); `solution-planner` assembles it
and owns its other sections. [`references/example-skeleton.md`](references/example-skeleton.md) is a
filled §3: its shapes are normative, its domain content illustrative.

**Inputs:** the system plan's §1 (what exists) and §2 (vision and scope), and, in an existing repo,
the code. §4 (epics) may be written after this section; the `Serves` column is filled once it exists.

## Evidence marks (the whole system plan)

| Marker | Means |
|---|---|
| `#confirmed` | Stated by the human, in this session or in a document they gave. Never read out of code (that is `#observed`) |
| `#inferred` | Your reasoning from indirect evidence; the human should scan these |
| `#observed` | Read out of existing code or behaviour, with `file:line` |
| `⚠️ Assumption:` | You proceeded on an unconfirmed premise; each is also a row in the plan's `## Open questions` |

An unknown is `[TBD - <owner>, <by when>]` plus an open question, never a synonym for vague. An
unmarked claim reads as `#confirmed`. Table cells use the one-word form of the same axis: `detected`
(found in the repo: a TFM, a lockfile, a migration, a route) ≈ `#observed` · `stated` ≈ `#confirmed` ·
`proposed` ≈ `#inferred`, the rows the human must look at · `proposed → approved` once confirmed at
`solution-planner`'s approval. In an existing repo `detected` beats every default; in a greenfield one
the `CLAUDE.md` Stack defaults are the proposal, marked `proposed`.

---

## Procedure

### Step 1 — Read what exists

In an existing repo, detect before deciding: the TFM, the JDK and Spring Boot BOM, the Node major from
`package.json`, the React or Next major, the live database's version, the folder layout, the auth
wiring, the error shape the API already returns. Every one of these is a `detected` row with
`file:line`. **An existing codebase keeps the stack and the architecture it has**; the skeleton
records them, it does not redesign them.

Done when every dimension the code answers is recorded as `detected`, with its evidence.

### Step 2 — Settle the stack and versions

One row per dimension the system needs: runtime and language, web framework, frontend, primary
datastore, cache, messaging, data access, auth provider, background jobs, hosting, CI, observability.
A row nobody needs invites a decision nobody has to make, so leave it out.

**Detected wins.** An upgrade is its own feature, never a side effect of another; an up-level-only API
is never planned onto a down-level project.

Done when every needed dimension has a row with a version and an evidence mark, and the version lane
line says what was detected and what it implies.

### Step 3 — Decide the architecture style

State the decision, the reason it is **earned for this system**, and what you rejected. Default toward
the least structure that works: a modular monolith built to be split later, with one team, one
deployable and no split trigger met. **A greenfield system or a live architecture decision → read
[`references/architecture-style.md`](references/architecture-style.md)** (the styles table, the four
split-later rules, the split triggers, the repository layout, the context diagram).

For each pattern in play (CQRS, event sourcing, Saga, Outbox, Repository over the ORM) write one line
stating why it is earned, loading `backend/_shared/pattern-guide` for the concept card when the
decision is live. **One pattern per problem**; a pattern with no stated reason is a finding against
your own skeleton.

Done when §3 holds the style, its reason, what was rejected, a reason per pattern, the modules (for a
modular monolith), the repository layout and a context diagram.

### Step 4 — Decompose into areas, trees and agents

A **functional area** is a coherent piece of business capability one person could own and test
(`Membership`, `Booking`, `Billing`), not a technical layer and not an endpoint. For each, one row:

| Column | Content |
|---|---|
| Area | Short noun phrase |
| Purpose | One sentence, in business terms |
| Serves | The `E` ids from §4 it serves, or `all` for the foundation area |
| Trees | The path globs its code lands in: `src/Booking/*`, `web/app/bookings/*`. A claim someone can falsify, never "the booking area" |
| Agents | The exact catalog names that build it |

- **The trees are what §5 rests on.** `epic-map` decides which features can be built side by side
  from these globs, so a tree two areas share is named in both rows.
- **6–8 areas is a lot.** Beyond that, split into separate systems or merge areas, and say which.
- **The foundation area** holds the scaffold, config, auth wiring, the telemetry base, CI and the app
  shell. In a repo where it is not built yet, it becomes the foundation feature `F1`.

**The agent catalog.** Pick only from these names; an invented one is the most damaging defect a
skeleton can carry, because every feature's implementation plan routes its tasks by them:

| Domain | Agents |
|---|---|
| Backend | `be-dotnet` · `be-java` · `be-node` · `be-python` (the isolated upload-processing worker only) · `be-rust` |
| Data | `data-architect` |
| Frontend | `fe-blazor` · `fe-react` |
| Mobile | `mobile-react-native` · `mobile-ios` · `mobile-android` |
| Desktop | `desktop-macos` · `desktop-windows` |
| Observability | `observability-engineer-dotnet` · `observability-engineer-java` · `observability-engineer-node` · `observability-engineer-rust` |
| DevOps | `devops-engineer` · `devops-auditor` |
| Agent tooling (MCP server or CLI over the project) | `tooling-engineer` |
| QA, per stack (`dotnet`, `java`, `typescript`) | `qa-api-<stack>` · `qa-ui-<stack>` · `qa-mobile-<stack>` · `qa-desktop-<stack>` · `qa-performance-<stack>` · `qa-llm-<stack>` · `qa-bdd-<stack>` · `qa-cicd-<stack>` · `qa-reporting-<stack>` |
| QA, stack-agnostic | `qa-security` · `qa-test-case-designer` · `qa-test-planner` |
| Audit | `code-auditor` |

A capability with no agent is said so, naming the human step or skill that covers it.

Done when every area has a purpose, its trees and its agents, and every agent is a catalog name.

### Step 5 — Auth

One paragraph: the provider and its flows (Authorization Code + PKCE for a SPA, Client Credentials
service to service), the roles and where they come from, where each check is enforced, and what one
user may read of another's data. The house default is Auth0.

Done when every actor in §2 maps to a role and the enforcement point is named.

### Step 6 — The shared entities

Only the entities **two or more features bind to**: name, owner area, one line. Their fields, states
and relationships belong to the spec of the feature that builds them (`## Data model`). An entity only
one feature uses is not shared, and is left to that feature.

Done when every entity two features name is in the table with exactly one owner area.

### Step 7 — Cross-cutting conventions

The conventions every feature follows without deciding again: the error envelope, ids, pagination,
dates and time zones, tenancy, config and secrets, the telemetry base (OpenTelemetry to the local
Grafana stack in `deploy/local/`, landing with the foundation), and the app shell when anything is
user-facing (sidebar, top nav or hybrid, per `design/ux-patterns` §2).

**The tenancy model is load-bearing**: it decides table shape, every query, the auth model and a class
of security test. In a multi-tenant system the isolation approach is stated here.

Done when every row has a convention or says why it does not apply.

### Step 8 — Hand the open decisions to the interview

Do not stop for approval here: `solution-planner` holds one approval over §2, §3 and the feature list.
Give it the questions that materially change the skeleton, each with two or three real options and
the recommended one first, and the `proposed` rows the human must look at. A question the repo
answers is not a question; ordinary engineering judgment is decided and marked `⚠️ Assumption:`.

Done when every `proposed` row and every open decision is listed for the interview.

---

## What stays out of §3

- **Anything one feature owns**: table columns and states, endpoint paths, screens and routes, key
  flows and decision tables, an integration's auth, retry and sandbox detail. `/product:plan-feature`
  designs them in the spec.
- **Quality targets, risks and success measures**: §2's, written by `ba-scoping-writeup`.
- **Features, their order and what runs side by side**: §4, §5 and §6.
- **Tasks, budgets and gates**: each feature's implementation plan.
- **Silent decisions**: every consequential decision carries a why and an evidence mark.

## Version policy

Version-aware, keyed to `CLAUDE.md`'s Stack defaults and its Version policy. In an existing repo the
**detected** version wins over every default, and §3 records it as `detected`.
