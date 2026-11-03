---
name: rules
description: Use when installing or updating the be-rust coding standards as path-scoped rules in .claude/rules/be-rust/. Triggers "install the Rust rules". Not for reviewing code (conventions-review).
disable-model-invocation: true
---

# Install the be-rust rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches persistence code never pays for the persistence rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `rust.md`: simplicity, ownership, errors, async, HTTP, logging, `unsafe`, performance, comments | any `*.rs` |
| `rust-persistence.md`: sqlx queries, transactions, migrations | `migrations/`, `store` / `db` / `repo` / `repository` / `persistence` / `queries` modules (`.rs` file or folder), `sqlx.toml` |
| `rust-tests.md` | `tests/`, `benches/`, `tests.rs` / `test_support.rs` / `test_utils.rs`, `*_test.rs` / `*_tests.rs` |
| `cargo.md`: toolchain, lockfile, lints, dependencies, release profile | `Cargo.toml`, `rust-toolchain(.toml)`, `clippy.toml`, `.cargo/config(.toml)` |

**Inline unit tests.** Rust keeps unit tests in a `#[cfg(test)] mod tests` inside the file under test, which no glob can tell apart from the code. `rust.md` (loaded for every `.rs`) says to Read `rust-tests.md` before writing one, and the be-rust agent and `unit-testing` skill read it whenever they test. A project that keeps its tests in sibling files (`mod tests;` → `tests.rs`, or `foo/tests.rs`) gets them loaded by glob.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-rust/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all four files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-rust` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to this project.**
   - **Persistence.** Find where the queries live: `git grep -l -e 'sqlx::query' -e 'query!(' -e 'query_as!(' -e 'QueryBuilder' -e 'diesel::' -e 'sea_orm::' -- '*.rs'`, and the migration folders: `git ls-files '*.sql' | xargs -n1 dirname | sort -u`. If a path either command lists matches none of the `rust-persistence.md` globs, propose the globs that would cover it (for example `"crates/orders/src/infra/**/*.rs"` or `"**/adapters/postgres/**"`) and add them to the installed copy with the user's agreement.
   - **Tests.** List the sibling test files: `git grep -l '#\[cfg(test)\]' -- '*.rs'` and look for `mod tests;` declarations that point at a separate file. Propose globs for any such file the `rust-tests.md` globs miss. Inline test modules stay with the pointer in `rust.md`; say so.
   - **Where the Rust lives.** If the repo holds several stacks, `git ls-files '*.rs' | cut -d/ -f1-2 | sort -u` shows the Rust roots. `**/*.rs` is already narrow, so only propose a prefix (`"services/**/*.rs"`) when the user asks for one.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-rust/rust.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and its `[lints]` tables for Rust rules that contradict these files (a lint the project allows that the rules deny, a different test-naming scheme) and list them. A written contradiction is the user's to settle.

## Report

```
be-rust rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-rust/
Persistence paths: default | widened with <globs>
Test paths: default | widened with <globs>; inline #[cfg(test)] modules: <count> (covered by the pointer in rust.md)
Committed: yes | ignored by git
Conflicts with CLAUDE.md / [lints]: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
