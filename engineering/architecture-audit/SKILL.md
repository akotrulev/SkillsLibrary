---
name: audit-architecture
description: Use when auditing a codebase's structure (shallow modules, forwarding layers, duplicated logic, tests tied to internals). Triggers "audit the architecture". Not for one feature (audit-feature).
---

# Architecture Audit

Audit the **structure** of an existing codebase and save one report: which modules hide little behind a wide surface, which layers only forward, which logic exists twice, which tests reach past a module's entry surface, and which identifiers drift from the glossary. Every finding is evidenced at `file:line`, severity-tabled and mapped to the skill that owns the fix.

This is the **ARCHITECTURE lane** of the `code-auditor` agent, run as a **CONVENTION-lane** audit on [`../standards-audit-engine/SKILL.md`](../standards-audit-engine/SKILL.md). The engine owns the rounds, the evidence rules, the report template and the hostile self-review; this skill owns the checklist and the four things a checklist owner supplies: the language lane, the applicability probes, what a module is, and the fence.

**Read-only analysis on product code.** The audit points; the stack agent fixes.

To run it from a session, delegate to the `code-auditor` agent, or type `/engineering:audit`. State the mode (A or B) and the target path in the first line of output.

## When to use

- "Is this codebase getting harder to change?" with no spec and no single feature named
- A sweep for shallow modules, forwarding layers and duplicated logic before a refactor
- Unit tests break whenever the code behind them is rewritten
- Code names and the client's glossary have drifted apart

## When NOT to use

- One feature's behaviour, validations and defects → `engineering:audit-feature`
- Code against a written spec, stories or ACs → `engineering:audit-spec`
- A stack's conventions (lint, nullability, DI, layering rules) → the stack's `standards-audit`
- One diff or one file → the stack's `code-review`
- Pruning or repairing a test suite → `qa-<stack>:test-audit`
- Security vulnerabilities → the `qa-security` agent
- The user wants the findings fixed → the owning `be-*` / `fe-*` / `mobile-*` / `desktop-*` agent; never edit product code here

## Read before sweeping

1. [`../standards-audit-engine/SKILL.md`](../standards-audit-engine/SKILL.md): Mode A / Mode B, the artifact contract, evidence rules, the 5 steps. Read it first.
2. [`references/checklist.md`](references/checklist.md): the 16 checks in sections A–E with their Locate recipes, the owner per section, the never-a-finding list and the fix-direction rule. Read it end to end before Step 2 of the engine.
3. [`../standards-audit-engine/references/report-template.md`](../standards-audit-engine/references/report-template.md): the Round-1 and Round-N skeletons. Read it before Step 3 of the engine.

Report path: `docs/audits/<NNN>-architecture-conformance-r<N>.md`. `architecture` takes the place of the plugin name in the engine's naming line, and the lineage `<NNN>` is minted once at `r1`.

When the checklist and the owning skill disagree, the owning skill wins; report the disagreement.

## What a module is

A **module** is a directory, package or project that other code imports through a **surface**: an index file, a public type, a project reference. A folder that nothing imports as a unit is a grouping, not a module.

The **module map** is section A's output and the report's first table: one row per module with its path, its surface, its public member count, its size in lines and the modules it imports.

Done when every top-level area appears in the map as a module or is named as a grouping.

## Step 0 — the language lane *(never skip)*

Detect each language in scope, then record how it hides things. A member is public only in that language's sense.

```bash
git ls-files | sed -E 's/.*\.//' | sort | uniq -c | sort -rn | head
git ls-files -- '*.sln' '*.csproj' 'package.json' 'pom.xml' '*.gradle*' 'pyproject.toml' 'Cargo.toml' 'Package.swift'
git log --oneline -5
```

| Language | Hidden by | A module's surface |
|---|---|---|
| C# | `internal`, `private`; `InternalsVisibleTo` widens | the project's `public` types and its project reference |
| Java | package-private, `module-info.java` `exports` | the package's `public` types and exported packages |
| Kotlin | `internal`, `private` | the module's `public` declarations |
| TypeScript, JavaScript | a file's unexported names; `exports` in `package.json` | the index file or the `exports` map; a barrel counts as the surface |
| Python | a `_name` and a module's `__all__` | the package's `__init__.py` names |
| Rust | no `pub`; `pub(crate)` stays inside the crate | the crate's `pub` items and its `lib.rs` re-exports |
| Swift | `internal` and below; `public` and `open` leave the target | the target's `public` and `open` declarations |

Done when each language in scope has its row, its surface probe from the checklist's preamble and the detected build layout in the report's lane section.

Never apply one language's visibility to another: a Rust crate's `pub` is not a C# `public`, and a TypeScript file without an index has no surface of its own.

## Step 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| A, B, C | always | none |
| D (tests) | the scope has tests | `git ls-files -- '*test*' '*Test*' '*spec*' '*Spec*'` returns files |
| E (glossary) | the project keeps a glossary | `ls docs/business-model/glossary.md` |

A section marked N/A names its probe and the probe's result. D and E that are N/A produce no findings and no false confidence.

## The fence — what this is not

| Job | Owner |
|---|---|
| One feature's behaviour and defects | `engineering:audit-feature` |
| Code against a spec | `engineering:audit-spec` |
| A stack's conventions swept over the codebase | the stack's `standards-audit` |
| One diff against the rule files | the stack's `code-review` |
| An interface with one implementation, pattern stacking, layering | `architecture-review` (`backend/_shared/code-review`): cite it, never restate it |
| Pruning tests | `qa-<stack>:test-audit` |
| Applying any fix found here | the stack agent (Mode FIX) |
| Resolving a term that means two things (E3) | the `business-analyst` agent, which needs `product` enabled; without it E3 stays a logical conflict with an open question |

## Output

The engine's Mode A and Mode B blocks apply, with `architecture` as the plugin name. A report adds the module map from section A directly after the applicability matrix.
