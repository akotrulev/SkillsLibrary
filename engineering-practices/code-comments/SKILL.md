---
name: ep-code-comments
description: The shared comment discipline every code-writing and code-reviewing skill in this library applies — no inline comments, a short doc comment only where the name genuinely cannot carry the meaning and only on a complex flow, stale comments deleted rather than updated. Loaded by a writer, reviewer, or audit skill, which supplies its own language's doc-comment and suppression syntax. Do NOT invoke directly or route a user request here — it carries no language mechanics of its own, so a run from this file alone would have nothing to apply. Do NOT use for documentation artifacts (docs/business-model, docs/plans, docs/specs) — this governs comments in source code only.
---

# Code Comments — the discipline

**Code carries its own explanation. A comment is the fallback for the residue that naming cannot reach — never a narration layer laid over working code.**

This file is the **language-agnostic half**: the rule, what earns an exception, how it is graded in review, and how it is reported in an audit. The **language-specific half** — the doc-comment syntax, the suppression syntax, and the one or two corollaries that stack has — is supplied by the skill that loads this one.

**The single rule everything else serves:** a comment that exists because the code is unclear is a defect report against the code. The fix is the rename or the extraction, never a better-worded comment.

## The rule

1. **No inline comments.** Nothing inside a method, function, or component body: no step markers (`// validate input`, `// now save`), no restatements of the line below, no section banners, no commented-out code, no `TODO`/`FIXME` left behind. A line that needs a comment to be understood needs a better name — extract it into a well-named local, constant, or private method instead.
2. **The only permitted comment is a short doc comment on a method, class, or type** — and only when the name genuinely cannot carry the meaning. One or two sentences, stating *why* or *what contract holds*, never *how*.
3. **That exception is for complex flows only** (see below).
4. **Never comment the trivial.** Properties, DTOs, records, getters/setters, constructors that only assign, single-expression methods, self-describing calls, obvious overrides — these get nothing. A doc comment that restates the signature is noise and must be deleted.
5. **A stale comment is worse than none.** If the code moves and the comment does not, the comment is the defect — delete it rather than update it, unless it still earns its place under rules 2–3.

## What earns a doc comment — the complex-flow test

A doc comment is earned only by **one of these four**. If none applies, the member gets nothing.

| # | Qualifying case | Example of the thing being recorded |
|---|---|---|
| 1 | A **non-obvious business rule or invariant** the code enforces but does not state | "Refunds are capped at the original capture, not the order total — card-scheme rule." |
| 2 | An **ordering / concurrency / lifetime constraint** a caller must respect | "Must be called inside the ambient transaction." · "Not safe after `Dispose`." · "Must be inside the provider." |
| 3 | A **deliberate deviation** from the obvious implementation, with its reason | "Polls rather than subscribes — the vendor's webhook drops events under load." |
| 4 | A **public API contract** the signature cannot express | What it throws · what it returns on the empty case · whether it mutates its input · which arguments are mutually exclusive |

Two failure modes to watch for, because both look like case 1:

- **A comment enumerating states, error cases, or permitted values** means the *type* is too weak. Widen the union, introduce the enum, or make the state explicit — the type is the documentation.
- **A comment explaining a positional or structural lookup** ("the third element is the price") means the *lookup* is brittle. Fix the accessor, not the prose.

## What is not a comment

These are **directives** — they change what a tool does, and they stay:

- Analyzer and lint suppressions, and compiler pragmas
- Serializer, validation, mapping, and API-schema annotations
- Source-generator and framework markers, and runtime directives that happen to use comment syntax

**But a suppression must carry its reason** — in the directive's own justification field where the tool supports one, otherwise on the same line. A bare suppression is its own finding: it is usually hiding the defect rather than accepting it.

**Database object comments are schema metadata, not source comments.** `COMMENT ON TABLE/COLUMN`, SQL Server extended properties, and their equivalents are queryable data-dictionary entries that tools and analysts read — they are governed by the schema conventions, not by this rule. A `--` comment inside a migration script or a query *is* a source comment and is governed here.

## Test code

The same rules apply, with the explanation coming from a different place: **the test name and its Arrange-Act-Assert shape are the documentation**, and a page object's intent-revealing method names are the documentation for the mechanics.

**Arrange/Act/Assert banner comments are the most common violation in test code.** They describe structure, and structure is carried by blank lines and a short body — if a test needs the labels to be legible, it is doing too much.

**Exactly three comments a test may carry**, and nothing else:

1. A **linked defect id** explaining a skip, a quarantine, or a documented workaround for an application bug.
2. An **explicitly instructed deviation** from the house rules — the Test-code rules require an instruction to accept more than one value to be *recorded in the test*, and that record is a comment.
3. The **source of a magic value the domain fixes** — a regulatory threshold, an environment-owned fixture id, a budget an SLO sets.

Each is one line stating a fact the code cannot.

## Grading it in review

| Situation | Severity |
|---|---|
| An inline comment | **minor** |
| A doc comment on trivia, or one restating the signature | **minor** |
| A bare suppression with no reason recorded | **minor** — **major** where it is hiding a real defect |
| A comment that is **wrong**, or that exists **because the code is unclear** | **major** |

For the major cases the suggested fix is **the rename or the extraction**, not a reworded comment. Never rewrite the code during review — point at the fix and let the human apply it.

## Reporting it in an audit

Two different shapes, and mixing them up is what makes a comment audit unreadable:

- **"No inline comments" is one finding family.** A codebase that has them has hundreds. Count them, cite 3–5 representative `file:line`s plus the worst offender, and give the fix direction once. Twenty sites of one mistake is one finding with a count — the engine's grouping rule.
- **Each stale comment is its own finding**, because each is a distinct false statement about the code, and each needs its own verdict on the next round.

A grep hit is never a finding: comment syntax appears inside strings, URLs, and directives. Read the line. And the staleness question — does this comment still describe what the code does — cannot be answered by grep at all; it is read fresh, every round.

## Writing new code

Emit no comments. Where a doc comment is genuinely earned under the complex-flow test, write one or two sentences and no more. **Remove scaffolded comments** from anything a template or CLI generated — placeholder headers, "add your code here" markers, sample remnants — before handing the file over.

If, while writing, you find yourself wanting to explain a block: that is the signal to extract it and name it. The urge to comment is a design signal, and acting on it as a design signal is the whole point of the rule.

## Handoffs

- **A reviewer applying this** supplies its language's doc-comment and suppression syntax, then grades per the table above.
- **An audit applying this** supplies the `Find it with` recipe and the permanent finding ID; the report shapes come from [`ep-standards-audit-engine`](../standards-audit-engine/SKILL.md).
- **Documentation artifacts are out of scope** — plans, specs, business-model documents, and audit reports are written to be read, and their prose is governed by the skills that own them.
