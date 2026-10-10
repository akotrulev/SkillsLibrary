# iOS — secure-coding rules (Swift 6 / iOS 16–27)

Applies to SwiftUI and UIKit alike; React Native iOS reaches the same APIs through the libraries named in `react-native.md`. Everything here is a **source / `Info.plist` / entitlements** read; what only shows at run time is marked **requires dynamic test → `qa-security`**.

## 1. App Transport Security (MASVS-NETWORK-1)

- Keep ATS on. `NSAllowsArbitraryLoads = true` is a blocker; `NSAllowsArbitraryLoadsInWebContent` and `NSAllowsLocalNetworking` each need a recorded reason.
- A per-domain `NSExceptionDomains` entry (`NSExceptionAllowsInsecureHTTPLoads`, `NSExceptionMinimumTLSVersion` below 1.2) is recorded in the PR or commit that adds it with the domain, the owner and the removal date; reasons never go in an inline plist comment.
- Never bypass trust in code: a `URLSessionDelegate` whose `urlSession(_:didReceive:completionHandler:)` calls `.useCredential` for every `serverTrust` is a blocker (`MASTG-TEST-0396`); the same for `WKNavigationDelegate` (`0397`).
- Pinning, when the threat model warrants it: pin the SPKI hash through ATS `NSPinnedDomains` (declarative, supports a backup pin and `NSPinnedLeafIdentities` / `NSPinnedCAIdentities`) rather than hand-rolled `SecTrust` code. Whether it holds → **requires dynamic test → `qa-security`**.

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSPinnedDomains</key>
    <dict>
        <key>api.example.com</key>
        <dict>
            <key>NSIncludesSubdomains</key>
            <true/>
            <key>NSPinnedCAIdentities</key>
            <array>
                <dict>
                    <key>SPKI-SHA256-BASE64</key>
                    <string>base64-of-primary-ca-spki</string>
                </dict>
                <dict>
                    <key>SPKI-SHA256-BASE64</key>
                    <string>base64-of-backup-ca-spki</string>
                </dict>
            </array>
        </dict>
    </dict>
</dict>
```

## 2. Keychain and data protection (MASVS-STORAGE-1, CRYPTO-2)

Tokens, refresh tokens and keys live in the Keychain, never `UserDefaults`, plist or a file.

| `kSecAttrAccessible…` | Use for |
|---|---|
| `WhenUnlockedThisDeviceOnly` | **Default** for tokens used while the app is foregrounded; not backed up, not migrated |
| `AfterFirstUnlockThisDeviceOnly` | Credentials needed by background fetch, push handlers or extensions after the first unlock |
| `WhenPasscodeSetThisDeviceOnly` | Highest-value secrets; items vanish if the passcode is removed |
| `…Always…` | **Deprecated; never** |

- Always the `…ThisDeviceOnly` variants unless a restore-to-new-device flow is a requirement and is documented.
- Biometric-gated secrets use `SecAccessControl` with `.biometryCurrentSet` (invalidated on enrollment change, `MASWE-0022`) and an `LAContext`; a boolean `evaluatePolicy` result alone is not authentication (`MASWE-0020`).
- Private files: `FileProtectionType.complete` (or `completeUnlessOpen` where writes continue while locked) via `Data.write(to:options: .completeFileProtection)`; check `0299`.
- Exclude regenerable or sensitive files from iCloud / iTunes backup with `URLResourceValues.isExcludedFromBackup = true` (`MASWE-0006`, `MASTG-TEST-0215`).

```swift
func store(token: Data, account: String) throws {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: account,
        kSecValueData as String: token,
        kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
    ]
    SecItemDelete(query as CFDictionary)
    let status = SecItemAdd(query as CFDictionary, nil)
    guard status == errSecSuccess else { throw KeychainError.unhandled(status) }
}
```

## 3. App switcher snapshot and screen capture (PLATFORM-3)

iOS snapshots the window when the app backgrounds. For screens showing balances, codes, messages or medical data, cover the content on `scenePhase` becoming `.inactive` / `.background` (SwiftUI) or `sceneWillResignActive` (UIKit) and remove the cover on active. Secure text fields (`isSecureTextEntry`, `SecureField`) and `UITextContentType.oneTimeCode` keep input out of the keyboard cache; set `autocorrectionType = .no` for secrets. `UIScreen.isCaptured` / `userDidTakeScreenshotNotification` are signals, not protection. Whether the snapshot is blank → **requires dynamic test → `qa-security`** (`MASTG-TEST-0290`).

## 4. Pasteboard (MASVS-STORAGE-2, PLATFORM-3)

`UIPasteboard.general` is readable by other apps. Never put a secret there; for a "copy code" action use `UIPasteboard.general.setItems(_:options:)` with `.localOnly: true` and an `.expirationDate` (`MASTG-TEST-0278–0280`). iOS 16+ prompts the user on a cross-app paste; do not read the pasteboard at launch.

## 5. URL handlers, links and extensions (PLATFORM-1, CODE-4)

- **Prefer Universal Links** (verified `apple-app-site-association`, `applinks:` entitlement) over custom schemes, which any app can claim. Validate every inbound URL — scheme, host allow-list, path, and each parameter's type and range — before routing; never pass a URL parameter into a file path, SQL string or `WKWebView` load (`MASTG-TEST-0370`, `0395`).
- `application(_:open:options:)` and `onOpenURL` treat `options[.sourceApplication]` as informational only; a custom-scheme call can be forged.
- Share extensions, widgets and App Group containers: data shared through `UserDefaults(suiteName:)` or files is readable by every member of the group — no tokens there (`MASTG-TEST-0388`); share through a Keychain access group instead.
- Custom keyboards: `allowsOpenAccess` / full access is justified in review (`0390`); apps handling secrets can refuse third-party keyboards with `application(_:shouldAllowExtensionPointIdentifier:)` (`0389`).

## 6. Logging and diagnostics (STORAGE-2)

`os.Logger` only (CLAUDE.md § Mobile code rules). Interpolated values default to `private`; mark non-sensitive ones `privacy: .public` deliberately, and never log tokens, PII or request bodies (`MASWE-0005`). No `print` in release. Crash reporters get scrubbed breadcrumbs.

## 7. WebViews (PLATFORM-2)

`WKWebView` only (`UIWebView` is gone). Set `javaScriptEnabled` only if needed; load only allow-listed `https` origins and decide navigation in `decidePolicyFor`; `allowFileAccessFromFileURLs` / `allowUniversalAccessFromFileURLs` stay off (`0335`); expose native code through `WKScriptMessageHandler` with `WKContentWorld` isolation, validate every message's origin and payload, and never `evaluateJavaScript` with interpolated user data (`0377`, `0379`, `0380`).

## 8. Binary and entitlement hygiene (CODE-3, RESILIENCE-2)

Release builds: PIE and stack protectors on (Xcode defaults), ARC on, `get-task-allow` absent from the release entitlements (`MASTG-TEST-0261`), `DEBUG` code out of release, symbols stripped for release. These are properties of the built binary — **requires dynamic test → `qa-security`** (`mobile-app-scan`) to confirm.

## 9. Attestation and tamper signals (RESILIENCE-1, 4)

`DCAppAttestService` (App Attest) and `DeviceCheck` produce assertions that **a server** verifies; a client-side "is this attested" boolean is theatre. Jailbreak, debugger and hook detection are advisory signals sent to the server; their efficacy → **requires dynamic test → `qa-security`**.
