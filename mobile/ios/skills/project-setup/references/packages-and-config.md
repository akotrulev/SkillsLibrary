# iOS project setup — packages, formatter and linter config

Reference for `mobile-ios-project-setup`. Version facts are the skill's table; this file is the shapes.

## A library package

```swift
// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "Core",
    platforms: [.iOS(.v17)],
    products: [.library(name: "Core", targets: ["Core"])],
    targets: [
        .target(
            name: "Core",
            swiftSettings: [
                .enableUpcomingFeature("NonisolatedNonsendingByDefault"),
                .enableUpcomingFeature("InferIsolatedConformances"),
            ]
        ),
        .testTarget(name: "CoreTests", dependencies: ["Core"]),
    ],
    swiftLanguageModes: [.v6]
)
```

- Tools version 6.2 is the floor for the two upcoming-feature flags and default isolation; on a 6.0 / 6.1 toolchain omit the flags and annotate explicitly (`basics`).
- **No `defaultIsolation(MainActor.self)` in a library package.** A UI-only package that is never used off the main actor may set it deliberately; say so in the PR.
- `public` is the package's contract; `package` for cross-target access inside the package family.
- A feature package depends on `Core` and, if needed, `Networking` — never on another feature.

## Feature package exposing one entry view

```swift
public struct OrdersFeature: View {
    public init(client: OrdersClient) { self.client = client }
    public var body: some View { OrdersList(client: client) }
    private let client: OrdersClient
}
```

The app target builds the client at the composition root and passes it in (initializer injection — [`architecture`](../../architecture/SKILL.md)).

## `.swift-format`

```json
{
  "version": 1,
  "indentation": { "spaces": 4 },
  "lineLength": 120,
  "maximumBlankLines": 1,
  "respectsExistingLineBreaks": true,
  "lineBreakBeforeEachArgument": true,
  "rules": { "AlwaysUseLowerCamelCase": true, "NeverForceUnwrap": true, "NeverUseForceTry": true }
}
```

`NeverForceUnwrap` / `NeverUseForceTry` lint via `swift-format lint`; tests are excluded by path in CI.

## `.swiftlint.yml`

```yaml
included: [App, Packages]
excluded: [.build, "**/.build", DerivedData]
opt_in_rules: [force_unwrapping, unused_import, unused_declaration, closure_spacing]
disabled_rules: [trailing_whitespace, line_length]
custom_rules:
  no_print:
    regex: '\b(print|NSLog|debugPrint|dump)\('
    message: Use os.Logger.
    severity: error
  no_gcd_main:
    regex: 'DispatchQueue\.main'
    message: Use @MainActor or await MainActor.run.
    severity: error
```

`disabled_rules` hands whitespace and line length to swift-format so the two tools do not fight.

## CI order

`xcrun swift-format lint --strict --recursive App Packages` → `swiftlint --strict` → build with the `Unit` test plan. The gate commands themselves belong to the release skill's pipelines, not this one.
