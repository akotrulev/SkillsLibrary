# Groovy → KTS, Java → Kotlin

Two independent moves; neither needs the other, both are safe on AGP 8 or 9.

## Groovy → Kotlin DSL (`build.gradle` → `build.gradle.kts`)

- **One file at a time**, leaf modules first; the root `settings.gradle` last. Groovy and KTS build files coexist in one project.
- Rename, then translate: string quoting `"` only, `=` assignment (`compileSdk = 37`, `isMinifyEnabled = true`), `plugins { alias(libs.plugins.x) }` from the catalog, `dependencies { implementation(libs.x) }`.
- Move literals to `libs.versions.toml` while there **only if the file already had them as strings** — the catalog adoption is a separate commit.
- Properties that changed spelling: `minifyEnabled` → `isMinifyEnabled`, `debuggable` → `isDebuggable`, `signingConfig signingConfigs.release` → `signingConfig = signingConfigs.getByName("release")`.
- Never combine with an AGP upgrade; a KTS compile error and an AGP error look alike.
- Verify: `./gradlew help` then `assembleDebug`; the dependency tree (`./gradlew :app:dependencies`) is identical before and after.

## Java → Kotlin

- **Per leaf class**, not per package; Android Studio's converter is the start, not the finish. Convert and **review** — a converter leaves platform types (`String!`), `lateinit`s and `!!`.
- Order: models and utilities (no Android types), repositories, ViewModels, then Fragments / Activities. Never convert a class and change its behaviour in one commit.
- After conversion apply the house standard ([`basics`](../../basics/SKILL.md)): null safety by type (remove `!!`), `data class` / `sealed interface` for models, `val` over `var`, injected dispatchers, structured concurrency for any `AsyncTask` / `Thread`.
- Interop annotations while both exist: `@JvmStatic`, `@JvmOverloads`, `@JvmField`, `@Throws` where Java callers need them; remove them when the last Java caller goes.
- **Nullability annotations on the Java side first** (`@Nullable` / `@NonNull`) on the API the Kotlin code calls, so the compiler enforces it before conversion.
- A Java file that is only consumed by Room 3 stays Java (KSP processes Java sources) — do not convert it just to convert it.
- Verify: unit tests for the converted class pass unchanged; Lint's Kotlin interop checks are clean; no `!!` introduced.
