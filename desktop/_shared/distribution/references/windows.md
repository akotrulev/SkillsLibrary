# Windows distribution — Store, MSIX, Velopack, Artifact Signing

Verified 2026-11-15 against learn.microsoft.com (choose-distribution-path, smartscreen-reputation, artifact-signing), nuget.org and the winapp CLI guide. Pipeline YAML is `devops-engineer`'s; this file names the steps.

## Contents

1. Choose a path
2. Microsoft Store
3. MSIX sideload and `.appinstaller`
4. Unpackaged and Velopack
5. Azure Artifact Signing
6. SmartScreen and Smart App Control
7. `winget`
8. Architectures and bundles
9. CI and secrets

## 1. Choose a path

| Path | Signing | Updates | Use when |
|---|---|---|---|
| **Store, packaged MSIX, framework-dependent** | Microsoft re-signs, free | Store | Default (template default; Microsoft's recommended path) |
| Store, MSI / EXE | Installer and every PE file signed with a Microsoft Trusted Root Program certificate | None from the Store | An existing installer cannot become MSIX |
| MSIX sideload | CA-trusted certificate | `.appinstaller` | Enterprise or closed distribution that needs package identity |
| Unpackaged (`WindowsPackageType=None`) + Velopack | Your certificate | Velopack | A recorded reason: a dependency that cannot run under identity |
| Packaged with external location | Your certificate | Your own | Brownfield apps adding identity |
| ClickOnce | Your certificate | ClickOnce | **WPF and WinForms only; not supported for WinUI** |

Store accounts: individuals register free (since September 2025, ID and selfie, no card); company accounts are free since 2026-05-07 (Entra ID sign-up).

## 2. Microsoft Store

- Packaged MSIX, framework-dependent. Submissions are re-signed by Microsoft, so no certificate is bought.
- Store apps never get a SmartScreen warning.
- Updates are Store-managed; the app ships no updater of its own. Flights (rings) are the beta channel.
- `Package.appxmanifest`: declare only the capabilities used, each with a reason; never `runFullTrust` without one.

## 3. MSIX sideload and `.appinstaller`

- The package `Publisher` must equal the certificate subject exactly; a mismatch fails signing with `0x8007000b`.
- The signing certificate must chain to a root the target machine trusts (a public CA or Artifact Signing). A self-signed certificate is test-only: `winapp cert generate` makes a development certificate with a default password and **never signs a release**.
- Auto-update uses an `.appinstaller` file served over HTTPS. The `ms-appinstaller:` one-click URI has been **disabled by default since December 2023**; link to the `.msix` / `.appinstaller` download instead.
- Rollback: publish a higher four-part version containing the old code.
- Packaging commands: `winapp pack`, or `MakeAppx`; signing: `SignTool` or `winapp az-sign`.

## 4. Unpackaged and Velopack

- **Velopack 1.2.161** (2026-09-29) is the stable version. **1.2.158 is deprecated for critical bugs**; 1.3 is preview. Pin 1.2.161 or a newer stable.
- Pipeline steps (named, not written): `vpk pack` produces the installer, the full package and deltas; `vpk upload` / a static host serves the feed over HTTPS; sign the binaries and the Setup before packing.
- Velopack installs per user without elevation, which satisfies the never-require-admin rule. Do not ship an installer that asks for UAC.
- `PublishSingleFile` only for unpackaged and self-contained builds.
- `PasswordVault` behaviour for unpackaged apps is **not verified** (plan §4.6); `desktop/_shared/security` owns the storage choice.

## 5. Azure Artifact Signing

Formerly Trusted Signing. Verified 2026-11-15 (learn.microsoft.com/azure/artifact-signing/quickstart).

| Fact | Value |
|---|---|
| Price | Basic $9.99/month (5,000 signatures, 1 certificate profile); Premium $99.99/month (100,000, 10 profiles); billed in full from account creation |
| **Eligibility, Public Trust** | **Organizations: United States, Canada, EU, UK, Australia, New Zealand, Japan, South Korea, Singapore, Switzerland, Norway, Israel. Individual developers: United States or Canada only.** Private Trust has no geographic limit |
| Subscription | Paid Azure subscription; free, trial and sponsored are rejected |
| Identity validation | Portal only; organizations 1–20 business days; individuals through a Verified ID check; must be renewed or signing stops |
| Certificates | Short-lived, held in the service (FIPS 140-3 Level 3), never handed over; always timestamped |
| Certificate type | **No EV certificates**, and none planned |
| Roles | *Identity Verifier* to validate; *Certificate Profile Signer* to sign |
| Signing routes | SignTool + dlib, the Azure DevOps task, the GitHub Action, PowerShell, the SDK, or `winapp az-sign` |
| Timestamp health | `curl http://timestamp.acs.microsoft.com` returns 200 |
| Regions | Resources only in listed Azure regions (for example East US, West Europe, North Europe) |

Outside the eligibility list: use the Store (free re-signing) or a conventional CA code-signing certificate held in an HSM or cloud KMS. The CN and O on the certificate are the validated legal name; customizing them is not possible. For MSIX, set the manifest `Publisher` to the full subject string copied from the portal.

## 6. SmartScreen and Smart App Control

| Fact | Consequence |
|---|---|
| Store apps never warn | Prefer the Store to avoid the reputation ramp |
| **EV certificates no longer bypass SmartScreen** | Do not buy EV for SmartScreen |
| Reputation builds per file hash and per publisher certificate over weeks | Keep **one** signing identity; never modify a signed file |
| **Smart App Control** (Windows 11) blocks unsigned executables without positive reputation, every executable, not only downloads | Sign every PE file, including helpers and DLLs the app launches |
| A false positive | Submit the signed file at microsoft.com/wdsi/filesubmission |

## 7. `winget`

A manifest in `microsoft/winget-pkgs` works on top of any path; it points at a signed, versioned installer URL. Pipeline steps: `wingetcreate update` and a PR (named, written by `devops-engineer`). The installer hash in the manifest must match the published artifact byte for byte, so re-signing after publishing breaks the manifest.

## 8. Architectures and bundles

x64 and ARM64; x86 is supported but secondary. Multi-architecture MSIX ships as an `.msixbundle`. .NET 11 needs x86-64-v2 or Arm64 LSE. TFM `net10.0-windows10.0.26100.0`; the Windows App SDK API floor is Windows 10 1809. **.NET 8 and 9 are out of support since 2026-11-10**: flag them, never target them.

## 9. CI and secrets

- Image `windows-2025`; the SDK pinned in `global.json`; Windows App SDK pinned by package version.
- Signing authenticates with OIDC or a managed identity into Artifact Signing, so no key sits on the runner. Where a certificate is unavoidable it lives in an HSM or cloud KMS, never as a `.pfx` in the repo.
- Signing jobs run on protected refs only.
- The Velopack feed, the `.appinstaller` and the `winget` manifest all point at HTTPS URLs the project controls.
