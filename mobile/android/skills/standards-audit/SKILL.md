---
name: standards-audit
description: Use to audit a whole Android app (Kotlin, Compose, Views, KMP) against the mobile-android plugin's conventions — version lane, structure, UI, navigation, data, device code, accessibility, resilience, test ids, security and store fragments — as a saved, re-runnable report in `docs/audits/`. Read-only. Triggers "audit our Android app against the plugin conventions". Do NOT use to review one diff (`mobile-android:conventions-review`) or check code against a spec (`code-auditor`).
---

# mobile-android Conformance Audit

Audit an existing **Android app** against the conventions this plugin defines — CLAUDE.md § Mobile code rules plus the hard rules each `mobile/android/skills/*` skill owns and the five `mobile/_shared/*` fragments — and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on product code.** The audit points; the `mobile-android` agent fixes.

State the mode — Mode A (baseline) or Mode B (re-audit) — and the target path in the first line of output.

## Read before sweeping

1. **[`engineering-practices/standards-audit-engine`](../../../../engineering-practices/standards-audit-engine/SKILL.md)** — Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping and coverage policy, the five steps, the hostile self-review. **Read it first**; this file adds only what is specific to Android.
2. [`references/conformance-checklist.md`](references/conformance-checklist.md) — sections A–X and every check; the section index at its end. **Read end-to-end** before Step 2.
3. `engineering-practices/standards-audit-engine/references/report-template.md` — the Round-1 / Round-N skeletons. Read before Step 3.
4. The fragments for sections K, L, T, U, X: `mobile/_shared/{security,store-compliance,release,observability,in-app-purchases}/references/audit-checks.md` — rows whose `Stacks` column names `android`.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins** — and report the disagreement.

Report path: `docs/audits/<NNN>-mobile-android-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one diff, inline table, no artifact, screenshot pass | [`code-review`](../code-review/SKILL.md) — this skill reuses its rows at repo scale |
| Code vs a written spec / stories | `dev:audit-spec` (or the `code-auditor` agent) |
| How one feature works, where it is defective | `dev:audit-feature` |
| Proof of pinning, on-disk data, resilience controls on a built APK / AAB | **peer** `qa-security` (`mobile-app-scan`, `mobile-runtime-testing`) — a row a static read cannot prove is reported **unverified**, never passed |
| E2E suites, device journeys | **peer** `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript` |
| Design heuristics on screens | `design/ux-review` on emulator screenshots |
| Applying any fix | the `mobile-android` agent |

## Step 0 — the Kotlin / AGP version lane *(never skip)*

```bash
ls -d settings.gradle.kts settings.gradle build.gradle.kts gradle/libs.versions.toml gradle/wrapper/gradle-wrapper.properties build-logic 2>/dev/null
rg -n "^(kotlin|agp|compose-bom|composeBom|ksp|hilt|room|navigation3?)\b" gradle/libs.versions.toml
rg -n "distributionUrl" gradle/wrapper/gradle-wrapper.properties
rg -n "compileSdk|targetSdk|minSdk|jvmToolchain|kapt|ksp\(|builtInKotlin|newDsl" -g '*.kts' -g '*.gradle' -g 'gradle.properties'
rg -n "org.jetbrains.kotlin.multiplatform|com.android.kotlin.multiplatform.library|org.jetbrains.compose" -g '*.kts' -g 'libs.versions.toml'
git ls-files | rg -c '\.kt$'; git ls-files | rg -c '\.java$'; git ls-files | rg -c 'res/layout.*\.xml$'; git log --oneline -5
```

Record: **Kotlin** (2.4 primary · 2.0–2.3 supported) · **AGP major and Gradle** (9.4 / 9.6+ primary · 8.x supported; an AGP 8 project is audited on its own lane, with the AGP 9 move a [`migration`](../migration/SKILL.md) hand-off) · **compile / target / min SDK** (37 / 36 / 24 primary; a `targetSdk` below 35 is finding A7 and a hand-off) · **Compose vs Views share** (composable files against layout XMLs and Fragments) · **Compose BOM** · **KSP vs kapt** · **DI** (Hilt, Koin, manual) · **persistence** (Room 3, Room 2.8, none) · **navigation** (Navigation 3, Navigation Compose, Fragments) · **KMP modules** · **Java file count** · **purchases** (Play Billing).

**The version rule binds every finding.** Never flag a down-level project for lacking an up-level API (Navigation 3 on Navigation Compose 2.10, `androidx.room3` on Room 2.8, a Kotlin 2.4 construct on 2.2, `com.android.kotlin.multiplatform.library` on AGP 8); never apply an up-level recipe to it. An **`[AGP9]`** row applies only on AGP 9, **`[N3]`** only on Navigation 3, **`[Views]`** only to Views code, **`[KMP]`** only to a project with multiplatform modules. A project mid-migration is finding A, not a licence to audit it against the highest lane present.

Then read 2–3 representative files (a screen with its ViewModel, the API client, a repository with its injection site) to calibrate conventions.

## Step 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| D (Compose rows) | Composables exist | `rg -ln "@Composable" -g '*.kt'` |
| D (Views rows `[Views]`) | Layout XML, Fragments, or `AndroidView` / `ComposeView` exist | `fd -e xml . -p 'res/layout'`; `rg -ln "Fragment\(\|AndroidView\|ComposeView" -g '*.kt'` |
| F (App Links rows F11, F14) | An `autoVerify` filter or a custom scheme is declared | `rg -n "autoVerify\|android:scheme" -g 'AndroidManifest.xml'` |
| F (Navigation 3 rows `[N3]`) | `navigation3` is a dependency | `rg -n "navigation3" -g 'libs.versions.toml' -g '*.kts'` |
| I (Room rows) | `androidx.room` / `androidx.room3` is a dependency | `rg -n "androidx.room" -g 'libs.versions.toml' -g '*.kts'` |
| J (notifications) | FCM or `NotificationManager` is referenced | `rg -ln "FirebaseMessaging\|NotificationManager\|POST_NOTIFICATIONS" -g '*.kt' -g 'AndroidManifest.xml'` |
| J (system integration) | WorkManager, a foreground service, Glance, an alarm or a shortcut exists | `rg -ln "WorkManager\|foregroundServiceType\|GlanceAppWidget\|AlarmManager\|ShortcutManager" -g '*.kt' -g 'AndroidManifest.xml'` |
| P (localization) | More than one `values-*` folder or per-app language is configured | `fd -t d 'values-' . -p 'res'`; `rg -n "localeConfig" -g 'AndroidManifest.xml'` |
| Q (motion) | Animation APIs or custom gestures are used | `rg -ln "animate\w+AsState\|AnimatedVisibility\|Animatable\|detectDragGestures\|SharedTransitionLayout" -g '*.kt'` |
| S (tests) | A `src/test` or `src/androidTest` tree exists — **no dev-side tests at all is a section S finding** (cite S1), not N/A | `fd -t d 'test\|androidTest' . -p 'src'`; `rg -ln "@Test" -g '*.kt'` |
| T (release) | A release signing config, Fastlane, or a CI release job exists — absent is a finding | `rg -n "signingConfigs\|isMinifyEnabled" -g '*.kts'`; `ls fastlane .github/workflows 2>/dev/null` |
| U (observability) | Always; **absent crash reporting is a finding**, not N/A | `rg -ln "Crashlytics\|Sentry\|ApplicationExitInfo\|ProfileInstaller" -g '*.kt' -g '*.kts' -g 'libs.versions.toml'` |
| W (Kotlin Multiplatform) | **N/A unless** a module applies `org.jetbrains.kotlin.multiplatform` or `com.android.kotlin.multiplatform.library`, or `commonMain` exists | `rg -n "kotlin.multiplatform" -g '*.kts' -g 'libs.versions.toml'`; `fd -t d commonMain` |
| X (in-app purchases) | The app sells anything: `com.android.billingclient`, `RevenueCat` | `rg -n "billingclient\|purchases" -g 'libs.versions.toml' -g '*.kts'` |

A–C, E, G, H, K, L, M, N, O, R, V apply to every app. A section that is N/A must name the probe that decided it — W's N/A line quotes the empty `kotlin.multiplatform` and `commonMain` results. `$SRC` is set by the checklist's recipe header.

## Step 2 notes — what the engine does not say

- **Generated and vendored code.** `build/`, `.gradle/` and KSP / Room / Hilt output under `build/generated/` are skipped by `rg`; do not add `--no-ignore` unless the project commits generated sources it owns, and state it in the coverage line.
- **Static-first.** Run no Gradle task, lint, profiler or emulator unless the user opts in for this audit. A row about runtime behaviour (process-death restore, R8 stripping, App Links verification, Compose recomposition) says **requires dynamic test** and is reported unverified.
- **Fragments.** Cite fragment findings with the fragment's own id (`K3`, `L2`); unreachable-by-static rows say **requires dynamic test → `qa-security`**. Rows shared with a section here (I-section / L1, J-section / L1, J-section / K) are reported once, under the fragment's id.
- **Deviations.** A deliberate project convention (Koin as the container, Room 2.8, Navigation Compose as the router, Views as the UI lane) is a noted deviation, not a finding; an inconsistent one is a finding.
- **Java and Views islands** are audited against the rows that apply to them and carry one finding with the file list — not a finding per file.
- **Section W** reads only the KMP modules; the `app` module's rows stay in the other sections.

## Handoffs

- **Apply fixes** → the `mobile-android` agent, FIX or EXTEND; a version or lane finding → [`migration`](../migration/SKILL.md) as its own run; a KMP finding → [`kotlin-multiplatform`](../kotlin-multiplatform/SKILL.md). The priority table is the artifact.
- **One diff instead** → [`code-review`](../code-review/SKILL.md)
- **Security-flavoured and unverified rows (K, part of L, T)** → peer `qa-security`
- **E2E gaps and test-id coverage proof** → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- **Design review of screens** → `design/ux-review`
- **A spec or feature trace** → `dev:audit-spec` / `dev:audit-feature` / `code-auditor`
