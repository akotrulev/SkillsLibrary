# 002 — Mobile plugins: React Native, iOS (Swift), Android (Kotlin) — plan (2026-10-10)

**Goal:** Three marketplace plugins in one new `mobile/` domain — `mobile-react-native` (Expo, the primary
lane), `mobile-ios` (Swift / SwiftUI) and `mobile-android` (Kotlin / Compose, with a Kotlin Multiplatform
lane) — each with the library's plugin shape: a coding standard, the common use-case skills, a
step-by-step agent that works greenfield and brownfield, a conformance audit, and a shared mobile layer
(store compliance, security, release, observability, in-app purchases) bundled into all three.

**Status:** C1 landed (2026-10-11): `mobile/` exists with the five July drafts moved and renamed under
`mobile/react-native/`, the three conformance-checklist skeletons, and `## Mobile code rules` in `CLAUDE.md`;
the stale `frontend/react-native` pointers are repointed. S1 landed (2026-10-11): `mobile/_shared/{store-compliance,security}` with their references and the `L1…L26` / `K1…K27` audit fragments. S2 landed (2026-10-11): `mobile/_shared/{release,observability}` with their references and the `T1…T19` / `U1…U20` audit fragments. S3 landed (2026-10-11): `mobile/_shared/in-app-purchases` with its references and the `X1…X22` fragment, plus `auth/auth0-{react-native,ios,android}`. N1 landed (2026-10-11): `mobile/{ios,android}/skills/basics` with `references/concurrency.md` each, and rows `A1…A5`/`B1…B16` (iOS), `A1…A4`/`B1…B16` (Android). R1 landed (2026-10-11): the five drafts rewritten onto SDK 57 and `mobile/react-native/skills/navigation` written, with RN checklist rows `A1…A7`, `B1…B13`, `C1…C10`, `D1…D10`, `E1…E13`, `F1…F15`. R2 landed (2026-10-11): `mobile/react-native/skills/{ui-components,forms,networking,offline-and-storage,native-modules}` with checklist rows `D10…D19`, `G1…G10`, `H1…H15`, `I1…I13`, `J1…J13`. R3 landed (2026-10-10): `mobile/react-native/skills/{device-features,notifications-and-links,animation,languages,test-ids}` with checklist rows `F15…F20`, `J14…J28`, `P1…P10`, `Q1…Q11`, `R1…R10`, and §8.5's RN mapping answered (D20 — the QA explorer's `content-desc` claim is refuted). R4 landed (2026-10-11): `mobile/react-native/skills/{accessibility,performance,error-handling,component-testing}` with `error-handling/references/{session-and-resume,writes-and-dependencies}.md` and checklist rows `M1…M13`, `N1…N13`, `O1…O22`, `S1…S12`. R5 landed (2026-10-11): `mobile/react-native/skills/{migration,code-review,standards-audit}` with `migration/references/{sdk-upgrade,new-architecture,bare-to-expo,embed-in-native-app}.md`, the RN checklist's closing section index, `mobile/react-native/agents/mobile-react-native.md` (13,888 characters, description 574 of 650) and `mobile/react-native/commands/{mobile-react-native,mobile-react-native-audit}.md`. I1 landed (2026-10-11): `mobile/ios/skills/{project-setup,architecture,ui-components,styling,navigation}` with `references/{packages-and-config,tca}.md` and checklist rows `A6…A11`, `B17…B24`, `C1…C10`, `D1…D11`, `E1…E12`, `F1…F11` (D21: MV over the corpus's MVVM rows). I2 landed (2026-10-11): `mobile/ios/skills/{forms,networking,offline-and-storage,uikit,device-features}` with `networking/references/request-policy.md`, `offline-and-storage/references/{swiftdata-migrations,keychain}.md`, `uikit/references/{uiscene-migration,interop-seams}.md`, `device-features/references/permissions.md` and checklist rows `D12…D20`, `G1…G10`, `H1…H12`, `I1…I14`, `J1…J12` (D22: new facts unconfirmed against Apple pages). I3 landed (2026-10-11): `mobile/ios/skills/{notifications-and-links,system-integration,animation,languages,test-ids}` with `notifications-and-links/references/apns-and-extensions.md`, `system-integration/references/background-and-activities.md` and checklist rows `F12…F15`, `J13…J28`, `P1…P11`, `Q1…Q11`, `R1…R10` (D23: new facts unconfirmed against Apple pages). I4 landed (2026-10-11): `mobile/ios/skills/{accessibility,performance,error-handling,unit-testing}` with `error-handling/references/{session-and-resume,writes-and-dependencies}.md` and checklist rows `M1…M14`, `N1…N13`, `O1…O21`, `S1…S15` (D24: new facts unconfirmed against Apple pages). I5 landed (2026-10-11): `mobile/ios/skills/{migration,code-review,standards-audit}` with `migration/references/{swift6-modules,observation,combine-to-async,uikit-to-swiftui,objc-to-swift,cocoapods-to-spm,ios27-sdk-and-targets}.md`, the iOS checklist's closing section index, `mobile/ios/agents/mobile-ios.md` (13,879 characters, description 640 of 650) and `mobile/ios/commands/{mobile-ios,mobile-ios-audit}.md` (D25: migration facts unconfirmed against Apple / swift.org pages). A1 landed (2026-10-10): `mobile/android/skills/{project-setup,architecture,ui-components,styling,navigation}` with `project-setup/references/gradle-config.md`, `architecture/references/hilt-and-modules.md` and checklist rows `A5…A13`, `B17…B20`, `C1…C13`, `D1…D15`, `E1…E12`, `F1…F13` (D26: no ViewModel-to-UI events over the corpus's Channel row; D27: Navigation 3 / Expressive / KSP facts partly unconfirmed). A2 landed (2026-10-10): `mobile/android/skills/{forms,networking,offline-and-storage,views-interop,device-features}` with `networking/references/{request-policy,connectivity-and-trust}.md`, `offline-and-storage/references/{room-migrations,keystore-and-secrets}.md`, `forms/references/validation-autofill-wizards.md`, `views-interop/references/recyclerview.md`, `device-features/references/{permissions,biometrics-and-credentials}.md` and checklist rows `D16…D25`, `G1…G10`, `H1…H15`, `I1…I14`, `J1…J12` (D28: Room 3 / Retrofit 3 / Compose-forms facts partly unconfirmed). A3 landed (2026-10-10): `mobile/android/skills/{notifications-and-links,system-integration,animation,languages,test-ids}` with `notifications-and-links/references/{fcm,app-links}.md`, `system-integration/references/foreground-services.md` and checklist rows `F14…F16`, `J13…J24`, `P1…P8`, `Q1…Q8`, `R1…R8` (D29: FCM registration is the Installation-ID flow; several Compose / Appium / FGS facts unconfirmed). A4 landed (2026-10-10): `mobile/android/skills/{accessibility,performance,error-handling,unit-testing}` with `error-handling/references/{session-and-resume,writes-and-dependencies}.md`, `unit-testing/references/{flows-and-seams,robolectric-and-screenshots}.md` and checklist rows `M1…M15`, `N1…N14`, `O1…O22`, `S1…S16` (D30: Robolectric / Turbine / Roborazzi versions and R8 keep-rule semantics unconfirmed). Next: A5.
A5 landed (2026-10-10): `mobile/android/skills/{kotlin-multiplatform,migration}` with three and nine references, and Android checklist rows `A14…A19` and `W1…W11`. Built but unverified: everything — the plan gates once, in G1. Flutter becomes a fourth plugin in its own plan, written
once this one lands (O4); it is **not** in this plan's tasks. Maestro arrives on the QA side through plan 003
(its X1); this plan feeds it the same test ids and an EAS Workflows job (D7). Every fact in §4 was web-verified
on 2026-10-10; the items listed under §4.5 were not.

**The cost, accepted and stated once:** the plan gates once, in G1. Intermediate commits are ungated,
so the tree is not known to pass the library check at every task boundary and the plan cannot be
stopped halfway and trusted. `mobile/` stays on the CLAUDE.md under-construction list until G1, so a
half-built domain is never uploaded.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| A mobile domain and plugins | `frontend/react-native/` — 5 drafted skills (`reference`, `project-scaffold`, `state-management`, `component-library` + 5 references, `styling`), the fenced Vercel seed `vendor/react-native-guidelines/`, `PLAN.md` + `HANDOFF.md` (node-per-session format, now superseded by plan-format). Listed as under construction in `CLAUDE.md` | `mobile/` domain, three plugins, the drafts moved, renamed and brought onto the §4.1 lane (C1, R1) |
| A mobile coding standard | Web and backend code rules only (`CLAUDE.md` § Frontend code rules (React) / (Blazor), § Backend code rules) | `## Mobile code rules` (§5) in `CLAUDE.md`, plus each stack's `basics` (C1, N1, R1) |
| React Native skills | 5 drafts, no agent, no audit | 23 skills, agent, 2 commands (R1–R5) |
| iOS / Swift skills | Nothing | 23 skills, agent, 2 commands (N1, I1–I5) |
| Android / Kotlin skills | Nothing | 24 skills incl. KMP, agent, 2 commands (N1, A1–A6) |
| Store compliance, mobile security, release, telemetry, IAP | QA side only: `qa/_shared/security-testing/{mobile-app-scan,mobile-runtime-testing}` (MASVS 2.1 scanning and dynamic testing). No dev-side rule set, no release/signing skill anywhere in `devops/` or `qa/cicd/` | Five `mobile/_shared/` skills with per-stack references and audit fragments (S1–S3) |
| Native auth | `auth/auth0-react`, `auth/auth0-blazor` (web SPA flows) | `auth/auth0-react-native`, `auth/auth0-ios`, `auth/auth0-android` (S3) |
| Conformance audits | `ep-standards-audit-engine` + per-stack checklists for fe-react, be-dotnet, qa-dotnet | Three mobile checklists on the engine, built row by row as each skill lands (D13) |
| E2E peer and the test-id hand-off | `qa-mobile-{java,dotnet,typescript}` (Appium) emit `missing-testids.md` (`qa/*/skills/mobile-screen-explorer/SKILL.md:104`); no dev agent consumes it for mobile. `mobile-screen-explorer/SKILL.md:10` says Android `content-desc` maps to an RN `testID` (§8.5 doubts it). Plan 003 moves the lane to Appium 3 and adds a Maestro lane to `qa-mobile-typescript` (its X1, D22) | Each stack's `test-ids` consumes the report and serves both lanes the same ids; W1 verifies and corrects the mapping line (003 D21 leaves that line to this plan); `mobile-shared-release` runs Expo projects' Maestro flows in EAS Workflows (S2) |
| Design layer for mobile | `design/ui-ux-pro-max` already carries `react-native.csv`, `swiftui.csv`, `jetpack-compose.csv`, `flutter.csv` and the 32-row `app-interface.csv` | Bundle it (minus web-only pieces, D10); query with `--stack` |
| Planning lane knows mobile | Stack token list is `be · fe · ts · data · infra · qa · docs · human` (`engineering-practices/writing-plans/references/plan-format.md:117`, `backend/_shared/delivery-plan/SKILL.md:43,118,282`, `backend/_shared/agents/solution-planner.md:15,79,229`); planner routes `fe` to `fe-react`/`fe-blazor` only (`solution-planner.md:198`) | A `mobile` token and the three agents in the planner's routing (W1, D11) |
| Stale pointers | `backend/node/skills/pattern-guide/SKILL.md:25`, `pattern-writer/SKILL.md:28`, `README.md:215`, `docs/skills-catalog.md` scope line, `docs/plans/{frontend-PLAN,backend-PLAN,CONFORMANCE-AUDIT-PLAN}.md` name `frontend/react-native` | Repointed in C1 (implemented plans and `docs/audits/` are records and are not edited) |

## 2. The shape

```
mobile/
  _shared/                       bundled into all three plugins
    store-compliance/  security/  release/  observability/  in-app-purchases/
  react-native/                  plugin mobile-react-native
    skills/ (23)  agents/mobile-react-native.md  commands/{mobile-react-native,mobile-react-native-audit}.md
    vendor/react-native-guidelines/   (the fenced Vercel seed, moved as-is)
  ios/                           plugin mobile-ios
    skills/ (23)  agents/mobile-ios.md  commands/{mobile-ios,mobile-ios-audit}.md
  android/                       plugin mobile-android
    skills/ (24)  agents/mobile-android.md  commands/{mobile-android,mobile-android-audit}.md
auth/auth0-react-native/  auth/auth0-ios/  auth/auth0-android/
```

| | `mobile-react-native` | `mobile-ios` | `mobile-android` |
|---|---|---|---|
| Own skills | `mobile/react-native/skills/*` | `mobile/ios/skills/*` | `mobile/android/skills/*` |
| Borrowed native skills | `mobile/ios/skills/basics`, `mobile/android/skills/basics` (native modules, D6) | — | — |
| Shared mobile | all 5 `mobile/_shared/*` | same | same |
| Auth | `auth/auth0-react-native` + `auth/_shared/{auth0-concepts,oidc-concepts}` | `auth/auth0-ios` + same | `auth/auth0-android` + same |
| Design (D10) | `design/{ui-ux-pro-max,visual-identity,design-tokens,theme-presets,brand-import,iconography,charts,ux-patterns,ux-writing,ux-review,accessible-by-design,ethical-patterns,ai-experience,motion}` | same | same |
| Workflow + planning | `engineering-practices/{agent-orientation-cache,code-comments,standards-audit-engine,brainstorming,writing-plans,systematic-debugging,verify-before-done,spec-vs-code-audit,feature-audit}`, `qa/manual/requirements-breakdown`, `backend/_shared/session-budget` | same | same |
| Agents | `mobile-react-native`, `code-auditor` | `mobile-ios`, `code-auditor` | `mobile-android`, `code-auditor` |

**Naming (D3).** New prefix `mobile`. Skill frontmatter is `mobile-<stack>-<folder>` with stacks
`react-native` · `ios` · `android` · `shared` (`mobile-ios-navigation`, `mobile-shared-release`). Auth
skills follow the existing `auth-auth0-<stack>` form. Agents and plugins share one name per stack.
Orientation caches: `docs/agent-context/mobile-<stack>.md`. Audit reports:
`docs/audits/<NNN>-mobile-<stack>-conformance-r<N>.md`.

## 3. Which stacks, and why

The user asked for React Native (primary), Swift and Kotlin, and for a recommendation on anything else
"very popular". Evidence gathered 2026-10-10:

| Framework | Stack Overflow 2024 (latest with a framework list) | JetBrains cross-platform share | App-store presence | Signal |
|---|---|---|---|---|
| React Native + Expo | 8.4% | 35% (2023) | Appfigures top-10k iOS: 1,350 apps, 47% of downloads; AppBrain top Android apps 14.8% | npm 14.2M/wk; ~6× Flutter's job postings |
| **Flutter** | **9.4%** | **46% (2023)**, "most used 4 years running" | Appfigures: 1,184 apps, 38% of downloads; **AppBrain new Android apps 12.4%** (RN 1.6%) | 179k GitHub stars; 4 stable releases/yr held through 2026 |
| Kotlin Multiplatform / Compose MP | — | **7% (2024) → 18% (2025)** | Appfigures: 218 apps, 27% of revenue | Google backs KMP for shared logic |
| .NET MAUI | 3.1% | — | — | regressions reported on .NET 10; Microsoft ships its own apps on RN/Electron |
| Ionic / Capacitor | 2.5% / 1.8% | — | — | Capacitor 5.2M npm/wk — a "web app to the stores" packager, not a mobile stack |
| Lynx · Valdi · NativeScript · Tauri mobile · Skip | marginal or beta | — | — | mention only |

Sources: survey.stackoverflow.co/2024/technology · kotlinlang.org/docs/multiplatform/kotlin-multiplatform-react-native.html ·
appfigures.com/resources/insights/20251219 · appbrain.com/stats/libraries · flutter.dev/blog/flutter-darts-2026-roadmap ·
devblogs.microsoft.com/dotnet/dotnet-maui-moves-to-coreclr-in-dotnet-11.

**Verdicts (D12):** **Flutter** earns a full fourth plugin — it is #1 or #2 on every measure and leads
new Android apps — written as its own plan once this one lands, reusing `mobile/_shared` (O4).
**KMP / Compose Multiplatform** is a lane of `mobile-android` (A5): same language, Gradle and Jetpack
libraries; shared logic by default, shared UI opt-in. **Capacitor** would be a "ship this web app to the
stores" lane of `fe-react` — not planned. **.NET MAUI** is deferred: revisit after .NET 11 GA
(November 2026); the only fit is a Blazor Hybrid lane in `fe-blazor` if Xamarin-migration demand
appears. Everything else is mention-only.

## 4. Version lanes (verified 2026-10-10)

Every skill is version-aware (CLAUDE.md § Version policy): detect first, key every recipe to what is
detected, never up-level, never flag a down-level project for lacking an up-level API.

### 4.1 React Native / Expo

| Lane | Expo SDK | React Native | React | Notes |
|---|---|---|---|---|
| **Primary** | **57** (2026-06-30) | 0.86 | 19.2 | Node ≥ 22.13 (library default Node 24), Xcode 26.4+, iOS 16.4+, Android 7+, compile/target SDK 36 |
| Next | 58 (beta since 2026-09-15) | 0.88 (RC) | 19.3 | **Becomes primary the day it ships stable** — the skill that owns each delta says so: native tabs stable at `expo-router/native-tabs`, Gesture Handler 3, Reanimated 4.7 + worklets 0.13, scene lifecycle default (iOS 27), AGP 9, Expo Router core reworked |
| Supported | 55–56 | 0.83 / 0.85 | 19.2 | SDK 56 + Hermes V1 has a Reanimated memory regression fixed in `expo@57.0.9` — steer to 57 |
| Floor | 54 | 0.81 | 19.1 | Last SDK where the legacy architecture can be on — the migration bridge only; critical fixes end when SDK 58 ships |
| Below 54 | — | — | — | A finding plus a `migration` run; never author for it |

Facts the skills carry: RN is New-Architecture-only since 0.82 / SDK 55 (the interop layer still
exists) · Hermes V1 is the default engine (RN 0.84 / SDK 56) · React Compiler 1.0 is on in the default
template, which changes memoization advice · RN officially recommends a framework, and it is Expo ·
Expo Router is SDK-versioned (`expo-router@57.x`), forked the React Navigation core in SDK 56 — **never
import `@react-navigation/*` in an Expo Router app** (`npx expo-codemod sdk-56-expo-router-react-navigation-replace`) — and
React Navigation 7.5 (8.0 alpha) is the bare-RN lane · the SDK 57 default template has `src/app`, the
`@/*` alias, `@expo/ui`, `expo-image`, `reactCompiler: true`, `typedRoutes: true`, TS `strict` on ~6.0 ·
`expo prebuild` cleans by default since SDK 57 (CNG — native changes go in config plugins) ·
`eslint-config-expo/flat` · `npx expo-doctor` checks React Native Directory · Expo UI (SwiftUI and
Compose primitives) stable since SDK 56 · DOM components (`'use dom'`) · RN 0.87 strict TS API (deep
`react-native/Libraries/*` imports are type errors; `InteractionManager` removed) · `EXPO_PUBLIC_*` is
inlined in plain text · Jest is the only runner (`jest-expo`, `@react-native/jest-preset` from 0.87),
**RNTL 14** makes `render`/`fireEvent`/`act`/`renderHook` async (codemod `rntl-v14-async-functions`),
Vitest is not viable · FlashList 2.3 (no `estimatedItemSize`), Legend List 3.6 · Reanimated 4 needs
`react-native-worklets` · Gesture Handler 3.3 (SDK 58 bundles 3.2.1, SDK 57 bundles 2.32) · MMKV 4
(`createMMKV()`, Nitro) · expo-sqlite / op-sqlite 18; WatermelonDB has not released since 2025-04 ·
TanStack Query 5, Zustand 5, React Hook Form 7.89 + Zod 4.6, i18next 26 / Lingui 6 · NativeWind 4.2
(v5 RC), Unistyles 3.5, Tamagui 3.0, gluestack v5 · brownfield: `expo-brownfield` (alpha; AAR /
XCFramework) and Callstack `@callstack/react-native-brownfield` 5.3 · `expo-observe` exports to any
OpenTelemetry backend; there is no official OTel React Native SDK.

Sources: expo.dev/changelog/sdk-57 · expo.dev/changelog/sdk-58-beta · reactnative.dev/blog (0.82, 0.84, 0.87) ·
expo.dev/blog/expo-router-v56-decoupling-from-react-navigation · docs.expo.dev/brownfield/overview ·
oss.callstack.com/react-native-brownfield · docs.expo.dev/eas/workflows/examples/e2e-tests.

### 4.2 iOS / Swift

| Item | Primary | Supported | Floor / rule |
|---|---|---|---|
| Xcode / Swift / SDK | **Xcode 27.0, Swift 6.4, iOS 27 SDK** (GA 2026-09-14/15) | Xcode 26.x, Swift 6.2–6.3 | Uploads need the Xcode 26 SDK since 2026-04-28 and the **iOS 27 SDK from April 2027** |
| Deployment target | **iOS 17** (`@Observable`, SwiftData, the `@State` macro fix) | iOS 16 (`NavigationStack`) | Below 16: the UIKit lane only, flagged. Uploads need ≥ iOS 13 since 2026-09-09. Xcode 27 debugs only on iOS 17+ devices |
| Language mode | Swift 6 + Approachable Concurrency for new modules | Swift 5-mode modules, migrated one module at a time | Xcode 27 templates still default `SWIFT_VERSION = 5.0` — `project-setup` sets 6 |

Linking against the iOS 27 SDK makes these mandatory: the UIScene lifecycle (TN3187), a launch screen,
Liquid Glass (`UIDesignRequiresCompatibility` is ignored), the `@State` macro; it deprecates
`PreviewProvider`, `FileDocument` and `canOpenURL:`. Swift 6.2 brought default MainActor isolation
(SE-0466), `nonisolated(nonsending)` + `@concurrent` (SE-0461), isolated conformances (SE-0470); Swift 6.4
`await` in `defer`, `weak let`, `~Sendable`. Swift Testing is the default (XCTest only for UI
automation, performance and Objective-C-exception tests). `xcrun swift-format` ships in the toolchain;
SwiftLint 0.65. **CocoaPods trunk goes read-only 2026-12-02.** TCA 1.26, swift-dependencies 1.17,
Factory 3.4, Tuist 4.207, GRDB 7.11, swift-snapshot-testing 1.19 — lanes only where a codebase already
uses them. MetricKit has a Swift-first API in iOS 27 (`MXMetricManager` deprecated at 27.2). OTel Swift
2.5.1. Apple ships agent skills in Xcode 27 (SwiftUI Specialist, app modernization,
`audit-xcode-security-settings`) and `xcrun mcp-server` — see D14. The Swift SDK for Android (official
since 6.3) and Skip are mention-only.

Sources: developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes · swift.org/blog/swift-6.4-released ·
developer.apple.com/news/upcoming-requirements · developer.apple.com/videos/wwdc2026 · blog.cocoapods.org/CocoaPods-Specs-Repo.

### 4.3 Android / Kotlin

| Item | Primary | Supported | Rule |
|---|---|---|---|
| Kotlin | **2.4.21** (K2 is the only compiler) | 2.0–2.3 in brownfield | Compose compiler is the Kotlin plugin `org.jetbrains.kotlin.plugin.compose`; strong skipping is default, its flag is a deprecation error in 2.4 |
| AGP / Gradle | **AGP 9.4, Gradle 9.6+** (built-in Kotlin, KSP only) | AGP 8.x in brownfield | AGP 9 escape hatches (`android.builtInKotlin=false`, `android.newDsl.optOut`) disappear in AGP 10 |
| SDK levels | **compileSdk 37, targetSdk 36, minSdk 24** | targetSdk 35 for existing apps' visibility | Play: new apps **and updates** must target API 36 since 2026-08-31 (extensions to 2026-11-01) |
| Compose | BOM **2026.09.00** (ui 1.12.1, material3 1.4.0) | — | Material 3 Expressive goes stable in material3 1.5 (beta) — version-key it |
| JDK | 21 toolchain | 17 minimum | Robolectric needs 21 for SDK 36 targets |

Facts the skills carry: Views are in maintenance mode (I/O 2026) · Google's architecture
recommendations (2026-10-05): repositories always, one `uiState: StateFlow` per screen ViewModel with
`stateIn(WhileSubscribed(5000))`, `collectAsStateWithLifecycle`, **no ViewModel-to-UI events**, single
activity, Hilt for complex apps / manual DI for simple, **fakes over mocks** · Navigation 3 1.2 stable
(Navigation Compose 2.10 is the existing-app lane; Google's own migration page still names it) · Hilt
Gradle plugin 2.59+ needs AGP 9 · **Room 3.0** (`androidx.room3`, KSP-only, `suspend`/`Flow` DAOs,
`SQLiteDriver`, drops Rx/LiveData/Paging integrations) alongside Room 2.8 · `security-crypto`
(EncryptedSharedPreferences) deprecated → DataStore + Tink or Keystore · Retrofit 3 / Ktor 3.6 ·
Credential Manager 1.6 (Google Sign-In / One Tap are legacy) · Compose UI test **v2** APIs run on
`StandardTestDispatcher` (tests relying on immediate execution break) · Robolectric 4.17 · Roborazzi ·
JUnit 4 is the default runner (JUnit 5 only via the mannodermaus plugin) · detekt 1.23.8 is the last
stable (2.0 alpha; Kotlin 2.4 compatibility unverified) · ktlint 1.8 · edge-to-edge enforced at target
35, predictive back on at 36, large-screen orientation/resizability ignored ≥ sw600dp at 36 with no
opt-out at 37 · AGP 9 R8: strict full-mode keep rules · API 37 adds `ACCESS_LOCAL_NETWORK` and
background-audio FGS rules · Android CLI is stable and agent-drivable · KMP stable; Compose Multiplatform
iOS stable since 1.8 (now 1.12.1); Swift export alpha in Kotlin 2.4; Hilt is Android-only (KMP uses Koin
or Metro).

Sources: kotlinlang.org/docs/whatsnew24.html · developer.android.com/build/releases/gradle-plugin ·
developer.android.com/topic/architecture/recommendations · developer.android.com/jetpack/androidx/releases/room3 ·
developer.android.com/google/play/requirements/target-sdk · developer.android.com/develop/ui/compose/testing/migrate-v2.

### 4.4 Store, security and accessibility dates (shared)

| Rule set | Current fact | Source |
|---|---|---|
| Apple upload | Xcode 26 SDK since 2026-04-28; iOS 27 SDK from April 2027; min target iOS 13 since 2026-09-09 | developer.apple.com/news/upcoming-requirements |
| Apple privacy | `PrivacyInfo.xcprivacy` + Required Reason APIs (FileTimestamp, SystemBootTime, DiskSpace, ActiveKeyboards, UserDefaults) enforced since 2024-05-01; listed third-party SDKs need manifest + signature | developer.apple.com/documentation/bundleresources/privacy-manifest-files |
| Apple review | Guidelines revised 2026-06-08. Hot spots: 2.1, 2.5.1, 2.5.2 + DPLA §3.3.1(B) (downloaded/interpreted code), 2.5.5 IPv6, 3.1.1 IAP, 4.8 login, 5.1.1(i) privacy policy, **5.1.1(v) in-app account deletion** (+ Sign in with Apple token revocation), 5.1.2(i) ATT (EU alternative prompt from iOS 27.2), 5.1.2 consent before sharing data with third-party AI; age-rating questionnaire mandatory since 2026-01-31; Accessibility Nutrition Labels voluntary | developer.apple.com/app-store/review/guidelines |
| Google Play | Target API 36 (above); **16 KB page size: updates blocked from 2027-02-01** (official page; forum dates conflict); Data safety + in-app **and** web account deletion; photo/video → photo picker unless core; `MANAGE_EXTERNAL_STORAGE`, exact alarms, FGS types (+ Console declaration), full-screen intents; developer verification enforced in BR/ID/SG/TH from 2026-09-30, global 2027; 2027-01-27: contact picker, location button | developer.android.com/guide/practices/page-sizes · support.google.com/googleplay/android-developer/table/12921780 |
| Android vitals | Crash 1.09% (8% per model), user-perceived ANR 0.47% (8% per model), excessive partial wake locks 5% (enforced 2026-03-01); memory vitals affect visibility from Feb 2027; slow start: cold ≥ 5 s, warm ≥ 2 s, hot ≥ 1.5 s | developer.android.com/topic/performance/vitals |
| iOS hangs | A hang is the main thread blocked ≥ 250 ms | developer.apple.com/documentation/xcode/understanding-hangs-in-your-app |
| OWASP MAS | **MASVS 2.1.0** (24 controls in 8 groups) → **MASWE 1.0.0** (2026-08-17, `MASWE-0001…0078`) → **MASTG 2.0.0** (2026-06-30, `MASTG-TEST-####`); Mobile Top 10 2024 | mas.owasp.org |
| Accessibility | WCAG2Mobile is a W3C Group Draft Note (2025-05-06); platform targets 44 × 44 pt / 48 × 48 dp; European Accessibility Act applies since 2025-06-28; EN 301 549 v3.2.1 harmonised, v4.1.1 (WCAG 2.2) awaiting its Official Journal citation (~2026-11-30) — target WCAG 2.2 AA | w3.org/TR/wcag2mobile-22 |
| Release tooling | fastlane 2.240.1; GitHub `macos-14` removed 2026-11-02 (`macos-latest` = macos-26 arm64); Azure DevOps macOS 26 / Xcode 27 agents in preview; pin runner image **and** Xcode | github.com/actions/runner-images |
| Mobile E2E (QA-owned) | Appium 3.8.0 (2026-09-24); Maestro CLI 2.11.0 (2026-09-29), black-box YAML flows for iOS, Android, RN and Flutter; Expo's E2E guide runs Maestro in EAS Workflows (`type: maestro` job). Plan 003 owns both lanes on the QA side | docs.expo.dev/eas/workflows/examples/e2e-tests · github.com/mobile-dev-inc/maestro |
| Mobile telemetry | OTel Swift 2.5.1; OTel Android agent 1.7.0 (agent API stable, instrumentations alpha); no official OTel RN SDK (`expo-observe` OTel export, Embrace RN 7.2, Grafana Faro RN "experimental"); Sentry RN 8.30 | github.com/open-telemetry |

### 4.5 Not verified — each owning task re-checks before writing it as fact

Required Reason API reason codes · Play's current exact-alarm wording · the 16 KB deadline history ·
EN 301 549 v4.1.1 adoption date · the EAA micro-enterprise wording · detekt 1.23 with Kotlin 2.4 ·
FCM current API, Turbine, MockK, ktfmt, Timber · the SDK 58 stable date · iPhone Duo layout
requirements (ships 2026-10-23; Duo screenshots required from April 2027) · Android 17's stable date ·
RN `testID` → Android `resource-id` mapping (§8.5) · Play Billing Library current major · Firebase Test
Lab quotas.

## 5. Mobile code rules — the coding standard

C1 copies this section into `CLAUDE.md` as `## Mobile code rules`, after § Frontend code rules (React).
Every mobile skill applies it; every audit checks it.

All three stacks:

- **Platform conventions first.** Native navigation, native controls, system text styles. An app never
  imitates the other platform or the web. Design facts come from `design/ui-ux-pro-max`
  (`--stack react-native | swiftui | jetpack-compose`).
- **The UI thread never blocks** — no disk, network, database or heavy compute on the main thread (or
  the RN JS thread). A frame budget is a correctness rule.
- **Lifecycle is part of the requirement.** Work a screen starts is cancelled when the screen goes;
  returning to the foreground revalidates instead of showing stale data; Android process death restores
  state; nothing assumes the app stays foregrounded mid-write.
- **Every data region has loading / loaded / failed states, plus stale and offline** — failure scoped to
  the response-dependent subtree, one persistent user-dismissed error banner inside the safe area,
  offline told apart from a server error, every request inside a timeout budget.
- **Secrets never ship in the binary or bundle** — `EXPO_PUBLIC_*`, `Info.plist`, `BuildConfig` and
  resources are public. Tokens live only in Keychain / Keystore-backed storage; nothing sensitive in
  logs, `UserDefaults`, `SharedPreferences` or `AsyncStorage`.
- **TLS only.** An ATS or cleartext exception carries a recorded reason. Deep links, push payloads and
  intents are untrusted input, validated before they route.
- **Permissions are asked in context, at the moment of use, after a pre-prompt; the denied path is a
  working screen.**
- **Accessible by default** — every interactive element labelled, touch targets ≥ 44 pt / 48 dp, text
  scales with the system setting and is never locked, Reduce Motion honoured, no state by colour alone.
- **Every interactive element and list container carries the stack's test id** — `testID` (RN),
  `accessibilityIdentifier` (iOS), `Modifier.testTag` with `testTagsAsResourceId` or `android:id`
  (Android) — PascalCase dot-separated and static, **never the accessibility label**.
- **Store rules are code rules** — privacy manifest and Required Reason APIs, in-app account deletion,
  permission declarations, target API level. `mobile/_shared/store-compliance` owns them.
- Constructor / initializer injection only; no service locator; no static mutable state; async all the
  way — never block on a result.
- **Dev-side tests** for the logic the agent writes (Swift Testing · JUnit + fakes · Jest + RNTL);
  device journeys and E2E belong to the `qa-mobile-<stack>` peer.
- Never up-level a project's toolchain, SDK or deployment target as a side effect of other work.

Per stack:

- **React Native:** Expo is the framework — Expo Router, development builds, CNG; native changes go in
  config plugins, never hand edits to generated `ios/` / `android/`. New Architecture only. Text only
  inside `<Text>`. Unbounded lists are virtualized (FlashList / Legend List). Animation runs on the UI
  thread (Reanimated), transform/opacity only. Server state lives in TanStack Query, never in a client
  store.
- **iOS (Swift):** Swift 6 mode with Approachable Concurrency for new modules — `@MainActor` default in
  app/UI modules, `nonisolated` in packages, `@concurrent` for CPU work; no `@unchecked Sendable` or
  `nonisolated(unsafe)` without a written justification; no force unwrap outside tests. SwiftUI first,
  UIKit where the codebase is UIKit. `@Observable` over `ObservableObject` on iOS 17+. `os.Logger` only.
- **Android (Kotlin):** Compose first. One `uiState: StateFlow` per screen ViewModel, collected with
  `collectAsStateWithLifecycle`; no ViewModel-to-UI events. Structured concurrency — no `GlobalScope`,
  dispatchers injected. No `!!` outside tests. KSP, never kapt. Room / DataStore over raw SQLite /
  `SharedPreferences`. R8 full mode and a Baseline Profile in release builds.

## 6. The skill set

### 6.1 The common spine (D4)

Every stack ships these folders with the same name and the same audit section (§8), so the three
plugins read alike and their audits compare letter for letter.

| Folder | Owns on every stack | § |
|---|---|---|
| `basics` | The language and platform mental model and the stack's coding standard (§5 applied) | A |
| `project-setup` | Greenfield scaffold, toolchain pins, strictness, formatter + linter, folder layout, env config | A, B |
| `architecture` | App structure, state ownership, DI, modularization — the simplest shape that holds (KISS) | C |
| `ui-components` | Writing screens and components: composition, previews, lists, the three-state region in markup, platform UI conventions | D |
| `styling` | Theme and tokens, dark mode, typography that scales, adaptive / responsive layout, safe areas | E |
| `navigation` | Routes, tabs, modals, typed parameters, in-app deep-link routing, back behaviour | F |
| `forms` | Input, validation, keyboard handling, autofill, server errors mapped to fields | G |
| `networking` | The API client: timeouts, cancellation, retries + `Retry-After`, ProblemDetails, token refresh, realtime (WebSocket / SSE) | H |
| `offline-and-storage` | Local persistence, secure storage, sync and conflict policy, storage-full degradation | I |
| `device-features` | Permissions (priming, denied path), camera / photo picker, location, biometrics, haptics, share, files | J |
| `notifications-and-links` | Push (client side), notification permission and channels, universal links / App Links, link validation | F, J |
| `animation` | Motion and gestures on the UI thread, transitions, Reduce Motion | Q |
| `languages` | Localization, plurals, RTL, locale-aware formatting | P |
| `accessibility` | Screen readers, labels/roles/traits, focus, text scaling, targets | M |
| `performance` | Startup, frame rate, lists, memory, app size, the stack's profilers | N |
| `error-handling` | The house resilience rule set with the mobile deltas (§6.5) | O |
| `test-ids` | The stack's test identifier on every interactive element and list container; consumes `missing-testids.md` | R |
| `unit-testing` (RN: `component-testing`) | Dev-side tests for logic the agent writes; E2E is the `qa-mobile-<stack>` peer's | S |
| `migration` | Version upgrades, legacy modernization, and (RN) embedding into an existing native app | A |
| `code-review` | Hostile review of a diff against every rule, plus a simulator/emulator screenshot pass | — |
| `standards-audit` | The conformance audit on `ep-standards-audit-engine`, with the stack checklist (§8) | — |

### 6.2 `mobile/react-native/skills` (23) — frontmatter `mobile-react-native-<folder>`

| Folder | Stack specifics (facts in §4.1) |
|---|---|
| `basics` | **Rewrite of the draft `reference`.** New Architecture only, Hermes V1, the JS / UI / worklet threads, React Compiler on, the web-React ↔ RN map (no RSC, no DOM, no CSS cascade, no SEO), Expo as the framework, the index into `vendor/react-native-guidelines/rules/` |
| `project-setup` | **Rewrite of `project-scaffold`.** `create-expo-app` default template on SDK 57, development builds over Expo Go, CNG / `prebuild --clean`, config plugins, EAS Build / Submit / Update / Workflows, monorepo (pnpm isolated installs), `eslint-config-expo/flat`, `expo-doctor`, `EXPO_PUBLIC_` is public |
| `architecture` | **Rewrite of `state-management`.** Feature-first layout, server state in TanStack Query, client state in Zustand / Context, navigation params as state, DI through props/context |
| `component-library` | **Rewrite of the draft.** One-of-N: StyleSheet + Expo UI (default) · NativeWind · Tamagui · Unistyles · gluestack · React Native Paper — `references/<lib>.md`, add `expo-ui.md` and `unistyles.md` |
| `styling` | **Rewrite of the draft**, absorbing the July plan's `responsive-design`: tokens, `useColorScheme`, platform fonts, safe areas, `useWindowDimensions`, tablets and foldables |
| `navigation` | Expo Router: file routes, typed routes, protected routes, modals, native tabs (`unstable-native-tabs` ≤ 57, `native-tabs` on 58), linking config; React Navigation 7.5 lane for bare RN |
| `ui-components` | Screens and components (the fe-react `component-writer` + `ui-rules` pair): `Pressable`, `expo-image`, FlashList / Legend List, native menus and modals, text-in-`<Text>`, compound components, empty/loading conventions |
| `forms` | React Hook Form + Zod, keyboard avoidance, input modes, secure fields, `setError` from ProblemDetails |
| `networking` | `fetch` + TanStack Query, `focusManager` on `AppState`, `onlineManager` on NetInfo, `AbortSignal.timeout`, ProblemDetails, token refresh, WebSocket / SSE paused on background |
| `offline-and-storage` | MMKV 4, expo-sqlite / op-sqlite, `expo-secure-store` for secrets, TanStack Query persistence, mutation queue, conflicts |
| `native-modules` | When to go native; Expo Modules API in Swift and Kotlin (loads `mobile-ios-basics` + `mobile-android-basics`), config plugins, Expo UI, Nitro modules, TurboModules in bare RN, DOM components |
| `device-features` | `expo-camera`, `expo-image-picker`, `expo-location`, `expo-local-authentication`, haptics, sharing, file system, `expo-background-task` |
| `notifications-and-links` | `expo-notifications` (tokens, Android 13+ permission, channels), APNs / FCM via EAS or the server, universal links / App Links through Expo Router |
| `animation` | Reanimated 4 + worklets, Gesture Handler 2.32 (SDK 57) vs 3 (SDK 58) — version-keyed, GPU-only props, layout animations, Reduce Motion |
| `languages` | `expo-localization` + i18next or Lingui, `I18nManager` RTL, hoisted `Intl` |
| `accessibility` | `accessibilityRole/Label/State` and the `role` / `aria-*` props, VoiceOver / TalkBack, focus, `allowFontScaling` never false |
| `performance` | The vendored list rules, React Compiler and memoization, startup via `expo-observe`, Expo Atlas bundle analysis, React Native DevTools |
| `error-handling` | The full React rule set with the §6.5 deltas; references split from the start |
| `test-ids` | `testID` on every interactive element and list container, the platform mapping (§8.5), the `missing-testids.md` hand-off |
| `component-testing` | Jest + `jest-expo` + RNTL 14 (async APIs), fakes for native modules, plain Jest for non-rendering logic; E2E is `qa-mobile-typescript`'s — Appium, or its Maestro lane on Expo projects (plan 003 X1) |
| `migration` | `references/sdk-upgrade.md` (one SDK at a time, `expo install --fix`, codemods), `new-architecture.md` (through the SDK 54 bridge), `bare-to-expo.md` (`install-expo-modules`, adopting prebuild), `embed-in-native-app.md` (`expo-brownfield` alpha, Callstack `react-native-brownfield`, RN core integration) |
| `code-review`, `standards-audit` | §6.1 |

### 6.3 `mobile/ios/skills` (23) — frontmatter `mobile-ios-<folder>`

| Folder | Stack specifics (facts in §4.2) |
|---|---|
| `basics` | The Swift coding standard (also bundled into `mobile-react-native`): API Design Guidelines naming, value types, optionals, errors, access control, the §5 concurrency standard, Observation, `os.Logger` |
| `project-setup` | Xcode 27 app with Swift 6 mode set, warnings as errors, local Swift packages as modules, xcconfig per environment, `xcrun swift-format` + SwiftLint, test plans, scene lifecycle + launch screen, String Catalog, a `PrivacyInfo.xcprivacy` from day one; Tuist respected where present |
| `architecture` | MV by default (`@Observable` models and services via initializer injection / `@Environment`); a view model only where logic needs testing apart from the view; `@State` / `@Binding` / `@Bindable` ownership; TCA as a lane only where the codebase uses it |
| `ui-components` | SwiftUI views: small views, `#Preview`, `.task` for loads (cancelled with the view), `List` / lazy stacks, SF Symbols, no work in `body` |
| `styling` | Liquid Glass (forced by the iOS 27 SDK), semantic colours, Dynamic Type text styles, asset-catalog tokens, size classes, resizable iPad windows |
| `navigation` | `NavigationStack(path:)` with typed routes, `NavigationSplitView`, sheets, `TabView`, `onOpenURL` → route |
| `forms` | `Form`, `@FocusState`, validation, `textContentType` for autofill and passkeys, keyboard toolbar |
| `networking` | `URLSession` async/await + `Codable`, one concrete API client (a protocol only once a second implementation exists), timeouts, `Task` cancellation, retries, ProblemDetails, a token-refresh actor, `URLSessionWebSocketTask` |
| `offline-and-storage` | SwiftData default (iOS 17+), Core Data / GRDB lanes where present, Keychain accessibility classes, `UserDefaults` (a Required Reason API), file protection, `VersionedSchema` migrations |
| `uikit` | The UIKit lane for brownfield apps: view controllers, Auto Layout, diffable data sources, UIKit Observation tracking, `UIHostingController` / `UIHostingConfiguration` / `UIViewRepresentable` interop |
| `device-features` | Permissions + `Info.plist` usage strings, `PhotosPicker`, AVFoundation camera, Core Location, LocalAuthentication, haptics, `ShareLink`, file importer |
| `notifications-and-links` | APNs, `UNUserNotificationCenter`, notification service extension, universal links (AASA), URL scheme caution |
| `system-integration` | App Intents, WidgetKit, Live Activities (4.5.3), `BGTaskScheduler`, `BGContinuedProcessingTask`, background `URLSession` |
| `animation` | `withAnimation`, transitions, `matchedGeometryEffect`, phase / keyframe animators, `accessibilityReduceMotion` |
| `languages` | String Catalogs, plurals, `FormatStyle`, RTL |
| `accessibility` | VoiceOver labels / traits / values, element grouping, rotors, Dynamic Type through the accessibility sizes, Differentiate Without Color, readiness for Accessibility Nutrition Labels |
| `performance` | Instruments (SwiftUI, Swift executors), launch time, hangs ≥ 250 ms, MetricKit, memory, app size |
| `error-handling` | The house rule set in SwiftUI (§6.5 rows that are not RN-only), `scenePhase` resume revalidation |
| `test-ids` | `accessibilityIdentifier` on every interactive element and container; Appium's XCUITest driver reads it as `accessibility id` |
| `unit-testing` | Swift Testing default, XCTest only where §4.2 says; fakes over mocks; clock and UUID seams; snapshot tests |
| `migration` | Swift 5 → 6 per module, `ObservableObject` → `@Observable`, Combine → async / `Observations`, UIKit → SwiftUI screen by screen, Objective-C → Swift, **CocoaPods → SPM before 2026-12-02**, the iOS 27 SDK forced changes, deployment-target raises — one `references/` file per path |
| `code-review`, `standards-audit` | §6.1 |

### 6.4 `mobile/android/skills` (24) — frontmatter `mobile-android-<folder>`

| Folder | Stack specifics (facts in §4.3) |
|---|---|
| `basics` | The Kotlin coding standard (also bundled into `mobile-react-native`): Kotlin conventions, null safety, immutability, sealed UI state, structured concurrency, injected dispatchers, Flow conventions |
| `project-setup` | AGP 9 with built-in Kotlin, version catalog, convention plugins only once two modules need them, compile 37 / target 36 / min 24, JDK 21 toolchain, Compose BOM, KSP, R8 full mode, detekt / ktlint, Android Lint + compose-lints, single activity, edge-to-edge, predictive back |
| `architecture` | Google's recommendations (§4.3): repositories, screen ViewModels with one `uiState`, use cases only in big apps, Hilt or manual DI, modules only when earned, `SavedStateHandle` for process death |
| `ui-components` | Compose: stateless composables with hoisted state, `modifier` as the first optional parameter, previews, lazy-list `key` / `contentType`, stability, side-effect APIs, Material 3 components |
| `styling` | Material 3 theme and tokens (1.4 vs Expressive in 1.5), dynamic colour, typography in `sp`, window size classes, large-screen rules at 36 / 37, insets |
| `navigation` | Navigation 3 for new apps, Navigation Compose 2.10 type-safe lane for existing ones, App Links, back stack, predictive back |
| `forms` | Compose text fields and state, validation, `KeyboardOptions`, autofill, IME insets |
| `networking` | Retrofit 3 + OkHttp (Ktor 3.6 in the KMP lane), kotlinx.serialization, timeouts, cancellation, `Retry-After`, ProblemDetails, OkHttp `Authenticator` refresh, WebSocket, Network Security Config |
| `offline-and-storage` | Room 3 for new / Room 2.8 lane, DataStore, Keystore / Tink in place of EncryptedSharedPreferences, WorkManager sync, Paging 3, offline-first repositories |
| `views-interop` | The XML Views lane for brownfield: ViewBinding, Fragments, `ComposeView` with `DisposeOnViewTreeLifecycleDestroyed`, `AndroidView` |
| `device-features` | Runtime permissions, the photo picker (policy), CameraX, location (precise / approximate), BiometricPrompt, Credential Manager and passkeys, SAF, `ACCESS_LOCAL_NETWORK` at 37 |
| `notifications-and-links` | FCM, channels, `POST_NOTIFICATIONS`, full-screen-intent policy, App Links verification (`assetlinks.json`), intent validation, immutable `PendingIntent` |
| `system-integration` | WorkManager, foreground-service types and their Play declaration, Glance widgets, shortcuts, exact-alarm policy |
| `animation` | Compose animation APIs, shared-element transitions, predictive-back animation, the animator duration scale as Reduce Motion |
| `languages` | String resources, plurals, per-app language, RTL, formatting |
| `accessibility` | Semantics, `contentDescription`, merged descendants, 48 dp, `sp` to 200%, TalkBack, `enableAccessibilityChecks()` in Compose tests |
| `performance` | Baseline + Startup Profiles, Macrobenchmark, AGP 9 R8 keep-rule strictness, App Startup, the §4.4 vitals, recomposition tracing, Perfetto |
| `error-handling` | The house rule set in ViewModel + Compose (§6.5 rows that are not RN-only), process-death restore |
| `test-ids` | `Modifier.testTag` + `semantics { testTagsAsResourceId = true }` at the root so Appium / UiAutomator see `resource-id`; `android:id` in Views; never `contentDescription` as an id |
| `unit-testing` | JUnit 4 (JUnit 5 lane where present), fakes over mocks, `runTest` / `StandardTestDispatcher`, Turbine, Robolectric, Compose UI test v2, Roborazzi |
| `migration` | AGP 8 → 9 (built-in Kotlin, `compilerOptions`, variant API, explicit `targetSdk`, kapt → KSP), Views → Compose in Google's order, Java → Kotlin, Groovy → KTS, LiveData / RxJava → Flow, Dagger → Hilt, Navigation Compose → Navigation 3, Room 2 → 3, targetSdk 35 / 36 / 37 behaviour changes, EncryptedSharedPreferences replacement — one `references/` file per path |
| `kotlin-multiplatform` | The KMP lane: shared logic by default (Room, DataStore, Ktor, kotlinx.serialization, KMP ViewModel, Koin or Metro), `com.android.kotlin.multiplatform.library`, the iOS side (XCFramework / SPM, Swift export alpha), Compose Multiplatform as the opt-in shared-UI sub-lane; the Swift consumer code is `mobile-ios`'s |
| `code-review`, `standards-audit` | §6.1 |

### 6.5 Error resilience — the mobile deltas

`error-handling` on every stack is authored against the full fe-react rule set
(`frontend/react/skills/error-handling/{SKILL.md,references/*}` + `data-fetching`), not a subset. The
deltas, carried over from the July RN plan so C1 can delete it:

| Rule (React) | Mobile delta |
|---|---|
| **Failure scoped** to the response-dependent subtree | Easier to get wrong: a list whose header carries search + filters (`ListHeaderComponent`, a `List` section header, a `LazyColumn` sticky header) loses the header to an early `return <Error/>` — scope the failure to the list body / empty slot |
| **Persistent, user-dismissed notification** | No viewport top-right — a **top-anchored banner inside the safe area**, clear of the status bar, notch, translucent headers and the keyboard; close control at 44 pt / 48 dp; no auto-dismiss for errors |
| Drifted / unparseable response is a **failed** state, never empty | Same |
| **Stale fourth state** | More visible — pull-to-refresh is the canonical refetch; a failed pull keeps the list and marks it stale |
| **Timeout budgets** | The highest-value rule on mobile: a request on a dying cell link hangs far longer than on wifi. Longer budgets than web, per endpoint class |
| **Session expiry ladder** (refresh → replay → re-auth in place) | Re-auth in place is a modal, not a redirect; biometric re-auth is often the right third rung; tokens in Keychain / Keystore-backed storage |
| **Version skew** | RN: **OTA-update skew** (`expo-updates`) — detect, prompt, one guarded `Updates.reloadAsync()`, never over unsaved work. Native: a forced-update path (MASVS-CODE-2) driven by a server-side minimum version |
| **Mutation failures** (double submit, idempotency key, announced rollback, 409, per-item bulk) | Backgrounding mid-write is routine, so the indeterminate outcome is the common case |
| `Retry-After`, bounded retries, stop-retrying circuit | Stronger — retries cost battery and data; no retries at all while offline |
| Notification volume cap + roll-up | Stronger — a phone fits one or two banners |
| **Third-party dependency failure** | Map, payment, push and analytics SDKs; a native module that fails to link is a crash, not a degraded region |
| **Storage failures degrade to memory** | Full disks are common and the OS wipes caches under pressure; `offline-and-storage` owns persistence, `error-handling` owns the degradation |
| Stale-tab restore | Becomes **app resume**: foreground transition + reconnect → revalidate |
| Gone-not-broken (404 on a record) | Same |
| Multi-tab, hydration mismatch | N/A on mobile |

Every mobile `error-handling` SKILL.md must fit 16,000 characters — fe-react's is 41,976 and is **not**
the size pattern. Put the rule bodies in `references/session-and-resume.md` and
`references/writes-and-dependencies.md` from the start.

### 6.6 Shared and auth skills

| Skill | Frontmatter | Owns | References |
|---|---|---|---|
| `mobile/_shared/store-compliance` | `mobile-shared-store-compliance` | Every App Store and Play rule in §4.4 that code or config can satisfy, as a dated table with a re-verify date per row; what lives only in App Store Connect / Play Console and so can only be flagged as a likely mismatch | `apple.md`, `google-play.md`, `audit-checks.md` |
| `mobile/_shared/security` | `mobile-shared-security` | Dev-side secure coding per MASVS 2.1 group, each rule keyed to its MASWE id and MASTG test; what a static audit cannot prove is marked **requires dynamic test** and handed to `qa-security` (`mobile-runtime-testing`) | `ios.md`, `android.md`, `react-native.md`, `audit-checks.md` |
| `mobile/_shared/release` | `mobile-shared-release` | Version + build numbers, signing (App Store Connect API key, fastlane `match`, Xcode Cloud, EAS credentials, Play App Signing + upload key — nothing in the repo), pinned CI runners, TestFlight / Play tracks, phased and staged rollout, OTA rules (`runtimeVersion` fingerprint, code-signed updates, never native changes), symbol upload (dSYM, R8 mapping, Hermes source maps). Pipeline YAML stays `devops-engineer`'s; CI test wiring stays `qa-cicd-<stack>`'s | `eas.md`, `fastlane.md`, `xcode-cloud.md`, `gradle-play.md`, `audit-checks.md` |
| `mobile/_shared/observability` | `mobile-shared-observability` | One crash reporter (Sentry or Crashlytics), OTel per stack (§4.4), app → public ingest gateway → OTel Collector / Alloy (`otlp` or `faro.receiver`) → Tempo / Loki / Prometheus-Mimir, on-device batching and sampling, resource attributes, PII scrubbing, structured logging. The Collector and backends are the `observability-engineer-<stack>` agents' (be-* plugins) | `react-native.md`, `ios.md`, `android.md`, `audit-checks.md` |
| `mobile/_shared/in-app-purchases` | `mobile-shared-in-app-purchases` | StoreKit 2, Play Billing, the RN lane (RevenueCat / `expo-iap` / `react-native-iap` — research which is current), server-side entitlement as the source of truth, server notifications (App Store Server Notifications v2, RTDN), restore, guideline 3.1.1 and Play payments policy, cancel-as-easy-as-subscribe (`design/ethical-patterns`) | `storekit.md`, `play-billing.md`, `react-native.md`, `audit-checks.md` |
| `auth/auth0-react-native` | `auth-auth0-react-native` | `react-native-auth0` with its Expo config plugin, Universal Login via the system browser (PKCE), the credentials manager, biometric unlock, logout | — |
| `auth/auth0-ios` | `auth-auth0-ios` | Auth0.swift, Universal Login via `ASWebAuthenticationSession`, `CredentialsManager` + Keychain, biometrics, Sign in with Apple through Auth0 | — |
| `auth/auth0-android` | `auth-auth0-android` | Auth0.Android, Custom Tabs, `SecureCredentialsManager`, App Links callback, passkeys | — |

## 7. Greenfield and brownfield — the agents

Each agent follows `.skill-template/agent.md`: role + two-modes note → skill-loading protocol →
operating rules (with the template's `Gate:` line verbatim) → working on existing code → steps →
related agents → output contract (both shapes) → when uncertain. `fe-react.md` is the content pattern
but **not** the size pattern: it is 29,289 characters and every mobile agent must fit the 14,000-character
agent budget (D16) — the detail lives in the skills, the agent routes.

### 7.1 Steps (greenfield; brownfield re-enters single rows)

| # | Step | Skills | Exit gate (outside a `Gate: none` plan task) |
|---|---|---|---|
| 0 | Project setup *(skip if one exists)* | `project-setup` | Builds; launches on a simulator / emulator; one screen renders |
| 1 | Foundations | `basics`, `architecture`, `styling`, `navigation` (+ RN `component-library`), `design/ux-patterns`, `design/ui-ux-pro-max` (`--design-system`, then `--stack react-native\|swiftui\|jetpack-compose`), `design/visual-identity`, `design/motion`; `auth/auth0-<stack>` + `auth/_shared/auth0-concepts` when there is sign-in | Decision record: the experience block per `design/ux-patterns` — or, when `docs/plans/<NNN>-*/experience-plan.md` exists, that plan validated, never redesigned; state + DI plan; theme; adaptive-layout contract; a design plan critiqued against the three AI-default looks and revised. Walking skeleton renders the shell |
| 2 | Feature build | `ui-components`, `navigation`, `forms`, `networking`, `offline-and-storage`, `device-features`, `notifications-and-links`, `test-ids`, `animation`, `languages`, `design/ux-writing`; RN `native-modules`; iOS `uikit`, `system-integration`; Android `views-interop`, `system-integration`, `kotlin-multiplatform`; `mobile/_shared/in-app-purchases` when there are purchases | Build + static checks clean; every screen three-state; every interactive element tagged; permissions primed with a working denied path; links validated |
| 3 | Quality layers | `accessibility`, `performance`, `error-handling`, `mobile/_shared/security`, `mobile/_shared/observability` | The §6.5 resilience gate; accessibility rules met in code; performance budget; security rules; crash reporting wired |
| 4 | Dev-side tests | `unit-testing` (RN `component-testing`) | Tests green; logic and non-rendering code covered |
| 5 | Review | `code-review`, `design/ux-review`, `design/visual-identity`, `design/ui-ux-pro-max` | No blocker / major rows after fixes; visual self-critique done on captured simulator / emulator screenshots |
| 6 | Release readiness *(when shipping is in scope)* | `mobile/_shared/release`, `mobile/_shared/store-compliance` | Store-compliance rows clean; signing and versioning configured; no secret in the repo |

**Single-skill triggers** (no other step runs): a `missing-testids.md` from QA → `test-ids` alone; "audit
against the conventions" → `standards-audit` alone (also `/mobile-<stack>-audit`); a version jump or
modernization → `migration` alone, one SDK / major per change.

### 7.2 The commands each agent runs (outside a `Gate: none` plan task)

| | React Native | iOS | Android |
|---|---|---|---|
| Build / run | `npx expo run:ios`, `npx expo run:android` (development build) | `xcodebuild -scheme <Scheme> -destination 'platform=iOS Simulator,name=<Device>' build` | `./gradlew :app:assembleDebug` |
| Static | `npx tsc --noEmit`, `npx expo lint`, `npx expo-doctor` | `xcrun swift-format lint --recursive <dirs>`, `swiftlint` | `./gradlew lint detekt` (+ ktlint where configured) |
| Tests | `npx jest` | `xcodebuild … test`; `swift test` in local packages | `./gradlew testDebugUnitTest` |
| Screenshot for Step 5 | `xcrun simctl io booted screenshot <file>` · `adb exec-out screencap -p > <file>`, then `Read` the image | `xcrun simctl io booted screenshot <file>` | `adb exec-out screencap -p > <file>` |

### 7.3 Brownfield — orientation cache fields

| Section | `mobile-react-native` | `mobile-ios` | `mobile-android` |
|---|---|---|---|
| Version lane | Expo SDK, RN, React; Expo vs bare; CNG adopted; New Arch status; Hermes; Compiler on/off; package manager | Xcode / Swift; deployment target; language mode per module; SwiftUI vs UIKit share; package manager (SPM / CocoaPods / Tuist) | Kotlin, AGP, Gradle; compile / target / min SDK; Compose vs Views share; KSP / kapt; KMP modules |
| Build, run & test | the project's own scripts and EAS profiles | schemes, test plans, `xcodebuild` destinations | Gradle tasks, flavours, managed devices |
| Layout | `src/app` routes, feature folders, `ios/` / `android/` generated or committed | targets, local packages, extensions | modules (`app` / `feature` / `core`), `build-logic` |
| Seams to reuse | router layout + protected routes, query client + persistence, stores, API client, theme + component library, native modules / config plugins, `testID` naming | models / services and their injection, API client, persistence stack, navigation routes, design tokens, `accessibilityIdentifier` naming | ViewModels + `uiState` shape, repositories, DI graph, navigation keys, theme, `testTag` naming |
| Conventions observed | deviations from §5 with their reasons | same | same |
| Known unknowns | native code nobody owns, unverified OTA config | Objective-C islands, unmigrated Swift 5 modules | Java islands, Views screens, R8 rules nobody understands |

**Mode A — FIX** loads `ep-systematic-debugging`: reproduce first (a failing unit test is the ideal
repro), root-cause against the stack's known traps — RN: text outside `<Text>`, a hand edit
overwritten by `prebuild --clean`, stale worklet closures, `AppState` gaps; iOS: Swift 6 dynamic
isolation crashes, `@State` initial values re-run below the iOS 27 SDK, main-thread publishing; Android:
process death, collection outside the lifecycle, recomposition loops, R8 stripping — then the smallest
fix, `ep-verify-before-done`, and sweep the defect class. **Mode B — EXTEND** re-enters only the touched
steps and reuses the cached seams. A legacy codebase (old SDK, UIKit, Views, Java, CocoaPods, old
architecture) is never modernized as a side effect: that is a separate `migration` run, offered, never
assumed.

## 8. Audits

### 8.1 The lanes

| Lane | Entry | What it checks |
|---|---|---|
| **Convention** | `/mobile-<stack>-audit` → `standards-audit` on `ep-standards-audit-engine` | The whole codebase against §5 and every skill's rules, sections A–W below; `docs/audits/<NNN>-mobile-<stack>-conformance-r<N>.md`, re-runnable (Mode A baseline / Mode B re-audit) |
| Spec and feature | `code-auditor` (bundled) | Code against stories / a spec, or a spec-less feature deep-dive — stack-agnostic, unchanged |
| Security testing | `qa-security` peer → `mobile-app-scan` (static, built APK/AAB/IPA), `mobile-runtime-testing` (dynamic, authorization-gated) | What a source read cannot prove: pinning holds, what lands on disk, resilience controls |
| Design | `design/ux-review` on simulator / emulator screenshots | Heuristics, flow, IA. The `design-auditor` agent is not bundled — its capture is Playwright-bound (D10) |

### 8.2 Sections — identical letters on every stack

| § | Section | Owner (RN) | Owner (iOS) | Owner (Android) |
|---|---|---|---|---|
| A | Version lane, toolchain & migration hygiene | `project-setup`, `migration`, `basics` | same | same |
| B | Project structure, strictness & language standard | `project-setup`, `basics` | same | same |
| C | Architecture, state & DI | `architecture` | same | same |
| D | UI components & platform conventions | `ui-components`, `component-library` | `ui-components`, `uikit` | `ui-components`, `views-interop` |
| E | Styling, theming & adaptive layout | `styling` | same | same |
| F | Navigation & deep links | `navigation`, `notifications-and-links` | same | same |
| G | Forms & input | `forms` | same | same |
| H | Networking & realtime | `networking` | same | same |
| I | Offline, storage & sync | `offline-and-storage` | same | same |
| J | Device features, permissions & native code | `device-features`, `notifications-and-links`, `native-modules` | `device-features`, `notifications-and-links`, `system-integration` | `device-features`, `notifications-and-links`, `system-integration` |
| K | Security | `mobile/_shared/security` (fragment) | same | same |
| L | Privacy & store compliance | `mobile/_shared/store-compliance` (fragment) | same | same |
| M | Accessibility | `accessibility` | same | same |
| N | Performance | `performance` | same | same |
| O | Error resilience | `error-handling` | same | same |
| P | Localization | `languages` | same | same |
| Q | Motion & gestures | `animation` | same | same |
| R | Testability & test ids | `test-ids` | same | same |
| S | Dev-side tests | `component-testing` | `unit-testing` | `unit-testing` |
| T | Release & signing | `mobile/_shared/release` (fragment) | same | same |
| U | Observability & logging | `mobile/_shared/observability` (fragment) | same | same |
| V | Comments & KISS | `ep-code-comments`, CLAUDE.md § Simplicity | same | same |
| W | Kotlin Multiplatform | — | — | `kotlin-multiplatform` (N/A unless KMP modules exist) |
| X | In-app purchases | `mobile/_shared/in-app-purchases` (fragment; N/A unless the app sells anything) | same | same |

### 8.3 How the checklists get built (D13)

C1 writes three skeletons — `mobile/<stack>/skills/standards-audit/references/conformance-checklist.md`
— with the fe-react header text adapted (permanent ids, "how to read a row", the recipe shape for the
stack, the lane tags), every section heading with its owners, and rows only for V. **Every skill task
appends its own rows** to its section the moment it writes the skill: columns
`| # | Check | Violation looks like | Find it with | Sev |`, numbering continuing from the last row,
lane tags in brackets (`[SDK58]`, `[iOS17+]`, `[Swift6]`, `[AGP9]`, `[KMP]`, `[UIKit]`, `[Views]`,
`[bare]`). Recipes use `rg` with the stack's globs (`*.ts,*.tsx` · `*.swift` · `*.kt,*.kts,*.xml`).
**Sections K, L, T, U and X hold no rows of their own.** Their heading says: the rows are those of
`mobile/_shared/<skill>/references/audit-checks.md` whose `Stacks` column names this stack, and the ids
are the fragment's (finding `K3` is row K3 of the security fragment). The fragment → letter map is fixed:
`security` K · `store-compliance` L · `release` T · `observability` U · `in-app-purchases` X. Each
fragment (written by S1–S3) numbers its own rows with its letter, carries a `Stacks` column, and — in
K — the MASWE id. A row a static read cannot prove says **requires dynamic test →
`qa-security`** and is reported as unverified, never as passed. Each stack's last task writes only the
audit `SKILL.md` (on the engine, in the `be-dotnet-standards-audit` shape) and a closing section index.

### 8.4 Severity anchors

blocker — ships a crash, a store rejection, or a hard security rule break (secret in the bundle,
cleartext auth traffic, an exported component leaking data, missing account deletion where accounts
exist). major — a rule in §5 broken where it will hurt soon (unbounded non-virtualized list, no timeout,
untagged interactive elements, permissions with no denied path). minor — style, naming, a single
missing label. nit — preference.

### 8.5 The test-id contract and the QA hand-off

`qa-mobile-<stack>` locates elements by `accessibility id` (iOS `name` = `accessibilityIdentifier`) and
by `id` (Android `resource-id`). The intended mapping is: RN `testID` → `accessibilityIdentifier` on iOS
and `resource-id` on Android; SwiftUI / UIKit `accessibilityIdentifier`; Compose `Modifier.testTag` +
`testTagsAsResourceId = true` → `resource-id`; Views `android:id`. The accessibility label
(`accessibilityLabel`, `contentDescription`) is for people, never an id. `qa/*/skills/mobile-screen-explorer/SKILL.md:10`
says Android `content-desc` maps to an RN `testID`. R3 verifies the RN mapping against the current RN
docs and writes the answer into `mobile-react-native-test-ids`; W1 corrects the QA line in all three
stacks to match. Maestro (plan 003's lane) selects with `id:`; R3 also verifies which identifier
`id:` matches on each platform, so one set of ids serves Appium and Maestro alike.

## 9. Integration (W1) and documentation (G1)

**Marketplace (W1).** Three entries in `.claude-plugin/marketplace.json`, in the fe-react entry's
shape (`source "./"`, `strict false`, the author block, `MIT`, `category "development"`), placed after
`fe-react`. Skills, commands and agents per §2. Commands: `engineering-practices/commands/code-auditor.md`,
the stack's two commands, `design/commands/design-<x>.md` for each bundled design skill (no
`design-ui-code-audit`, `design-landing-patterns`, `design-auditor`), `engineering-practices/commands/{dev-design,dev-plan-feature,ep-spec-vs-code-audit,ep-feature-audit}.md`,
`qa/manual/commands/qa-requirements-breakdown.md`. Agents: the stack agent and
`engineering-practices/agents/code-auditor.md`. Descriptions in the fe-react description's voice.

**Planning lane (W1, D11).** Add `mobile` — "the native or React Native client app" — to the stack list
at `engineering-practices/writing-plans/references/plan-format.md:117`, `backend/_shared/delivery-plan/SKILL.md:43,118,282`,
`backend/_shared/agents/solution-planner.md:15,79,229`, and to CLAUDE.md § Planning's "one stack and one
agent per task" bullet ("a task touching the API tree and an app tree is two tasks"). Add the three
agents to the planner's routing beside `fe-react` / `fe-blazor` (`solution-planner.md:61,198`): they
execute `mobile` tasks, take `experience-plan.md` §2–§4 as their IA, and close out the same way.

**QA peers (W1).** `qa/{java,dotnet,typescript}/agents/qa-mobile-<stack>.md` § Related agents names
the three dev agents as the consumers of `missing-testids.md`; the three `mobile-screen-explorer` line-10
corrections per §8.5; `qa/_shared/security-testing/{mobile-app-scan,mobile-runtime-testing}/SKILL.md`
peer lines name the three dev agents as where fixes go.

**Documentation (G1).** `CLAUDE.md` § Repository map gets a `mobile/` row and `mobile/` leaves the
under-construction line; `docs/skills-catalog.md` gets its scope paragraph updated, three rows in the
slash-command surface table (the CLAUDE.md "93-command" count is recomputed, not guessed), and a
`## Mobile dev catalog` section; `README.md` gets its layout line and status-table row.

## 10. Authoring rules — every skill task

1. **Shape.** `.skill-template/` sections (When to use / When NOT / inputs / procedure / output /
   example); the stack's fe-react or be-* sibling is the voice pattern. A version-lane table near the top
   keyed to §4. Routing clauses name siblings by frontmatter name.
2. **Budgets** (`tools/token-audit.py` enforces them at G1): description **≤ 500 characters**, starting
   "Use when…" with triggers and a "Do NOT use for…" clause; SKILL.md body **≤ 16,000 characters — aim
   for 14,000** and move per-tool, per-lane or per-path detail into `references/` from the start. Count
   your own files with `wc -m` as you go — counting what you wrote is not a gate.
3. **Research first, §4 is the floor.** §4's facts are verified; anything else you state as a version
   or a date gets checked against the official source (docs.expo.dev, reactnative.dev,
   developer.apple.com, swift.org, developer.android.com, kotlinlang.org) before it is written, and the
   §4.5 items are re-checked before use. A fact that contradicts §4 is a dated `D<n>` in `## Decisions`,
   not a silent edit.
4. **The house rules bind the examples.** Code samples follow §5, CLAUDE.md § KISS (no unearned
   protocol / interface, no wrapper that only forwards) and `ep-code-comments` (no inline comments in
   samples). Test samples follow CLAUDE.md § Test code rules.
5. **Checklist rows.** Append your section's rows per §8.3 in the same task. A skill with no audit rows
   is unfinished.
6. **Corpus.** Any design fact (palette, type, spacing, motion preset, platform convention) cites a
   `design/ui-ux-pro-max` query with `--stack react-native|swiftui|jetpack-compose`; where the corpus and
   a skill disagree, the corpus wins.
7. **No vendored tree is edited** (`mobile/react-native/vendor/**`); skills point into it by exact
   filename.
8. **Unattended-session shell limits** (learned in plan 001): no brace expansion, no `$VAR` expansion,
   no `.sh` files, nothing written outside the worktree (not even `/tmp`). Scratch work goes in an
   untracked folder inside the worktree, deleted before committing.

## 11. The gate (G1 only)

Run in this order from the repo root, and fix what fails — a failure may belong to any task above G1.

1. `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` exits 0.
2. The library check below prints `OK` and exits 0.
3. `python3 tools/token-audit.py`: nothing under either description heading; the body and file
   violation counts stay **109 and 51** (the 2026-10-10 baseline) — no listed path starts with `mobile/`
   or `auth/auth0-react-native`, `auth/auth0-ios`, `auth/auth0-android`. The script exits non-zero while
   the old violations remain; read the counts, not the exit code.

Save the script as `scratch/library-check.py` inside the worktree (untracked; delete before
committing) and run `python3 scratch/library-check.py`. It is plan 001's §7 check with the mobile scope,
the `mobile` name prefix, the stale-path check and the mobile structure check added.

```python
import json, os, re, sys

SCOPE = ("qa frontend/blazor frontend/react design backend observability data devops security "
         "business-analysis training-data tooling engineering-practices auth/_shared "
         "auth/auth0-blazor auth/auth0-react auth/auth0-react-native auth/auth0-ios auth/auth0-android "
         "mobile .skill-template").split()
EXCL = re.compile(r'/ui-ux-pro-max/(data|scripts)/|/vendor/')
ALLOW = {"data-testid", "data-test", "data-theme", "data-table", "data-bs-target", "data-enhance",
         "data-provider-thread-count", "data-access", "data-density", "mobile-first"}
LINK_EXAMPLES = re.compile(r'screen-map-template\.md$|ba-project-memory/SKILL\.md$|business-documentation/SKILL\.md$')
GATE_LINE = "prompt block's `Gate:` line"
CHECKS = {
    "removed name": r"ep-(test-driven-development|worktrees|finish-branch|delegate-to-subagents|requesting-code-review|receiving-code-review|executing-plans)|/dev-build|Task tool|TaskCreate|TaskUpdate|TodoWrite",
    "dated emphasis": r"Iron Law|Violating the letter|HARD-GATE|REQUIRED SUB-SKILL|Announce at start|[Uu]ltrathink|YOU MUST|your human partner",
    "branch/worktree": r"git worktree add|git checkout -b|EnterWorktree|[Ww]ork on a branch",
    "stale RN path": r"frontend/react-native|fe-react-native",
}
STACKS = {"react-native": 23, "ios": 23, "android": 24}
FRAGMENTS = {"security": "K", "store-compliance": "L", "release": "T", "observability": "U",
             "in-app-purchases": "X"}

fail = []
market = json.load(open(".claude-plugin/marketplace.json"))
for plugin in market["plugins"]:
    for kind in ("skills", "commands", "agents"):
        for path in plugin.get(kind, []):
            if not os.path.exists(path):
                fail.append(f"marketplace {plugin['name']}: missing {path}")
names = {p["name"] for p in market["plugins"]}
for stack in STACKS:
    if f"mobile-{stack}" not in names:
        fail.append(f"marketplace: no mobile-{stack} plugin")

defined = set()
for root, dirs, files in os.walk("."):
    if "/.git" in root:
        continue
    defined.update(dirs)
    for f in files:
        if not f.endswith(".md"):
            continue
        path = os.path.join(root, f)
        if "/commands/" in path:
            defined.add(f[:-3])
        if f == "SKILL.md" or "/agents/" in path:
            m = re.search(r"^name:\s*(\S+)", open(path, errors="ignore").read(), re.M)
            if m:
                defined.add(m.group(1))

name_token = re.compile(r"`((?:ep|qa|be|fe|design|data|ba|tool|devops|secgov|pentest|purpleteam|observability|auth|td|dev|mobile)-[a-z0-9-]+)`")
md_link = re.compile(r"\]\((?!https?:|mailto:|#)([^)\s]+?\.md)(?:#[^)]*)?\)")
for top in SCOPE:
    for root, _, files in os.walk(top):
        for f in files:
            path = os.path.join(root, f)
            if not f.endswith(".md") or EXCL.search(path):
                continue
            text = open(path, errors="ignore").read()
            for label, pattern in CHECKS.items():
                for m in re.finditer(pattern, text):
                    fail.append(f"{label}: {path}: {m.group(0)}")
            for m in name_token.finditer(text):
                if m.group(1) not in defined and m.group(1) not in ALLOW:
                    fail.append(f"unresolved name: {path}: {m.group(1)}")
            for m in md_link.finditer(text):
                target = os.path.normpath(os.path.join(root, m.group(1)))
                if not os.path.exists(target) and not LINK_EXAMPLES.search(path):
                    fail.append(f"broken link: {path}: {m.group(1)}")
            if "/agents/" in path and GATE_LINE not in text:
                fail.append(f"agent without the Gate line: {path}")

for stack, count in STACKS.items():
    base = os.path.join("mobile", stack, "skills")
    folders = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    if len(folders) != count:
        fail.append(f"{base}: {len(folders)} skill folders, expected {count}")
    for d in folders:
        skill = os.path.join(base, d, "SKILL.md")
        if not os.path.exists(skill):
            fail.append(f"missing {skill}")
            continue
        m = re.search(r"^name:\s*(\S+)", open(skill).read(), re.M)
        if not m or m.group(1) != f"mobile-{stack}-{d}":
            fail.append(f"{skill}: name is {m.group(1) if m else None}, expected mobile-{stack}-{d}")
    checklist = open(os.path.join(base, "standards-audit", "references", "conformance-checklist.md")).read()
    letters = "ABCDEFGHIJMNOPQRSV" + ("W" if stack == "android" else "")
    for letter in letters:
        if not re.search(rf"^\| {letter}\d+ \|", checklist, re.M):
            fail.append(f"{stack} checklist: section {letter} has no rows")
    agent = os.path.join("mobile", stack, "agents", f"mobile-{stack}.md")
    if not os.path.exists(agent) or len(open(agent, encoding="utf-8").read()) > 14000:
        fail.append(f"{agent}: missing or over 14,000 characters")
for d, letter in FRAGMENTS.items():
    fragment = os.path.join("mobile", "_shared", d, "references", "audit-checks.md")
    if not os.path.exists(fragment):
        fail.append(f"missing {fragment}")
    elif not re.search(rf"^\| {letter}\d+ \|", open(fragment).read(), re.M):
        fail.append(f"{fragment}: no {letter} rows")

print("\n".join(fail) or "OK")
sys.exit(1 if fail else 0)
```

`mobile-first` is in `ALLOW` because `design/ui-ux-pro-max/references/quick-reference.md` uses it as
a design term, not a name (the only hit when this script was dry-run on 2026-10-10, besides the two
stale paths C1 removes). Any other entry added to `ALLOW` or `LINK_EXAMPLES` is justified in G1's
`As built` note. These three steps are
also how to re-check the library later.

## Decisions

**D1 — Three plugins in one `mobile/` domain.** Answered by the user on 2026-10-10. It keeps the
library's one-plugin-per-stack rule and keeps each install's always-on description cost near
fe-react's (~55 skills). Cost: the shared layer is bundled three times, and a team doing RN plus native
modules installs one plugin that borrows two native skills (D6).

| Option | Verdict | Why |
|---|---|---|
| Three plugins, one `mobile/` domain | **chosen** | Stack-first; lean installs; shared layer written once |
| One `mobile` plugin, three agents | rejected | ~60 skill descriptions in every session; breaks one plugin per stack |
| RN stays `frontend/react-native` as `fe-react-native`, native plugins in `mobile/` | rejected | Splits mobile across two domains; the shared layer would have no single home |

**D2 — The July RN drafts are moved and rewritten, not discarded; `PLAN.md` and `HANDOFF.md` are
deleted.** The five drafts are sound content on a one-SDK-stale lane; the two companion files break the
plan format (no companion files, no "nodes"). §6.5 carries the one table worth keeping. Cost: R1 rewrites
rather than authors, and the drafts' 1,000-character descriptions must shrink to 500.

**D3 — Skill names are `mobile-<stack>-<folder>`, a new `mobile` prefix.** Matches the plugin and agent
names, so a skill's owner is readable from its name. Cost: long names
(`mobile-react-native-offline-and-storage`); CONTRIBUTING's prefix list and the library check's name
regex both change (C1, §11).

**D4 — One common skill spine, identical folder names and audit letters on all three stacks; extras
only where a platform has a concept the others lack** (RN `native-modules`, `component-library`; iOS
`uikit`, `system-integration`; Android `views-interop`, `system-integration`, `kotlin-multiplatform`).
Audits then compare section by section, and a prompt for one stack transfers to the next. Cost: a few
folders are thin on one platform. The fe-react names are kept where the concept is the same; the
native stacks use `unit-testing` (the be-* name) and RN keeps `component-testing` (the fe-react name).

**D5 — Cross-stack rules live once, in `mobile/_shared/`**, each skill with per-stack references and an
`audit-checks.md` fragment that the three checklists include. Cost: a stack-specific nuance of a shared
rule lives in a reference file, not in the stack folder.

**D6 — `mobile-react-native` borrows exactly two native skills: `mobile-ios-basics` and
`mobile-android-basics`**, for Expo Modules and config plugins. That is why N1 writes both before any RN
task. Nothing else crosses stacks.

**D7 — E2E stays with `qa-mobile-<stack>`; this plan feeds both of its lanes and authors neither**
(revised 2026-10-10 on the user's answer, O6). The lanes are Appium on every stack and Maestro in
`qa-mobile-typescript` for Expo projects — plan 003 moves Appium to 3 and adds the Maestro skill (its
X1, D22, O8). The dev plugins own unit, component and snapshot tests; they give both lanes one set of
test ids (§8.5) and, on Expo, an EAS Workflows job that runs the Maestro flows (`mobile-shared-release`,
`references/eas.md`). Cost: an Expo team gets Maestro only once plan 003's X1 lands; until then the
EAS job has no flows to run, and S2 says so rather than shipping an empty job as working.

**D8 — The test id is never the accessibility label** (§8.5). Overloading `accessibilityLabel` /
`contentDescription` as an id breaks VoiceOver and TalkBack for real users.

**D9 — Version lanes per §4: Expo SDK 57 primary (correcting July's 56), SDK 58 promoted the day it
ships stable; iOS deployment target 17 by default; Android target 36 / compile 37 / min 24.** Cost: an
SDK 58 release mid-plan makes R-task text one SDK behind until someone runs the `migration` lane on the
skills — each R task writes the 58 deltas as `[SDK58]` rows now so the switch is an edit, not a rewrite.

**D10 — The design layer is bundled minus its web-only pieces** (`ui-code-audit` is the Vercel Web
Interface Guidelines, `landing-patterns` is marketing pages, the `design-auditor` agent captures with
Playwright). Visual self-critique uses simulator / emulator screenshots read back as images. Cost: no
one-call whole-app design audit for mobile; `design/ux-review` on screenshots covers the review.

**D11 — The planning lane gains a `mobile` stack token** ("the native or React Native client app");
`fe` stays "the web client". A plan that builds an API, a web app and a mobile app gets three lanes
with three agents. Cost: edits to plan-format, delivery-plan and solution-planner (W1). The user's
global `~/.claude/CLAUDE.md` gained the same token on 2026-10-10 (O5).

**D12 — Flutter is a fourth plugin, in its own plan after this one (the user chose it, O4); KMP is a lane of
`mobile-android`; Capacitor, .NET MAUI and the rest are not planned** — evidence in §3.

| Option | Verdict | Why |
|---|---|---|
| Flutter as plugin 4, its own plan | **chosen (O4)** | #1–#2 on every measure; Dart / pub fit no existing plugin; reuses `mobile/_shared` |
| Flutter inside this plan | rejected | Adds ~6 sessions to a 23-task plan before RN, iOS and Android are proven |
| KMP as its own plugin | rejected | Same language, Gradle and Jetpack libraries as Android; usually shared logic under native UI |
| .NET MAUI plugin | deferred | 3.1% usage, .NET 10 regressions; revisit after .NET 11 GA |

**D13 — The audit checklists are built incrementally:** every skill task appends its own rows; each
stack's last task writes only the audit `SKILL.md`. The author of a rule is the best author of its
check, and nothing re-reads 23 skills. Cost: row quality varies by task; the G1 check fails any section
left without rows.

**D14 — Apple's Xcode 27 agent skills, `xcrun mcp-server` and the Android CLI are tools the user may
run; no house skill depends on or wraps them.** They change on Apple's and Google's cadence, not the
library's. Cost: some overlap with Apple's SwiftUI Specialist and modernization skills.

**D15 — The plan gates once, in G1** (cost stated in the header).

**D16 — Every mobile agent fits the 14,000-character agent budget.** fe-react's agent (29,289) is the
content pattern only. Routing stays in the agent; procedure stays in the skills.

**D17 — C1 repointed more than the plan listed (2026-10-11).** The plan said the vendor `SKILL.md` clause
names `fe-react-native`; it names the paths `frontend/react-native/skills/{performance,motion,ui-conventions,navigation,reference}`.
Reading A: change only the prefix. Reading B (taken): also rename the folders to §6.2's names
(`animation`, `ui-components`, `basics`) so the clause resolves once the skills exist. Also repointed, to
satisfy the deliverable grep: `docs/plans/003-qa-playwright-appium-upgrade.md` (O2), the F8 row of
`docs/plans/backend-PLAN.md`, `docs/plans/frontend-PLAN.md` F10 and Phase 5 lines, the `README.md`
status-table `frontend` row, and `docs/plans/CONFORMANCE-AUDIT-PLAN.md` item 7.

**D18 — React Native purchase libraries changed hands (S3, 2026-10-11).** The plan left the RN lane as "RevenueCat / `expo-iap` / `react-native-iap` — research which is current". Reading A: recommend one. Reading B (taken): `react-native-purchases` (RevenueCat, 10.12.2) is the default when there is no purchase backend; `expo-iap` 6.0.0 and `react-native-iap` 17.0.0 are the own-backend lanes, both published from the `hyodotdev/openiap` monorepo on 2026-10-09 (their previous repos are archived), so `references/react-native.md` pins exact versions, records the check date and tells the reader to read installed types instead of copying hook names. Also recorded: Play Billing's rule is "that major **or later**" — 8 passes today, 9 is required from 2027-08-31, and X15 reports that date.

**D19 — R1 mapped the drafts' stale sibling names to §6.2 (2026-10-11).** The July drafts linked to skills the 23-folder set does not have (`generator`, `reviewer`, `data-access`, `offline-first`, `motion`, `testability`, `ui-conventions`, `responsive-design`, `project-scaffold`, `reference`), to `design/frontend-design` (no such folder) and to `auth/auth0-react`. Reading A: leave them until each target skill lands. Reading B (taken): rewrite every link to the §6.2 folder that owns the topic (`ui-components`, `networking`, `offline-and-storage`, `animation`, `test-ids`, `code-review`, `basics`, `project-setup`), `design/visual-identity` / `design/theme-presets` / `design/design-tokens`, and `auth0-react-native`, so the links resolve once R2–R5 land. Also taken: Zustand `persist` and the persistence table default to MMKV 4 (AsyncStorage is legacy only), and the default component-library option is "StyleSheet + Expo UI" rather than "none".

**D20 — The QA explorer's test-id claim is wrong, and its Android locator rung does not reach a `testID` (R3, 2026-10-10).** §8.5 asked R3 to verify "Android `content-desc` maps to an RN `testID`" (`qa/*/skills/mobile-screen-explorer/SKILL.md:10`). Reading A (the QA text): `content-desc` / `name` both carry the `testID`, so `$('~…')` is the single cross-platform rung. Reading B (verified from RN source, `BaseViewManager.setTestId` + `ReactAccessibilityDelegate`): on Android `testID` becomes the bare `resource-id`, and `content-desc` carries `accessibilityLabel`; on iOS `testID` is `accessibilityIdentifier` (the Appium `~`). Built as B in `mobile-react-native-test-ids`. Cost: W1 changes more than the mapping sentence — the locator ladder must say `~` on iOS and `id=` / `resourceId` on Android, and the explorer's suggested kebab-case ids (`login-email`) conflict with this library's PascalCase dot-separated rule, which the dev skill resolves by treating the suggestion as a hint. The explorers are 600 characters from budget, so W1 rewrites sentences in place rather than adding any.

**D21 — `architecture` is MV by default, against the swiftui corpus rows 48–49 (I1, 2026-10-11).** `design/ui-ux-pro-max/data/stacks/swiftui.csv` rows 48 "Use MVVM pattern" and 49 "Keep views dumb" say a view model per screen. Reading A (corpus wins, §10.6): MVVM default. Reading B (taken, §6.3 and I1): `@Observable` models and services, with a view model only where logic needs a test apart from the view — the corpus rows pre-date `@Observable` and describe the `ObservableObject` era. Cost: the corpus and the skill disagree on this one row; `mobile-ios-architecture` says so, and an audit must not flag an MV codebase against corpus row 48. Also: Liquid Glass API names (`glassEffect`, `GlassEffectContainer`, `.buttonStyle(.glass)`) are iOS 26 names carried from prior knowledge, unconfirmed against an Apple page for the iOS 27 SDK (§4.5-style: re-check in I3/G1 if the SDK docs are reachable).

**D22 — I2's new iOS facts are unconfirmed against Apple pages (I2, 2026-10-11).** §10.3 says research first. Reading A: fetch developer.apple.com for each API before writing it. Reading B (taken): Apple's documentation renders client-side and the session had no page fetch that returned text (the same limit I1 hit, D21), so the skills state the long-standing API shapes from prior knowledge — UIKit Observation tracking (`updateProperties()`, iOS 26 default, `UIObservationTrackingEnabled` on iOS 18), the `UIApplicationSceneManifest` keys, SwiftData `VersionedSchema` / `SchemaMigrationPlan` / `@ModelActor`, `CLLocationUpdate.liveUpdates()`, `DataScannerViewController`, the `NS…UsageDescription` key list. `uikit/references/uiscene-migration.md` tells the reader to read TN3187 against the installed SDK before editing; `device-features/references/permissions.md` says to confirm a rarely used key. Cost: G1 (or any session with a working page fetch) re-checks these; until then an audit row built on them is a finding to read, not a certainty.

**D23 — I3's new iOS facts are unconfirmed against Apple pages (I3, 2026-10-11).** §10.3 says research first. Reading A: fetch developer.apple.com for each API before writing it. Reading B (taken): the session ran with no Apple page fetch (the limit I1 and I2 hit, D21, D22), so the skills state the long-standing API shapes from prior knowledge — `UNUserNotificationCenter` and APNs headers, the AASA `components` format, `BGTaskScheduler` and background `URLSession`, ActivityKit and its 4 KB / 8-hour limits, WidgetKit timelines, App Intents, String Catalogs and `FormatStyle`, `accessibilityIdentifier` grouping behaviour. The least settled are `BGContinuedProcessingTask` (iOS 26), widget push updates (iOS 26) and the `.accessibilityIdentifier`-on-a-container propagation; each is hedged in its skill and `system-integration` says to read the installed SDK. Guideline 4.5.3 for Live Activities follows the task prompt (and 4.5.4 for push, from memory); S1's fragments carry no 4.5.3 row, so J21 is this task's own. Cost: G1 (or any session with a working fetch) re-checks these; until then a row built on them is a finding to read, not a certainty.

**D24 — I4's new iOS facts are unconfirmed against Apple pages (I4, 2026-10-11).** §10.3 says research first. Reading A: fetch developer.apple.com / swift.org for each API before writing it. Reading B (taken): Apple's pages render client-side and the session's search returned only third-party summaries, so the skills state them with that caveat inline — the Swift-first MetricKit `MetricManager` (async `metricReports` / `diagnosticReports`; sources disagree on whether `MXMetricManager` is formally *deprecated* or *no longer recommended for new adoption* — the plan's "deprecated at 27.2" is kept and both branches are version-tagged), Swift Testing exit tests (Swift 6.2+, not on iOS targets) and the possible Xcode 27 XCTest interop modes (stated as unconfirmed, nothing relies on them), the Apple ~400 ms first-frame launch guidance (a starting target), the Accessibility Nutrition Label option names. G1's pass should confirm them against the Xcode 27 release notes.

**D25 — I5's migration facts are unconfirmed against Apple / swift.org pages (I5, 2026-10-11).** §10.3 says research first. Reading A: fetch swift.org/migration, Apple's TN3187, the Xcode 27 release notes and blog.cocoapods.org for each claim before writing it. Reading B (taken): this session ran no web search or fetch, so the references state the facts from prior knowledge and tell the reader to re-read the source before a run — `swift package migrate` (SwiftPM 6.2+; flag names left to `--help`), the `-disable-dynamic-actor-isolation` downgrade flag (named as reported in the SE-0423 discussion, "confirm against the installed compiler"), the dynamic-isolation crash signatures, `SWIFT_STRICT_CONCURRENCY = complete`, `Observations` (SE-0475, iOS 26), the CocoaPods trunk freeze mechanics (read-only: existing versions keep resolving), and the Xcode 27 SDK's mandatory changes beyond §4.2's list. Nothing relies on a flag name working. G1's pass should confirm them.

**D26 — `architecture` forbids ViewModel-to-UI events, against the jetpack-compose corpus row 16 (A1, 2026-10-10).** `design/ui-ux-pro-max/data/stacks/jetpack-compose.csv` row 16 ("Event-based navigation") says the ViewModel emits navigation events through a `Channel` + `receiveAsFlow()`. CLAUDE.md § Design facts says the corpus wins on a design fact; §4.3 and §5 (Google's recommendations of 2026-10-05, the Mobile code rules) say one `uiState` and **no ViewModel-to-UI events**. Reading A: follow the corpus row and allow a `Channel`. Reading B (taken): a ViewModel-to-UI event is an architecture rule, not a design fact — the outcome is a field in `uiState` that the UI consumes and the ViewModel clears, and `mobile-android-architecture` says so by name. Cost: one more field per screen with a one-off outcome; the corpus row is not edited (vendored), and `mobile-android-code-review` (A6) must not flag the Channel pattern's absence as a corpus violation.

**D27 — A1's new Android facts are partly unconfirmed against official pages (A1, 2026-10-10).** §10.3 says research first. Reading A: fetch every artifact version and API signature before writing it. Reading B (taken): the Navigation 3 overview page carries no coordinates or signatures, so `NavDisplay` / `rememberNavBackStack` / `entryProvider` / entry-decorator names, the `ListDetailSceneStrategy` and `material3-adaptive-navigation3` artifact, `MaterialExpressiveTheme` / `MotionScheme.expressive()` and the material3 1.5 status, KSP's version-to-Kotlin pairing, ktlint 1.8's `ktlint_official` / Composable-naming settings, the foojay resolver version and the compose-lints ruleset names are written from recall. The skills tell the reader to confirm artifacts against the release pages; no version number outside §4.3 is pinned as fact (the catalog sample uses a placeholder for KSP). Cost: A2–A6 inherit the same caveat; G1's review should re-check these items.

**D28 — A2's new Android facts are partly unconfirmed against official pages (A2, 2026-10-10).** §10.3 says research first. Reading A: fetch every artifact version and API signature before writing it. Reading B (taken): confirm the facts the skills could mislead on (Room 3 package, KSP-only, driver requirement, removed integrations, builder call, `security-crypto` deprecation) and write the rest from the plan's §4.3 floor, flagged. Unconfirmed: the Room 3 `Migration.migrate(SQLiteConnection)` signature, `BundledSQLiteDriver` / `setQueryCoroutineContext` spellings and the Room 3 migration-test helper name (`references/room-migrations.md` says to re-check them); whether Retrofit 3 sits on OkHttp 4.12 or 5.x (the changelog says 4.12, a migration guide says 5.x — `networking` tells the reader to check `./gradlew :app:dependencies`); the Retrofit first-party `converter-kotlinx-serialization` coordinates; the `TextFieldState` text-field API and `ContentType` semantics availability per material3 / ui version (`forms` tells the reader to re-check the release notes); the CameraX, Credential Manager and fused-location call shapes (written from the plan's names, not a fetched page). Cost: G1 or a later pass re-checks these against developer.android.com; each is marked in the text where it carries risk.

**D29 — Android push registration teaches the Firebase Installation ID, not the token (A3, 2026-10-10).** §4.5 left "FCM current API" unverified. Reading A (the plan's implicit one, the long-standing API): `onNewToken(token)` / `FirebaseMessaging.token` as primary. Reading B (built): Firebase's current get-started page calls the token path deprecated ("removed in a future release") and registers by FID — manifest `firebase_messaging_installation_id_enabled`, `onRegistered(installationId)`, `register()` when auto-init is off — so `mobile-android-notifications-and-links` teaches that as primary and `onNewToken` as the `[FCM-token]` lane for existing apps, never flagged. Costs: the BoM version and the HTTP v1 field that targets an FID were not on the pages read, so the skill says to read them before writing either as fact; `mobile-react-native-notifications-and-links` (R3) was written before this check and may still teach tokens — W1 or G1 should reconcile it. Also unconfirmed in A3 (stated as such in the skills, §10.3): Compose shared-element stability, `PredictiveBackHandler` naming, infinite animations at animator scale 0, `testTagsAsResourceId` in separate windows, Appium `id=` package autocompletion, the AGP 9 locale-filter DSL.

**D30 — Android quality-layer tool versions are not all confirmed (A4, 2026-10-10).** §4.3 names Robolectric 4.17; a search found only `4.17-beta-2` (Bazel registry), Turbine 1.2.0 (changelog, 2024-10-16) and Roborazzi 1.63.0 (listing, 2026-05-20), none from the vendors' release pages. Reading A (plan): 4.17 is current stable. Reading B (built): `mobile-android-unit-testing` keys every tool to "the project's catalog", marks Robolectric 4.17 stable status and the Turbine version as unconfirmed, and never raises a version. Costs: G1 or a later pass should confirm against the GitHub release pages. Compose UI test v2's dispatcher change, its package moves and the accessibility-check API were verified on developer.android.com; the R8 keep-rule semantics beyond the AGP 9.3 `keepRules` source set were not, and the skills say so.

**D31 — KMP and migration facts that §4.3 did not carry (A5, 2026-10-10).** §4.3 says "Swift export alpha in Kotlin 2.4" and names `com.android.kotlin.multiplatform.library` only through the task's traps. Reading A (plan): state them as listed. Reading B (built): the library plugin's block is **`android { }` inside `kotlin { }`** on AGP 8.12+ / 9 (`androidLibrary { }` is the older, deprecated spelling), the Android app must be its own `com.android.application` module (the multiplatform plugin may not sit beside `com.android.library` / `com.android.application` under built-in Kotlin), Kotlin/Native 2.4 raises the iOS minimum to 15, and `swiftPMDependencies` is new in 2.4 — all from the vendors' pages. Costs: SKIE's Kotlin 2.4 status, the Metro / Koin Compiler Plugin versions and Navigation 3 KMP availability stay unconfirmed and are written as "check before use"; G1 or a later pass re-checks them.

## Answered questions (2026-10-10)

**O1 — Packaging: one plugin or several?** Three plugins in one `mobile/` domain (the user; D1).
**O2 — Which other stacks are popular enough?** Flutter (full plugin, own plan); KMP (Android lane);
the rest deferred (research, §3; D12).
**O3 — Keep the July RN drafts?** Yes — moved and rewritten (D2).
**O4 — Flutter?** Yes: `mobile-flutter` is the next plan written once 002 is filed, reusing
`mobile/_shared` (the user). Its number comes from the high-water mark then — `003` already belongs to
the QA Playwright / Appium plan.
**O5 — `mobile` in the global task rule?** Yes (the user). Rules 1, 2 and 6 of `~/.claude/CLAUDE.md`
§ "How features are broken down into tasks" were updated on 2026-10-10; the library files follow in W1.
**O6 — Maestro?** Yes (the user). The lane is QA-owned and lives in plan 003 (X1 adds
`ui-test-author/maestro` to `qa-mobile-typescript`); this plan feeds it one set of test ids (§8.5) and
the EAS Workflows job (S2). See D7.

## Open questions

None — Q1–Q3 were answered on 2026-10-10 (O4–O6).

## 12. Tasks

Every task is `docs` on `general-purpose`: the deliverables are skill, agent and command files in this
library, written by one session that researches and writes. "CLAUDE.md files" in a budget means the
library `CLAUDE.md`, the user's global `~/.claude/CLAUDE.md` and the memory index (~13k together).
Execution shape: one operator runs the queue back to back, so the tasks are batched by file tree (D1's
stacks in turn) — `mobile-react-native` is usable from a checkout once R5 lands and installable once W1
lands; `mobile-ios` after I5 / W1; `mobile-android` after A6 / W1.

### C1 — the `mobile/` domain, the code rules, and the move

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile/react-native/skills/{basics,project-setup,architecture,component-library,styling}`
carry `mobile-react-native-*` names; the three checklist skeletons exist with every §8.2 section heading
and its owners (rows only in V); `CLAUDE.md` has `## Mobile code rules`; and
`grep -rn "frontend/react-native"` finds nothing outside `docs/plans/implemented/`, `docs/audits/` and
this plan.
**Depends on:** —
**Budget:** ~95k — CLAUDE.md files 13k; this plan §1, §2, §4 tables, §5, §8 ~16k; the five drafts'
frontmatter and cross-links ~8k; `frontend/react/skills/standards-audit/references/conformance-checklist.md`
header and section A as the skeleton pattern ~5k; edits to CLAUDE.md, CONTRIBUTING.md and seven pointer
files ~15k; three skeletons ~12k; greps ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `git mv frontend/react-native mobile/react-native`; then, in `mobile/react-native/skills/`,
  `git mv reference basics`, `git mv project-scaffold project-setup`, `git mv state-management architecture`.
  Set each of the five `name:` lines to `mobile-react-native-<folder>` and repoint the drafts'
  references to each other's old names. Bodies otherwise untouched — R1 rewrites them.
- `git rm mobile/react-native/PLAN.md mobile/react-native/HANDOFF.md` (D2; §6.5 keeps their one table).
- In `mobile/react-native/vendor/react-native-guidelines/SKILL.md`, repoint only the house-written
  "Do NOT use directly" routing clause (added 2026-07-12) from `fe-react-native` to `mobile-react-native`.
  Nothing else under `vendor/` changes.
- Write `mobile/{react-native,ios,android}/skills/standards-audit/references/conformance-checklist.md`
  per §8.3: the fe-react header adapted per stack (permanent ids, how to read a row, the `rg` recipe
  shape and globs, the lane tags), then every §8.2 section heading with its owning skills as relative
  links — A to V on every stack, W on Android only, X on all three — the fragment wording for K, L, T, U,
  X, and **V's rows** written now from CLAUDE.md § Comments and § Simplicity (at least six: inline
  comment, signature-restating doc comment, commented-out code / `TODO`, protocol or interface with one
  implementer, a wrapper that only forwards, configurability nothing uses).
- `CLAUDE.md`: § Stack defaults gains a **Mobile** line (React Native + Expo primary · Swift / SwiftUI ·
  Kotlin / Jetpack Compose, KMP lane) and the test-runner line gains Swift Testing, JUnit 4 + Robolectric,
  Jest + RNTL; § Version policy gains one bullet per §4.1–§4.3 table (primary / supported / floor); §5 of
  this plan goes in verbatim as `## Mobile code rules`, after § Frontend code rules (React); the
  under-construction line names `mobile/` in place of `frontend/react-native/`.
- `CONTRIBUTING.md` § Naming conventions: add `mobile` to the prefix list and `mobile-ios-navigation`
  to the stack-scoped examples.
- Repoint: `backend/node/skills/pattern-guide/SKILL.md:25` and `backend/node/skills/pattern-writer/SKILL.md:28`
  → `mobile/react-native` (the `mobile-react-native` agent); `README.md:215` → a `mobile/` line
  (react-native, ios, android, _shared — under construction); the `docs/skills-catalog.md` scope
  paragraph; `docs/plans/frontend-PLAN.md` Phase 5 and its two react-native notes, `docs/plans/backend-PLAN.md:52`
  and the `docs/plans/CONFORMANCE-AUDIT-PLAN.md` scope line → "superseded by
  `docs/plans/002-mobile-plugins.md`". Never edit `docs/plans/implemented/**` or `docs/audits/**`.
- **Not in C1:** any skill body (R1), the marketplace (W1), the catalog's mobile section (G1).

- **As built (2026-10-11):** the five drafts moved to `mobile/react-native/skills/{basics,project-setup,architecture,component-library,styling}` with `name: mobile-react-native-<folder>`; their cross-links point at each other's new names and `frontend/react-native/vendor` paths became `mobile/react-native/vendor`. `PLAN.md` and `HANDOFF.md` are removed. The vendor `SKILL.md` "Do NOT use directly" clause named paths, not `fe-react-native`, so its prefix and folder names were repointed to `mobile/react-native/skills/{performance,animation,ui-components,navigation,basics}` (D17). Three checklist skeletons exist at `mobile/{react-native,ios,android}/skills/standards-audit/references/conformance-checklist.md` — 23 / 23 / 24 sections, every owner a relative link, K, L, T, U, X carrying the fragment wording, V holding rows V1–V8 (`grep -n "^| V" <file>`). `CLAUDE.md` gained the Mobile stack line, the test-runner additions, three Version-policy bullets, `## Mobile code rules` (§5 verbatim, before `## Backend code rules`) and `mobile/` on the under-construction line; `CONTRIBUTING.md` lists `mobile` and `mobile-ios-navigation`. `grep -rIn "frontend/react-native"` outside this plan, `docs/plans/implemented/` and `docs/audits/` returns nothing. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint. Built but unverified: the relative links in the skeletons point at skills that later tasks write; the `rg` recipes in V1–V8 have not been run against a real project.

### S1 — shared: store compliance and mobile security

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-shared-store-compliance` (with `references/{apple,google-play,audit-checks}.md`)
and `mobile-shared-security` (with `references/{ios,android,react-native,audit-checks}.md`) exist;
every §4.4 row they own appears with its source and a re-verify date; the L and K fragments have rows.
**Depends on:** C1.
**Budget:** ~145k — CLAUDE.md files 13k; plan §4.4, §4.5, §5, §6.6, §8.3–§8.4, §10 ~14k;
`qa/_shared/security-testing/mobile-app-scan/SKILL.md` (the fence) ~6k and
`frontend/react/skills/accessibility/SKILL.md` (skill shape) ~5k; research — Required Reason reason
codes, Play's exact-alarm wording, the 16 KB page, MASWE ids, the Mobile Top 10 ~40k; writes: two
SKILL.md ~9k, five references ~25k, two fragments ~10k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `mobile/_shared/store-compliance/SKILL.md`: when to run it (before a release, on adding a permission,
  an SDK, accounts, tracking or purchases, near a store deadline); procedure — inventory what the app
  does, select the rules that apply, split "in the repo" from "in App Store Connect / Play Console only"
  (flagged as a likely mismatch, never passed); a dated rule table with `Source` and `Re-verify after`
  columns.
- `references/apple.md`: privacy manifest keys, Required Reason categories **with reason codes checked
  against Apple's current list**, listed third-party SDKs (manifest + signature), ATT and the iOS 27.2 EU
  prompt, 5.1.1(v) + Sign in with Apple token revocation, 2.5.2 / DPLA 3.3.1(B) for interpreted code
  and OTA, 3.1.1, 4.8, 5.1.2 AI consent, the age-rating questionnaire, Accessibility Nutrition Labels
  (voluntary), upload-SDK dates.
- `references/google-play.md`: target-API table, 16 KB (the official 2027-02-01 date, the conflicting
  forum dates recorded as such), Data safety, account deletion in-app and on the web, permission
  declarations (photo/video, all-files, exact alarms — re-verified, FGS types, full-screen intents),
  developer verification timeline, the 2027-01-27 deadlines.
- `mobile/_shared/security/SKILL.md`: MASVS 2.1 group by group → the dev-side rule → its MASWE id and
  MASTG test; the static-vs-dynamic boundary (§8.3 "requires dynamic test"); the Mobile Top 10 2024 map;
  the fence — scanning and attacking are `qa-security`'s (`mobile-app-scan`, `mobile-runtime-testing`).
  `references/ios.md` (ATS, Keychain accessibility classes, app-switcher snapshot, pasteboard, URL
  handlers), `android.md` (exported components, Network Security Config, `allowBackup` +
  `dataExtractionRules`, WebView, immutable `PendingIntent`, `FLAG_SECURE`, Keystore, the
  EncryptedSharedPreferences replacement, Play Integrity), `react-native.md` (bundle secrets and
  `EXPO_PUBLIC_*`, Hermes bytecode is not obfuscation, secure-store / keychain, WebView
  `originWhitelist`, `Linking` validation, pinning and RASP library maintenance checks).
- `references/audit-checks.md` for each, per §8.3: `| # | Check | Violation looks like | Find it with | Sev | Stacks |`
  (+ a `MASWE` column in K), rows `L1…` and `K1…`, every row's `Stacks` naming `rn`, `ios`, `android`.
- **Not in S1:** release signing (S2), IAP rules (S3), anything stack-local.

- **As built (2026-10-11):** `mobile/_shared/store-compliance/` (`SKILL.md` 11.5k chars; `references/{apple,google-play,audit-checks}.md`; rows `L1…L26`, five marked console-only) and `mobile/_shared/security/` (`SKILL.md` 12.6k chars; `references/{ios,android,react-native,audit-checks}.md`; rows `K1…K27`, MASWE as a last column, every row's `Stacks` naming `rn`/`ios`/`android` as applies — `K27` is `rn` only, `K4` carries `android, rn`). Verified at source this session: 16 KB (developer.android.com page-sizes: updates blocked from 2027-02-01; other dates recorded as circulating), Play exact-alarm wording (`USE_EXACT_ALARM` restricted + declaration, `SCHEDULE_EXACT_ALARM` user-approved, not pre-granted since Android 13), MASVS 2.1 groups/controls, MASWE-0001…0078 ids, the MASTG test ids used. **Built but unverified:** Apple's Required Reason page is client-rendered and could not be fetched — `CA92.1`, `1C8F.1`, `C56D.1`, `AC6B.1`, `C617.1`, `35F9.1`, `E174.1` were confirmed from a Microsoft Learn page quoting Apple's table; `3B52.1`, `DDA9.1`, `0A2A.1`, `8FFB.1`, `3D61.1`, `85F4.1`, `7D9E.1`, `B728.1`, `3EC4.1`, `54BD.1` are written from recall and flagged **unconfirmed** in `apple.md` §2; the iOS 27.2 EU ATT alternative API is flagged unconfirmed (`apple.md` §5); MASVS control one-line statements and the RESILIENCE-1…4 naming were not re-read; the MASTG ids come from the tests index and each MASWE ↔ test pairing is the author's mapping. The `rg` recipes in `L*` / `K*` have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### S2 — shared: release and observability

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-shared-release` (with `references/{eas,fastlane,xcode-cloud,gradle-play,audit-checks}.md`)
and `mobile-shared-observability` (with `references/{react-native,ios,android,audit-checks}.md`) exist;
the T and U fragments have rows.
**Depends on:** C1.
**Budget:** ~140k — CLAUDE.md files 13k; plan §4.4, §6.6, §8.3, §10 ~10k; `devops/github-actions/SKILL.md`
head (the fence) ~4k, `observability/logs-traces-setup/SKILL.md` ~6k; research — EAS credentials and
`runtimeVersion`, fastlane `match` + App Store Connect API keys, Xcode Cloud, Gradle Play Publisher,
OTel Swift / Android, `expo-observe`, Embrace, Faro RN, Sentry, Crashlytics ~40k; writes: two SKILL.md
~9k, seven references ~28k, two fragments ~8k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `mobile/_shared/release/SKILL.md`: version + monotonic build number, signing with nothing in the repo,
  pinned runner image **and** Xcode, TestFlight / Play tracks, phased and staged rollout with a halt
  path, OTA rules, symbol upload. The fence: pipeline YAML is `devops-engineer`'s, CI test wiring is
  `qa-cicd-<stack>`'s. One reference per tool; `eas.md` carries `runtimeVersion` (`fingerprint`),
  update code signing, "never ship a native change over the air", and the EAS Workflows E2E job — a
  simulator / emulator build, then a `type: maestro` job running the project's `.maestro/` flows. The
  flows are `qa-mobile-typescript`'s Maestro lane (plan 003); a project with no flows gets no E2E job,
  never an empty one (D7).
- `mobile/_shared/observability/SKILL.md`: one crash reporter, the §6.6 pipeline, on-device batching
  and sampling, the resource attributes (`service.name`, `service.version`, `os.*`,
  `device.model.identifier`, `session.id`), PII scrubbing, the public ingest gateway (no backend
  credential in the app). Per-stack references with §4.4's maturity facts; the Collector and backends
  hand off to the `observability-engineer-<stack>` agents.
- Fragments: rows `T1…` and `U1…` per §8.3.
- **Not in S2:** in-app purchases and auth (S3).
- **As built (2026-10-11):** `mobile/_shared/release/` (`SKILL.md` 9.5k chars; `references/{eas,fastlane,xcode-cloud,gradle-play,audit-checks}.md`; rows `T1…T19`) and `mobile/_shared/observability/` (`SKILL.md` 7.6k chars; `references/{react-native,ios,android,audit-checks}.md`; rows `U1…U20`); every row's `Stacks` names `rn`/`ios`/`android` as applies. Verified at source this session: the EAS Workflows E2E shape (`type: build` + `type: maestro`, `needs`, `build_id`, `flow_path`; the simulator / emulator setting lives in the `eas.json` profile, not the workflow), the `fingerprint` runtime-version policy, `updates.codeSigningCertificate`. OTel Android maturity is written as the split (agent API stable, instrumentations alpha) with the conflicting `1.7.0` / `1.7.0-alpha` BOM labelling recorded. **Built but unverified:** `npx expo-updates fingerprint:generate` (subcommand unconfirmed, flagged in `eas.md`); `expo-observe`'s current status; iOS phased-release percentages and 30-day pause, Play staged-rollout steps and `versionCode` ceiling, Xcode Cloud quota, Gradle Play Publisher DSL, Timber (written from recall); Apple 2.5.2 / DPLA 3.3.1(B) and Play device-and-network-abuse wording were not re-read this session; `GitHub macos-14` removal 2026-11-02 is taken from §4.4. The `rg` recipes in `T*` / `U*` have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### S3 — shared: in-app purchases and native Auth0

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-shared-in-app-purchases` (with `references/{storekit,play-billing,react-native,audit-checks}.md`)
and `auth-auth0-react-native`, `auth-auth0-ios`, `auth-auth0-android` exist; the X fragment has rows.
**Depends on:** C1.
**Budget:** ~145k — CLAUDE.md files 13k; plan §6.6, §8.3, §10 ~8k; `auth/auth0-react/SKILL.md` ~6k
and `auth/_shared/auth0-concepts/SKILL.md` ~5k; research — StoreKit 2 + App Store Server API +
Server Notifications v2, the current Play Billing Library major + RTDN, RevenueCat / `expo-iap` /
`react-native-iap`, `react-native-auth0`, Auth0.swift, Auth0.Android ~45k; writes: IAP SKILL.md, three
references and the fragment ~20k, three auth SKILL.md ~15k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `mobile/_shared/in-app-purchases/SKILL.md` per §6.6: the server owns entitlements, the client never
  decides access from a local receipt alone; restore; refunds and revocations from server notifications;
  the store-policy boundary (3.1.1 and the US-storefront link exception, Play payments policy); cancel
  as easy as subscribe (`design-ethical-patterns`). Fragment rows `X1…`.
- `auth/auth0-react-native/SKILL.md`, `auth/auth0-ios/SKILL.md`, `auth/auth0-android/SKILL.md` in the
  `auth/auth0-react` shape, each routing concepts to `auth-auth0-concepts` / `auth-oidc-concepts`:
  Universal Login through the system browser with PKCE, the callback (universal link / App Link), the
  credentials manager on Keychain / Keystore, biometric unlock, refresh-token rotation, logout that
  clears the browser session. No embedded web view login.
- **Not in S3:** anything else stack-local.

- **As built (2026-10-11):** `mobile/_shared/in-app-purchases/` (`SKILL.md` 11.0k chars; `references/{storekit,play-billing,react-native,audit-checks}.md`; rows `X1…X22`, `Stacks` column set per row) and `auth/auth0-react-native/SKILL.md` (11.3k), `auth/auth0-ios/SKILL.md` (9.5k), `auth/auth0-android/SKILL.md` (9.5k), frontmatter names `auth-auth0-react-native` / `-ios` / `-android`. Verified at source this session (npm registry, GitHub API, official docs): Play Billing Library **9.1.0** current, **8+ required since 2026-08-31, 9+ from 2027-08-31** (developer.android.com deprecation FAQ, page dated 2026-09-09); `react-native-purchases` 10.12.2, `expo-iap` 6.0.0, `react-native-iap` 17.0.0 — the last two now live in `hyodotdev/openiap` with the old `hyochan/*` / `dooboolab-community/*` repos archived (D18); `react-native-auth0` 5.11.1, Auth0.swift 3.1.0, Auth0.Android 4.1.0. **Built but unverified:** App Store Server API endpoint paths, Server Notification type names and the `AppStore.showManageSubscriptions` / win-back iOS floors (written from recall, not re-read); Play RTDN type list and `purchases.subscriptionsv2` field names (recall); the Play management URL; the US-storefront link-out status (taken from press reports — the guideline text was **not** re-read, so the row is marked unsettled and X14 asks for a re-verify); `react-native-auth0` Android platform minimum (the README fetch said API 35 — not trusted, the skill tells the reader to read the installed README); `expo-iap` hook names (skill says to read installed types); Auth0.swift `canRenew()` / `hasValid()` / `WebAuthError.userCancelled` and the Auth0.Android passkey and `assetlinks` relation wording (recall). The `rg` recipes in `X*` have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### N1 — the Swift and Kotlin coding standards

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-ios-basics` and `mobile-android-basics` exist — each its stack's coding standard
per §5 and the first rows of §6.3 / §6.4 — with rows in sections A and B of their stack checklists.
**Depends on:** C1.
**Budget:** ~110k — CLAUDE.md files 13k; plan §4.2, §4.3, §5, §6.3–§6.4 first rows, §8.3, §10 ~12k;
`frontend/react/skills/basics/SKILL.md` (shape) ~5k; research — Swift API Design Guidelines, SE-0466 /
0461 / 0470 and the Swift 6.4 features, Kotlin coding conventions, Kotlin 2.4 features, coroutine and
Flow conventions ~35k; writes: two SKILL.md + one `references/concurrency.md` each ~22k; rows ~4k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `mobile/ios/skills/basics/SKILL.md`: naming, value vs reference types, optionals (no `!` outside
  tests), errors, access control, the §5 concurrency standard with its Swift 6.2 / 6.4 version tags,
  Observation, `os.Logger`. `references/concurrency.md` holds isolation, `Sendable`, task cancellation
  and the escape hatches with their justification rule.
- `mobile/android/skills/basics/SKILL.md`: Kotlin conventions, null safety (no `!!`), `val` and data
  classes, sealed interfaces for state, structured concurrency, injected dispatchers, `Flow` vs
  `StateFlow` vs `SharedFlow`, context parameters only when earned. `references/concurrency.md` holds
  scopes, cancellation, `runCatching` pitfalls with coroutines, and testing seams.
- Both are bundled into `mobile-react-native` (D6): write them so a native-module author with no app
  context can apply them.
- **Not in N1:** project setup and everything after it (I1, A1).

- **As built (2026-10-11):** `mobile/ios/skills/basics/SKILL.md` (15.6k chars) + `references/concurrency.md` (11.2k) and `mobile/android/skills/basics/SKILL.md` (14.0k) + `references/concurrency.md` (9.3k); frontmatter names `mobile-ios-basics` / `mobile-android-basics`. iOS checklist rows `A1…A5`, `B1…B16`; Android `A1…A4`, `B1…B16` (`grep -n "^| [AB][0-9]" <checklist>`). The iOS skill separates Swift language mode, default actor isolation (SE-0466) and Approachable Concurrency as three switches; both skills name app-level skills in prose only. Verified at source this session: Kotlin 2.4.0 stabilises context parameters (explicit context arguments still experimental, `-Xexplicit-context-arguments`), explicit backing fields stable, context receivers revoked (kotlinlang.org/docs/whatsnew24.html). **Built but unverified:** the iOS skill is 15.6k chars — over the 14k aim, under the 16k cap; build-setting names `SWIFT_DEFAULT_ACTOR_ISOLATION` / `SWIFT_APPROACHABLE_CONCURRENCY`, `SwiftSetting.defaultIsolation`, `Observations` (iOS 26+) and the Swift 6.4 features (`await` in `defer`, `weak let`, `~Sendable`, taken from §4.2 with no semantics beyond their names) were written from recall and not re-read at swift.org / developer.apple.com; SE-0430 `sending` and `Mutex` / `OSAllocatedUnfairLock` likewise; the `rg` recipes in A/B have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### R1 — React Native foundations: the five drafts rewritten, plus navigation

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-react-native-{basics,project-setup,architecture,component-library,styling}`
rewritten onto §4.1 (SDK 57 primary, SDK 58 deltas tagged `[SDK58]`) within the §10 budgets, and
`mobile-react-native-navigation` written; RN checklist sections A–F have rows.
**Depends on:** C1.
**Budget:** ~140k — CLAUDE.md files 13k; plan §4.1, §5, §6.2, §8.3, §10 ~14k; the five drafts and the
component-library references ~22k; `frontend/react/skills/routing/SKILL.md` ~5k; the vendor rules the
drafts cite ~6k; research — SDK 57 and 58 changelogs, Expo Router 57 docs, native tabs, protected routes
~30k; writes: six SKILL.md ~27k, `component-library/references/{expo-ui,unistyles}.md` ~6k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each rewrite per its §6.2 row: description ≤ 500 characters in the "Use when…" form, version table on
  §4.1, July's SDK 56-primary statements corrected, `[SDK58]` rows for what changes when 58 ships.
- `styling` absorbs responsive design (safe areas, `useWindowDimensions`, tablets, foldables).
- `component-library`: add `references/expo-ui.md` and `references/unistyles.md`; reconcile `none.md`
  with the StyleSheet + Expo UI default; mark NativeWind v5 as RC.
- `navigation` per §6.2, with the hard rule "no `@react-navigation/*` import in an Expo Router app" and
  its codemod.
- Rows: A (lane, SDK floor, New Arch, Hermes), B (strict TS, flat ESLint, `expo-doctor`, `EXPO_PUBLIC_`
  misuse), C, D (component-library authority), E, F.
- **Not in R1:** the feature-build skills (R2, R3).

- **As built (2026-10-11):** `mobile/react-native/skills/{basics,project-setup,architecture,component-library,styling,navigation}/SKILL.md` — bodies 9.7k / 8.6k / 9.3k / 7.5k / 12.7k / 10.8k chars, descriptions 485 / 494 / 462 / 496 / 474 / 478 chars (counted with `python3 -I`, no gate run); frontmatter names `mobile-react-native-<folder>`. `component-library/references/` gained `expo-ui.md` and `unistyles.md`, `none.md` was rewritten as "StyleSheet + your own atoms" with Expo UI in the default, and the four kit references were repointed (NativeWind 4.2 stable / v5 RC, Tamagui 3.0, gluestack v5, Paper 5.x). `styling` absorbed responsive design (no `responsive-design` folder). Checklist rows `A1…A7`, `B1…B13`, `C1…C10`, `D1…D10`, `E1…E13`, `F1…F15` (`grep -n "^| [A-F][0-9]" mobile/react-native/skills/standards-audit/references/conformance-checklist.md` → 64 rows). The drafts' links to skills that never got a folder (`generator`, `reviewer`, `data-access`, `offline-first`, `motion`, `testability`, `ui-conventions`, `responsive-design`, `project-scaffold`, `reference`) now name the §6.2 folders (D19). Verified at source this session (docs.expo.dev): native tabs import paths (`unstable-native-tabs` on SDK 55–57, `native-tabs` on 58), the compound `Trigger` / `Label` / `Icon` / `Badge` API, the 5-tab Android limit and the other limitations; `Stack.Protected` `guard`, with `redirectTo` available from SDK 58; Expo UI's `Host` rule and the `swift-ui` / `jetpack-compose` imports. **Built but unverified:** Expo UI component names and props beyond `Host` (the reference tells the reader to confirm them in the SDK 57 docs; the `Button label onPress testID` sample is not checked); Unistyles 3.5 setup (Babel plugin options, `StyleSheet.configure`, module augmentation) and gluestack v5's styling core and CLI (written from recall — the reference says to confirm at install); the NativeWind / Tamagui / Paper reference bodies were not re-read against current docs beyond the version lines; `sheetAllowedDetents`, `unstable_settings.anchor`, `+native-intent.tsx`, Android 16 ignoring orientation locks at ≥ 600 dp, and RN core `SafeAreaView` being deprecated are from recall; the codemod name is from §4.1. The `rg` recipes in A–F have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### R2 — React Native feature build: components, forms, networking, storage, native modules

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-react-native-{ui-components,forms,networking,offline-and-storage,native-modules}`
exist; RN checklist sections D, G, H, I, J have rows from them.
**Depends on:** N1 (the two native basics `native-modules` loads), S1 (secret storage rules).
**Budget:** ~150k — CLAUDE.md files 13k; plan §4.1, §5, §6.2, §6.5, §8.3, §10 ~14k;
`frontend/react/skills/{component-writer,forms,data-fetching}/SKILL.md` headings and rule lists ~12k;
vendor `list-performance-*`, `ui-*` rules ~6k; `mobile-ios-basics` / `mobile-android-basics` frontmatter
~2k; `mobile/_shared/security/references/react-native.md` ~4k; research — FlashList 2, Legend List 3,
keyboard handling, TanStack Query RN integration, MMKV 4, expo-sqlite / op-sqlite, Expo Modules API,
Nitro ~40k; writes: five SKILL.md ~23k + references ~8k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.2 row. `networking` carries the §6.5 timeout, retry and offline rules as the
  request-level half; `error-handling` (R4) owns the UI half.
- `offline-and-storage`: secrets only in `expo-secure-store`; MMKV 4's `createMMKV()`; WatermelonDB
  flagged stale; storage-full degradation handed to `error-handling`.
- `native-modules`: the decision ladder (an Expo SDK module → a maintained community module → Expo
  Modules API → Nitro / TurboModule in bare), config plugins for every native change, Expo UI; it loads
  `mobile-ios-basics` and `mobile-android-basics` for the Swift / Kotlin it writes.
- **Not in R2:** device features and links (R3).

- **As built (2026-10-11):** `mobile/react-native/skills/{ui-components,forms,networking,offline-and-storage,native-modules}/SKILL.md` — bodies 13.3k / 13.0k / 13.1k / 15.5k / 14.7k chars, descriptions all under 500 (counted with `wc -m`, no gate run); frontmatter names `mobile-react-native-<folder>`. References: `networking/references/request-policy.md` (AppError, ProblemDetails, `Retry-After` parse, single-flight refresh, timeout table, circuit) and `native-modules/references/expo-modules-api.md` (Swift / Kotlin / TS wrapper samples); `ui-components`, `forms` and `offline-and-storage` have none. Checklist rows appended: `D10…D19`, `G1…G10`, `H1…H15`, `I1…I13`, `J1…J13` (J holds only `native-modules` rows; R3 continues from `J14`) — `grep -n "^| [DGHIJ][0-9]" mobile/react-native/skills/standards-audit/references/conformance-checklist.md`. R1's note says `D1…D10` but the skeleton held `D1…D9` only, so R2's first row is `D10`. Verified at source this session (web search, secondary mirrors): MMKV 4 `createMMKV()` / `remove()` / Nitro dependency / RN ≥ 0.75; FlashList 2 removals (`estimatedItemSize`, `estimatedListSize`, `estimatedFirstItemOffset`, `onBlankArea`, `inverted` → `maintainVisibleContentPosition`, `masonry` prop); TanStack Query `onlineManager` / `focusManager` RN wiring. **Built but unverified:** Expo Modules API names (`AsyncFunction`, `Record`, `OnDestroy`, `requireOptionalNativeModule`, `expo-module.config.json` shape) and `create-expo-module --local` — written from recall plus a secondary mirror, the reference tells the reader to confirm at docs.expo.dev; `AbortSignal.timeout` / `.any` availability on Hermes V1 (the skill says detect first); `react-native-keyboard-controller` component names; `expo-sqlite` 18 async API names; `@tanstack/query-sync-storage-persister` with an MMKV adapter and `setMutationDefaults` / `scope` for ordered replay; `expo-secure-store` `keychainAccessible` constant names; Legend List 3.6 props; Nitro `nitrogen` / `nitro.json` workflow; `'use dom'` semantics; sibling skill names `mobile-ios-offline-and-storage` / `mobile-android-offline-and-storage` and `mobile-ios-unit-testing` / `mobile-android-unit-testing` (§6.3 / §6.4 names, not yet written). The `rg` recipes in D10–J13 have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### R3 — React Native device and platform: features, notifications and links, motion, languages, test ids

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-react-native-{device-features,notifications-and-links,animation,languages,test-ids}`
exist; RN checklist sections F, J, P, Q, R have rows from them; §8.5's RN mapping is answered in
`mobile-react-native-test-ids` with its source.
**Depends on:** S1 (permission declarations and link validation rules).
**Budget:** ~140k — CLAUDE.md files 13k; plan §4.1, §5, §6.2, §8.3, §8.5, §10 ~14k;
`frontend/react/skills/{animation,languages,test-ids}/SKILL.md` headings and rules ~12k; vendor
`animation-*` rules ~4k; `mobile/_shared/store-compliance/references/{apple,google-play}.md` permission
parts ~6k; research — `expo-notifications`, universal links / App Links in Expo Router, Reanimated 4,
Gesture Handler 2.32 vs 3, i18next vs Lingui on RN, RN `testID` platform mapping ~40k; writes: five
SKILL.md ~23k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.2 row. `device-features`: permission priming and the denied path as a hard rule.
- `animation`: Gesture Handler 2.32 on SDK 57 and 3.x on SDK 58 are different APIs — both lanes, tagged.
- `test-ids`: the §8.5 mapping verified against the current RN docs and written with its URL, plus
  which identifier Maestro's `id:` matches on each platform; the `missing-testids.md` hand-off; static
  ids for list rows; never `accessibilityLabel` as an id.
- **Not in R3:** quality layers (R4); the QA-side correction (W1).

- **As built (2026-10-10):** `mobile/react-native/skills/{device-features,notifications-and-links,animation,languages,test-ids}/SKILL.md` — bodies 13.8k / 12.1k / 13.2k / 11.9k / 14.6k chars, descriptions 486 / 451 / 471 / 464 / 438 (counted with `python3 -I`, no gate run); frontmatter names `mobile-react-native-<folder>`; no `references/` files. Checklist rows appended: `F15…F20`, `J14…J28`, `P1…P10`, `Q1…Q11`, `R1…R10` (`grep -n "^| [FJPQR][0-9]" mobile/react-native/skills/standards-audit/references/conformance-checklist.md`). R1's note says `F1…F15` but the skeleton held `F1…F14`, so R3's first F row is `F15`. **§8.5 answered** in `test-ids` § "How `testID` reaches the device", read from RN source on `main` and Maestro's docs / source: iOS `testID` → `accessibilityIdentifier` (`RCTViewComponentView.mm`); Android `testID` → `resource-id` (`BaseViewManager.setTestId` stores `R.id.react_test_id`; `ReactAccessibilityDelegate` sets `info.viewIdResourceName`), the **bare** string, not `<package>:id/…`; reactnative.dev/docs/view states **no** platform mapping. Maestro `id:` → iOS `accessibilityIdentifier` (docs.maestro.dev/platform-support/ios-uikit), Android `resource-id` (`Filters.idMatches` reads `attributes["resource-id"]`); `id`/`text` are case-insensitive regexes. **The QA explorer's claim is refuted** — Android `content-desc` is the `accessibilityLabel`, not the `testID` (D20). Verified at source this session: expo-notifications handler shape (`shouldShowBanner` / `shouldShowList`), channel-before-permission on Android 13+, `useLastNotificationResponse`, config-plugin options; Gesture Handler 3 upgrade-guide renames (`onStart`/`onEnd` → `onActivate`/`onDeactivate`, hooks, relation renames); Reanimated `ReduceMotion` enum and `useReducedMotion` semantics; expo-localization `supportedLocales` / `supportsRTL` / `forcesRTL` (the page documents RTL default-on from SDK 58); expo-image-picker, expo-location, expo-local-authentication, expo-background-task option names. **Built but unverified:** whether UiAutomator2's `id=` strategy prepends the app package to a bare `resource-id` (the skill says to read the page source and fall back to `resourceId(...)`); iOS XCUITest hiding the children of an `accessible` parent (written from experience); `scheduleOnRN` vs `runOnJS` naming per Reanimated / worklets version; Gesture Handler 3 `GestureHandlerRootView` / `runOnJS` replacements (not on the upgrade page); Lingui 6 and i18next 26 specifics (§4.1 versions only); `expo-background-fetch` deprecation; `+native-intent.tsx`, `pathPrefix` / `autoVerify` intent-filter shape and the AASA / `assetlinks.json` requirements (from recall); `LSApplicationQueriesSchemes` / `canOpenURL` deprecation (§4.2); the `rg` recipes in F15–R10 have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### R4 — React Native quality layers and component tests

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-react-native-{accessibility,performance,error-handling,component-testing}` exist,
`error-handling` with `references/{session-and-resume,writes-and-dependencies}.md` and every §6.5 row;
RN checklist sections M, N, O, S have rows.
**Depends on:** S2 (crash reporting hand-off), R2 (`networking`'s request-level rules).
**Budget:** ~150k — CLAUDE.md files 13k; plan §4.1, §5, §6.2, §6.5, §8.3, §10 ~14k;
`frontend/react/skills/error-handling/SKILL.md` + its two references ~16k (the rule source),
`frontend/react/skills/{component-testing,accessibility}/SKILL.md` ~10k; vendor `list-performance-*`
rules ~8k; research — RNTL 14, `jest-expo` 57, `@react-native/jest-preset`, `expo-observe`, RN
accessibility props ~30k; writes: four SKILL.md ~18k + two references ~10k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `error-handling`: every rule of the fe-react set with its §6.5 delta; OTA skew with one guarded
  `Updates.reloadAsync()`; the safe-area banner; the expo-router `ErrorBoundary` export.
- `component-testing`: RNTL 14's async API in every sample; the v13 → v14 codemod named; native modules
  faked at the boundary; plain Jest for non-rendering logic; E2E handed to `qa-mobile-typescript`
  (Appium, or its Maestro lane on Expo projects — plan 003).
- `performance`: the vendor list rules by filename; React Compiler's effect on manual memoization.
- **Not in R4:** migration, review, audit, agent (R5).
- **As built (2026-10-11):** `mobile/react-native/skills/{accessibility,performance,error-handling,component-testing}/SKILL.md` — bodies 13.4k / 14.2k / 15.7k / 14.0k chars (counted with `wc -m`, no gate run; `error-handling` is over the 14k aim, under the 16k cap — fe-react's 42.5k set was condensed, with OTA skew, the 401 ladder and app resume in `references/session-and-resume.md` (7.5k) and mutations, third parties and storage-full degradation in `references/writes-and-dependencies.md` (7.0k)); frontmatter names `mobile-react-native-<folder>`, descriptions all under 500. Every §6.5 row is covered (failure scope, safe-area banner, stale / pull-to-refresh, timeouts, ladder with biometric re-auth, OTA skew with one ref-guarded `Updates.reloadAsync()`, mutations, `Retry-After` / circuit by pointer to `networking`, banner cap and roll-up, third parties incl. a native module that fails to link, storage-full via a typed `StorageFullError` at the `offline-and-storage` boundary, app resume; multi-tab and hydration marked N/A). Checklist rows appended: `M1…M13`, `N1…N13`, `O1…O22`, `S1…S12` (`grep -n "^| [MNOS][0-9]" mobile/react-native/skills/standards-audit/references/conformance-checklist.md` → 60 rows). Verified at source this session: RNTL 14 (async `render` / `renderHook` / `rerender` / `unmount` / `fireEvent` / `act`; `test-renderer` replaces `react-test-renderer`; React 19+, RN 0.78+, Node `^22.13 || >=24`; codemods `rntl-v14-update-deps` and `rntl-v14-async-functions`; removed `update`, `UNSAFE_*`, `concurrentRoot`, `createNodeMock`), `expo-observe` (beta; `ObserveRoot`, `markInteractive`, `Observe.configure`; SDK 57 JS error reporting is preview, no native crashes), Expo Atlas (`EXPO_ATLAS=true npx expo export` then `npx expo-atlas .expo/atlas.jsonl`; `EXPO_UNSTABLE_ATLAS` is the older flag; experimental), `expo-updates` `useUpdates` / `checkForUpdateAsync` / `fetchUpdateAsync` / `reloadAsync`. **Built but unverified:** the RNTL 14 matcher registration path (`extend-expect`) and whether `userEvent` is exported from the package root — the skill says to confirm in the v14 docs; `jest-expo` 57 `transformIgnorePatterns` copy; the exact RN 0.86 `AccessibilityInfo.sendAccessibilityEvent` signature on a ref (written from recall); `aria-*` coverage of every state prop; `eslint-plugin-react-native-a11y` currency; `react-compiler-healthcheck`; Metro inline requires default; `requestIdleCallback` as the `InteractionManager` replacement; the `expo-router` `ErrorBoundary` prop names (`error`, `retry`). The `rg` recipes in `M*`–`S*` have not been run. Not run (Gate: none): `tools/token-audit.py`, §11's script, any lint.

### R5 — React Native migration, review, audit, agent and commands

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-react-native-{migration,code-review,standards-audit}` exist;
`mobile/react-native/agents/mobile-react-native.md` (≤ 14,000 characters, the template's Gate line
verbatim) and `mobile/react-native/commands/{mobile-react-native,mobile-react-native-audit}.md` exist; the
RN checklist ends with a section index.
**Depends on:** R1–R4 (every skill the agent routes to), S1–S3, N1.
**Budget:** ~140k — CLAUDE.md files 13k; plan §6.1–§6.2, §7, §8, §10 ~16k; `.skill-template/agent.md`
~6k; `frontend/react/agents/fe-react.md` ~8k; `backend/dotnet/skills/standards-audit/SKILL.md` ~5k and
`engineering-practices/standards-audit-engine/SKILL.md` ~6k; `frontend/react/skills/code-review/SKILL.md`
head ~5k and both fe-react commands ~2k; the RN checklist ~12k; the 22 RN skills' frontmatter ~6k;
research — Upgrade Helper, `install-expo-modules`, adopting prebuild, `expo-brownfield`, Callstack
brownfield ~20k; writes: migration SKILL.md + four references ~18k, code-review ~4k, standards-audit
~4k, agent ~4k, commands ~2k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `migration` per §6.2 — one SDK per change, never a version jump inside feature work.
- `code-review`: hostile review of a diff against the RN checklist and §5, plus the Step-5 screenshot
  pass (§7.2).
- `standards-audit` in the `be-dotnet-standards-audit` shape on the engine: the version gate keyed to
  §4.1, the applicability probes (Expo vs bare, IAP present, native code present), report path per §2.
- The agent per §7 and D16; its tools are `Read, Write, Edit, Bash, Glob, Grep, WebSearch`; its
  Related agents name `qa-mobile-typescript` for E2E in either lane (D7). The two
  commands in the fe-react commands' shape.
- **Not in R5:** marketplace wiring (W1).

**As built (2026-10-11):**
- Built to the task with no divergence. `mobile/react-native/skills/migration/SKILL.md` (8,181 chars) + four `references/` files; `code-review/SKILL.md` (8,935); `standards-audit/SKILL.md` (description 474 chars) loads the engine and carries the §4.1 version gate and the probes (Expo Router vs React Navigation, storage, native code, localization, motion, tests, release, observability, purchases); the checklist ends with a `## Section index` table (A–X, no W).
- The agent is 13,888 characters by `wc -m` (D16 budget 14,000) with the template's Gate sentence verbatim at `mobile/react-native/agents/mobile-react-native.md` (`Operating rules`). It was first written at 16,414 and cut by removing restated skill content — I1/A1 mirrors should write to the budget from the start (the Steps table and the two output shapes are the bulk).
- Facts re-verified this session from docs.expo.dev: SDK 54 is the last legacy-architecture SDK and `newArchEnabled` leaves `app.json` in SDK 55; `expo-brownfield` is alpha (SDK 55; `build:ios` / `build:android`, isolated vs integrated); `npx install-expo-modules` then prebuild is the bare → Expo path; one-SDK-at-a-time is Expo's own walkthrough advice. **Not verified:** the Callstack `react-native-brownfield` 5.x API surface (no search result named 5.x) — `embed-in-native-app.md` names it without version-specific calls and says to read its release notes.
- Built but unverified: everything — Gate: none. Section A of the checklist (A1–A7) is the audit hook for `migration`.

### I1 — iOS foundations

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-ios-{project-setup,architecture,ui-components,styling,navigation}` exist; iOS
checklist sections A–F have rows from them.
**Depends on:** N1 (`mobile-ios-basics`).
**Budget:** ~150k — CLAUDE.md files 13k; plan §4.2, §5, §6.3, §8.3, §10 ~13k; `mobile-ios-basics` ~5k;
fe-react `project-setup`, `state-management`, `component-writer`, `styling`, `routing` headings and
When-NOT clauses ~10k; research — Xcode 27 templates and build settings, swift-format configuration,
Liquid Glass APIs, `NavigationStack`, `@Observable` + `@Environment` injection ~45k; writes: five
SKILL.md ~23k + references ~6k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.3 row. `project-setup` sets `SWIFT_VERSION` to 6 explicitly (the Xcode 27
  template still says 5.0) and adds `PrivacyInfo.xcprivacy` on day one.
- `architecture`: MV by default; a view model is earned by logic that needs a test apart from the view;
  initializer injection, never a container; TCA only as an existing-codebase lane.
- **Not in I1:** data, UIKit and device skills (I2).

- **As built (2026-10-11):** `mobile/ios/skills/{project-setup,architecture,ui-components,styling,navigation}/SKILL.md` — bodies 13.7k / 11.8k / 11.0k / 10.6k / 11.3k chars, descriptions 487 / 498 / 446 / 437 / 456 chars (`wc -m` / `python3 -I` counts, no gate run); frontmatter `mobile-ios-<folder>`. References: `project-setup/references/packages-and-config.md`, `architecture/references/tca.md`. Checklist rows (`grep -c "^| [A-F][0-9]" mobile/ios/skills/standards-audit/references/conformance-checklist.md` → 79): `A6…A11`, `B17…B24`, `C1…C10`, `D1…D11`, `E1…E12`, `F1…F11`; I2's `uikit` continues D at `D12`, and I3's `notifications-and-links` continues F at `F12`. Two lane tags beyond §8.3's list were used, `[TCA]` and `[Tuist]`. Research: the web search found only third-party posts on Liquid Glass and the Xcode 27 template — no Apple page confirmed the Xcode 27 template's `SWIFT_DEFAULT_ACTOR_ISOLATION` / `SWIFT_APPROACHABLE_CONCURRENCY` values or the iOS 27 glass API signatures; the skills set both settings explicitly and tell the reader to confirm `glassEffect` / `GlassEffectContainer` / `.glass` button styles against the installed SDK (D21). Built but unverified: everything (no build, no lint). `mobile-ios-basics` (N1) has a 504-character description — over §10.2's 500; G1's token audit will flag it.

### I2 — iOS forms, networking, storage, UIKit and device features

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-ios-{forms,networking,offline-and-storage,uikit,device-features}` exist; iOS
checklist sections D, G, H, I, J have rows from them.
**Depends on:** S1 (Keychain and permission rules).
**Budget:** ~150k — CLAUDE.md files 13k; plan §4.2, §5, §6.3, §6.5, §8.3, §10 ~14k;
`mobile/_shared/security/references/ios.md` ~4k; fe-react `forms`, `data-fetching` rule lists ~8k;
research — `URLSession` patterns, SwiftData migrations, Keychain accessibility, UIKit Observation
tracking and `UIHostingConfiguration`, `PhotosPicker`, LocalAuthentication ~45k; writes: five SKILL.md
~23k + references ~8k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.3 row. `networking`: one concrete client; a protocol appears only with the
  second implementation (a test fake counts); the request-level half of §6.5.
- `uikit`: the lane for UIKit codebases and the interop seams both ways; UIScene migration (TN3187).
- **Not in I2:** notifications, system integration, motion, languages, test ids (I3).

- **As built (2026-10-11):** `mobile/ios/skills/{forms,networking,offline-and-storage,uikit,device-features}/SKILL.md` — bodies 14.3k / 14.7k / 14.9k / 15.0k / 13.9k chars, descriptions 461 / 444 / 439 / 461 / 487 chars (`python3 -I` counts, no gate run); frontmatter `mobile-ios-<folder>`. References: `networking/references/request-policy.md`, `offline-and-storage/references/{swiftdata-migrations,keychain}.md`, `uikit/references/{uiscene-migration,interop-seams}.md`, `device-features/references/permissions.md`. Checklist rows (`grep -c "^| [DGHIJ][0-9]" …/conformance-checklist.md` → 68 in D, G, H, I, J): `D12…D20` (`[UIKit]`), `G1…G10`, `H1…H12`, `I1…I14`, `J1…J12`; I3's `notifications-and-links` and `system-integration` continue J at `J13`. `networking` is one concrete `APIClient` (a `final class` conforming to nothing) with a `TokenStore` actor; no protocol appears in any sample. Keychain samples use `…ThisDeviceOnly` throughout; `offline-and-storage` carries the `UserDefaults` `CA92.1` and file-timestamp `C617.1` declarations by pointing at `mobile-shared-store-compliance`. Research: no web search was run in this session — the new facts (UIKit Observation tracking via `updateProperties()` and `UIObservationTrackingEnabled` on iOS 18, the scene-manifest keys, `UIHostingConfiguration`, `PhotosPicker`, SwiftData `VersionedSchema` API shape, `CLLocationUpdate`, `DataScannerViewController`) are from prior knowledge and not confirmed against an Apple page (D22). Built but unverified: everything (no build, no lint). Four SKILL.md bodies are over §10.2's 14,000 aim (all under 16,000); G1's token audit decides whether `networking`, `offline-and-storage` or `uikit` need a further move into `references/`.

### I3 — iOS notifications and links, system integration, motion, languages, test ids

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-ios-{notifications-and-links,system-integration,animation,languages,test-ids}`
exist; iOS checklist sections F, J, P, Q, R have rows from them.
**Depends on:** S1 (link validation, Live Activities guideline 4.5.3), R3 (the verified test-id mapping).
**Budget:** ~145k — CLAUDE.md files 13k; plan §4.2, §5, §6.3, §8.3, §8.5, §10 ~14k;
`mobile-react-native-test-ids` (the mapping R3 verified) ~4k; fe-react `animation`, `languages` rule
lists ~8k; research — APNs and notification service extensions, AASA, App Intents, WidgetKit, Live
Activities, `BGContinuedProcessingTask`, String Catalogs ~45k; writes: five SKILL.md ~23k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.3 row. `test-ids` uses the §8.5 contract exactly as R3 recorded it.
- **Not in I3:** quality layers and tests (I4).

- **As built (2026-10-11):** `mobile/ios/skills/{notifications-and-links,system-integration,animation,languages,test-ids}/SKILL.md` — bodies about 14.2k / 15.5k / 12.5k / 12.9k / 13.2k chars, descriptions 458 / 487 / 470 / 466 / 437 chars (`wc -m` counts, no gate run); frontmatter `mobile-ios-<folder>`. References: `notifications-and-links/references/apns-and-extensions.md` (APNs headers and payloads, the service extension, the AASA file, URL schemes) and `system-integration/references/background-and-activities.md` (entitlement keys, Live Activity push, background-task skeleton, background `URLSession` checklist, extension limits). Checklist rows: `F12…F15` (payload and link validation, AASA, `canOpenURL`), `J13…J28` (notification permission, delegate, token lifecycle, extension handler, background modes, widgets, Live Activities incl. 4.5.3, App Intents, App Group, BG tasks, background sessions), `P1…P11`, `Q1…Q11`, `R1…R10`; `grep -c "^| [FJPQR][0-9]"` over the checklist counts 75 across F, J, P, Q, R. `test-ids` is the §8.5 contract exactly as R3 recorded it (D20): iOS `accessibilityIdentifier` is XCUITest `identifier` / Appium `name` / Maestro `id:`, the label is `text:`; Maestro's regex caveat carried over; the grouping rule (`.combine` hides children) is stated as XCUITest experience, not re-verified. `languages` bans new `.strings` files (migrate with Xcode's String Catalog command). `system-integration` is just under §10.2's 16,000 cap — G1's token audit decides whether the Live Activities section moves into `references/`. Research: no web search or Apple fetch (D23). Built but unverified: everything (no build, no lint). The prompt blocks below needed no rewrite: I4 reads sections M, N, O, S, which I3 did not touch.

### I4 — iOS quality layers and unit tests

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-ios-{accessibility,performance,error-handling,unit-testing}` exist,
`error-handling` with `references/{session-and-resume,writes-and-dependencies}.md`; iOS checklist
sections M, N, O, S have rows.
**Depends on:** S2 (MetricKit / crash reporting hand-off), I2 (`networking`), R4
(`mobile-react-native-error-handling`, the mobile deltas applied once).
**Budget:** ~145k — CLAUDE.md files 13k; plan §4.2, §5, §6.3, §6.5, §8.3, §10 ~14k;
`frontend/react/skills/error-handling` SKILL.md + two references ~16k; `mobile-react-native-error-handling`
(the mobile deltas already applied once) ~5k; research — Swift Testing (parameterized, exit tests,
interop modes), swift-snapshot-testing, Instruments, MetricKit iOS 27, VoiceOver APIs ~35k; writes:
four SKILL.md ~18k + two references ~10k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.3 row; `error-handling` carries every §6.5 row that is not RN-only, with the
  forced-update path for version skew.
- `unit-testing`: Swift Testing in every sample; XCTest only where §4.2 says; journeys handed to
  `qa-mobile-<stack>`.
- **Not in I4:** migration, review, audit, agent (I5).

- **As built (2026-10-11):** `mobile/ios/skills/{accessibility,performance,error-handling,unit-testing}/SKILL.md` — bodies 12.5k / 12.0k / 13.4k / 14.0k chars, descriptions 451 / 441 / 460 / 458 chars (`python3 -I` counts, no gate run); frontmatter `mobile-ios-<folder>`. `error-handling/references/{session-and-resume,writes-and-dependencies}.md` (8.0k / 7.9k) carry the 401 ladder with a `SessionGate` sheet, the forced-update path (server minimum version, numeric compare, fail open, fixed store URL), `scenePhase` resume, writes (`WriteState`, one idempotency key per intent), third parties and the `GuardedStore` full-disk fallback; OTA skew is RN-only and absent. Checklist rows in `mobile/ios/skills/standards-audit/references/conformance-checklist.md` (`grep -c '^| [MNOS][0-9]'` → 63): `M1…M14`, `N1…N13`, `O1…O21`, `S1…S15`. Built but unverified: everything; the Swift samples were not compiled. New facts (MetricKit `MetricManager` member names, Swift Testing exit-test platform limits, XCTest interop modes, Accessibility Nutrition Label option names) are third-party-sourced only — D24.

### I5 — iOS migration, review, audit, agent and commands

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-ios-{migration,code-review,standards-audit}` exist; `mobile/ios/agents/mobile-ios.md`
(≤ 14,000 characters, Gate line verbatim) and `mobile/ios/commands/{mobile-ios,mobile-ios-audit}.md`
exist; the iOS checklist ends with a section index.
**Depends on:** I1–I4, S1–S3, N1, R5 (the sibling agent, commands, review and audit).
**Budget:** ~140k — CLAUDE.md files 13k; plan §6.1, §6.3, §7, §8, §10 ~16k;
`mobile/react-native/agents/mobile-react-native.md` (the sibling, already on budget) ~4k and both RN
commands ~2k; `mobile-react-native-standards-audit` ~4k; engine ~6k; the iOS checklist ~12k; the 22
iOS skills' frontmatter ~6k; research — swift.org migration guide, `swift package migrate`, CocoaPods →
SPM, TN3187, UIKit → SwiftUI ~25k; writes: migration SKILL.md + references ~18k, code-review ~4k,
standards-audit ~4k, agent ~4k, commands ~2k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `migration` per §6.3, one `references/` file per path; CocoaPods → SPM carries the 2026-12-02 date.
- `code-review`, `standards-audit`, agent and commands mirror R5's on the iOS lane (§4.2 version gate;
  probes: SwiftUI vs UIKit share, Swift 6 modules, IAP present, extensions present).
- **Not in I5:** marketplace wiring (W1).

- **As built (2026-10-11):** `mobile/ios/skills/migration/SKILL.md` (9.8k chars, description 469) with seven `references/` files (one per path: `swift6-modules` 6.7k, `observation`, `combine-to-async`, `uikit-to-swiftui`, `objc-to-swift`, `cocoapods-to-spm` — carries 2026-12-02 and the pod inventory, `ios27-sdk-and-targets` — the forced SDK changes and the deployment-target raise); `code-review/SKILL.md` (10.7k, description 476) and `standards-audit/SKILL.md` (9.5k, description 466) — the latter carries the §4.2 version gate (Step 0) and the probes SwiftUI vs UIKit share, Swift language mode per module, StoreKit purchases, extensions, Objective-C count, TCA / Tuist; the checklist ends with a `## Section index` (A–X, no W; row ranges A1–A11 … V1–V8, S1–S15). `mobile-ios` agent is 13,879 characters by `wc -m` with the template's Gate sentence verbatim (`Operating rules`); written to the budget from the start by routing to skills. Related agents name `qa-mobile-java`, `qa-mobile-dotnet` and `qa-mobile-typescript` (the Maestro lane is the TypeScript peer's). Swift 6 migration: module by module, leaves first; `swift6-modules.md` § "Finding dynamic isolation checks" is the part of that move's gate that finds `@MainActor` callbacks arriving on another queue — static grep of the seams, then Thread Sanitizer + Main Thread Checker while driving each seam, and the crash signatures to search for. Built but unverified: everything — Gate: none; no web search or Apple fetch was run (D25). Proof: `wc -m` counts above; `grep -c "^| [A-X][0-9]" mobile/ios/skills/standards-audit/references/conformance-checklist.md` unchanged by this task (only the index was appended).

### A1 — Android foundations

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-android-{project-setup,architecture,ui-components,styling,navigation}` exist;
Android checklist sections A–F have rows from them.
**Depends on:** N1 (`mobile-android-basics`), I1 (`mobile-ios-{project-setup,architecture}` as the domain shape).
**Budget:** ~150k — CLAUDE.md files 13k; plan §4.3, §5, §6.4, §8.3, §10 ~13k; `mobile-android-basics`
~5k; the iOS siblings `mobile-ios-{project-setup,architecture}` (shape across the domain) ~8k; research
— AGP 9 built-in Kotlin and new DSL, version catalogs, Google's architecture recommendations,
Navigation 3, Material 3 1.4 / 1.5, window size classes ~45k; writes: five SKILL.md ~23k + references
~6k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.4 row. `project-setup` sets `targetSdk` explicitly (AGP 9 defaults it to
  compileSdk) and never applies `org.jetbrains.kotlin.android` on AGP 9.
- `architecture`: one `uiState` per screen ViewModel; no ViewModel-to-UI events; convention plugins and
  modules only when earned.
- **Not in A1:** data, Views and device skills (A2).

- **As built (2026-10-10):** `mobile/android/skills/{project-setup,architecture,ui-components,styling,navigation}/SKILL.md` — bodies 14.6k / 13.1k / 14.1k / 11.7k / 12.9k chars, descriptions 465 / 464 / 483 / 449 / 476 (`wc -m`, no gate run); frontmatter `mobile-android-<folder>`. References: `project-setup/references/gradle-config.md`, `architecture/references/hilt-and-modules.md`. Checklist rows (`grep -c "^| [A-F][0-9]" mobile/android/skills/standards-audit/references/conformance-checklist.md` → 86): `A5…A13`, `B17…B20`, `C1…C13`, `D1…D15`, `E1…E12`, `F1…F13`; A2's `views-interop` continues D at `D16`, A3's `notifications-and-links` continues F at `F14`. Lane tags used beyond §8.3's list: `[AGP8]`, `[NavCompose]`, `[N3]`, `[M3-1.5]`, `[M2]`. Verified at source this session: built-in Kotlin migration page (plugin removal, `compilerOptions`, kapt → KSP / `com.android.legacy-kapt`, `android.builtInKotlin` + `android.newDsl` opt-outs removed in AGP 10, `enableKotlin = false`) and the window-size-class breakpoints incl. Large / Extra-large behind `supportLargeAndXLargeWidth`. Built but unverified: see D27. Built but unverified overall: everything (no build, no lint, no `rg` recipe run).

### A2 — Android forms, networking, storage, Views interop and device features

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-android-{forms,networking,offline-and-storage,views-interop,device-features}`
exist; Android checklist sections D, G, H, I, J have rows from them.
**Depends on:** S1 (Keystore, Network Security Config, permission rules), I2 (`mobile-ios-networking` as the sibling shape).
**Budget:** ~150k — CLAUDE.md files 13k; plan §4.3, §5, §6.4, §6.5, §8.3, §10 ~14k;
`mobile/_shared/security/references/android.md` ~4k; `mobile-ios-networking` (sibling shape) ~4k;
research — Retrofit 3, OkHttp `Authenticator`, Room 3, DataStore + Tink, WorkManager sync, Compose text
fields, photo picker, CameraX, Credential Manager ~45k; writes: five SKILL.md ~23k + references ~8k;
rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.4 row. `offline-and-storage`: Room 3 for new code, Room 2.8 as a lane, and
  never EncryptedSharedPreferences in new code.
- **Not in A2:** notifications, system integration, motion, languages, test ids (A3).

- **As built (2026-10-10):** `mobile/android/skills/{forms,networking,offline-and-storage,views-interop,device-features}/SKILL.md` — `wc -m` of the whole file 15,294 / 15,809 / 16,319 / 15,379 / 16,000 (bodies ≈ 0.6k less; descriptions all under 500), no gate run. Detail moved to `references/` to fit §10.2: `forms/references/validation-autofill-wizards.md`, `networking/references/{request-policy,connectivity-and-trust}.md`, `offline-and-storage/references/{room-migrations,keystore-and-secrets}.md`, `views-interop/references/recyclerview.md`, `device-features/references/{permissions,biometrics-and-credentials}.md`. Checklist rows (`grep -c "^| [GHIJ][0-9]" mobile/android/skills/standards-audit/references/conformance-checklist.md` → 51): `D16…D25` (views-interop, `[Views]` lane tag), `G1…G10`, `H1…H15`, `I1…I14`, `J1…J12`; A3 continues J at `J13`. Lane tag beyond §8.3's list: `[Room2]`. Verified at source this session: Room 3.0.3 release page (`androidx.room3`, `room3-*` artifacts, KSP-only, `SQLiteDriver` required, `suspend`/`Flow` DAOs, converter artifacts for Paging / Rx / Guava / LiveData, `createFlow`, `withWriteTransaction`, builder `Room.databaseBuilder<T>(…).setDriver(…)`) and the `security-crypto` page (all APIs deprecated since 1.1.0-beta01; platform APIs and Keystore recommended). Built but unverified: see D28. Built but unverified overall: everything (no build, no lint, no `rg` recipe run).

### A3 — Android notifications and links, system integration, motion, languages, test ids

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-android-{notifications-and-links,system-integration,animation,languages,test-ids}`
exist; Android checklist sections F, J, P, Q, R have rows from them.
**Depends on:** S1 (FGS declarations, full-screen intents, App Links validation), R3 (the verified test-id mapping).
**Budget:** ~145k — CLAUDE.md files 13k; plan §4.3, §5, §6.4, §8.3, §8.5, §10 ~14k;
`mobile-react-native-test-ids` (the mapping) ~4k; research — FCM current API, channels, App Links
verification, foreground-service types and API 37 changes, Glance, per-app language, Compose animation
~45k; writes: five SKILL.md ~23k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.4 row. `test-ids`: `testTagsAsResourceId` set once at the root, per §8.5.
- **Not in A3:** quality layers and tests (A4).

- **As built (2026-10-10):** `mobile/android/skills/{notifications-and-links,system-integration,animation,languages,test-ids}/SKILL.md` — `wc -m` of the whole file 15,539 / 15,705 / 13,172 / 13,325 / 14,458 (descriptions 475 / 477 / 461 / 498 / 412), no gate run. References: `notifications-and-links/references/{fcm,app-links}.md`, `system-integration/references/foreground-services.md`. Checklist rows (`grep -c "^| [FJPQR][0-9]"` over the Android checklist → 64, 39 added): `F14…F16`, `J13…J24`, `P1…P8`, `Q1…Q8`, `R1…R8`. Verified at source this session: FCM get-started and receive-messages (Installation-ID registration — `firebase_messaging_installation_id_enabled`, `onRegistered`; the token flow and `onNewToken` are marked deprecated; `POST_NOTIFICATIONS` declared by SDK ≥ 23.0.6), the foreground-service types page (full type / permission / prerequisite table, timeouts), Android 17 behaviour changes and the background-audio hardening page, App Links verification, per-app languages, WorkManager 2.12.0 (minSdk 24) and Glance 1.2.0 release pages. **Differed from the plan:** `notifications-and-links` teaches the FID flow as primary and the token flow as `[FCM-token]` (§4.5's "FCM current API" resolved — D29). Built but unverified: the FCM BoM version and the server field that targets an FID; Compose shared-element stability and the `PredictiveBackHandler` name; infinite-animation behaviour at animator scale 0; whether `testTagsAsResourceId` reaches `Dialog` / `Popup` windows and Appium's `id=` package autocompletion (community sources); the AGP 9 locale-filter DSL; Glance refresh signatures. Built but unverified overall: everything (no build, no lint, no `rg` recipe run).

### A4 — Android quality layers and unit tests

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-android-{accessibility,performance,error-handling,unit-testing}` exist,
`error-handling` with `references/{session-and-resume,writes-and-dependencies}.md`; Android checklist
sections M, N, O, S have rows.
**Depends on:** S2, A2 (`networking`), I4 (`mobile-ios-error-handling`, the native deltas applied once).
**Budget:** ~145k — CLAUDE.md files 13k; plan §4.3, §4.4 vitals, §5, §6.4, §6.5, §8.3, §10 ~14k;
`mobile-ios-error-handling` + its references (the native deltas already applied once) ~10k; research —
Baseline / Startup Profiles, Macrobenchmark, R8 in AGP 9, Compose UI test v2, Robolectric 4.17, Turbine,
Roborazzi, Compose accessibility checks ~40k; writes: four SKILL.md ~18k + two references ~10k; rows ~6k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Each skill per its §6.4 row; `error-handling` adds process-death restore to the §6.5 set.
- `unit-testing`: fakes over mocks in every sample; Compose UI test v2 and its dispatcher change stated.
- **Not in A4:** KMP and migration (A5).

- **As built (2026-10-10):** `mobile/android/skills/{accessibility,performance,error-handling,unit-testing}/SKILL.md` — `wc -m` of the whole file 13,201 / 15,117 / 15,913 / 16,451 (bodies about 0.6–0.7k less; descriptions 462 / 426 / 487 / 459), no gate run. References: `error-handling/references/{session-and-resume,writes-and-dependencies}.md` (11.6k / 10.1k; process-death restore is a section of `session-and-resume.md`), `unit-testing/references/{flows-and-seams,robolectric-and-screenshots}.md` (moved out to fit §10.2). Checklist rows (`grep -c "^| [MNOS][0-9]"` over the Android checklist → 67): `M1…M15`, `N1…N14`, `O1…O22`, `S1…S16` (`M15` is the `[Views]` row; `S5` carries the new lane tag `[Compose v2]`). Verified at source this session: the Compose UI test v2 migration page (package moves to `…junit4.v2` / `…test.v2`, `StandardTestDispatcher` vs `UnconfinedTestDispatcher`, `waitForIdle` / `runOnIdle` / `mainClock.scheduler.runCurrent()`, `InputMode.Touch` pinned, `ComposeUiTestConfig` 1.13.0-alpha01+), Baseline / Startup Profile overview (plugin, `BaselineProfileRule`, AGP 8.2 R8 rewrite, `startup-prof.txt`), Macrobenchmark overview (`MacrobenchmarkRule.measureRepeated`, `CompilationMode`, `StartupMode`, profileable `benchmark` build type, no emulators), launch-time page (`reportFullyDrawn`, `ReportDrawn*`, App Startup), Compose accessibility-test page (`enableAccessibilityChecks`, Compose 1.8+), the R8 optimisation page (AGP 9.3 `keepRules` source set, global options filtered from library consumer rules). **Differed from the plan:** nothing structural; `error-handling` holds process-death restore in `session-and-resume.md` rather than a third file. Built but unverified: Robolectric 4.17 final release (only `4.17-beta-2` was found in a search — D30), Turbine 1.2.0 and Roborazzi 1.63.0 versions (search listings), `-keepclassmembers` full-mode semantics and the `-allowaccessmodification` placement (the R8 page defers them to subpages), the `PullToRefreshBox` / `LifecycleResumeEffect` names, `WindowInsets.safeDrawing` as the banner inset, the 1 MB saved-state limit wording, the ENOSPC mapping of `SQLiteFullException` / `IOException`. Built but unverified overall: everything (no build, no lint, no `rg` recipe run).

### A5 — Kotlin Multiplatform and Android migration

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-android-kotlin-multiplatform` and `mobile-android-migration` exist; Android
checklist sections A and W have rows from them.
**Depends on:** A1–A4 (the choices KMP and migration build on).
**Budget:** ~125k — CLAUDE.md files 13k; plan §3 verdicts, §4.3, §6.4, §8.3, §10 ~12k; `mobile-android-{architecture,networking,offline-and-storage}`
~12k; research — KMP project structure, `com.android.kotlin.multiplatform.library`, Swift export,
SKIE status, Compose Multiplatform 1.12, AGP 8 → 9 migration, Views → Compose strategy, Room 2 → 3 ~45k;
writes: two SKILL.md ~9k + migration references ~16k + KMP references ~8k; rows ~4k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- `kotlin-multiplatform` per §6.4: shared logic is the default, Compose Multiplatform is opt-in; the
  Swift consumer code is `mobile-ios`'s; DI is Koin or Metro because Hilt is Android-only.
- `migration` per §6.4, one `references/` file per path; AGP 8 → 9 lists each escape hatch as
  temporary (gone in AGP 10).
- **Not in A5:** review, audit, agent (A6).

- **As built (2026-10-10):** `mobile/android/skills/kotlin-multiplatform/SKILL.md` (13,030 `wc -m`) with `references/{module-and-gradle,ios-and-swift-export,compose-multiplatform}.md` (4.4k / 4.3k / 4.3k), and `mobile/android/skills/migration/SKILL.md` (9,228) with nine references, one per path: `agp8-to-9`, `target-sdk-behaviour`, `java-kotlin-gradle-kts` (Groovy → KTS and Java → Kotlin share a file), `livedata-rx-to-flow`, `dagger-to-hilt`, `room2-to-3`, `views-to-compose`, `navigation-to-nav3`, `encrypted-prefs-replacement` (2.3k–4.8k each). No gate run. Checklist rows: `A14…A19` (AGP 9 `kotlinOptions` / `sourceSets`, `targetSdk` one level at a time, Room 2 / 3 mixing, `EncryptedSharedPreferences`, LiveData / Rx, one move per change) and `W1…W11` (Hilt in shared code, library plugin, separate app module, Android types in `commonMain`, CMP decision record, Swift export Alpha, DI shape, secrets, exported surface, per-target KSP, `commonTest`). **Differed from the plan:** nothing structural; Groovy → KTS and Java → Kotlin are one reference rather than two. Verified at source this session: the Android-KMP library plugin page (`android { }` inside `kotlin { }`, `androidLibrary { }` deprecated since AGP 9.1, opt-in host / device tests, single variant, resources off, no `BuildConfig`), the built-in Kotlin migration page (every step, the module-by-module bridge, "cannot disable in AGP 10", KMP note), the Swift export page (Alpha, limits, `embedSwiftExportForXcode`), What's new in Kotlin 2.4 (Swift export Alpha with `suspend` → `async` and `Flow` → `AsyncSequence`, `swiftPMDependencies`, iOS minimum 15, KGP needs AGP ≥ 8.5.2), the Room 3 page (package, artifacts, driver, removed APIs, converters, `@ColumnTypeConverter`, `room3-sqlite-wrapper`), Google's Views → Compose strategy page, the Navigation 3 migration guide. Built but unverified: SKIE's Kotlin 2.4 support (a search found only work on 2.4 RC in progress, no release), Metro's and Koin Compiler Plugin's current versions (the skill pins neither), the KMP Room 3 builder / constructor annotation spellings (the skill says to check the KDoc), Navigation 3 and Navigation Compose KMP availability under Compose Multiplatform, the `testTag` → iOS accessibility-identifier mapping in CMP, the `targetSdk` 35 / 36 / 37 behaviour list beyond §4.3 (the skill sends the reader to each level's behaviour-changes page), the Hilt-to-AGP-9 and `legacy-kapt` details beyond §4.3 and the migration page, WorkManager being Android-only. Built but unverified overall: everything (no build, no lint, no `rg` recipe run).

### A6 — Android review, audit, agent and commands

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-android-{code-review,standards-audit}` exist; `mobile/android/agents/mobile-android.md`
(≤ 14,000 characters, Gate line verbatim) and `mobile/android/commands/{mobile-android,mobile-android-audit}.md`
exist; the Android checklist ends with a section index.
**Depends on:** A1–A5, S1–S3, N1, I5 (the sibling agent, commands, review and audit).
**Budget:** ~105k — CLAUDE.md files 13k; plan §6.1, §6.4, §7, §8, §10 ~16k;
`mobile/ios/agents/mobile-ios.md` ~4k, both iOS commands ~2k, `mobile-ios-{code-review,standards-audit}`
~8k; engine ~6k; the Android checklist ~12k; the 23 Android skills' frontmatter ~6k; writes:
code-review ~4k, standards-audit ~4k, agent ~4k, commands ~2k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Mirror I5's review, audit, agent and commands on the §4.3 lane; audit probes add Compose vs Views
  share, KMP modules (section W), AGP major.
- **Not in A6:** marketplace wiring (W1).

### W1 — marketplace, planning lane and QA wiring

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-react-native`, `mobile-ios` and `mobile-android` are listed in
`.claude-plugin/marketplace.json` with every path existing on disk; the plan format, delivery plan and
solution planner accept a `mobile` task routed to the three agents; the QA mobile peers name the dev
agents and carry the §8.5 mapping.
**Depends on:** R5, I5, A6 (the agents and commands), R3 (§8.5's answer), S1–S3.
**Budget:** ~120k — CLAUDE.md files 13k; plan §2, §8.5, §9 ~8k; the fe-react marketplace entry ~4k and
three entries written ~12k; `plan-format.md` §4 table ~3k, `delivery-plan/SKILL.md` cited lines ~6k,
`solution-planner.md` cited lines ~8k; the three `qa-mobile-<stack>.md` Related-agents sections ~6k,
three explorer line-10 paragraphs ~3k, two security-testing peer lines ~3k; the test-id mapping in
`mobile-react-native-test-ids` ~2k; folder listings to build the arrays ~4k; edits ~10k.
**Gate: none** — this plan gates once, in G1. Do not run `tools/token-audit.py`, §11's script, or any lint.

- Marketplace per §9; build each `skills` array from `ls` of the folders, not from memory.
- Planning lane per §9 and D11.
- QA peers per §9 and §8.5. The three `mobile-screen-explorer` bodies are within 600 characters of the
  16,000 budget — the correction replaces a sentence, it does not add one.
- **Not in W1:** CLAUDE.md map, catalog, README (G1).

### G1 — documentation, the gate, and filing the plan

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `CLAUDE.md`, `docs/skills-catalog.md` and `README.md` describe the mobile domain; §11's
three checks pass; this plan is in `docs/plans/implemented/`.
**Depends on:** every task above.
**Budget:** ~140k — CLAUDE.md files 13k; plan header, §2, §6, §9, §11 ~14k; the catalog's scope
paragraph, slash-command table and `## Frontend-React dev catalog` as the section pattern ~10k; README
layout and status rows ~4k; writes ~12k; gate output ~15k; fixes ~50k (descriptions over 500, bodies
over 16,000, unresolved names and broken links across ~85 new files).
**Gate (run order, the plan's only gate):** §11 steps 1–3. Fix what fails — a failure may belong to any
task above.

- Documentation per §9: `CLAUDE.md` § Repository map row and the under-construction line;
  `docs/skills-catalog.md` scope paragraph, three slash-surface rows, a recomputed command count, the
  `## Mobile dev catalog` section; `README.md` layout line and status row.
- The gate per §11; every `ALLOW` / `LINK_EXAMPLES` addition justified in the `As built` note.
- Rewrite `**Status:**` one last time — what the plan delivered, and what is still **unverified**
  (no agent has been run against a real app; the version facts are as of 2026-10-10; SDK 58 may have
  shipped; Maestro is live only if plan 003's X1 has landed) and what is next (the Flutter plan, O4) —
  and `git mv` this plan to `docs/plans/implemented/002-mobile-plugins.md`.

## Close-out — every task

Before you stop, in this order, in this file:

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Your own block** — delete it, and update the line above the blocks that says which have landed.
   Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming the blocker and
   its owner.
5. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified.
6. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified) and `git mv` this plan into `docs/plans/implemented/`, same
   name and number — a `solution-planner` pack moves its whole initiative folder.
7. **Commit** — the code, its tests and these plan edits together, in one commit.

## Prompts — one per task

Run them in order, one Plan Queue session each; every block is complete on its own. Only G1 runs the
gate (§11) — no other block runs `tools/token-audit.py`, §11's script, a linter or anything that builds;
counting the characters of a file you wrote with `wc -m` is allowed (§10.2). No block edits
`mobile/react-native/vendor/**` (C1's one routing line excepted), `docs/plans/implemented/**` or
`docs/audits/**`. **Unattended sessions refuse some shell forms** (plan 001): no brace expansion, no
`$VAR` expansion, no `.sh` files, nothing written outside the worktree — not even `/tmp`. Scratch work
goes in an untracked `scratch/` folder inside the worktree, deleted before committing.

| # | Stack | Agent | Depends on | Budget |
|---|---|---|---|---|
| C1 | `docs` | `general-purpose` | — | ~95k |
| S1 | `docs` | `general-purpose` | C1 | ~145k |
| S2 | `docs` | `general-purpose` | C1 | ~140k |
| S3 | `docs` | `general-purpose` | C1 | ~145k |
| N1 | `docs` | `general-purpose` | C1 | ~110k |
| R1 | `docs` | `general-purpose` | C1 | ~140k |
| R2 | `docs` | `general-purpose` | N1, S1 | ~150k |
| R3 | `docs` | `general-purpose` | S1 | ~140k |
| R4 | `docs` | `general-purpose` | S2, R2 | ~150k |
| R5 | `docs` | `general-purpose` | R1–R4, S1–S3, N1 | ~140k |
| I1 | `docs` | `general-purpose` | N1 | ~150k |
| I2 | `docs` | `general-purpose` | S1 | ~150k |
| I3 | `docs` | `general-purpose` | S1, R3 | ~145k |
| I4 | `docs` | `general-purpose` | S2, I2, R4 | ~145k |
| I5 | `docs` | `general-purpose` | I1–I4, S1–S3, N1, R5 | ~140k |
| A1 | `docs` | `general-purpose` | N1, I1 | ~150k |
| A2 | `docs` | `general-purpose` | S1, I2 | ~150k |
| A3 | `docs` | `general-purpose` | S1, R3 | ~145k |
| A4 | `docs` | `general-purpose` | S2, A2, I4 | ~145k |
| A5 | `docs` | `general-purpose` | A1–A4 | ~125k |
| A6 | `docs` | `general-purpose` | A1–A5, S1–S3, N1, I5 | ~105k |
| W1 | `docs` | `general-purpose` | R5, I5, A6, R3, S1–S3 | ~120k |
| G1 | `docs` | `general-purpose` | every task above | ~140k |

C1, S1, S2, S3, N1, R1, R2, R3, R4, R5, I1, I2, I3, I4, I5, A1, A2, A3, A4 and A5 have landed (their blocks are deleted); every block below is live.

---

### A6 — Android review, audit, agent and commands (general-purpose, docs)

````
You are `general-purpose`. Task A6 of docs/plans/002-mobile-plugins.md: write
`mobile-android-{code-review,standards-audit}`, the `mobile-android` agent and its two commands.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §6.1, §6.4, §7, §8, §10, task A6, and "Close-out — every task".
3. `mobile/ios/agents/mobile-ios.md`, both iOS commands, `mobile-ios-{code-review,standards-audit}`;
   `engineering-practices/standards-audit-engine/SKILL.md`.
4. The Android checklist in full; the frontmatter of the other Android skills.

Build:
- Mirror I5's review, audit, agent and commands on the §4.3 lane; audit probes add the Compose vs Views
  share, KMP modules (section W), the AGP major; the closing section index.

Traps:
- Agent ≤ 14,000 characters with the template's Gate sentence verbatim — `mobile-ios.md` landed at 13,879 (`wc -m`) by routing to skills from the start; copy its shape (Steps table, two output shapes) and its Related agents naming the three `qa-mobile-<stack>` peers.
- Section W is N/A unless KMP modules exist — the probe decides, and N/A names the probe. Section W already holds `W1…W11` and section A runs to `A19` (A5); the audit `SKILL.md` and the closing index only reference them — add no rows, renumber nothing.

Gate: none — this plan gates once, in G1. Do not run tools/token-audit.py, §11's script, or any lint.

Commit: `feat(mobile A6): Android review, audit, agent and commands`.
Close out per the plan's "Close-out — every task" before you stop.
````

### W1 — marketplace, planning lane and QA wiring (general-purpose, docs)

````
You are `general-purpose`. Task W1 of docs/plans/002-mobile-plugins.md: list the three mobile plugins in
the marketplace, teach the planning lane a `mobile` stack, and wire the QA mobile peers.

Read, in this order:
1. CLAUDE.md.
2. The plan: §2, §8.5, §9, D11, task W1, and "Close-out — every task".
3. The `fe-react` entry of `.claude-plugin/marketplace.json`.
4. `engineering-practices/writing-plans/references/plan-format.md` §4's Stack row (line 117);
   `backend/_shared/delivery-plan/SKILL.md` lines 43, 118, 282; `backend/_shared/agents/solution-planner.md`
   lines 15, 61, 79, 198, 229.
5. `qa/{java,dotnet,typescript}/agents/qa-mobile-*.md` § Related agents; line 10 of each
   `qa/*/skills/mobile-screen-explorer/SKILL.md`; the peer lines of
   `qa/_shared/security-testing/{mobile-app-scan,mobile-runtime-testing}/SKILL.md`.
6. The mapping section of `mobile/react-native/skills/test-ids/SKILL.md`.

Build:
- Three marketplace entries per §9, after `fe-react`; every `skills` array built from `ls` of the
  folders, never from memory.
- `mobile` added to the stack lists at the cited lines and to CLAUDE.md § Planning's one-stack bullet;
  the three agents added to the planner's routing beside `fe-react` / `fe-blazor`.
- QA: the three dev agents named as consumers of `missing-testids.md`; each explorer's line 10 and its `~`
  ladder rung corrected to R3's verified mapping (D20); the security-testing peer lines name where fixes go.

Traps:
- plan-format.md is the contract every plan follows — add the token and its one-phrase gloss, nothing else.
- R3 refuted the explorers' claim (D20): Android `content-desc` is the `accessibilityLabel`, the `testID` is
  the bare `resource-id`. Correct the line-10 sentence **and** the locator-ladder rung that says `~` is the
  default (`~` on iOS; `id=` / UiSelector `resourceId` on Android) — nothing else in the strategy changes.
  The explorers' kebab-case "Suggested testID" stays a hint; the dev skill derives PascalCase. Their bodies sit
  at 15,400–15,900 of the 16,000-character budget: replace sentences in place, never add one.
- Do not run §11's script — G1 does; a path you doubt, `ls` it.

Gate: none — this plan gates once, in G1. Do not run tools/token-audit.py, §11's script, or any lint.

Commit: `feat(mobile W1): marketplace entries, mobile planning lane, QA wiring`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — documentation, the gate, and filing the plan (general-purpose, docs)

````
You are `general-purpose`. Task G1 of docs/plans/002-mobile-plugins.md: document the mobile domain, run
the plan's only gate, fix what it finds, and file the plan.

Read, in this order:
1. CLAUDE.md.
2. The plan: the header, §2, §6, §9, §11, every task's As built note, and "Close-out — every task".
3. `docs/skills-catalog.md` — the scope paragraph, the slash-command surface table, and
   `## Frontend-React dev catalog` as the section pattern; `README.md` layout and status rows.

Build:
- CLAUDE.md § Repository map row for `mobile/`; `mobile/` off the under-construction line.
- `docs/skills-catalog.md`: scope paragraph, three slash-surface rows, the command count recomputed
  from the marketplace (unique command files), a `## Mobile dev catalog` section; `README.md` layout
  line and status row.

Gate (this is the last task, so it carries the plan's only gate, in run order):
  python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
  python3 scratch/library-check.py        (§11's script, saved into an untracked scratch/ folder)
  python3 tools/token-audit.py            (read the counts: 109 body, 51 file, nothing under mobile/ or the three new auth/ folders)
Fix what it finds — a failure may belong to any task above, and the As built note says whose it was.

Traps:
- token-audit exits non-zero because of the 160 pre-existing violations — judge by the counts.
- An over-budget body is fixed by moving detail into `references/`, never by deleting rules.
- Delete `scratch/` before committing.

Then rewrite `**Status:**` one last time — what the plan delivered, what is still unverified (no agent
has been run against a real app; versions are as of 2026-10-10; SDK 58 may have shipped; Maestro is
live only if plan 003's X1 has landed), and what is next (the Flutter plan, O4) — and `git mv` this
plan to docs/plans/implemented/002-mobile-plugins.md.

Commit: `feat(mobile G1): mobile catalog and docs, gate passed, plan filed`.
Close out per the plan's "Close-out — every task" before you stop.
````
