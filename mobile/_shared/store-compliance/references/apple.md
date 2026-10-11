# Apple — App Store rules that code and config satisfy

Verified 2026-10-10 against developer.apple.com (§4.4 of plan 002) except where a row says **unconfirmed**. Apple's documentation site renders client-side, so the Required Reason code tables could not be fetched as text in the session that wrote this file; the codes marked *confirmed* were read from a Microsoft Learn page that quotes Apple's table, the rest are recalled from Apple's documentation. **Before relying on an unconfirmed code, open Xcode → Product → Archive → Generate Privacy Report, or Apple's "Describing use of required reason API" page.** Re-verify this whole file after **2027-01-15**.

## 1. Privacy manifest (`PrivacyInfo.xcprivacy`)

Enforced at upload since **2024-05-01**. An app, and every third-party SDK / framework / dynamic library that touches a Required Reason API, carries its own manifest. Code in an SDK reports to the SDK's manifest; an SDK cannot rely on the app's.

| Key | Meaning |
|---|---|
| `NSPrivacyTracking` | Boolean — does the app or an SDK track users per ATT's definition |
| `NSPrivacyTrackingDomains` | Domains that are contacted for tracking; they are blocked until ATT consent |
| `NSPrivacyCollectedDataTypes` | Each collected data type: `…DataType`, `…Linked`, `…Tracking`, `…Purposes` |
| `NSPrivacyAccessedAPITypes` | One dict per Required Reason category: `NSPrivacyAccessedAPIType` + `NSPrivacyAccessedAPITypeReasons` |

Where the file comes from per lane:

| Lane | Source of the manifest |
|---|---|
| SwiftUI / UIKit | A `PrivacyInfo.xcprivacy` file in the app target's *Copy Bundle Resources* |
| Swift Package | A resource in the package target, declared `resources: [.copy("PrivacyInfo.xcprivacy")]` |
| Expo managed / CNG | `app.json` → `expo.ios.privacyManifests`; Expo aggregates SDK manifests at prebuild |
| RN bare | The file in the Xcode project; each pod ships its own via `s.resource_bundles` |

The merged result is verified, never assumed: Xcode → Archive → *Generate Privacy Report* produces one PDF aggregating every manifest in the build.

## 2. Required Reason API categories and reason codes

A declaration must match actual use, and the data may not be used for tracking. A use that fits no listed reason is requested from Apple, never invented.

| Category (`NSPrivacyAccessedAPIType`) | Triggering APIs (examples) | Reason codes |
|---|---|---|
| `NSPrivacyAccessedAPICategoryUserDefaults` | `UserDefaults`, `@AppStorage`, RN `AsyncStorage` / MMKV on iOS | `CA92.1` app-only (*confirmed*) · `1C8F.1` same App Group (*confirmed*) · `C56D.1` from an SDK (*confirmed*) · `AC6B.1` read of `com.apple.configuration.managed` / `com.apple.feedback.managed` (*confirmed*) |
| `NSPrivacyAccessedAPICategoryFileTimestamp` | `creationDate`, `modificationDate`, `fileModificationDate`, `stat` / `fstat` | `C617.1` inside the app container, app group or CloudKit container (*confirmed*) · `3B52.1` files the user granted access to · `DDA9.1` shown to the user · `0A2A.1` third-party SDK wrapper (**unconfirmed**) |
| `NSPrivacyAccessedAPICategorySystemBootTime` | `systemUptime`, `mach_absolute_time()` | `35F9.1` elapsed time between in-app events (*confirmed*) · `8FFB.1` absolute timestamps from boot reference · `3D61.1` third-party SDK wrapper (**unconfirmed**) |
| `NSPrivacyAccessedAPICategoryDiskSpace` | `volumeAvailableCapacityKey`, `volumeAvailableCapacityForImportantUsageKey`, `statfs` | `E174.1` check space before writing in the container (*confirmed*) · `85F4.1` display to the user · `7D9E.1` / `B728.1` narrower cases (**unconfirmed**) |
| `NSPrivacyAccessedAPICategoryActiveKeyboards` | `activeInputModes` | `3EC4.1` customise UI in a keyboard extension · `54BD.1` customise UI in the app (**unconfirmed**) |

A default .NET MAUI app needs `C617.1`, `35F9.1`, `E174.1` plus `CA92.1` when it uses preferences — the same set a React Native app typically needs once `expo-file-system`, timers and storage are present.

```xml
<key>NSPrivacyAccessedAPITypes</key>
<array>
    <dict>
        <key>NSPrivacyAccessedAPIType</key>
        <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
        <key>NSPrivacyAccessedAPITypeReasons</key>
        <array><string>CA92.1</string></array>
    </dict>
</array>
```

Expo equivalent:

```json
{
  "expo": {
    "ios": {
      "privacyManifests": {
        "NSPrivacyAccessedAPITypes": [
          {
            "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults",
            "NSPrivacyAccessedAPITypeReasons": ["CA92.1"]
          }
        ]
      }
    }
  }
}
```

## 3. Listed third-party SDKs

Apple publishes a list of commonly used SDKs that **must** ship a privacy manifest and a valid code signature when included in an app (source: developer.apple.com/support/third-party-SDK-requirements). Rules the repo can check:

- Dependency versions are at or above the SDK vendor's first manifest-bearing release (Firebase, Google Mobile Ads, Facebook / Meta SDK, Alamofire, AFNetworking, Lottie, SDWebImage, Realm and similar are on the list — read the current list, do not trust this sentence).
- Signed XCFramework / binary SDKs carry the vendor signature; a repackaged or vendored copy loses it.
- CocoaPods trunk goes read-only on **2026-12-02** — a pod pinned to a spec the repo cannot refetch is a release risk.
- Never author a manifest for a vendor's SDK; update the SDK.

## 4. Purpose strings

Every protected resource the binary can reach needs its `NS…UsageDescription` in `Info.plist` — camera, microphone, photo library (`NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription`), location (`NSLocationWhenInUseUsageDescription`, `…AlwaysAndWhenInUse…`), contacts, Bluetooth, Face ID (`NSFaceIDUsageDescription`), motion, tracking. The string states **why this app needs it, for this feature** — "Used to scan receipts" passes, "Needs camera access" is a rejection. In Expo they are set through the module's config plugin (`expo-camera` `cameraPermission`) so each is authored once.

## 5. App Tracking Transparency and the EU prompt

- Any "tracking" (linking app data with third-party data for advertising or sharing with data brokers) requires `NSUserTrackingUsageDescription` and an `ATTrackingManager.requestTrackingAuthorization` call **before** the tracking SDK initialises.
- `NSPrivacyTrackingDomains` lists the tracking endpoints; without consent iOS blocks them.
- **iOS 27.2 adds an EU alternative prompt** (Apple guideline 5.1.2(i)): where the alternative applies, the ATT call path is not the only compliant one. The exact API is **unconfirmed** — read guideline 5.1.2 and the iOS 27.2 release notes before wiring it; the code must branch on the OS capability, not on a region constant.
- Ask after a pre-prompt screen that explains the value (CLAUDE.md § Mobile code rules, permissions in context); the denied path is a working screen.

## 6. Account deletion — guideline 5.1.1(v)

An app that lets a person create an account must let them **delete it inside the app**. A "contact support" link or a web-only flow is a rejection.

- Reachable in at most a few taps from Settings / Profile; names what is deleted; confirms; shows completion.
- Calls a backend deletion endpoint that removes or anonymises the data (legal-retention carve-outs are stated).
- **Sign in with Apple:** when the account was created with Apple, the deletion flow must revoke the user's Apple token through Apple's `/auth/revoke` REST endpoint using the server-side client secret (a signed JWT). Revoking on-device is not possible; the call belongs to the backend.
- Subscriptions are separate: deleting an account does not cancel an App Store subscription — say so and link to subscription management.

## 7. Downloaded and interpreted code — 2.5.2, DPLA §3.3.1(B)

An app may not download, install or execute code that introduces or changes features after review. Interpreted JavaScript run by the app's own WebKit / JavaScriptCore runtime is permitted **provided it does not change the primary purpose** of the app as reviewed.

For OTA tooling (`expo-updates`, EAS Update, CodePush successors): ship JS and assets only; never native modules, never new entitlements or permissions; keep updates inside the declared runtime version (`runtimeVersion` fingerprint policy); do not use updates to enable a feature that was not in review. `mobile-<stack>:release` owns the mechanics; this file owns the rule.

## 8. Payments — 3.1.1, and login — 4.8

- **3.1.1:** digital goods and features unlocked in the app use In-App Purchase. The repo check: no external payment link or price comparison for digital goods outside a region/entitlement where Apple permits it, no custom paywall that bypasses StoreKit. Mechanics live in `mobile-<stack>:in-app-purchases`.
- **4.8:** an app whose primary sign-in is a third-party or social login offers an equivalent login service that limits data collection to name and email, lets the user hide their email, and does not track — Sign in with Apple satisfies it. An app whose only login is the company's own account system is exempt.

## 9. Sharing data with third-party AI — 5.1.2

Before personal data leaves the device for a third-party AI service, the app discloses the recipient and what is sent, and gets **explicit consent** — a dedicated screen or sheet, not buried in terms. Repo check: every call that sends user content to an external model API sits behind a consent flag read from persisted state, and the consent copy names the provider.

## 10. Age rating and labels (console only)

- The **age-rating questionnaire** has been mandatory for every app since **2026-01-31**; answers must match features in the binary (UGC, web access, chat, AI).
- **App Privacy nutrition labels** must match the merged privacy manifests and SDK behaviour — the privacy report is the evidence.
- **Accessibility Nutrition Labels** are voluntary. Claim a label only for a feature that was tested on a device; a false claim is worse than none. The stack's `accessibility` skill owns the implementation.

## 11. Upload dates

| Date | Rule |
|---|---|
| 2026-04-28 | Uploads built with the Xcode 26 SDK |
| 2026-09-09 | Minimum deployment target iOS 13 |
| 2026-12-02 | CocoaPods trunk read-only |
| April 2027 | Uploads need the iOS 27 SDK |

Linking the iOS 27 SDK makes mandatory: the UIScene lifecycle, a launch screen and Liquid Glass (`UIDesignRequiresCompatibility` is ignored). Plan these before April 2027 rather than discovering them at upload.
