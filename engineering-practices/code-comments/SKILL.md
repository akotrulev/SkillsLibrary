---
name: ep-code-comments
description: The shared comment discipline every code-writing and code-reviewing skill applies — only complex code carries a comment, and only a short doc comment on a method, class, or type; no inline comments; stale comments deleted rather than updated. Loaded by a writer, reviewer, or audit skill, which supplies its own language's syntax. Do NOT invoke directly or route a user request here. Do NOT use for documentation artifacts (docs/plans, docs/specs) — this governs source-code comments only.
---

# Code Comments — the discipline

**Code carries its own explanation. Only complex code earns a comment, and then only to make it readable — never as a narration layer over working code.**

This file is the **language-agnostic half**. The doc-comment syntax, the suppression syntax, and any stack-specific corollary come from the skill that loads this one.

**The single rule everything else serves:** a comment that exists because the code is unclear is a defect report against the code. The fix is the rename or the extraction, never a better-worded comment.

## The rule

1. **No inline comments.** Nothing inside a method, function, or component body: no step markers, no restatements of the line below, no section banners, no commented-out code, no `TODO`/`FIXME`. A line that needs a comment needs a better name — extract it into a well-named local, constant, or private method.
2. **The only permitted comment is a short doc comment on a method, class, or type** — the loader's syntax (XML doc in C#, Javadoc in Java, TSDoc in TS) — one or two sentences, stating *why* or *what contract holds*, never *how*.
3. **It is earned only by complex code** — one of the four cases below. If none applies, the member gets nothing. Properties, DTOs, records, getters/setters, constructors that only assign, single-expression methods, self-describing calls, and obvious overrides never qualify; a doc comment restating the signature (`/// Gets the user id.`) is noise and is deleted.
4. **Generated and scaffolded comments are removed** — template headers, framework placeholders, "add your code here" markers, sample remnants — unless a tool depends on them, in which case they are directives, not comments (below).
5. **A stale comment is worse than none.** The comment is the defect — delete it rather than update it, unless it still earns its place under 2–3.

## What counts as complex

| # | Qualifying case | Example |
|---|---|---|
| 1 | A **non-obvious business rule or invariant** the code enforces but does not state | "Refunds are capped at the original capture, not the order total — card-scheme rule." |
| 2 | An **ordering / concurrency / lifetime constraint** a caller must respect | "Must be called inside the ambient transaction." · "Not safe after `Dispose`." |
| 3 | A **deliberate deviation** from the obvious implementation, with its reason | "Polls rather than subscribes — the vendor's webhook drops events under load." |
| 4 | A **public API contract** the signature cannot express | What it throws · what it returns on the empty case · whether it mutates its input |

Two near-misses that look like case 1 but are design defects: a comment **enumerating states, error cases, or permitted values** means the *type* is too weak (widen the union, introduce the enum); a comment explaining a **positional or structural lookup** ("the third element is the price") means the *lookup* is brittle. Fix the type or the accessor, not the prose.

## What is not a comment

**Directives** change what a tool does and they stay: analyzer/lint suppressions and compiler pragmas (`#pragma`, `eslint-disable`), serializer/validation/mapping/OpenAPI annotations that produce output, source-generator and framework markers. **A suppression must carry its reason** — in the tool's justification field where one exists, otherwise on the same line; a bare suppression is its own finding, usually hiding the defect rather than accepting it.

**Database object comments are schema metadata**, not source comments — `COMMENT ON`, extended properties, and equivalents are queryable data-dictionary entries governed by the schema conventions. A `--` comment inside a migration or a query *is* a source comment and is governed here.

## Test code

Same rule; the explanation comes from the test name and the Arrange-Act-Assert shape, and from a page object's intent-revealing method names. **`// Arrange` / `// Act` / `// Assert` banners are the most common violation** — structure is carried by blank lines and a short body.

**Exactly three comments a test may carry**, one line each: a **linked defect id** behind a skip/quarantine/workaround · an **explicitly instructed deviation** from the house rules (the Test-code rules require the instruction to be recorded in the test) · the **source of a magic value the domain fixes** (a regulatory threshold, an environment-owned fixture id, an SLO budget).

## Grading it in review

| Situation | Severity |
|---|---|
| An inline comment | **minor** |
| A doc comment on trivia, or one restating the signature | **minor** |
| A bare suppression with no reason recorded | **minor** — **major** where it hides a real defect |
| A comment that is **wrong**, or that exists **because the code is unclear** | **major** |

For the major cases the suggested fix is **the rename or the extraction**, not a reworded comment. Never rewrite the code during review.

## Reporting it in an audit

- **"No inline comments" is one finding family** — count them, cite 3–5 representative `file:line`s plus the worst offender, give the fix direction once.
- **Each stale comment is its own finding**, because each is a distinct false statement needing its own verdict next round.

A grep hit is never a finding — comment syntax appears inside strings, URLs, and directives, and staleness cannot be answered by grep at all. Read the line, fresh, every round.

## Writing new code

Emit no comments except where the complex-flow test is genuinely met, and then one or two sentences. Strip whatever the template or CLI generated (rule 4) before handing the file over. If you find yourself wanting to explain a block, that is the signal to extract it and name it.

## Handoffs

- **A reviewer applying this** supplies its language's doc-comment and suppression syntax, then grades per the table above.
- **An audit applying this** supplies the `Find it with` recipe and the permanent finding ID; report shapes come from [`ep-standards-audit-engine`](../standards-audit-engine/SKILL.md).
- **Documentation artifacts are out of scope** — plans, specs, business-model documents, and audit reports are governed by the skills that own them.
