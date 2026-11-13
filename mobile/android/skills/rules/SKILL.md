---
name: rules
description: Use when installing or updating the mobile-android standards as path-scoped rules in .claude/rules/mobile-android/. Triggers "install the Android rules", "set up this project". Not for reviewing code (conventions-review).
argument-hint: "[replace | keep | beside]"
---

# Install the mobile-android rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a manifest never pays for the manifest rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `android.md`: lane, simplicity, Kotlin, coroutines, architecture and DI, errors and secrets, comments | Kotlin under `src/main`, `src/debug`, `src/release`, `src/test*`, and any `src/*Main` / `src/*Test` source set |
| `android-ui.md`: composables, state, effects, lists, theming, insets, navigation | `*Screen` / `*Route` / `*Content` / `*Component` / `*Theme` / `*Activity` / … files, `ui/`, `screens/`, `presentation/`, `components/`, `theme/`, `navigation/` |
| `android-ui-states.md`: data regions, the error banner, failure kinds, forms | the same as `android-ui.md`, plus `*ViewModel` files and `form/` folders |
| `android-ui-a11y.md`: accessibility, test ids, strings, motion | the same as `android-ui.md`, plus `res/layout*/` and `res/values*/strings.xml` |
| `android-views.md`: Fragments, ViewBinding, adapters, interop | `*Fragment` / `*Adapter` / `*ViewHolder` / `*View` files, `res/layout*/` |
| `android-data.md`: Room, DataStore, Keystore, networking, offline | `*Dao` / `*Database` / `*Entity` / `*Repository` / `*Api` / `*Client` / … files, `data/`, `db/`, `network/`, `storage/`, `sync/`, Room `schemas/` |
| `android-platform.md`: permissions, camera, location, biometrics, notifications, WorkManager, services, alarms, widgets | `*Permission*` / `*Notification*` / `*Worker*` / `*Service*` / `*Widget*` / … files, `permission*/`, `notification*/`, `work*/`, `widget*/`, … |
| `android-tests.md` | `src/test*/`, `src/*Test/` (`androidTest`, `commonTest`, `androidUnitTest`, …) |
| `android-build.md`: AGP, KSP, SDK levels, catalog, R8 | `*.gradle.kts`, `*.gradle`, `gradle/libs.versions.toml`, `gradle.properties`, `proguard-rules.pro`, `consumer-rules.pro` |
| `android-manifest.md`: TLS, exported components, permissions, services, links, backup | `AndroidManifest.xml`, `res/xml/*.xml` |
| `android-kmp.md` | the KMP source sets (`commonMain`, `androidMain`, `iosMain`, `jvmMain`, …), `src/commonTest/` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/mobile-android/`.

## Run by a person or by a model

A person types `/mobile-android:rules`. A model runs this skill itself, as `mobile-android:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/mobile-android/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all eleven files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/mobile-android` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
5. **Fit the paths to where the Android code really lives.** The defaults follow Android's conventional layout, and `*.kt` / `*.gradle.kts` are shared with Kotlin backends, so check both ways and change the installed copies only with the user's agreement.
   - **Find the Android modules**: `git grep -l -e 'com.android.application' -e 'com.android.library' -e 'com.android.kotlin.multiplatform.library' -e 'kotlin.multiplatform' -e 'plugins.android.application' -e 'plugins.android.library' -- '*.gradle.kts' '*.gradle'`. Each hit's folder is a module.
   - **Narrow** when Kotlin or Gradle files exist outside those modules (a Ktor or Spring service, a Gradle plugin): `git ls-files '*.kt' '*.gradle.kts'` and list what falls outside. Propose prefixing each glob with the module folders (`"{app,feature,core}/**/src/main/**/*.kt"`) so a backend file never loads the Android rules.
   - **Widen** for sources the defaults miss: product-flavour or build-type source sets (`git ls-files '*/src/*/*' | cut -d/ -f1-3 | sort -u`, e.g. `src/free/`, `src/staging/`) go into `android.md`; composables outside the UI globs (`git grep -l '@Composable' -- '*.kt'`) into the three `android-ui*.md` files; Room, DataStore and HTTP code outside the data globs (`git grep -l -e '@Dao' -e '@Database' -e '@Entity' -e 'Retrofit.Builder' -e 'OkHttpClient' -e 'DataStore<' -- '*.kt'`) into `android-data.md`; Fragments and adapters (`git grep -l -e ': Fragment(' -e 'ListAdapter<' -e 'RecyclerView.Adapter' -- '*.kt'`) into `android-views.md`; permission, notification and background-work code (`git grep -l -e 'rememberLauncherForActivityResult' -e 'NotificationCompat' -e 'CoroutineWorker' -e 'BiometricPrompt' -- '*.kt'`) into `android-platform.md`. Propose the directory glob that covers each cluster (`"**/orders/impl/**/*.kt"`), not one glob per file.
   - A lane the project does not have (no `res/layout`, no `commonMain`) needs no change: its file simply never loads.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/mobile-android/android.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for Android or Kotlin rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
mobile-android rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/mobile-android/
Android modules: <folders>
Paths: default | narrowed to <modules> | widened with <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
