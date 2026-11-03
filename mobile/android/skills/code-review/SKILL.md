---
name: conventions-review
description: Use when reviewing a Kotlin, Jetpack Compose or Views diff against plugin conventions, plus an emulator screenshot pass. Triggers "review this PR". Not for a whole-repo audit (standards-audit).
---

# Android — Code Review

A **hostile review of one diff** against the mobile-android rule files, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite** — it points, and the `mobile-android` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md).

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the mobile-android rule files `android.md` (core), `android-ui.md`, `android-ui-states.md`, `android-ui-a11y.md`, `android-views.md`, `android-data.md`, `android-platform.md`, `android-tests.md`, `android-build.md`, `android-manifest.md` and `android-kmp.md`.

1. **The project's copies first**: `.claude/rules/mobile-android/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `mobile/android/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/mobile-android:rules` installs them.

Read `android.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. A composable, repository or worker whose name and folder miss the default globs still gets `android-ui*.md`, `android-data.md` or `android-platform.md`: decide by what the file contains. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead. Signing, store declarations, privacy and purchases are checked by the shared skills that own them (`mobile/_shared/{security,store-compliance,release,in-app-purchases}`); load the one the diff touches.

## Version lane

Detect before flagging: Kotlin (`gradle/libs.versions.toml`), AGP and Gradle (`gradle/wrapper/gradle-wrapper.properties`), `compileSdk` / `targetSdk` / `minSdk`, the Compose BOM, Compose vs Views for the files in the diff, KSP vs kapt, Hilt vs manual DI, Room 2.8 vs 3, Navigation 3 vs Navigation Compose, any Kotlin Multiplatform module. The rule files' "the codebase wins" line applies: a convention the project follows consistently is not a finding.

| Lane | Review consequence |
|---|---|
| **AGP 9 · Kotlin 2.4 · compile 37 / target 36** | The rules as written |
| AGP 8 / Kotlin 2.0–2.3 | AGP 9 rules are advice for the project's own migration run, not findings on a feature diff; a *new* module applying `kotlin-android` or `kapt` on AGP 9 is a finding |
| Views screen | `android-views.md` applies; a Compose rule is not flagged on an XML screen, and a Views codebase is not asked to convert |
| Navigation Compose 2.10 | Navigation 3 is not asked for; type-safe routes are correct |
| Room 2.8 | `androidx.room3` is not asked for; KSP and `suspend` / `Flow` DAOs still are |
| Below minSdk 24 or a floor mismatch | One finding plus a [`migration`](../migration/SKILL.md) run |

An API above the detected Kotlin, compileSdk or BOM is a finding, and so is a version move inside a feature diff: reject it, it is a [`migration`](../migration/SKILL.md) run.

## When to use

- A `.kt` / `.kts` / `.xml` / `AndroidManifest.xml` / `libs.versions.toml` / `proguard-rules.pro` diff, before merge
- Step 5 of the agent: the whole change set, after the quality layers
- "Why does this recompose forever / lose its state on rotation / crash after process death?"

## When NOT to use

- Whole codebase, saved re-runnable report → [`standards-audit`](../standards-audit/SKILL.md)
- Explaining a concept → [`basics`](../basics/SKILL.md); writing code → the owning feature skill
- Reviewing **E2E test code** (Appium / UiAutomator / Maestro) → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- Pen-test or runtime security → peer `qa-security` (`mobile-app-scan`, `mobile-runtime-testing`)
- A spec-versus-code audit → `code-auditor`

## Inputs needed

1. **The diff** (files or `git diff` range) and the screens it touches
2. **Lane facts** above, from the project's catalog and build files
3. **Whether an emulator is available** for the screenshot pass

## Procedure

1. Read the rule files that apply (above), then each changed file end to end.
2. Walk the blocker rules first: `!!`, the main thread, `GlobalScope`, secrets and logging, link and push validation, `PendingIntent`, exported components and cleartext, Room migrations. Then the rest.
3. For a mechanical lead over the changed files, the audit's [`conformance-checklist.md`](../standards-audit/references/conformance-checklist.md) has a *Find it with* recipe per row. A grep hit is a lead, not a finding: read the code at every hit.
4. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment. One row per defect family with a count, not per site.
5. Run the screenshot pass (below) if an emulator is available; otherwise say it was not run.
6. Do not rewrite. Hand off to the `mobile-android` agent or the owning skill.

## The screenshot pass (Step 5)

Only when an emulator is available and the app builds; otherwise report "screenshot pass not run" and why.

```bash
adb exec-out screencap -p > android-<screen>.png
```

`Read` each image. Capture the changed screens in **light and dark**, at **a large font scale** (`adb shell settings put system font_scale 2.0`) and at a **tablet / foldable size** where the app supports one, in each of loading, loaded, failed and empty where the diff changes them. Check against the diff, not against taste: edge-to-edge insets under the status and navigation bars, text truncation at large sizes, contrast, touch-target size, the error banner position, Material 3 components rather than a web or iOS look. Cite the `design/ux-review` heuristic and the corpus row (`design/ui-ux-pro-max --stack jetpack-compose`) behind each visual finding. Save images only under a scratch folder inside the worktree and delete them before committing.

## Output format

```
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker  | app/src/main/kotlin/profile/ProfileViewModel.kt:41 | `user.avatarUrl!!` on a server value — crashes on a missing avatar | Handle null and show the placeholder per `basics` |
| major    | app/src/main/kotlin/orders/OrdersClient.kt:18 | `OkHttpClient()` with no timeout budget | Per-endpoint-class timeouts per `networking` |
```

Close with the lane line (`Kotlin 2.4 · AGP 9.4 · compile 37 / target 36 / min 24 · Compose · Hilt`), the screenshot-pass status, the finding counts by severity, and one line: `Rules: project .claude/rules/mobile-android/ | plugin copy (not installed)`.

## Handoffs

- Fix → the `mobile-android` agent (FIX or EXTEND), or the owning feature skill
- A rule is missing or wrong → edit the project's `.claude/rules/mobile-android/`; for every project, the plugin's `mobile/android/skills/rules/`
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`unit-testing`](../unit-testing/SKILL.md)
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- Security proof → peer `qa-security`
