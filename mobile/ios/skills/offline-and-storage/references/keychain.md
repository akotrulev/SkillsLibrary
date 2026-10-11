# Keychain — the wrapper, biometric gating, groups, wipe

The rules and the audit are [`mobile-<stack>:security`](../../../../_shared/security/SKILL.md) § 2. This file is the Swift that satisfies them. **Every item uses a `…ThisDeviceOnly` class** — `WhenUnlockedThisDeviceOnly` by default, `AfterFirstUnlockThisDeviceOnly` where a background task, push handler or extension reads it after the first unlock.

## 1. One small wrapper — add-or-update, typed errors

```swift
struct KeychainStore: Sendable {
    let service: String

    func set(_ data: Data, for account: String) throws {
        let key: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        let updated = SecItemUpdate(key as CFDictionary, attributes as CFDictionary)
        if updated == errSecItemNotFound {
            let added = SecItemAdd(key.merging(attributes) { $1 } as CFDictionary, nil)
            guard added == errSecSuccess else { throw KeychainError.unhandled(added) }
        } else if updated != errSecSuccess {
            throw KeychainError.unhandled(updated)
        }
    }

    func data(for account: String) throws -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        switch status {
        case errSecSuccess: return result as? Data
        case errSecItemNotFound: return nil
        default: throw KeychainError.unhandled(status)
        }
    }

    func remove(_ account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw KeychainError.unhandled(status) }
    }
}

enum KeychainError: Error { case unhandled(OSStatus) }
```

- **Update first, add on `errSecItemNotFound`** — delete-then-add opens a window with no item and loses the access control.
- The wrapper is a concrete struct: one implementation. Tests use a distinct `service` per run and remove their items in teardown; the unit-test seam appears when a second implementation (an in-memory fake) is needed.
- **The first read happens off the main actor** and the result is held by the `TokenStore` actor ([`networking`](../../networking/SKILL.md)).
- `errSecInteractionNotAllowed` means the device is locked (a background read of a `WhenUnlocked` item) — retry later; it is not a sign-out.

## 2. Biometric-gated secrets

```swift
func makeBiometricAccess() throws -> SecAccessControl {
    var error: Unmanaged<CFError>?
    guard let access = SecAccessControlCreateWithFlags(
        nil,
        kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
        .biometryCurrentSet,
        &error
    ) else { throw error!.takeRetainedValue() }
    return access
}
```

Add `kSecAttrAccessControl: access` (instead of `kSecAttrAccessible`) and `kSecUseAuthenticationContext: LAContext()` to the add / read query; the system prompts for Face ID / Touch ID on read. **`.biometryCurrentSet` invalidates the item when enrolment changes** — the app handles `errSecItemNotFound` / `errSecAuthFailed` as "re-authenticate with the password". A bare `LAContext.evaluatePolicy` result gating a UI flow protects nothing (`MASWE-0020`); the secret itself must be behind the access control. The prompt and its denied path are [`device-features`](../../device-features/SKILL.md)'s.

## 3. Access groups — sharing with an extension

Secrets shared with an extension or a sibling app go through a **Keychain access group** (`kSecAttrAccessGroup`, declared in the `keychain-access-groups` entitlement), never an App Group `UserDefaults` suite or file. The class is still `…ThisDeviceOnly`.

## 4. First launch and logout

```swift
func clearIfFreshInstall(defaults: UserDefaults, keychain: KeychainStore, accounts: [String]) throws {
    guard !defaults.bool(forKey: "hasLaunchedBefore") else { return }
    for account in accounts { try keychain.remove(account) }
    defaults.set(true, forKey: "hasLaunchedBefore")
}
```

Keychain items can outlive an uninstall; the flag lives in `UserDefaults` (which does not), so a reinstall starts signed out. Logout removes the access token, refresh token and any derived keys, clears the SwiftData / Core Data store and the caches, and revokes the refresh token server-side.
