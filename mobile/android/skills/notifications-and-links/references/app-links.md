# App Links — assetlinks.json and verification

Verified 2026-10-10 against developer.android.com/training/app-links/verify-android-applinks. The page does not document the JSON shape or redirect rules; those lines come from the Digital Asset Links format and are marked.

## The hosted file

`https://<host>/.well-known/assetlinks.json`, one per unique host in the manifest filters:

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.example.app",
    "sha256_cert_fingerprints": ["14:6D:E9:…"]
  }
}]
```

- The fingerprint is the SHA-256 of the **signing certificate of the build users install**. With Play App Signing that is the **app signing key** shown in Play Console, not the upload key; list both if you also sideload upload-signed builds. (Digital Asset Links format — not on the verification page.)
- Served over valid HTTPS, `application/json`, **no redirect and no authentication** (not on the verification page — keep as a rule; the verifier fetches it unauthenticated).
- A debug build signed with the debug key is not covered; add a debug statement only on a non-production host.

## What the system checks

For each intent filter with `VIEW`, `BROWSABLE` + `DEFAULT` and `http` / `https`, the system asks each unique host for the file at install. On Android 11 (API 30) and lower the app becomes the default handler only if **every** host in the manifest verifies; on 12+ each host is independent.

## Verifying

| Step | Command |
|---|---|
| Wait ≥ 20 s after install, then read state | `adb shell pm get-app-links <package>` |
| Reset and re-verify (Android 12+) | `adb shell pm set-app-links --package <package> 0 all` then `adb shell pm verify-app-links --re-verify <package>`; wait a few minutes |
| Per-user selection state | `adb shell pm get-app-links --user cur <package>` |
| Open a link | `adb shell am start -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d "https://app.example.com/orders/<id>"` |

States: `verified` (pass) · `approved` (forced by shell) · `none` (wait, re-run) · `denied` · `legacy_failure` (rejected, reason unknown) · `1024`+ (device-specific verifier error — check network, retry).

## Update latency

- API 35+: the system re-verifies in the background; a change to `assetlinks.json` can take **up to seven days** to reach devices.
- API 34 and lower: a change is picked up only at install or update.
- To force it while testing, reinstall; server-side caching may still delay a new file by hours.

## Runtime association

`DomainVerificationManager.getDomainVerificationUserState(packageName).hostToStateMap` lists per-host state; for an unverified host, explain why and open `Settings.ACTION_APP_OPEN_BY_DEFAULT_SETTINGS` with `package:<name>`. Only one app per device is associated with a domain at a time.
