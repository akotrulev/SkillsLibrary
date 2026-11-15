# desktop-windows Conformance Checklist — the 21 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`B3`, `M1`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number. The letters are identical on both desktop platforms (`macos`, `windows`) and keep their meaning from the mobile checklists: `M` is Accessibility everywhere. `Q` (motion) and `T` (release) are unused: motion is in E, release in L.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a grep hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `bin/`, `obj/` and `x64/` when ignored are skipped without flags. Without ripgrep, `grep -rn --include='*.cs' --include='*.xaml' --include='*.cpp' --include='*.h' --exclude-dir=bin --exclude-dir=obj` is equivalent. Set the source roots once:

```bash
SRC=$(ls -d src Source App *App* 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" $SRC -g '*.cs'   # the shape every recipe below uses
```

If the repo gitignores generated sources (`*.g.cs`, `*.g.i.cs`, `Generated Files/`) you still need to read, add `--no-ignore` and exclude it explicitly — and say so in the report's coverage line.

**The version lane gates everything.** Before flagging, confirm the check applies to the detected target framework and Windows App SDK major (2.x primary), the UI framework (WinUI, WPF, WinForms) and whether the app is packaged. Rows tagged **[WinUI]**, **[WPF]**, **[WinForms]**, **[C++]**, **[packaged]** and **[unpackaged]** apply only in that lane.

**Fragment sections.** K, L and U carry no rows here: their rows live in `desktop/_shared/<skill>/references/audit-checks.md` and are filtered by the `Platforms` column. X is owned by `interop` and `cpp-winrt` and is not applicable without P/Invoke, COM or C++ projects. Every other section is filled by the task that writes its skill — an empty section means that skill is not written yet, not that the code passes.

**Severity.** blocker — ships a crash, a store or notarization rejection, or a hard security rule break. major — a rule in CLAUDE.md § Desktop code rules broken where it will hurt soon. minor — style, naming, a single missing label. nit — preference.

---

## A — Version lane, toolchain & migration hygiene
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`migration`](../../migration/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## B — Project structure, strictness & language standard
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## C — Architecture, state & DI
*Owning skill: [`architecture`](../../architecture/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## D — UI components & platform conventions
*Owning skills: [`ui-components`](../../ui-components/SKILL.md) · [`wpf`](../../wpf/SKILL.md) · [`winforms`](../../winforms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## E — Styling, theming, motion & adaptive layout
*Owning skill: [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## F — Windows, navigation & commands
*Owning skill: [`windows-and-navigation`](../../windows-and-navigation/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## G — Forms & input
*Owning skill: [`forms`](../../forms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## H — Networking & realtime
*Owning skill: [`networking`](../../networking/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## I — Storage, documents & sync
*Owning skill: [`offline-and-storage`](../../offline-and-storage/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## J — Platform integration, permissions & background
*Owning skills: [`platform-integration`](../../platform-integration/SKILL.md) · [`activation-and-notifications`](../../activation-and-notifications/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## K — Security
*Owning fragment: [`desktop/_shared/security`](../../../../_shared/security/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/security/references/audit-checks.md` whose `Platforms` column names `windows`, and the ids are the fragment's — finding `K3` is row K3 of the security fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## L — Distribution & store compliance
*Owning fragment: [`desktop/_shared/distribution`](../../../../_shared/distribution/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/distribution/references/audit-checks.md` whose `Platforms` column names `windows`, and the ids are the fragment's — finding `L3` is row L3 of the distribution fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## M — Accessibility
*Owning skill: [`accessibility`](../../accessibility/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## N — Performance
*Owning skill: [`performance`](../../performance/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## O — Error resilience
*Owning skill: [`error-handling`](../../error-handling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## P — Localization
*Owning skill: [`languages`](../../languages/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## R — Testability & test ids
*Owning skill: [`test-ids`](../../test-ids/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## S — Dev-side tests
*Owning skill: [`unit-testing`](../../unit-testing/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## U — Observability & logging
*Owning fragment: [`desktop/_shared/observability`](../../../../_shared/observability/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `desktop/_shared/observability/references/audit-checks.md` whose `Platforms` column names `windows`, and the ids are the fragment's — finding `U3` is row U3 of the observability fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## V — Comments & KISS
*Owning skills: [`engineering-practices/code-comments`](../../../../../engineering-practices/code-comments/SKILL.md) · CLAUDE.md § Comments and § Simplicity (KISS)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| V1 | No inline comments in a body | A `//` line inside a method body (C#, C++) — a step marker, a restatement of the next line, a section banner | `rg -n "^\s+//[^/]" $SRC -g '*.cs' -g '*.cpp' -g '*.h'` | minor |
| V2 | A doc comment states a contract, not the signature | An XML doc comment that restates the name or signature (`Gets the user id`) on a property, DTO, getter or single-expression method | `rg -n -A1 "^\s*/// <summary>" $SRC -g '*.cs'`; read each hit against the member it sits on | minor |
| V3 | No commented-out code, no `TODO` / `FIXME` left behind | A `//` line holding code, or a `TODO` / `FIXME` / `HACK` marker in committed source | `rg -n "^\s*//\s*(var\|await\|return\|if\|using\|auto\|co_await)\b" $SRC -g '*.cs' -g '*.cpp' -g '*.h'` · `rg -n "TODO\|FIXME\|HACK" $SRC -g '*.cs' -g '*.xaml' -g '*.cpp' -g '*.h'` | minor |
| V4 | A comment that exists because the code is unclear | A comment explaining what a badly named local or method does — the fix is the rename or extraction, not a reworded comment | Read the comment hits from V1; ask whether a name would carry it | major |
| V5 | No `interface` with one implementation | An abstraction introduced for one caller and one implementation, with no second real need | `rg -n "^\s*(public \|internal )?interface I\w+" $SRC -g '*.cs'`; then count implementers per hit | major |
| V6 | No wrapper that only forwards | A class or method whose whole body delegates one call to the next layer (service → repository → store as three layers) | `rg -n -A2 "\) =>\s*_\w+\.\w+\(" $SRC -g '*.cs'`; read each hit for a single delegated call | major |
| V7 | No configurability nothing uses | An options bag, flag, generic parameter or extension point that no caller passes or varies | `rg -n "Options\b\|Configuration\b\|\bconfig\b" $SRC -g '*.cs'`; then search for a call site that supplies it | major |
| V8 | A generated or scaffolded comment is removed | A template header, a framework placeholder comment (`// TODO: Add your code`) or a wizard banner left in a source file, with no tool depending on it | `rg -n "Generated by\|<auto-generated\|This file was\|Copyright \(c\)" $SRC -g '*.cs' -g '*.cpp' -g '*.h'` — skip generated sources | minor |

---

## X — Interop & native code
*Owning skills: [`interop`](../../interop/SKILL.md) · [`cpp-winrt`](../../cpp-winrt/SKILL.md)*

Not applicable without P/Invoke, COM or C++ projects.

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---
