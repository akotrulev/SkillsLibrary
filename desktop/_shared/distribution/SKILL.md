---
name: distribution
description: Use when a macOS or Windows desktop app is signed, notarized, packaged, published or auto-updated. Triggers "notarize", "MSIX", "Sparkle". Not for pipeline YAML (devops-engineer).
disable-model-invocation: true
---

# Desktop — Distribution, Signing and Updates

Rules for getting a desktop build from a commit to a user's machine: **which channel carries it, what signs it, how it updates, and what the CI runner and secret store must look like.** Tool detail lives in one reference per platform.

**The fence.** This skill states *what must be true*; it writes no pipeline. Workflow / pipeline YAML (GitHub Actions, Azure Pipelines) is `devops-engineer`'s (`devops/github-actions`, `azure-pipelines`); the test-suite CI lane is `qa-cicd-<stack>`'s. Where a rule needs a pipeline step, name the step and hand it over.

## Version lane (verified 2026-11-15)

| Fact | Value | Re-verify after |
|---|---|---|
| Sparkle | **2.10.1** (2026-10-25); macOS 12+; EdDSA feed | 2027-01-15 |
| Velopack | **1.2.161** (2026-09-29); **1.2.158 is deprecated (critical bugs)**; 1.3 is preview | 2027-01-15 |
| Azure Artifact Signing | Basic **$9.99/month** (5,000 signatures, 1 profile), Premium $99.99/month; billed from account creation, not pro-rated | 2027-01-15 |
| Developer ID CA | Original Sub-CA expires **2027-02-01**; re-sign `.pkg` with a **G2** certificate | 2027-02-01 |
| `notarytool` | Only tool the notary accepts since 2023-11-01 (`altool` rejected) | — |
| Mac App Store | No published macOS SDK floor for uploads; no `com.apple.quarantine` on any file since 2025-02-18 | 2027-01-15 |
| GitHub-hosted macOS | `macos-latest` = `macos-26` arm64; `xcode-27` label in preview; `macos-14` retired 2026-11-02; Intel only `macos-26-intel` / `macos-15-intel` | 2027-01-15 |
| Windows | .NET 10 LTS / 11 STS; .NET 8 and 9 out of support since 2026-11-10; Windows App SDK 2.6.x | 2027-01-15 |

Sources: developer.apple.com/news (upcoming requirements, Developer ID CA) · github.com/sparkle-project/Sparkle/releases · nuget.org/packages/velopack · learn.microsoft.com/azure/artifact-signing · github.com/actions/runner-images. **Detect the project's channel first** (`.entitlements`, `Package.appxmanifest`, `Info.plist`, `.csproj`), then follow the matching reference.

## Procedure

1. **Detect** the shipped channel per platform from the files above. One channel owns each artifact; several may coexist (Store plus direct download).
2. **Decide the channel** with the decision tables below. Write the decision and the reason in the project's docs.
3. **Version.** Two numbers, two jobs. The human version (`CFBundleShortVersionString` / MSIX `Version` four-part) is bumped by a person. The build number (`CFBundleVersion` / the fourth MSIX part) is **monotonic and machine-assigned**, never reused. Sparkle compares `CFBundleVersion`; a non-monotonic one makes updates invisible.
4. **Sign with nothing in the repo.** No `.p12`, `.pfx`, `.p8`, notary password or Sparkle private key in git or in the bundle. See *Where secrets live*.
5. **Notarize / trust-chain before anything ships.** macOS Developer ID: Hardened Runtime, secure timestamp, `notarytool`, staple. Windows: Store re-signing, or Artifact Signing with a timestamp.
6. **Update through a signed channel only.** Sparkle EdDSA feed over HTTPS; Velopack over HTTPS from a signed release; Store-managed; `.appinstaller` from a CA-trusted signed package. An update never restarts the app over unsaved work (`desktop code rules`).
7. **Pin the toolchain.** The runner image and Xcode / SDK version are named, never `latest`.
8. **Ship to a ring first.** Direct channels: a beta feed (Sparkle channel, Velopack channel, Store flight) before stable. Store: TestFlight for Mac / Store flights before production.

## macOS channel decision

| Question | Developer ID (direct) | Mac App Store |
|---|---|---|
| Sandbox | Optional, recommended | **Required** |
| Review | Notarization (automated) | App Review |
| Signing | Developer ID Application (+ Installer for `.pkg`) | Apple Distribution + Mac Installer Distribution |
| Updates | Your own: **Sparkle 2** | **Mac App Store only** (2.4.5) |
| Needs a helper, kext-like system access, own licensing, full-disk workflows | Fits | Rarely fits |
| Beta | Own feed / channel | TestFlight for Mac |

Choose **Mac App Store** when the app is sandbox-clean and wants discovery, payments and updates handled. Choose **Developer ID** when the app needs what 2.4.5 forbids (self-updater, licence keys, downloaded code, root escalation) or ships outside the store for a business reason. Both channels can ship the same codebase; they never share an updater: **no Sparkle in a Mac App Store build.** Detail: [`references/macos.md`](references/macos.md).

## Windows channel decision

| Question | Microsoft Store (MSIX) | MSIX sideload | Unpackaged + Velopack |
|---|---|---|---|
| Signing | Microsoft re-signs, free | Your CA-trusted cert (Artifact Signing) | Your cert (Artifact Signing) |
| Updates | Store-managed | `.appinstaller` | Velopack |
| SmartScreen | Never warns | Reputation per cert and file hash | Reputation per cert and file hash |
| Identity / capabilities | Full package identity | Full package identity | None; needs a recorded reason |
| Enterprise, offline, no Store | No | Fits | Fits |

**Default: packaged MSIX, framework-dependent, through the Store**; it is Microsoft's recommended path and adds no signing cost. Choose **sideload** for enterprise or closed distribution that needs package identity. Choose **unpackaged + Velopack** only with a recorded reason (a dependency that cannot run under identity, a custom installer flow). `winget` is an add-on to any path, not a channel. ClickOnce is not supported for WinUI; it is WPF / WinForms only. Detail: [`references/windows.md`](references/windows.md).

## Signing and update rules

| # | Rule | Platform |
|---|---|---|
| R1 | Developer ID builds: Hardened Runtime, secure timestamp, no `get-task-allow`, every nested executable signed inside-out (never `--deep`), notarized and stapled | macOS |
| R2 | `.pkg` signed with a Developer ID Installer cert from the **original CA stops installing on 2027-02-01**: re-sign with a **G2** cert (select the G2 Sub-CA in Xcode) | macOS |
| R3 | Mac App Store uploads carry no `com.apple.quarantine`; sandbox entitlements declared with a reason | macOS |
| R4 | Sparkle: `SUPublicEDKey` in `Info.plist`, `SUFeedURL` over HTTPS, `SURequireSignedFeed` on, EdDSA private key never in the repo; DSA retired | macOS |
| R5 | Architectures stated per deployment target; `pkgbuild` sets `hostArchitectures` explicitly | macOS |
| R6 | Every PE file and the package signed; one signing identity for the life of the app (SmartScreen reputation follows it); signed files never modified after signing | Windows |
| R7 | **EV certificates no longer bypass SmartScreen**; Smart App Control blocks unsigned executables with no reputation: unsigned is never acceptable | Windows |
| R8 | MSIX `Publisher` equals the certificate subject exactly | Windows |
| R9 | `.appinstaller` served over HTTPS; the `ms-appinstaller:` one-click URI is disabled by default since December 2023 | Windows |
| R10 | Velopack: pin **1.2.161 or newer stable** (never 1.2.158); feed over HTTPS; the release set signed | Windows |
| R11 | The app never requires administrator or root to install or update (elevated apps lose notifications) | both |
| R12 | HTTPS only; certificate validation never overridden in the updater | both |

## Azure Artifact Signing

The Windows signing service (formerly Trusted Signing). Public Trust certificates are issued to **organizations in the United States, Canada, the EU, the UK, Australia, New Zealand, Japan, South Korea, Singapore, Switzerland, Norway and Israel; individual developers must be in the United States or Canada** (checked 2026-11-15, learn.microsoft.com quickstart). Outside those lists the Store (free re-signing) or a conventional CA certificate is the path. It needs a **paid** Azure subscription (free, trial and sponsored are rejected), organization identity validation takes 1–20 business days, certificates are short-lived and never given to you, and it issues **no EV certificates**. Signing runs through SignTool plus the dlib, the Azure DevOps task or GitHub Action, or `winapp az-sign`; the identity needs the *Artifact Signing Certificate Profile Signer* role. Handing it to a pipeline is `devops-engineer`'s work.

## CI runners

| Rule | Why |
|---|---|
| Name the image: `macos-26` (arm64) or `macos-26-intel`; never `macos-latest` | The SDK changes under a release with no diff; `macos-14` is gone |
| Name the Xcode: `xcode-select` / `DEVELOPER_DIR` to an explicit version | Xcode 27 installs only on Apple-silicon Macs on Tahoe 26.6+ |
| Windows: `windows-2025` plus the .NET SDK pinned by `global.json` | A floating SDK changes the TFM floor |
| Signing and notarization jobs run on protected branches / tags only | A fork PR must never reach a signing secret |
| A signing job uses the shortest-lived credential the platform offers (OIDC to Azure, an App Store Connect API key) | A long-lived secret on a runner is a standing breach |

## Where secrets live

| Secret | Lives in | Never |
|---|---|---|
| Developer ID / Distribution `.p12` | CI secret store, imported into a temporary keychain deleted after the job | In git; in a runner image; a login keychain on a shared runner |
| Notarization credentials | App Store Connect API key (`.p8`, key id, issuer id) in the secret store, stored via `notarytool store-credentials` into the temporary keychain | An Apple ID password or app-specific password in a script |
| Sparkle EdDSA private key | Keychain on the release machine, or the secret store; exported only to the signing step | In the repo; next to the appcast |
| Windows signing | Artifact Signing (no key on disk) via OIDC / managed identity; or an HSM / cloud-KMS-held key | A `.pfx` in git; a password in a `.csproj` or script; `winapp cert generate` output in production (test only) |
| Store credentials | Partner Center / App Store Connect API credentials in the secret store | In `Package.appxmanifest` or the repo |

## Output

When the task is a design: the channel decision per platform with its reason, the version scheme, the signing chain, the update channel, the runner pins, and the list of secrets with their store. When it is a review: the `L` rows hit, each with its location and severity. Report what was *not* verified: console-only facts (App Store Connect, Partner Center, Azure portal) are reported as unverified, never assumed.

## Reference files

| File | Contents |
|---|---|
| [`references/macos.md`](references/macos.md) | Developer ID and Mac App Store flows, Hardened Runtime and entitlements, `notarytool` and stapling, DMG / `.pkg`, the 2027-02-01 CA, Sparkle 2, architectures |
| [`references/windows.md`](references/windows.md) | Store, MSIX, `.appinstaller`, `msixbundle`, `winget`, Velopack, Artifact Signing, SmartScreen / Smart App Control, `winapp` |
| [`references/audit-checks.md`](references/audit-checks.md) | Rows `L1…Ln`; the `Platforms` column routes each row to the macOS and Windows checklists |

Siblings: `desktop/_shared/security` (update-channel integrity, runtime signature checks), `desktop/_shared/observability` (symbols), `devops-engineer` (pipelines), `mobile-<stack>:release` (the mobile counterpart).
