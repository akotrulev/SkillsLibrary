# Security — macOS reference

Lane: Swift 6 / SwiftUI first, AppKit where the codebase is AppKit; Developer ID or Mac App Store; sandboxed or not. Facts from `docs/research/012-desktop-plugins/macos.md` §3.1, §3.3, §4 (verified 2026-11-15). The Apple pages are script-rendered; entries marked *re-verify* are from Apple's documented behaviour and must be re-read before a finding cites them.

## Keychain

Tokens, refresh tokens and keys live in the Keychain, never in `UserDefaults`, a plist, a file or the bundle.

```swift
func store(token: Data, account: String) throws {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: "com.example.app.auth",
        kSecAttrAccount as String: account,
        kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        kSecValueData as String: token,
        kSecUseDataProtectionKeychain as String: true
    ]
    SecItemDelete(query as CFDictionary)
    let status = SecItemAdd(query as CFDictionary, nil)
    guard status == errSecSuccess else { throw KeychainError.unhandled(status) }
}
```

- `kSecUseDataProtectionKeychain: true` selects the data-protection keychain, the same model as iOS; the legacy file keychain prompts and is ACL-based.
- A class without `ThisDeviceOnly` is allowed only with a recorded restore need. `kSecAttrAccessibleAlways*` is never allowed.
- An app group that shares tokens widens the blast radius: keep tokens in the app's own access group (row K21).

## Sandbox and entitlements

- App Sandbox is mandatory for the Mac App Store (guideline 2.4.5) and the default for new Developer ID apps. A Developer ID app that skips it records why.
- Every entitlement carries a reason in the entitlements review: `com.apple.security.network.client` yes, `network.server` only for a listener, `files.user-selected.read-write` over `files.all`. A temporary-exception entitlement is a finding unless a store reviewer asked for it.
- macOS 27 denies access to other teams' containers and app-group containers by default, and apps cannot read the TCC database: code that depended on either is a defect, not a permission to request.
- Xcode 27 ships an `audit-xcode-security-settings` agent skill (Enhanced Security, entitlements); use it where installed, never require it.

## Hardened Runtime and library validation

- Hardened Runtime is required for notarization and stays on for every release configuration (`ENABLE_HARDENED_RUNTIME = YES`; `codesign --options runtime`). *re-verify*: it enforces library validation (only Apple- or same-Team-signed libraries load) and ignores `DYLD_*` variables.
- Relaxations, narrowest first: `com.apple.security.cs.allow-jit` (a `MAP_JIT` region) before `allow-unsigned-executable-memory`; `disable-library-validation` only for a host that loads third-party plug-ins or a framework signed by another team, with the reason beside it; `allow-dyld-environment-variables` essentially never in release.
- Plug-ins inherit the host's entitlements (research §3.1): a plug-in host that holds `disable-library-validation` and a TCC permission hands that permission to every plug-in.
- Release entitlements never carry `com.apple.security.get-task-allow` (notarization rejects it) or the debugger entitlement.
- Dylib hijacking: link frameworks by `@rpath` to locations inside the bundle; no `LC_LOAD_WEAK_DYLIB` to a path a user can write; the load path is part of the audit (`otool -L` on a built app is **requires dynamic test → `qa-security`**).
- Sparkle with library validation: ad-hoc local builds can fail to load it; sign Debug with an Apple Development certificate, or relax library validation in Debug only.

## XPC and helpers

- `SMAppService` registers login items, agents and daemons; a daemon is root: keep its surface tiny and its input validated. `launchd` on macOS 27 ignores plists carrying the quarantine attribute.
- A listener rejects a peer that does not satisfy a code-signing requirement:

```swift
let listener = try XPCListener(service: "com.example.app.helper") { request in
    request.accept { (message: HelperRequest) in
        try await handler.handle(message)
    }
}
```

Set the peer requirement (team id and bundle id) on the session or listener — `XPCListener.InitializationOptions` / `setPeerRequirement` (Swift XPC, macOS 14+, *re-verify the exact API*); with `NSXPCConnection`, `setCodeSigningRequirement(_:)`. A listener that accepts any peer is a blocker for a privileged helper.
- Every message type is a `Codable` struct decoded with bounds; paths in a message are canonicalised and checked against an allowed root before use.

## URL schemes, file activation, Services

- `onOpenURL` / `application(_:open:)` / `NSAppleEventManager` handlers treat the URL as untrusted: check `scheme`, `host`, `path` components against an allow-list, parse query items into a typed value, and reject the rest. A URL never becomes a file path, a shell argument or an `NSPredicate` string.
- A custom URL scheme is claimable by any app: it never carries a credential and never completes an authorisation; an OAuth redirect uses `ASWebAuthenticationSession` (`auth0-macos`).
- A document-type handler opens a file read-only first, bounds its size, and treats the content as hostile. Opened files outside the sandbox container come only through open panels and security-scoped bookmarks, with start/stop balanced.
- A hand-built Apple Events or AppleScript surface (`NSAppleScript` with an interpolated string) is command injection: use an argument array or `NSUserScriptTask`.

## `WKWebView`

```swift
final class Allowlist: NSObject, WKNavigationDelegate {
    private let hosts: Set<String>

    init(hosts: Set<String>) { self.hosts = hosts }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction) async -> WKNavigationActionPolicy {
        guard let url = action.request.url, url.scheme == "https", let host = url.host, hosts.contains(host) else {
            return .cancel
        }
        return .allow
    }
}
```

- Decide every navigation (and frame navigation) in `decidePolicyFor`; open anything off the list in the default browser with `NSWorkspace.open`.
- A `WKScriptMessageHandler` exposes one audited message name per capability; the body is validated as untrusted and the sender's `frameInfo.request.url` checked; no generic "call native" proxy.
- `allowsContentJavaScript = false` per navigation for static content. `isInspectable` stays `false` in release (*re-verify*: macOS 13.3+, default false); a `#if DEBUG` guard is the only place it is `true`.
- Local content loads with `loadFileURL(_:allowingReadAccessTo:)` pointing at one folder, never the user's home.
- Cookies and storage for untrusted sites use a non-persistent `WKWebsiteDataStore`.

## What a source read cannot prove

Entitlements actually present in the signed app (`codesign -d --entitlements -`), library-validation behaviour at launch, XPC peer rejection, what the Keychain item's ACL really is, Gatekeeper / quarantine behaviour, and whether the bridge validates every path: **requires dynamic test → `qa-security`**.
