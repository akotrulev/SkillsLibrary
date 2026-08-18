# Model & harness portability — staged plan of action

**Date:** 2026-08-18
**Goal:** make every skill and agent in this library runnable **outside Claude Code and outside Anthropic models** — on Cursor/Windsurf/Cline, opencode/Codex/Gemini CLI, and agent SDKs driving GPT/Gemini/Llama-class models — **and** raise the floor so a mid-tier model executes them without silently degrading. One source of truth, many emitted targets.
**Status:** proposed. Nothing built yet. This document sequences the work; each stage ships independently and is separately approvable.
**Scope:** the whole library — 374 `SKILL.md`, 49 agents, 76 commands, 110 `references/` folders, 12 published plugins. Two independent tracks that share one measurement harness: **Track A — portability** (§3–§7) and **Track B — small-model hardening** (§8–§13). Track B is worth doing *even if Track A is never shipped*: everything it fixes also improves Claude's own adherence.
**Non-goals:** rewriting skill *content* for another stack's idioms; supporting harnesses with no filesystem or no shell; maintaining hand-edited per-target forks (the exporter is the only sanctioned path).

---

## 1. Where we are today (measured 2026-08-18)

The good news is that the coupling is **thin and mechanical**, not architectural.

| Surface | Count | Portability verdict |
|---|---|---|
| `SKILL.md` frontmatter keys | `name` (374) · `description` (374) · `metadata` (9) | **Portable** — a two-key contract every framework can map |
| Agent frontmatter keys | `name` · `description` · `tools` (46) · `model` (45) | **Mostly portable** — `model: inherit` on all 45, so **no hardcoded Claude model id anywhere** |
| `${CLAUDE_PLUGIN_ROOT}` | **123 files** | Harness-specific — needs one indirection |
| Literal "Claude Code" in prose | **44 files** | Cosmetic, but leaks the harness into the instructions |
| Claude Code tool names in prose (`TaskCreate`, `EnterWorktree`, `WebFetch`, …) | **24 files** | Needs a capability glossary |
| `tools:` values | 31 agents share `Read, Write, Edit, Bash, Glob, Grep, WebSearch` | **Portable** — one canonical set covers 2/3 of agents |
| MCP tool names (playwright, appium) | 11 agents | **Already cross-vendor** — MCP is a multi-vendor standard; no work needed |
| `commands/*.md` | 76 | Claude Code slash-command surface; other harnesses have analogues or none |
| Body content | ~5.5M chars of English procedure | **Fully portable** |

**Size distribution — the number that matters for Track B:**

| | n | min | p50 | p90 | max |
|---|---|---|---|---|---|
| `SKILL.md` | 374 | 1,856 | **13,305** | **21,273** | 43,180 |
| Agent files | 49 | 7,287 | **17,917** | **22,842** | 29,456 |

Against `TOKEN-OPTIMIZATION-PLAN.md`'s budgets (body ≤16,000 · agent ≤14,000), **the median agent is 28% over budget and the p90 skill is 33% over.** On Claude that costs tokens. On a mid-tier model it costs *compliance* — which is the whole Track B thesis.

**Two defects found during this survey (fold into Stage 0):**
1. Three `meta/skill-creator/agents/` files (`grader`, `comparator`, `analyzer`) carry **no `tools:` and no `model:`** frontmatter. Out of plugin scope, but they are the exporter's edge case if left unfixed.
2. One agent frontmatter carries a stray **`Examples`** key that no consumer reads.

---

## 2. Design principles carried into every stage

1. **One source, many emissions.** The repo stays authored for Claude Code — that is the primary target and the one with the richest harness. Every other target is a **build artifact**, never a hand-maintained fork. A per-target fork is dead within two releases.
2. **Portability is a transform, not a rewrite.** If a stage proposes changing what a skill *says* in order to port it, the stage is wrong. Only what it *references* changes.
3. **Degrade loudly.** A target that cannot express a capability (no sub-agents, no persistent files) gets an explicit stated limitation in the emitted header — never a silently weaker agent that reads as complete.
4. **Small-model work improves every model.** Front-loaded invariants, numbered steps, checkable exit criteria and machine-verifiable output contracts are not a downgrade path; they are better instructions. Nothing in Track B may make the Claude experience worse.
5. **Capability tiers are declared, not guessed.** A skill that genuinely needs frontier-level reasoning says so in metadata, and the exporter refuses to emit it for a low-tier profile rather than shipping something that will confabulate.
6. **The invariants are the product.** Across this library the load-bearing rules are behavioural, not informational: read-only contracts, `file:line`-actually-read evidence, `#confirmed`/`#inferred` tiering, blocking approval gates, `#volatile` authorization. **Those are exactly what weak models break first**, so every stage of Track B is measured against them, not against prose fidelity.

---

# Track A — portability

## 3. Stage A0 — Measure the coupling (tooling first)

- [ ] `tools/portability-audit.py`, modelled on the existing `tools/token-audit.py`. Per plugin and per file, report:
  - `${CLAUDE_PLUGIN_ROOT}` occurrences (123 today)
  - harness-name leakage ("Claude Code", "the Skill tool", "the Agent tool", "slash command")
  - Claude-Code-only tool names in prose, matched against a canonical allow-list
  - agents whose `tools:` deviate from the canonical set (and why)
  - frontmatter-schema violations (missing `tools`/`model`, stray keys)
- [ ] Commit a **baseline report** to `docs/audits/` so every later stage shows movement, in the same round-over-round shape the `code-auditor` lane uses.
- [ ] Fix the two Stage-0 defects from §1.

**Exit:** one command prints the full coupling inventory; the number is known, not estimated.

## 4. Stage A1 — Decouple the source (in-repo, no exporter yet)

Each item below is a **source change that keeps Claude Code working identically.**

- [ ] **Path indirection.** Replace the raw `${CLAUDE_PLUGIN_ROOT}` prose with one sentence sourced from a single shared snippet: *"Skill paths resolve against the library root — the repo root when working inside it, the plugin root when installed, or the directory this file was loaded from."* The `code-auditor` already words this correctly (its line 37) — promote that wording to the standard and sweep the other 122 files to match.
- [ ] **Capability glossary** — `meta/PORTABILITY.md`, one table mapping each Claude Code tool to the generic capability it stands for: `Read/Glob/Grep` → *file read & search*; `Bash` → *shell*; `Write/Edit` → *file write*; `WebSearch/WebFetch` → *web access*; `Agent` → *sub-agent dispatch*; `TaskCreate/TaskUpdate` → *task tracking*; `EnterWorktree` → *isolated workspace*; `Skill` → *load a referenced document*. Skills reference the capability; the glossary owns the per-harness name.
- [ ] **Sweep the 24 tool-name files** to lead with the capability and name the Claude Code tool parenthetically — `ep-executing-plans`, `ep-worktrees`, and `ep-delegate-to-subagents` are the concentrated cases.
- [ ] **Normalize the 44 "Claude Code" mentions** — keep it only where the statement is genuinely about the harness (plugin install, marketplace, command surface); elsewhere say "the harness" or "your agent runtime".
- [ ] **Freeze the frontmatter contract** in `CONTRIBUTING.md`: `name` + `description` mandatory on skills; `name` + `description` + `tools` + `model` on agents; anything else goes under `metadata:`.

**Exit:** `portability-audit.py` reports zero raw-path and zero unglossed-tool findings; Claude Code behaviour unchanged (spot-check three agents end to end).

## 5. Stage A2 — The exporter

- [ ] `tools/export.py --target <t> --plugin <p> --out <dir>`, driven by per-target **adapter modules** so a new target is one file, not a fork of the generator.
- [ ] **Target adapters**, in shipping order (each is independently useful):

| Order | Target | Emission shape | Fidelity |
|---|---|---|---|
| 1 | **`markdown`** (baseline) | Flat bundle: agent body + every skill it loads, inlined, with a generated table of contents | Full content, no auto-trigger, no persistence guarantees |
| 2 | **`opencode` / `AGENTS.md`** | Near-1:1 — agent files with remapped frontmatter, skills as referenced docs | High |
| 3 | **`cursor`** (also Windsurf/Cline) | Custom modes + `.mdc` rules; `description` becomes the mode's activation text | High for single-agent flows; sub-agent dispatch degrades |
| 4 | **`sdk`** | Python/TS package: system prompt per agent + a JSON tool manifest derived from `tools:` + a skill registry for on-demand loading | Full, but the consumer must implement the tools |

- [ ] **Progressive disclosure is the hard part.** Claude Code lazily loads `SKILL.md` → `references/*.md`. Targets without that get one of three declared strategies, chosen per target and stated in the emitted header: **inline-all** (bloat, full fidelity) · **inline-SKILL-only + reference index** (default) · **retrieval** (SDK target only).
- [ ] **Emitted header, mandatory, on every artifact:** source commit, export date, target, chosen disclosure strategy, and an explicit **"capabilities unavailable on this target"** list. Principle 3, made physical.
- [ ] Exports are **generated into `dist/` and gitignored** — never committed, so they cannot drift into a second source of truth.

**Exit:** `export.py --target markdown --plugin be-dotnet` produces a bundle a human can paste into any chat and get correct behaviour from.

## 6. Stage A3 — Cross-model conformance harness

Porting the text proves nothing. This stage proves the *behaviour* survives.

- [ ] **Fixture repos** under `tools/fixtures/` — small, deliberately flawed codebases with a **known defect list**: one .NET service, one React app, one Terraform+K8s stack. Each ships an expected-findings key.
- [ ] **Scored runs**: pick 5 representative agents (`code-auditor`, `be-dotnet`, `fe-react`, `qa-api-typescript`, `devops-auditor`) × the emitted targets × a model matrix (Opus/Sonnet-class, GPT-class, Gemini-class, a small open-weight model).
- [ ] **Score on invariants, not prose** — per §2.6:
  - did it produce the artifact at the contracted path, with the contracted header?
  - did it honour the read-only contract (zero writes outside `docs/`)?
  - **citation verification**: sample 10 `file:line` claims and machine-check that the cited line exists and plausibly supports the claim — *fabricated citations are the headline metric*
  - recall/precision against the fixture's known-defect key
  - did it stop at the blocking gate, or barrel through?
- [ ] Publish a **support matrix** (target × model → tier: supported / degraded / unsupported) in `meta/PORTABILITY.md`. An honest "unsupported" is a feature.

## 7. Stage A4 — Publish & document

- [ ] `README.md` section: what ports, what doesn't, how to export, the support matrix.
- [ ] A worked example — `code-auditor` on Cursor and via the SDK, start to finish.
- [ ] CI check: `portability-audit.py` runs on PR and fails on new raw-path/unglossed-tool findings, so Stage A1 cannot regress the way `TOKEN-OPTIMIZATION-PLAN.md` Phase 1 did.

---

# Track B — small-model hardening

The four observed failure modes of weaker models against *this* library, in severity order:

1. **Contract violation** — "helpfully" fixing a defect inside a read-only audit (destroys the audit's trustworthiness).
2. **Evidence fabrication** — inventing `file:line` citations, or promoting `#inferred` to `#confirmed` to get a clean metrics row.
3. **Phase collapse** — merging or skipping phases; running Mode B as Mode A; walking through a blocking gate without waiting.
4. **Instruction decay** — with an 18K-char agent prompt plus 2–5 loaded skills, rules stated once mid-document stop firing.

Every stage below targets one of those, and each is independently shippable.

## 8. Stage B1 — Shrink to the budgets that already exist

Fixes: **decay**. Cheapest, highest-leverage, already-agreed budgets.

- [ ] Bring the **49 agents** to ≤14,000 chars (median is 17,917 — most of the overage is worked examples and rationale that belong in a loaded skill, not the always-resident agent prompt).
- [ ] Bring the **p90 skills** to ≤16,000 (move depth to `references/`, which is already the library's rule and already lazily loaded).
- [ ] Wire both budgets into the same CI gate as A4.

## 9. Stage B2 — Front-load the invariants

Fixes: **contract violation**, **decay**.

- [ ] Every agent opens, immediately after the frontmatter, with a short **`## NEVER`** block — 3–6 lines, imperative, no rationale: *never write outside `docs/audits/`* · *never cite a line you did not read this run* · *never mark Resolved without a fresh re-trace* · *never act outside the scope file*. The rules already exist in these files; today they are stated mid-document in prose (`code-auditor` line 9, line 33, line 135) and a weak model loses them by page three.
- [ ] Each agent **repeats its single most-violated invariant at the phase where it bites**, not only at the top. Repetition is a cost worth paying for exactly the load-bearing rules.
- [ ] Same treatment for the always-on pair (`ep-agent-orientation-cache`, `ep-code-comments`) since they ride in every plugin.

## 10. Stage B3 — Make procedures mechanical

Fixes: **phase collapse**.

- [ ] Convert every phase description into a **numbered step list with an explicit exit criterion** and a one-line self-check the model must emit before continuing (*"Phase 2 exit: register saved at `<path>`, N requirements, N sections — printed before any product code was read"*). The strong agents (`code-auditor`, `be-planner`) already half-do this; the pattern needs to be uniform and complete.
- [ ] Convert prose decision rules into **decision tables** — mode selection, lane selection, version gating. A table is followed far more reliably than a paragraph.
- [ ] **Blocking gates get a literal stop token**: the phase ends with an instruction to output a fixed marker and produce nothing further until the human answers. `be-planner`, `devops-engineer`, `infra-security-tester`, `penetration-tester` and `security-test-planner` all depend on this and all currently rely on the model *understanding* that it should block.

## 11. Stage B4 — Make the output contract machine-checkable

Fixes: **fabrication**, **phase collapse**.

- [ ] Tighten the existing output-contract blocks into strictly parseable key/value headers (they are already close — see `code-auditor` lines 99–127).
- [ ] `tools/verify-artifact.py` — validates a produced audit/plan/report against its contract: required header fields present, ID format and continuity, no renumbering across rounds, **every `file:line` citation resolves to an existing line**, `#confirmed` claims carry a citation. This is the same script Stage A3 scores with, so it is built once and used twice.
- [ ] Add a **self-verification step** as the last phase of every artifact-producing agent: run the check (or perform it manually), report the result. `ep-verify-before-done` is the existing skill; this makes it mandatory and mechanical rather than cultural.

## 12. Stage B5 — Cap the simultaneous load

Fixes: **decay**.

- [ ] Audit every agent phase for how many skills it loads at once; where a phase loads 3+, define a **reduced profile** that loads the router-level guidance only and defers `references/` until the specific branch is chosen.
- [ ] Emit the reduced profile behind `export.py --profile compact`, and measure it in the Stage A3 harness against the full profile — if compact scores equal or better on a mid-tier model, it becomes that model's default.

## 13. Stage B6 — Declare capability tiers

Fixes: honest limits, per §2.5.

- [ ] Add `metadata.min_capability: frontier | strong | mid` to every skill and agent, justified in one line. Expected shape: the **audit/planning/security lanes are `frontier`** (they hinge on judgment, evidence discipline and refusal-to-act); **code-writing skills are `strong`** (output is verifiable by build+test, so errors surface); **scaffolding and convention lookups are `mid`**.
- [ ] `export.py --min-capability mid` **omits** higher-tier items and says so in the emitted header — the exporter refuses to ship something that will confabulate, rather than shipping it with a warning nobody reads.
- [ ] Feed the Stage A3 scores back into the tiers so they are *measured*, not asserted. A tier that survives a mid-tier model in testing gets demoted to `mid`; one that fails on a strong model gets promoted to `frontier`.

---

## 14. Sequencing & effort

| Stage | Depends on | Rough effort | Ships value alone? |
|---|---|---|---|
| A0 measure | — | S | Yes — the inventory is useful immediately |
| A1 decouple | A0 | M (123-file sweep, mechanical) | Yes — cleaner source for Claude too |
| B1 shrink | A0 | M | **Yes — biggest single quality win, any model** |
| B2 invariants | — | M | Yes |
| B3 mechanical procedures | B2 | L | Yes |
| A2 exporter | A1 | M | Yes |
| B4 verifier | B3 | M | Yes — usable as a Claude-side gate |
| A3 harness | A2, B4 | L (fixtures are the cost) | Yes — first real evidence |
| B5 compact profile | A3 | M | Only with A3 |
| B6 tiers | A3 | S | Only with A3 |
| A4 publish | A3 | S | Closes Track A |

**Recommended first slice if only one thing gets done: B1 + B2.** They need no new tooling, improve Claude's own adherence, and are prerequisites for everything in Track A that matters.

## 15. Risks

- **Fork drift** — the single largest risk. Mitigated by gitignoring `dist/` and never committing an export.
- **Regression by later plans** — exactly what happened to `TOKEN-OPTIMIZATION-PLAN.md` Phase 1 when the conformance rollout re-inflated descriptions under a contradicting budget. Mitigated by the A4 CI gate and by this plan explicitly deferring to `TOKEN-OPTIMIZATION-PLAN.md`'s numbers rather than restating its own.
- **Track B flattening the writing** — over-mechanizing turns nuanced guidance into a checklist that loses the judgment the frontier lanes depend on. Mitigated by §2.4: nothing may make the Claude experience worse, and B3 converts *procedures* to steps, never *judgment* to rules.
- **Harness capability gaps we cannot close** — no sub-agent dispatch means `ep-delegate-to-subagents` and `ep-parallel-agents` are simply unsupported on some targets. Declare it (§2.3); do not simulate it.
- **Fixture maintenance** — the Stage A3 fixtures rot. Keep them small and version-pinned; three fixtures, not thirty.

## 16. Open questions (for the owner)

1. **Which non-Claude targets actually matter?** The adapter order in §5 is a guess. If only one target is real, Stage A2 shrinks to a week.
2. **Is `dist/` genuinely never committed** — or is there a distribution need (a Cursor marketplace, a shared team repo) that forces a published artifact and therefore a drift-control policy?
3. **Does Track B ship as a library-wide sweep, or plugin-by-plugin** behind the existing conformance-audit machinery? Plugin-by-plugin is slower but each plugin is verifiably done.
4. **Do the 76 `commands/` files get a target analogue at all**, or are commands accepted as a Claude-Code-only convenience?
