---
name: rules
description: Use when installing or updating the be-rust coding standards in .claude/rules/be-rust/. Triggers "install the Rust rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the be-rust rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file.

**Inline unit tests.** Rust keeps unit tests in a `#[cfg(test)] mod tests` inside the file under test, which no glob can tell apart from the code. `rust.md` (loaded for every `.rs`) says to Read `rust-tests.md` before writing one, and the be-rust agent and `unit-testing` skill read it whenever they test. A project that keeps its tests in sibling files (`mod tests;` → `tests.rs`, or `foo/tests.rs`) gets them loaded by glob.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/be-rust/`.

## Run by a model

A model runs this skill itself, as `be-rust:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/be-rust/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs and list it under `Waiting for the user:` in the report.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **List the source**: every `*.md` in `${CLAUDE_SKILL_DIR}` except `SKILL.md`. If the list is empty, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/be-rust` and `cp` it byte for byte. Done when every source file is in the target.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.

   With nobody to ask and no argument, write the plugin's copy beside it. Done when each file already present is up to date, replaced, kept or written beside as `<name>.plugin`.
5. **Fit the paths to this project.**
   - **Persistence.** Find where the queries live: `git grep -l -e 'sqlx::query' -e 'query!(' -e 'query_as!(' -e 'QueryBuilder' -e 'diesel::' -e 'sea_orm::' -- '*.rs'`, and the migration folders: `git ls-files '*.sql' | xargs -n1 dirname | sort -u`. If a path either command lists matches none of the `rust-persistence.md` globs, propose the globs that would cover it (for example `"crates/orders/src/infra/**/*.rs"` or `"**/adapters/postgres/**"`) and add them to the installed copy with the user's agreement.
   - **Tests.** List the sibling test files: `git grep -l '#\[cfg(test)\]' -- '*.rs'` and look for `mod tests;` declarations that point at a separate file. Propose globs for any such file the `rust-tests.md` globs miss. Inline test modules stay with the pointer in `rust.md`; say so.
   - **Where the Rust lives.** If the repo holds several stacks, `git ls-files '*.rs' | cut -d/ -f1-2 | sort -u` shows the Rust roots. `**/*.rs` is already narrow, so only propose a prefix (`"services/**/*.rs"`) when the user asks for one.

   - **Lint config.** `git ls-files '*Cargo.toml' '*clippy.toml' '*.cargo/config*'`; `cargo.md` matches all three. List the member crates that do not inherit the table: `git grep -L '^workspace = true' -- '*/Cargo.toml'` shows a member with no `[lints] workspace = true`, which gets none of the rows.
   With nobody to ask, change no path and list each proposed glob under `Waiting for the user:` in the report. Done when every file each command lists is matched by an installed glob, or a glob is proposed for it.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/be-rust/rust.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and its `[lints]` tables for Rust rules that contradict these files (a lint the project allows that the rules deny, a different test-naming scheme) and list them. A written contradiction is the user's to settle. Done when each contradiction is listed, or the report says none.
8. **Report lint gaps.** Read the `## Enforced by the build` table in `<root>/.claude/rules/be-rust/cargo.md`, then the workspace `Cargo.toml` (`[workspace.lints]`, or each crate's `[lints]`), every `clippy.toml` and `.cargo/config.toml`. A clippy or rustc row is enforced when its lint is `deny` or `forbid` in a table that every member inherits, and, for a `disallowed_*` row, its path is in `clippy.toml`. `unused_result_ok` needs a `rust-version` of 1.82 or later; below that it is not a gap. List every other row under `Not enforced by the build:` with its id and house rule. Never edit the project's config: the user, or a stack agent they ask, turns the rule on. Done when each table row is enforced or listed.

## Report

```
be-rust rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/be-rust/
Persistence paths: default | widened with <globs>
Test paths: default | widened with <globs>; inline #[cfg(test)] modules: <count> (covered by the pointer in rust.md)
Committed: yes | ignored by git
Conflicts with CLAUDE.md / [lints]: none | <one line each>
Not enforced by the build: none | <id: house rule>   (one line per row)
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.

## When to use

- Installing or updating the rules.

## When NOT to use

- Writing code: the rule files apply themselves.
