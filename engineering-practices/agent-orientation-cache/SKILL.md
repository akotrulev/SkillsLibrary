---
name: ep-agent-orientation-cache
description: The shared protocol every agent uses to persist and reuse its orientation pass — write the current-state map to docs/agent-context/<agent-name>.md, validate it against a git delta on later runs, and update it before finishing. Loaded by an agent, which supplies its own field list. Do NOT invoke directly or route a user request here — it carries no fields of its own. Do NOT use for findings, plans, or specs (docs/audits, docs/plans, docs/specs) or the business model (docs/business-model).
---

# Agent Orientation Cache — the protocol

Every agent in this library opens brownfield work with an **orientation pass**: detect the version lane, map the layout, inventory the **seams to reuse**, learn how the thing is built and run. That answer is the same for every run of the same agent type and changes rarely — so compute it once, persist it, and on later runs re-derive only what provably moved.

This file is the **agent-agnostic half**: where the map lives, its format, how trust in it is earned per run, and when it must be thrown away. The **agent-specific half** — *which fields this agent's orientation derives* — is supplied by the agent that loads this skill.

**The single rule everything else serves:** a cached map that is silently wrong is worse than no map. Trust is earned per run, never assumed.

## The artifact

`docs/agent-context/<agent-name>.md` — in the **target** project, resolved against the current working directory, versioned with the code like `docs/app-map/` and `docs/business-model/`. Never in this skills-library checkout and never in a global config directory (`~/.claude/...`) unless the user explicitly asks for a shared copy.

**One file per agent type** (`fe-react.md`, `be-dotnet.md`, `qa-api-typescript.md`). Not one shared file: each agent orients on different things, so a shared file would be the union of unrelated concerns and stale for everyone. Different agent types never write the same file, so there is no cross-agent write contention.

Leave it untracked if the project's `.gitignore` already excludes `docs/`; otherwise it is a normal committed file. Committing is still governed by the global rule — commit only when the user asks.

## Phase 1 — Read-validate (before any orientation work)

Run these checks in order and stop at the first that matches.

| # | Condition | Verdict |
|---|---|---|
| 1 | File absent, or no `<!-- orientation-cache v1 -->` marker, or a version marker you don't understand, or the header block won't parse | **FULL** |
| 2 | `git rev-parse HEAD` fails (not a git repo) | **FULL** |
| 3 | `git merge-base --is-ancestor <baseline> HEAD` fails — the baseline is not an ancestor of HEAD (rebase, squash, shallow clone, different branch lineage) | **FULL** |
| 4 | `Last verified` is more than **30 days** old | **FULL** |
| 5 | The delta set (below) is **empty** | **TRUST** — skip orientation entirely |
| 6 | Anything else | **DELTA** — go to the delta pass |

**Always exclude `docs/agent-context/` from the delta set.** The update-after step stamps the current `HEAD` into the file and that stamp is itself a change — so a naive `HEAD == baseline` test can never be true once the cache is committed, and the TRUST path would never fire. The cache's own churn is not evidence about the code.

Three commands answer 2, 3, 5 and feed 6:

```bash
git rev-parse HEAD                                  # 2 — fails ⇒ not a git repo
git merge-base --is-ancestor <baseline> HEAD        # 3 — non-zero ⇒ FULL
git status --porcelain && git diff --name-only <baseline>..HEAD   # 5, 6
```

**Use `merge-base --is-ancestor`, never `cat-file -e`.** After a rebase or squash the old baseline commit usually still *exists* in the local object store while no longer being on your branch — `cat-file -e` would pass and `git diff <baseline>..HEAD` would then report a large, meaningless delta. Ancestry is the question that matters.

### The delta pass

Union the paths from `git diff --name-only <baseline>..HEAD` and `git status --porcelain`, drop anything under `docs/agent-context/`, then:

- **Any fingerprint file in the delta** (the manifests/lockfiles/build config listed in the file's header) → the **version lane is invalid**, and so is every field keyed to it. Re-run version detection from scratch, then re-derive the version-dependent sections.
- **Any changed path under a mapped area** → that section's entries are stale. Re-derive **that section only**; carry the rest forward unchanged.
- **Delta touches nothing the map covers** → treat as TRUST, and say so.

Report the outcome as one line — `Orientation: cached (delta: 2 sections refreshed)` — not as a narration of the checks.

### Never cached — re-derive on every run regardless of verdict

- **Green-on-arrival.** Whether the thing builds and its tests pass is working-tree state, not layout. Always re-verified through the agent's own gate. A red state on arrival is still a finding to report, not your bug to absorb.
- **Anything the current change depends on directly.** Before editing a file the map names, confirm it exists and still matches the description. **The map is a lead, not evidence** — the same rule the audit lane applies to a "Resolved" verdict.
- **`#volatile` fields.** Live-resource facts describe a system that can change with no commit behind it: a database server version probe, a live cloud read, a device/emulator state, a deployed API's shape. Recorded for context, always re-probed before use.

## Phase 2 — Derive the gaps

Whatever the gate left unresolved, derive it exactly as the agent's own orientation pass says — **recover, don't author**. Then write or refresh those sections. On a FULL verdict this is the whole orientation; on DELTA it is a slice; on TRUST it is nothing.

## Phase 3 — Update-after (part of closing the work, not an afterthought)

Every run that reached the work — fix, extend, or full build — closes by updating the file:

1. **Correct anything the run disproved.** A wrong line in the cache is worse than a missing one; if you found the map lying, fix the line before you finish.
2. **Add the seams the run created.** A new page object, typed client, builder, migration, state container, endpoint, dashboard — this is the highest-value delta in the whole protocol, and the one most often skipped.
3. **Re-stamp** `Last verified` (today) and `Baseline commit` (current `HEAD`), and recompute the fingerprint hashes.
4. **Prepend one session-log line** — date · mode · one line on what changed. Keep the newest 10, drop the rest.
5. If the run ended early or was blocked, still update what you learned, and say in your output contract that the cache is partial.

## Authoring rules

- **A map, not a mirror.** Record the pointer and the convention, not the enumeration: `page objects: tests/pages/, 34 classes, BasePage.cs:12 sets the convention` — never a list of 34 classes. Ceiling ~400 lines; a file pushing it is recording the wrong altitude.
- **Short declarative statements** with `file:line` evidence. Every line in the seams and conventions sections is `#confirmed` (has evidence), `#inferred` (derived, plausible, unverified), or `#volatile` (live resource, always re-probed). Untagged means `#confirmed`.
- **Critical facts near the top.** Version lane and build/run commands before layout; layout before seams.
- **Skip what the repo already states.** Cite the project's own CLAUDE.md / README convention, don't copy it.
- **Newest-first** in the session log, one consolidated "known unknowns" list rather than per-session copies that go stale.

## The fence — what this file is not

It records **what the code is**. It never records what is wrong with it or what to do next:

| Content | Belongs in |
|---|---|
| Findings, verdicts, severity tables, conformance rounds | `docs/audits/` |
| Implementation plans, task lists | `docs/plans/` |
| Designs, specs, approved approaches | `docs/specs/` |
| Business flows, entity states, decision tables, conflicts | `docs/business-model/` (`ba-project-memory`) |
| Screen inventories from a live crawl | `docs/app-map/` (`mobile-app-crawler`) |
| Missing `data-testid` reports for the dev team | `missing-testids.md` |

A cache that accumulates opinions has become a findings document nobody reviews. If a line is a judgment rather than an observation, it is in the wrong file.

## Output contract

Every agent that loads this skill adds one line to its own output contract:

```
Orientation: cached (full) | cached (delta: <n> sections refreshed — <what invalidated them>) | full (<reason>)
Orientation cache: updated | updated (partial — <why>) | created
```

## Anti-examples

**Bad:** the agent reads `docs/agent-context/be-dotnet.md`, sees `DbContext: src/Data/AppDbContext.cs:18`, and edits that file without checking — but a refactor three commits ago moved it. The delta gate exists precisely to catch this, and the spot-check exists for when the gate's granularity misses.

**Bad:** the cache grows a "Known issues" section listing 14 things the agent noticed and never fixed. Those are audit findings with no round, no ID, and no owner. They belong in `docs/audits/` or nowhere.

**Bad:** a run finishes, having added four new page objects and a fixture, and doesn't update the file. The next run's map is confidently incomplete — worse than the run before it, because the delta gate will report only the sections git says changed and the agent will trust the rest.

## Handoffs

- The file skeleton to write → `references/file-template.md`
- The agent's own field list (what goes in each section) → the agent that loaded this skill
- Persist a *business* model instead of a code map → `business-analysis/skills/ba-project-memory`
- Verify a claim before reporting the work done → `engineering-practices/verify-before-done` (`ep-verify-before-done`)
