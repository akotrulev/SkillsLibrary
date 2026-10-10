# EAS — Build, credentials, Update, E2E job

For Expo apps. Docs: docs.expo.dev/eas, docs.expo.dev/eas-update. Pipeline YAML for *other* CI stays `devops-engineer`'s; the `.eas/workflows/*.yml` below is EAS's own config and lives with the app.

## Build profiles and versions

- `eas.json` holds the profiles (`development`, `preview`, `production`, and an `e2e-test` profile when E2E exists).
- Set `cli.appVersionSource` to `remote` and `autoIncrement: true` on the production profile: EAS owns the build number (monotonic, never hand-edited). The human `version` stays in `app.json`.
- Pin the image per profile (`ios.image`, `android.image`) — a named image, not `latest`.

## Credentials

- `eas credentials` manages iOS distribution certs and profiles, and the Android upload keystore, **remotely**. Nothing goes in the repo; `credentials.json` is for local builds only and is gitignored.
- For App Store upload use an **App Store Connect API key** registered with EAS (`eas submit`), not an Apple ID password.
- Play: a **service account key** with release-manager rights goes into EAS as a secret; the app signing key stays with Play App Signing.
- Build-time secrets are EAS environment variables (`secret` visibility), never `EXPO_PUBLIC_*` — that prefix is bundled and public.

## EAS Update and `runtimeVersion`

```json
{
  "expo": {
    "runtimeVersion": { "policy": "fingerprint" },
    "updates": {
      "url": "https://u.expo.dev/<project-id>",
      "codeSigningCertificate": "./code-signing/certificate.pem",
      "codeSigningMetadata": { "keyid": "main", "alg": "rsa-v1_5-sha256" }
    }
  }
}
```

- **`fingerprint` policy** hashes dependencies, native project files, custom native code and config (`@expo/fingerprint`). A change that touches native code changes the runtime version, so the update is not served to old binaries. This is the default for this library. `appVersion` is weaker: native changes without a version bump mismatch silently. A fixed string is for bare projects that manage it by hand.
- The cost of `fingerprint`: you cut a build more often. That is the point — it is the guard behind "never ship a native change over the air".
- **Never ship a native change over the air.** Before `eas update`, confirm the fingerprint equals the one on the target build (`npx expo-updates fingerprint:generate` against the installed build's runtime version — verify the exact subcommand with `--help`; it moved between SDKs).
- **Code signing:** generate a key pair, keep the **private key out of the repo** (CI secret), commit only the certificate referenced by `codeSigningCertificate`. The client rejects updates not signed by that chain.
- **Channels and rollout:** one channel per environment (`production`, `staging`); `eas update --channel production --rollout-percentage N` for a staged OTA; **rollback** by `eas update:rollback` / republishing the prior update. Same halt discipline as a store rollout.
- OTA boundary: Apple 2.5.2 / DPLA §3.3.1(B) and Play's device-and-network-abuse policy — see the parent skill.

## Symbols

- Hermes source maps: `expo export --source-maps` (or the Sentry / Crashlytics Expo plugin) and upload per release; the reporter's plugin does it on `eas build` via a post-build hook.

## EAS Workflows — the E2E job

Rule: **a simulator / emulator build, then a `type: maestro` job running the project's `.maestro/` flows.** The flows are written by `qa-mobile-typescript`'s Maestro lane (plan 003). **No flows → no E2E job — never an empty one.**

`eas.json` carries the build shape (the simulator / emulator setting is a profile field, not a workflow field):

```json
{
  "build": {
    "e2e-test": {
      "withoutCredentials": true,
      "ios": { "simulator": true },
      "android": { "buildType": "apk" }
    }
  }
}
```

`.eas/workflows/e2e-test-android.yml` (the iOS file differs only in `platform: ios`):

```yaml
name: e2e-test-android
on:
  pull_request:
    branches: ['main']
jobs:
  build_android_for_e2e:
    type: build
    params:
      platform: android
      profile: e2e-test
  maestro_test:
    needs: [build_android_for_e2e]
    type: maestro
    params:
      build_id: ${{ needs.build_android_for_e2e.outputs.build_id }}
      flow_path: ['.maestro/home.yml']
```

- `flow_path` lists real files under `.maestro/`; add flows there, never inline here.
- Source: docs.expo.dev/eas/workflows/examples/e2e-tests — re-verify the `type: maestro` params after 2027-01-15.
- Ids the flows select with come from the stack's test-id skill (`testID`); this job never edits them.
