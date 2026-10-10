# TCA and friends — the existing-codebase lane

Reference for `mobile-ios-architecture`. **Use only where the codebase already depends on The Composable Architecture (1.26), Factory (3.4) or swift-dependencies (1.17).** Never introduce them to a project that did not choose them, and never rewrite a TCA feature to MV as a side effect of other work.

## Detecting

`rg -n "ComposableArchitecture|import Factory|import Dependencies" -g '*.swift' -g 'Package.swift' -g 'Package.resolved'`. If absent, stop: the skill's MV default applies.

## Working inside a TCA codebase

- **Match the existing shape.** One `@Reducer` per feature, state a `struct` with `@ObservableState`, actions an `enum`, side effects returned as `Effect` — whatever the neighbouring features do.
- **Dependencies go through `@Dependency` and `DependencyKey`** (swift-dependencies), with a `liveValue`, a `testValue` that fails loudly on use, and a `previewValue`. Do not add a second injection mechanism alongside it.
- **Views use `Store`** (`@Bindable var store: StoreOf<Feature>`, `store.send(.tapped)`), scoped to child stores; do not reach into a store's state from outside the view that owns it.
- **Tests use `TestStore`** exhaustively. Swift Testing is the runner; the rules of [`unit-testing`](../../unit-testing/SKILL.md) (one logical assertion, fakes over mocks) still apply, with `TestStore` as the fake.
- **Navigation** follows the codebase's choice (`@Presents` / `StackState`) — [`navigation`](../../navigation/SKILL.md) covers the plain `NavigationStack(path:)` default only.

## What stays the same

Swift 6 mode, `os.Logger`, no force unwrap, accessibility, test ids and every audit row apply unchanged; a TCA store is not an exemption. The audit rows that say "initializer injection" read `@Dependency` as the injection point in a TCA module.

## Factory / swift-dependencies without TCA

Same rule: keep the existing container for the features that use it, route new code through it, and do not spread it to new modules. A new module in such a codebase may still take plain `init` parameters from the composition root — prefer that unless the surrounding feature is already container-based.

## Moving off

A migration away from TCA is a plan of its own and is not an architecture task; [`mobile-ios-migration`](../../migration/SKILL.md) does not include it.
