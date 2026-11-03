---
name: conventions-review
description: Use when reviewing Rust code for production panics, needless clones, locks across .await or blocking the runtime. Triggers "review this Rust module". Not for explanations (patterns).
---

# Rust — Reviewer

Reviews Rust code against the be-rust rule files and produces a findings table. It does **not** rewrite: it points to the fix and hands off to the skill that owns the recipe. Loads `backend/_shared/code-review` for pattern-stacking and architecture-altitude concerns.

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the be-rust rule files `rust.md` (core), `rust-persistence.md`, `rust-tests.md` and `cargo.md`.

1. **The project's copies first**: `.claude/rules/be-rust/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `backend/rust/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/be-rust:rules` installs them.

Read `rust.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. **Read `rust-tests.md` too whenever a file under review holds a `#[cfg(test)]` module**: inline tests match no test glob. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the file does not contain; propose it as a rule change instead.

## Version policy

Detect the toolchain, `edition` and `rust-version`, and the tokio / axum / sqlx versions in `Cargo.lock` first. Do not flag a 2021-edition crate for lacking a 2024-only form, or an API newer than its `rust-version`. The rule file's "the codebase wins" line applies: a convention the project follows consistently is not a finding.

## When to use

- A diff, crate or module submitted for review
- A pre-merge gate on anything under `src/`, `tests/`, `benches/`, `migrations/` or a `Cargo.toml`
- "Is this safe to run in production", "why is this deadlocking"

## When NOT to use

- Conceptual questions → `pattern-guide`
- Writing the fix → `pattern-writer` / `async-concurrency` / `database-code`
- Measuring a performance claim → `performance` (a review flags the suspicion; a profile proves it)
- Dependency CVEs, SAST, DAST → `qa-security`

## Procedure

1. **Let the tools find what tools find.** Run `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings` and the tests before reading a line. A clippy finding is reported by its lint name, grouped with a count rather than one row each; the review's value is what clippy cannot see.
2. Read the rule files, then each changed file end to end.
3. Walk the rules in this order: Panics and errors, Async on tokio, persistence, secrets and `unsafe`, then the rest. Most blockers live there.
4. Per finding: file and line, the rule broken, a one-sentence fix naming the skill section that holds the recipe. The severity is the tag on the rule, never a new judgment.
5. Do not rewrite. Hand off below.

## Output format

```
| Severity | Location                   | Issue                                                              | Suggested fix                                                      |
|----------|----------------------------|--------------------------------------------------------------------|--------------------------------------------------------------------|
| blocker  | src/orders/http.rs:41      | `MutexGuard` from `state.cache.lock()` held across `repo.save(..).await` | Copy the value out and drop the guard first (`async-concurrency` → Locks) |
| major    | src/orders/domain.rs:18    | `qty * unit_price` on request input wraps in release               | `checked_mul` returning `PlaceOrderError::TotalOverflow`           |
| major    | src/orders/store.rs:52     | Query inside a loop over orders (N+1)                              | One `= ANY($1)` query, grouped in memory (`database-code` → N+1)   |
| minor    | src/orders/domain.rs:7     | `fn total(lines: &Vec<Line>)`                                      | Take `&[Line]`                                                     |
```

Blockers first. End with one line: `Rules: project .claude/rules/be-rust/ | plugin copy (not installed)`.

## Handoffs

- Fixes → `pattern-writer` / `async-concurrency` / `database-code`
- A suspected hot spot → `performance` (profile before changing)
- Missing tests → `unit-testing`
- A rule is missing or wrong → edit the project's `.claude/rules/be-rust/`; for every project, the plugin's `backend/rust/skills/rules/`
- Cross-stack architecture critique → `backend/_shared/code-review`
- Dependency audit, SAST → `qa-security`
