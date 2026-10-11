# 006 — A docs-only agent that writes a feature's document and its e2e test cases — plan (2026-10-11)

**Goal:** One agent, `qa-feature-spec-writer`, run per feature as `/qa-<stack>:feature-spec`. It traces a feature once and writes two documents in the service repo: the feature document and an **e2e-only** test-case suite. Every case runs through a public surface or a test hook the deployed environment already has. A separate QA repository implements the suites; the agent writes no code and runs nothing.

**Status:** E1 and E2 built 2026-10-11; the gate (§6) passed. Next: the user's `git push origin master`, then H1 (run it on two real features). Built but unverified: no run of `/qa-<stack>:feature-spec` on a real feature yet (H1). Prerequisite outside the plan: plan 005's 8 commits are not on `origin/master` (005 H1 report, D1), so the installed plugins carry neither 005 nor this plan until the push; this machine's shell has no GitHub credential, so the push is the user's job.

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| One run per feature produces the document and the suite | Two agents, two runs: `be-feature-documenter` (`backend/_shared/agents/be-feature-documenter.md`, `/dev:document-feature`) writes `docs/features/<NNN>-<slug>.md`; `qa-test-case-designer` Code mode (`qa/manual/agents/qa-test-case-designer.md:72-80`) traces the **same** code again for the basis | One agent that traces once and writes both from that one trace (§2) |
| Cases are e2e only | The designer writes whatever the basis supports. In the 005 H1 trial its suite was automated in-process (WebApplicationFactory + Testcontainers, `WebhookRetryAndDeliveryTests.cs`), and nothing in the suite says which surface a case uses | An e2e rule: every case names its surface and its seam, Setup and Cleanup included; a case that needs another seam is written as **needs-hook** (§3) |
| The QA repo knows which agent automates which case | The hand-off notes are prose (`qa-test-case-designer.md:163`) | `Surface` and `Automated by` on every case (§3.3) |
| Test hooks are found once, not 163 times | No step looks for them | A seam inventory, kept in the orientation cache (§3.2) |
| The document and the suite share a number | The documenter takes the next free number in `docs/features/`, and the designer the next free one in `docs/test-cases/`. The two counters can drift (005 H1, D9) | One `NNN` for all three files (§4) |
| The trace finds every writer of a shared field | Edges asks for *readers* of written fields only (`backend/_shared/feature-trace/SKILL.md:89`). The 005 trial missed the operator-settle writer (005 H1, D2) | Edges also lists other writers (§5) |
| Code mode has slice ids | `connections.md:7` takes ids from the KB only. With no KB, the 005 trial invented `L<n> T<n>` (005 H1, D3) | A local id scheme for Code mode (§5) |
| Async budgets are not guesses | The budget comes from "the reaction's mode or the NFR" (`qa/manual/test-case-writer/SKILL.md:54`). Code mode has neither, so every budget was `#assumption` (005 H1, D7) | In e2e mode the budget is one named environment parameter (§5) |

## 2. The agent — one trace, two documents

`qa/manual/agents/qa-feature-spec-writer.md`, shipped in all three `qa-*` plugins beside `qa-test-case-designer`. The command is `qa/manual/commands/feature-spec.md`, which gives `/qa-java:feature-spec`, `/qa-dotnet:feature-spec` and `/qa-typescript:feature-spec`.

**Input:** a feature sentence plus its entry points — exactly the form of a `docs/features/INVENTORY.md` command line. Or a row number (`#57`) when that file exists.

**It procedures by citation, not by copy.** The document's shape and self-review belong to `be-feature-documenter`; the five steps and the depth gate belong to `qa-test-case-designer`. The new agent reads the named sections of those two files and follows them. It adds only what §3 and §4 define. If one of them changes, the other picks the change up with no edit.

| # | Step | Follows | Adds | Exit gate |
|---|---|---|---|---|
| 0 | Orient | `engineering-practices/agent-orientation-cache` against `docs/agent-context/qa-feature-spec-writer.md` | The seam inventory (§3.2) on a FULL verdict | Verdict in one line; seams listed |
| 1 | Locate & scope | `be-feature-documenter.md` Step 1 (proportional gate and scope table) | Takes the `NNN` (§4) | Scope table shown |
| 2 | Trace, once | `dev:doc-feature-trace`, all ten stops, seven inventories | Nothing — this trace record feeds steps 3 and 4 | Every scoped entry point traced |
| 3 | Write the feature document | `be-feature-documenter.md` "Document contract" and its Step 4 checklist | — | Document written; checklist passes |
| 4 | Write the suite | `qa-test-case-designer.md` Steps 1–5. Step 1 takes the document and the trace record as its basis, with no second trace | The e2e rule (§3) in Steps 3–5 | Suite and basis written; depth gate and e2e gate pass |
| 5 | Report | — | Marks the `INVENTORY.md` row `documented + suite` when the file exists | Output contract (§4) |

**Write reach:** `docs/features/**`, `docs/test-cases/**`, `docs/agent-context/qa-feature-spec-writer.md`. **Bash** is inspection only: no build, no test run, no package install, no commit unless asked.

## 3. The e2e rule

### 3.1 Allowed seams

| Seam | Means | Example |
|---|---|---|
| `public` | What a real user, partner or provider can reach in the deployed environment: the gateway API, the web UI, the mobile app, inbound webhooks signed the way the provider signs them | `POST /payments/webhooks/paysafe` with the sandbox signing key |
| `hook:<name>` | A test-only hook that **already exists in the code** and is meant to be enabled in a test environment | DevTestHarness command, payment TestMode, an admin "run job now" endpoint |
| `needs-hook:<name>` | The case needs a seam that does not exist yet: a settable clock, a job trigger, fault injection, a bus read | "Advance the retry job's clock by 15 min" |

Not allowed: anything in-process (unit, component or WebApplicationFactory-style tests), direct database reads or writes, and direct bus publish or consume. **This applies to Setup and Cleanup too:** seed and tear down through the API or a hook, never with SQL.

### 3.2 The seam inventory (step 0)

Grep the repo for test hooks: test-mode flags, harness projects (`*TestHarness*`, `*TestMode*`), admin or management endpoints that run a job or set state, sandbox credentials in `appsettings.*`, and feature flags. Each hook gets one row: name, what it does, entry point `file:line`, how it is enabled. Whether it is **enabled in the deployed test environment** is not visible in code, so every hook carries that as an open question until a run confirms it. The rows go into the cache's *Seams to reuse* section and are reused by every run.

### 3.3 What changes in a case

Each case gains three fields after `Technique`:

| Field | Values |
|---|---|
| `Surface` | `API` · `UI` · `Mobile` · `Webhook` |
| `Seam` | `public` · `hook:<name>` · `needs-hook:<name>` |
| `Automated by` | `qa-api-<stack>` (API, Webhook) · `qa-ui-<stack>` (UI) · `qa-mobile-<stack>` (Mobile) |

- **The assertion is observable on the same surfaces.** "Balance is 150.00" is asserted by reading the account through the API, not the table. An effect that no surface shows is either asserted through a hook, or the case is `needs-hook` with the read it needs.
- **Async effects** read `within <BUDGET_NAME>, <observable>` and are polled. `<BUDGET_NAME>` is one environment parameter declared once in Setup, e.g. `ASYNC_BUDGET = 30 s #assumption`, which replaces a per-case invented number.
- **Field validation stays where the public API shows it**, e.g. a parameterized `400` case per field. A rule that lives only inside a pure function and that no surface exposes is not a case: it is listed under *Not e2e-testable* with the reason.
- **A `needs-hook` case is fully written**, steps and expected result included, so it is ready on the day the hook lands. Its hook is described once in a `## Hooks needed` section of the suite: what it must do, why, which cases wait on it, and that it routes to `be-<stack>`.

### 3.4 The e2e gate (step 4, added to the depth gate's rows)

| Condition | Severity |
|---|---|
| A case, its Setup or its Cleanup touches a seam outside §3.1 | blocker |
| A case has no `Surface`, `Seam` or `Automated by` | major |
| A `needs-hook` case's hook is missing from `## Hooks needed` | major |
| An async case uses a number instead of the named budget | major |
| A P1 case is `needs-hook` and has no P1 alternative over a public seam, where one exists | major |

## 4. Files, numbering and the report

- **One `NNN` per feature**: the next number free in **both** `docs/features/` and `docs/test-cases/`. Files: `docs/features/<NNN>-<slug>.md`, `docs/test-cases/<NNN>-<slug>-basis.md`, `docs/test-cases/<NNN>-<slug>.md`. An existing feature document for the same scope is reused (brownfield): the suite takes its number.
- **The agent never commits.** In a repo where the docs stay untracked, they stay untracked.
- **Report:**

```
Orientation: <verdict> · seams: <n> hooks (<n> unconfirmed in the environment)
Feature: <name> — <n> entry points traced
Written: docs/features/<NNN>-<slug>.md · docs/test-cases/<NNN>-<slug>-basis.md · docs/test-cases/<NNN>-<slug>.md
Cases: <n> — by surface (API n · UI n · Mobile n · Webhook n) · by seam (public n · hook n · needs-hook n) · by layer
Depth gate: <result> · E2E gate: <result>
Hooks needed: <n> — one line each, routed to be-<stack>
Not e2e-testable: <n> — one line each
Open questions: <n> — the highest-value ones
INVENTORY: row #<n> marked | no inventory
```

## 5. Skill fixes from the 005 trial that this agent depends on

| Fix | File | Change |
|---|---|---|
| D2 — other writers | `backend/_shared/feature-trace/SKILL.md` §7 Edges (`:89`) and the trace-record copy (`:146`) | "For every written field, search for the readers **and the other writers**." Add an `Also written by` column. One-line addition to the self-check |
| D3 — Code-mode ids | `qa/manual/requirements-breakdown/references/connections.md` (`:7`) and `qa/manual/cross-feature-test-design/SKILL.md` Procedure 1 | With no KB: `T<n>` trigger, `R<n>` reaction, `S<n>` shared field, `I<n>` invariant, local to the basis, and stated to be local in §8's header. KB ids win whenever a KB exists |
| D7 — async budget | `qa/manual/test-case-writer/SKILL.md` *Async effects* (`:54`) | Add: "With no mode or NFR, declare one named budget in Setup and cite it by name." That is the same rule §3.3 applies |

D4–D6 (the .NET timing skill and `qa-api-dotnet` are NUnit + RestSharp only) are **out of scope**: the target QA repo is NUnit + RestSharp, so they do not bite there. D1 is the push (Status). D8 needs no change.

## 6. The gate (E2 only)

Run from the SkillsLibrary root, in this order:

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` exits 0.
2. `claude plugin validate .` ends with `✔ Validation passed`.
3. `python3 tools/plugin-surface-check.py` reports OK.
4. `python3 tools/token-audit.py --violations-only` lists none of the files this plan wrote or changed.
5. `python3 tools/qa-version-check.py` reports OK.
6. Cross-reference check: every section heading the new agent cites by name in `be-feature-documenter.md` and `qa-test-case-designer.md` exists verbatim (`grep -n` each one).
7. Format sweep over the changed files: no inline `TODO`, every `file:line` in §5 still points at the edited text.

## Decisions

**D1 — A new agent, not an e2e mode on the designer.** The user chose this (2026-10-11).

| Option | Verdict | Why |
|---|---|---|
| New agent that cites the two existing ones | **chosen** | One run per feature over 163 features; one trace instead of two; the e2e rule lives in one file |
| An `e2e-only` mode on `qa-test-case-designer`, after `be-feature-documenter` | rejected | Two runs and two traces per feature: about 160 extra sessions |

Cost: a third file couples to the section headings of the other two. The gate's step 6 checks that.

**D2 — Procedures by citation.** The agent reads `be-feature-documenter.md` "Document contract" + "Step 4 checklist" and `qa-test-case-designer.md` "Steps" + their step details, and does not copy them. Cost: a heading rename in either file breaks the new agent silently until the next gate. That is why gate step 6 exists.

**D3 — Allowed seams are public surfaces plus existing test hooks.** The user chose this (2026-10-11). A case that needs any other seam is written as `needs-hook` and routed to `be-<stack>`. Cost: until those hooks land, the temporal and fault cases from 005 (exact-instant clock, lost bus message) stay unautomated.

**D4 — Output goes to the service repo's `docs/`, untracked.** The user chose this (2026-10-11). The QA-repo session reads the suites by absolute path. Cost: the docs exist on one machine only, and nothing versions them.

**D5 — It ships in the three `qa-*` plugins, not in `dev`.** It is a QA deliverable, and `dev` stays stack-free. `be-feature-documenter` stays where it is for documentation-only runs.

**D6 — (2026-10-11, E2) `test-case-writer/SKILL.md` stays over the token budget.** The gate's step 4 expected no listed file this plan changed; that file was already a violation (17576) and the §5 sentence adds 76. Reading A: trim the skill now. Reading B (taken): leave it — the violation predates this plan and trimming unrelated text exceeds E2's scope. Cost: the audit still lists the file until someone splits it.

## Answered questions (2026-10-11)

**O1 — Where do the documents go:** flexinvest `docs/`, untracked.
**O2 — Which seams count as e2e:** public surfaces plus test hooks that already exist; anything else is `needs-hook`.
**O3 — New agent or a mode:** a new agent.

## 7. Tasks

### E1 — the agent, its command and their registration

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa/manual/agents/qa-feature-spec-writer.md` and `qa/manual/commands/feature-spec.md` exist and are registered in `qa-java`, `qa-dotnet` and `qa-typescript` in `.claude-plugin/marketplace.json`. The agent implements §2–§4.
**Depends on:** —
**Budget:** ~110k — CLAUDE.md 25k, this plan §1–§4 and D1–D5 12k, `be-feature-documenter.md` 12k, `qa-test-case-designer.md` 15k, `qa/manual/commands/test-cases.md` as the command pattern 1k, `test-case-writer/SKILL.md` case forms 8k, marketplace `qa-*` entries 5k, writes ~25k (agent ~180 lines, command, three registrations).
**Gate: none** — this plan gates once, in E2. Do not run `claude plugin validate`, the `tools/*.py` checkers, the token audit or any compiler.

- Frontmatter: `name: qa-feature-spec-writer`; a description ≤ 500 characters with triggers ("document this feature and write its e2e test cases", "spec this inventory row") and fences (docs only → `be-feature-documenter`; cases without the e2e rule → `qa-test-case-designer`; automation → `qa-api/ui/mobile-<stack>`); `tools: Read, Write, Edit, Bash, Glob, Grep`.
- Body: §2's step table and write reach, §3 in full (seams, seam inventory, case fields, e2e gate), §4's numbering and report. Each step cites the exact section headings of the two agents it follows (D2).
- Command: the same shape as `test-cases.md`, adopting the new agent; `argument-hint: [feature sentence + entry points | #<inventory row>]`.
- Register the agent and the command in all three `qa-*` plugin entries, next to `qa-test-case-designer` and `test-cases.md`.
- **Not in E1:** the §5 skill fixes, the catalog and README, and the gate (all E2).
- **As built (2026-10-11):** as planned, no divergence. `qa/manual/agents/qa-feature-spec-writer.md` (description 440 chars, 5-step table, e2e rule, report) and `qa/manual/commands/feature-spec.md`; registered in qa-java, qa-dotnet and qa-typescript beside `qa-test-case-designer` / `test-cases.md` (`.claude-plugin/marketplace.json`, 6 added lines, `json.tool` OK). Cited headings, for E2's step 6: be-feature-documenter — `Steps`, `Document contract — \`docs/features/<NNN>-<feature-slug>.md\``, `Step 4 checklist`; qa-test-case-designer — `Code mode — a feature in the code → test basis`, `Steps`, `Step 1 detail`…`Step 5 detail`, `Output contract`. Unverified: the gate has not run; `Step 4 checklist` is a bold lead-in, not a `#` heading, so grep it as text.

### E2 — the three skill fixes, the docs and the gate

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** §5's three fixes are in place, the catalog and README list the agent and the command, and §6 passes.
**Depends on:** E1 (the agent the docs describe and the gate checks).
**Budget:** ~110k — CLAUDE.md 25k, this plan §3.3, §5, §6 and E1's As built 10k, `feature-trace/SKILL.md` 10k, `connections.md` 8k, `cross-feature-test-design/SKILL.md` 6k, `test-case-writer/SKILL.md` 10k, catalog and README sections 10k, the E1 agent for the gate's step 6 8k, edits ~10k, gate output ~10k.
**Gate:** §6, in order. Fix what it finds: a failure may belong to E1.

- Apply §5's three rows exactly as written there.
- `docs/skills-catalog.md`: the `qa-*` row of the command table (`:33`) gains `:feature-spec`; one bullet under the qa/manual agents next to `qa-test-case-designer` (`:144`); the `qa/manual/` sentence (`:58`) names three agents.
- `README.md`: the same command and agent count changes wherever it lists the `qa-*` surface.
- Run §6. Then close out; this task deletes the last automated block, but H1's block stays, so the plan does **not** move.
- **As built (2026-10-11):** §5's three rows applied as written — `feature-trace/SKILL.md:89-91` and `:147` (`Also written by` column in both Edges tables, sample row, self-check 9), `connections.md:7` plus its Edges-column mapping, `cross-feature-test-design/SKILL.md:35` (Code-mode `T<n>`/`R<n>`/`S<n>`/`I<n>`, local to the basis, stated in §8's header), `test-case-writer/SKILL.md:54` (named budget in Setup). Catalog `:27,:33,:58` plus a new `agents/qa-feature-spec-writer` bullet; README `:63,:104,:106` plus a `:feature-spec` row. Recounted: 65 command files, 73 registrations, 12 commands per qa stack (13 for qa-dotnet); `CLAUDE.md` "64-command" → "65-command". Gate: `json.tool` OK; `claude plugin validate .` ✔ Validation passed; `plugin-surface-check.py` OK; `qa-version-check.py` OK; `token-audit --violations-only` lists none of the new files, only `qa/manual/test-case-writer/SKILL.md` [qa-java] at 17652 (17576 before — see D6); §6 step 6: every cited heading found in both agents (`Step 4 checklist` is a bold lead-in at `be-feature-documenter.md:70`); step 7: no `TODO`/`FIXME` in changed files, §5 lines still point at the edited text. Repair: E1's commit had left the plan's tail duplicated (a second Close-out, Prompts and stale E1/E2 blocks); removed the duplicates, leaving one Prompts section with H1's block.

### H1 — run it on real features (the user)

**Stack:** `human` · **Agent:** `human` · **Owner:** the user
**Deliverable:** H1's As built records whether two INVENTORY rows produced documents and suites that the QA repo can automate without asking the service repo anything, and which hooks were requested.
**Depends on:** E2, and the push (Status).
**Gate:** the checklist in H1's prompt block.

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them in order, one session each, in the SkillsLibrary checkout on `master`; never create a branch. Each block is complete on its own. Only E2 runs the gate (§6). No prompt writes into any project's `docs/business-model/`. **The cost, accepted and stated once:** E1's commit is ungated, so the tree is not known to validate until E2, and the plan cannot be stopped after E1 and trusted.

| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| E1 | `docs` | `general-purpose` | — | ~110k |
| — | `git push origin master` | **the user** | E2 | — |
| H1 | `human` | **the user** | E2, the push | two features |

E1 and E2 landed 2026-10-11; their blocks are deleted. H1 is live.

---

### H1 — run it on real features (the user)

````
H1 of docs/plans/006-e2e-feature-spec-writer.md — your checklist.

0. In SkillsLibrary: `git push origin master`, then `claude plugin marketplace update skills-library`.
   Open a fresh session at ~/projects/flexinvest-microservices (qa-dotnet, dev and business-analysis
   are enabled in .claude/settings.local.json).
1. Pick two rows from docs/features/INVENTORY.md: one with an API trigger and one with a schedule or
   a consumer. Run `/qa-dotnet:feature-spec #<row>` for each, one session each.
2. Check each suite:
   - every case has Surface, Seam and Automated by; nothing seeds or reads the DB or the bus;
   - the seam inventory found the hooks you know about (DevTestHarness, payment TestMode, …);
   - `## Hooks needed` names hooks a backend dev could build from the description alone;
   - async cases cite the one named budget;
   - the feature document, basis and suite share one NNN, and the INVENTORY row is marked.
3. In a session at ~/projects/Quality-Assurance: `/qa-dotnet:api` Mode B with one of the two suites
   (absolute path). Check that it automates the public and hook cases in ApiTests without needing
   anything from the service repo except the suite, and that it reports the needs-hook cases as
   deferred.
4. Tell a session in SkillsLibrary to record your verdict as H1's As built (what worked, what the QA
   session still had to ask, hooks requested), then close out per the plan's "Close-out — every task".
   Deleting this block files the plan into docs/plans/implemented/.
````
