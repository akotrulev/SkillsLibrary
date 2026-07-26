# meta/ Remediation Plan

Source: audit of `meta/skill-creator` + `meta/writing-skills`, 2026-07-12.

**Context.** `meta/` holds the two skill-authoring skills. The audit found: (1) the two skills directly contradict each other on how to write a skill description; (2) neither references the library's real authoring authority (`.skill-template/`, CLAUDE.md conventions); (3) `writing-skills` is unregistered, collides with `skill-creator` on triggers, and carries stale obra/superpowers leftovers; (4) its Iron Law mandates per-edit subagent pressure-testing, violating the library's conservative agent-spawning policy; (5) assorted mechanical nits.

**Ground rules for executing this plan:**
- Run one phase at a time, checking items off as they land. Commit per phase.
- `skill-creator` is live (registered plugin skill) — edits to it take effect immediately; re-read edited sections with fresh eyes before committing.
- `meta/` is out of remote scope per CLAUDE.md — do not add it to `marketplace.json` in any phase.

---

## Phase 1 — Resolve the description-rule contradiction (highest impact, do first)

The one finding that actively misleads today, since `skill-creator` is live.

**House rule to adopt** (already the de-facto `.skill-template` + shipped-catalog style):

> A description states **when to trigger** (concrete "Use when…" conditions + literal trigger phrases) and **when NOT to** (named sibling/peer to defer to). It may name what the skill produces in one clause, but must **never summarize the skill's internal workflow/process** — a workflow-summary description causes Claude to follow the description and skip the body (evidence: `writing-skills/SKILL.md` CSO section).
>
> Shape: `Use when <conditions>. Triggers: "<phrase>", "<phrase>". Do NOT use for <adjacent case> (use <sibling>).`

- [ ] 1.1 In `skill-creator/SKILL.md` (~line 67, the `description` bullet in "Write the SKILL.md"): replace the "pushy description / include what it does AND when to use" guidance with the house rule above. Keep the undertriggering warning, but redirect the cure from "pushy prose" to "enumerate concrete trigger phrases and symptoms"; add the workflow-summary trap as an explicit don't.
- [ ] 1.2 In `writing-skills/SKILL.md` (CSO section, ~line 150): soften "NEVER state what it does" to match the house rule (one what-clause is fine; workflow summary is not). Keep the ❌/✅ examples — they carry the evidence.
- [ ] 1.3 Cross-check: both skills now state the *same* rule in compatible words; each cites `.skill-template/*.SKILL.md` as the canonical example of the shape.
- [ ] 1.4 Commit: `meta: reconcile description-authoring rule across skill-creator and writing-skills`.

## Phase 2 — Decide writing-skills' fate (everything else about it follows)

Decision to make with the user before executing: **(a) merge** or **(b) register fenced**.

- **Option (a) — merge & retire (recommended):** move the unique content into `skill-creator/references/` and delete the rest.
  - Unique content worth preserving: the CSO section (description trap + keyword coverage), the rationalization-table / red-flags / loophole-closing patterns for discipline skills, `testing-skills-with-subagents.md`, `persuasion-principles.md`.
  - Redundant with skill-creator or upstream-specific: anatomy/structure sections, word-count budgets, Iron Law framing, deployment checklist.
- **Option (b) — keep & fence:** keep `writing-skills` as a standalone reference skill with a non-colliding description: `Use for the TDD/pressure-testing discipline when hardening a skill against rationalization; use skill-creator for the interactive create→eval→improve loop.`

Steps (written for option (a); adapt if (b) is chosen):

- [ ] 2.1 Confirm option with the user.
- [ ] 2.2 Create `skill-creator/references/cso-descriptions.md` from the CSO section (description trap evidence, keyword coverage, naming guidance — lowercased examples, see Phase 4).
- [ ] 2.3 Create `skill-creator/references/discipline-skills.md` from the rationalization tables, red-flags list, loophole-closing, and spirit-vs-letter material; fold in a pointer to `persuasion-principles.md`.
- [ ] 2.4 Move `testing-skills-with-subagents.md` and `persuasion-principles.md` to `skill-creator/references/`; update internal links. Move `graphviz-conventions.dot` + `render-graphs.js` too, or drop them if the flowchart guidance is cut.
- [ ] 2.5 Add a short "Hardening discipline skills" pointer section to `skill-creator/SKILL.md` referencing the new files ("read when the skill enforces a rule agents will rationalize around").
- [ ] 2.6 Delete `meta/writing-skills/`; update `README.md` lines 64 and 174 (folder listing + provenance table) to reflect the merge.
- [ ] 2.7 Commit: `meta: fold writing-skills into skill-creator references, retire the standalone skill`.

## Phase 3 — Purge stale upstream (obra/superpowers) references

Applies to whichever files survive Phase 2.

- [ ] 3.1 Replace `superpowers:test-driven-development` / `superpowers:systematic-debugging` with `ep-test-driven-development` / `ep-systematic-debugging` (the library's adapted names).
- [ ] 3.2 Delete the personal-skills-directory note (`~/.claude/skills`, `~/.agents/skills/` Codex path) — irrelevant to this repo's layout.
- [ ] 3.3 Delete the deployment-checklist items "push to your fork" / "contribute back via PR" — upstream leftovers; replace with the library's actual finish step (update the domain plan/handoff docs, commit).
- [ ] 3.4 Fix the `@`-link self-contradiction: `@graphviz-conventions.dot` and `@testing-skills-with-subagents.md` use the force-load syntax the same skill forbids. Change to plain-name references with "read when…" guidance.
- [ ] 3.5 Reframe the Iron Law: subagent pressure-testing becomes a **recommended verification step**, subject to the library's cost-before-speed spawning policy (each extra agent is a deliberate spend, per `ep-delegate-to-subagents` / `ep-parallel-agents`). Remove the "delete it, start over" absolutism for edits; keep the core insight (untested skills fail in ways you won't predict — verify before shipping).
- [ ] 3.6 Grep sweep: `grep -rn "superpowers\|~/.agents\|your fork" meta/` returns nothing.
- [ ] 3.7 Commit: `meta: purge superpowers-upstream leftovers, gate subagent testing behind spawning policy`.

## Phase 4 — Anchor to the library's house conventions

- [ ] 4.1 Add an "In this library" preamble near the top of `skill-creator/SKILL.md` (after the intro): when authoring for *this* repo, `.skill-template/{generator,reference,reviewer}.SKILL.md` + `.skill-template/agent.md` + CLAUDE.md conventions are authoritative — domain prefixes (`qa-*`, `ba-*`, `ep-*`, `fe-*`, `be-*`), router+`references/` shape for one-of-N families, version-aware recipes, peer-handshake fences. On conflict, house style wins; the skill's generic guidance applies to skills authored for other targets.
- [ ] 4.2 Same preamble notes the memory-encoded workflow: research existing skills first (web-search for prior art before drafting), plan-file-then-step-by-step, one node per session with GAP-ANALYSIS/HANDOFF updates.
- [ ] 4.3 Replace `writing-skills`-origin word-count budgets (<200/<500 words) wherever they survive with the library's actual budget: SKILL.md < ~500 *lines*, depth in `references/`, TOC for reference files >300 lines (skill-creator already states this — make it the only stated budget).
- [ ] 4.4 Commit: `meta: anchor skill-creator to the library's house conventions`.

## Phase 5 — Mechanical nits + hygiene

- [ ] 5.1 Fix duplicate `### 4.` headings (Token Efficiency and Cross-Referencing) and the Discovery Workflow numbering skip (`1,3,4,5,6`) — in whichever file the content lands after Phase 2.
- [ ] 5.2 Lowercase the frontmatter example `name: Skill-Name-With-Hyphens` → `name: skill-name-with-hyphens`.
- [ ] 5.3 Add a provenance header to `anthropic-best-practices.md` (source URL + import date); strip `theme={null}` artifacts and dead relative `/en/docs/...` links.
- [ ] 5.4 De-duplicate: `skill-creator/SKILL.md`'s anatomy/progressive-disclosure section vs `anthropic-best-practices.md` — keep the inline version terse, point to the reference file for depth.
- [ ] 5.5 Redirect `skill-creator`'s eval workspace: `<skill-name>-workspace/` sibling dir → a top-level `eval-workspaces/<skill-name>/` (or the session scratchpad); add `eval-workspaces/` to `.gitignore` so eval artifacts never leak into plugins or git.
- [ ] 5.6 Commit: `meta: mechanical fixes — numbering, naming example, provenance, eval-workspace path`.

## Phase 6 — Verify

- [ ] 6.1 Re-read both final SKILL.md(s) end-to-end for internal consistency (no surviving contradiction between description rule, budgets, testing policy).
- [ ] 6.2 `grep -rn "superpowers\|Skill-Name-With\|@graphviz\|@testing-skills" meta/` — clean.
- [ ] 6.3 Confirm `README.md` folder listing + provenance table match the final state of `meta/`.
- [ ] 6.4 Trigger sanity check: skill-creator's description still triggers on "create a skill", "improve this skill", "run evals on the skill"; no collision remains (writing-skills either gone or fenced).
- [ ] 6.5 Final commit if anything moved in verification.

---

## Deferred / out of scope

- Registering `meta/` skills in `marketplace.json` — meta stays local-only per the CLAUDE.md scope fence.
- Renaming to a `meta-*` prefix — only worth doing if meta is ever bundled into a plugin; revisit then.
- Running skill-creator's own eval loop on the edited skills — nice-to-have; the edits here are reference-content fixes, verify by read-through (Phase 6) instead.
