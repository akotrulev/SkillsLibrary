# mobile-android Conformance Checklist — the 24 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`B3`, `M1`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number. The letters are identical on all three mobile stacks (`react-native`, `ios`, `android`): `M` is Accessibility everywhere.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a grep hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `build/`, `.gradle/`, `.idea/` and `local.properties` are skipped without flags. Without ripgrep, `grep -rn --include='*.kt' --include='*.kts' --include='*.xml' --exclude-dir=build --exclude-dir=.gradle` is equivalent. Set the source roots once:

```bash
SRC=$(ls -d app/src */src 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" $SRC -g '*.kt' -g '*.kts' -g '*.xml'                      # the shape every recipe below uses
```

If the repo gitignores generated sources (KSP / Room / Hilt output under `build/generated/`) you still need to read, add `--no-ignore` and exclude it explicitly — and say so in the report's coverage line.

**The version lane gates everything.** Before flagging, confirm the check applies to the detected Kotlin, AGP and Compose BOM versions (AGP 9 / Kotlin 2.4 primary, AGP 8 supported in brownfield), whether the UI is Compose or Views, and whether any Kotlin Multiplatform module exists. Rows tagged **[AGP9]**, **[KMP]** and **[Views]** apply only in that lane.

**Fragment sections.** K, L, T, U and X carry no rows here: their rows live in `mobile/_shared/<skill>/references/audit-checks.md` and are filtered by the `Stacks` column. Every other section is filled by the task that writes its skill — an empty section means that skill is not written yet, not that the code passes.

**Severity.** blocker — ships a crash, a store rejection, or a hard security rule break. major — a rule in CLAUDE.md § Mobile code rules broken where it will hurt soon. minor — style, naming, a single missing label. nit — preference.

---

## A — Version lane, toolchain & migration hygiene
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`migration`](../../migration/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | The Kotlin version is detected, and no feature above it is used | `context(...)` or an explicit backing field in a module on Kotlin 2.3 or below; Kotlin raised as a side effect of other work | `rg -n "^kotlin\|kotlin = " gradle/libs.versions.toml`; `rg -n "context\(" $SRC -g '*.kt'` | major |
| A2 | Context receivers are gone | `context(Foo)` with a type, not a named parameter, left from the revoked feature | `rg -n "context\(\w+[,)]" $SRC -g '*.kt'` | major |
| A3 | `kapt` is not used `[AGP9]` | `kotlin-kapt` or `kapt(` in a build file | `rg -n "kapt" -g '*.kts' -g '*.gradle' -g 'libs.versions.toml'` | major |
| A4 | Explicit API mode in a library module that publishes | A published library module with `public` by default and no `explicitApi()` | `rg -n "explicitApi" -g '*.kts'` | minor |

---

## B — Project structure, strictness & language standard
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | No `!!` outside tests | `value!!` in app or module source | `rg -n "!!" $SRC -g '*.kt' -g '!*Test*'` | blocker |
| B2 | No `lateinit` for an injectable dependency | `lateinit var repo: Repo` where a constructor parameter fits | `rg -n "lateinit var" $SRC -g '*.kt'` | major |
| B3 | No `GlobalScope` | `GlobalScope.launch` / `.async` | `rg -n "GlobalScope" $SRC -g '*.kt'` | blocker |
| B4 | Dispatchers are injected, not named in a class body | `Dispatchers.IO` / `Default` / `Main` written inside a repository or ViewModel | `rg -n "Dispatchers\.(IO\|Default\|Main)" $SRC -g '*.kt' -g '!*Module*'` | major |
| B5 | No `runBlocking` in production code | `runBlocking` outside tests and `main` | `rg -n "runBlocking" $SRC -g '*.kt' -g '!*Test*'` | blocker |
| B6 | `CancellationException` is rethrown | `catch (e: Exception)` / `Throwable`, or `runCatching`, around a `suspend` call with no rethrow | `rg -n "runCatching\|catch \(\w+: (Exception\|Throwable)\)" $SRC -g '*.kt'`; read each for a suspend call | major |
| B7 | A `suspend` function that blocks is main-safe | Blocking I/O in a `suspend` function with no `withContext(ioDispatcher)`, left to the caller | `rg -n -A6 "suspend fun" $SRC -g '*.kt'`; read for blocking calls | major |
| B8 | State is a sealed interface; `when` over it has no `else` | Three booleans for loading / error / data; an `else` branch on a sealed type | `rg -n "isLoading\|isError" $SRC -g '*.kt'`; `rg -n -B6 "else ->" $SRC -g '*.kt'` | major |
| B9 | A UI state class is an immutable `data class` | A `var` property or a `MutableList` field in a state class; a `StateFlow` of a mutable object | `rg -n "data class \w+State" -A8 $SRC -g '*.kt'` | major |
| B10 | No ViewModel-to-UI events; one `uiState: StateFlow` | A `SharedFlow` / `Channel` of one-off UI events exposed from a ViewModel | `rg -n "SharedFlow\|Channel<" $SRC -g '*.kt'` | major |
| B11 | `StateFlow` is updated atomically | `_state.value = _state.value.copy(` | `rg -n "\.value = .*\.value\.copy" $SRC -g '*.kt'` | minor |
| B12 | Flows are collected lifecycle-aware | `collectAsState()`, `launchWhenStarted` or a bare `lifecycleScope.launch { flow.collect }` in UI code | `rg -n "collectAsState\(\)\|launchWhenStarted\|lifecycleScope\.launch" $SRC -g '*.kt'` | major |
| B13 | No mutable collection in a public signature | `MutableList` / `MutableMap` as a parameter or return type | `rg -n "(: \|-> )Mutable(List\|Map\|Set)<" $SRC -g '*.kt'` | minor |
| B14 | `val` over `var`; no `var` never reassigned | A `var` with no reassignment | `rg -n "\bvar \w+" $SRC -g '*.kt'`; the compiler warns on never-reassigned | minor |
| B15 | No Java-isms | `get`/`set` method pairs, `Optional`, a static-holder class, `object` holding mutable state | `rg -n "Optional<\|fun (get\|set)[A-Z]\w+\(\|^object \w+" $SRC -g '*.kt'` | minor |
| B16 | A context parameter is not a service locator | `context(...)` carrying a repository or service used as a lookup | `rg -n "context\(" $SRC -g '*.kt'` | major |

---

## C — Architecture, state & DI
*Owning skill: [`architecture`](../../architecture/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## D — UI components & platform conventions
*Owning skills: [`ui-components`](../../ui-components/SKILL.md) · [`views-interop`](../../views-interop/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## E — Styling, theming & adaptive layout
*Owning skill: [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## F — Navigation & deep links
*Owning skills: [`navigation`](../../navigation/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md)*

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

## I — Offline, storage & sync
*Owning skill: [`offline-and-storage`](../../offline-and-storage/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## J — Device features, permissions & native code
*Owning skills: [`device-features`](../../device-features/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md) · [`system-integration`](../../system-integration/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## K — Security
*Owning fragment: [`mobile/_shared/security`](../../../../_shared/security/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/security/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `K3` is row K3 of the security fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## L — Privacy & store compliance
*Owning fragment: [`mobile/_shared/store-compliance`](../../../../_shared/store-compliance/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/store-compliance/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `L3` is row L3 of the store-compliance fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

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

## Q — Motion & gestures
*Owning skill: [`animation`](../../animation/SKILL.md)*

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

## T — Release & signing
*Owning fragment: [`mobile/_shared/release`](../../../../_shared/release/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/release/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `T3` is row T3 of the release fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## U — Observability & logging
*Owning fragment: [`mobile/_shared/observability`](../../../../_shared/observability/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/observability/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `U3` is row U3 of the observability fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## V — Comments & KISS
*Owning skills: [`ep-code-comments`](../../../../../engineering-practices/code-comments/SKILL.md) · CLAUDE.md § Comments and § Simplicity (KISS)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| V1 | No inline comments in a body | A `//` line inside a function or method body — a step marker, a restatement of the next line, a section banner | `rg -n "^\s+//[^/]" $SRC -g '*.kt'` | minor |
| V2 | A doc comment states a contract, not the signature | A doc comment that restates the name or signature (`Returns the user id`, `@param id the id`) on a property, DTO, getter or single-expression function | `rg -n -A1 "^\s*\* @(return\|param)\b" $SRC -g '*.kt'` | minor |
| V3 | No commented-out code, no `TODO` / `FIXME` left behind | A `//` line holding code, or a `TODO` / `FIXME` / `HACK` marker in committed source | `rg -n "^\s*//\s*(val\|var\|fun\|import\|return\|if)\b" $SRC -g '*.kt'` · `rg -n "TODO\|FIXME\|HACK" $SRC -g '*.kt'` | minor |
| V4 | A comment that exists because the code is unclear | A comment explaining what a badly named local or method does — the fix is the rename or extraction, not a reworded comment | Read the comment hits from V1; ask whether a name would carry it | major |
| V5 | No `interface` with one implementer | An abstraction introduced for one caller and one implementation, with no second real need | `rg -n "^(fun )?interface \w+" $SRC -g '*.kt'`; then count implementers per hit | major |
| V6 | No wrapper that only forwards | A class or function whose whole body delegates one call to the next layer (service → repository → ORM as three layers) | `rg -n -A2 "fun \w+\(.*\) =\s*$" $SRC -g '*.kt'`; read each hit for a single delegated call | major |
| V7 | No configurability nothing uses | An options bag, flag, generic parameter or extension point that no caller passes or varies | `rg -n "options: \|config: \|Config\(" $SRC -g '*.kt'`; then search for a call site that supplies it | major |
| V8 | A generated or scaffolded comment is removed | A template header, a framework placeholder comment or a wizard banner left in a source file, with no tool depending on it | `rg -n "Created by\|Generated by\|This file was\|Copyright \(c\)" $SRC` — skip generated sources (KSP / Room / Hilt output under `build/generated/`) | minor |

---

## W — Kotlin Multiplatform
*Owning skill: [`kotlin-multiplatform`](../../kotlin-multiplatform/SKILL.md)* — N/A unless Kotlin Multiplatform modules exist

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## X — In-app purchases
*Owning fragment: [`mobile/_shared/in-app-purchases`](../../../../_shared/in-app-purchases/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/in-app-purchases/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `X3` is row X3 of the in-app-purchases fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed. Not applicable unless the app sells anything.
