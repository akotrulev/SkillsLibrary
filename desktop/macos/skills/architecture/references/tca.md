# The Composable Architecture on the Mac — an existing-codebase lane

Depth for [`../SKILL.md`](../SKILL.md). **Use this only where the project already depends on `swift-composable-architecture`.** A new feature in a codebase that does not use it gets `@Observable` models, never TCA. Pin read from `Package.resolved` before advising: current is **1.26.2** (2026-08-28); never bump it as a side effect.

## What carries over

- A feature is a `@Reducer` with `State` (a value type), `Action` and a body. Views hold `@Bindable var store: StoreOf<Feature>`.
- Dependencies come from `@Dependency` (swift-dependencies): a client, a clock, a UUID generator. A test overrides them with `withDependencies`; this is the clock and UUID seam [`unit-testing`](../../unit-testing/SKILL.md) asks for.
- Effects are `.run { send in … }` and cancel with `.cancellable(id:)` / `.cancel(id:)`, tied to the window's lifetime: a feature stored per window is released when the window closes.

## What is Mac-specific

| Concern | Rule |
|---|---|
| One store per window | Scope a child store per window's root view; state several windows share lives in a parent store passed in, never copied |
| Menu commands | Publish the **store** (or a scoped slice) with `focusedSceneValue`; the command sends an action. A command whose store is nil is disabled, not hidden |
| `@FocusedValue` key | Declare with `@Entry` on `FocusedValues`; the value is the narrowest store slice that serves |
| Settings scene | A separate store built at the composition root, injected into `Settings` |
| Isolation | The reducer runs on the main actor in a `MainActor`-default module; keep `Sendable` conformances on `State` and `Action` |

## Testing

`TestStore` with exhaustive assertions is the project's Swift Testing lane; assert state changes and received actions, override the clock, and never sleep. Coverage and test naming follow CLAUDE.md § Test code rules.

## Migration

Moving off TCA is never a side effect of other work. When asked: `@Observable` model per feature, `@Dependency` clients become initializer-injected clients, tests port feature by feature. Recorded in [`migration`](../../migration/SKILL.md).
