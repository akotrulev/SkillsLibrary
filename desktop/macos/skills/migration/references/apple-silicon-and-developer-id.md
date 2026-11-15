# Intel → Apple silicon only, and the Developer ID CA expiry

Two **dated** moves that one run often handles together, because both change what the build and the installer say about the Mac. Facts are plan §4.1's and `desktop/_shared/distribution/references/macos.md` §3 and §7; re-read developer.apple.com/news (upcoming requirements, Developer ID) before a run, because Apple's dates move.

## A. Architectures: a decision, not a default

| Deployment target | Build |
|---|---|
| Below 27, Intel Macs on Tahoe in scope | Universal (arm64 + x86_64) |
| 27 or later | arm64 only: `ARCHS_STANDARD` drops x86_64 |
| A 27 target that must ship x86_64 | Add it to `ARCHS` by hand; **nothing warns** |

macOS 26 Tahoe is the last macOS for Intel; Intel software stops running on macOS 28. A `.pkg` with no `hostArchitectures` now defaults to arm64. Xcode 27 installs only on Apple-silicon Macs on Tahoe 26.6 or later, so an Intel build machine cannot make the 27 SDK build at all.

### Steps

1. **State the decision in writing** (the plan, the PR, `docs/agent-context/desktop-macos.md`): who still runs Intel, from analytics or the support list, and until when. Never drop x86_64 as a side effect of a deployment-target raise.
2. **Inventory**: `rg -n "ARCHS|ONLY_ACTIVE_ARCH|EXCLUDED_ARCHS|MACOSX_DEPLOYMENT_TARGET" -g '*.xcconfig' -g '*.pbxproj'`; `lipo -archs` on every built product, helper, XPC service and embedded framework.
3. **Set `ARCHS` explicitly** in the xcconfig for the release configuration; `ONLY_ACTIVE_ARCH = NO` in Release.
4. **Check every dependency**: an arm64-only binary package inside a universal build fails at link or, worse, at launch on Intel. Rosetta is for the user's old apps, not a plan for yours.
5. **Installers**: set `hostArchitectures` on `pkgbuild` / `productbuild` explicitly; pre- and post-install scripts that assume Intel are fixed.
6. **CI**: name the runner image (`macos-26` arm64, or `macos-26-intel` / `macos-15-intel` for Intel); never `macos-latest`.
7. **Say it in the product**: the minimum system requirements, the Sparkle appcast's `minimumSystemVersion` and the store listing match the decision.

Verify: `lipo -archs <product>` equals the stated list for the app, every helper and every embedded framework; the app launches on the oldest supported hardware that is still in scope.

## B. The Developer ID CA expires 2027-02-01

| Artifact | Effect on 2027-02-01 |
|---|---|
| `.pkg` signed with a certificate from the original Developer ID CA | **Stops installing.** Re-sign with a G2 certificate and re-notarize |
| A notarized app that carries a secure timestamp | Keeps working |
| New certificates | Issued from **Developer ID CA (G2)**; choose the G2 Sub-CA in Xcode |

A project that ships a `.pkg` before that date and has not re-signed has a **blocker-class** finding (L3 of the distribution fragment).

### Steps

1. **Find what ships as a `.pkg`**: installers, helper installers, the Sparkle feed's package items. A DMG with a notarized, timestamped app is not affected.
2. **Read the chain**: `security find-identity -v -p basic`, then `codesign -dvv <artifact>` for apps and `pkgutil --check-signature <file.pkg>` for packages; read the `Authority` lines.
3. **Create the G2 Developer ID Installer certificate** in the developer account, choose the G2 Sub-CA in Xcode, and update the CI secret store (the certificate is never committed).
4. **Re-sign, re-notarize with `notarytool`, staple**; `altool` is rejected. Publish the new package under a higher `CFBundleVersion` where Sparkle serves it.
5. **Test the install** of the re-signed `.pkg` on a clean Mac, and an update from the previous version.

Verify: `pkgutil --check-signature` shows the G2 chain; `spctl -a -vv -t install <file.pkg>` is accepted; `xcrun stapler validate` passes.

## Do not

- Raise the deployment target to 27 and leave `ARCHS` to the default.
- Treat the CA expiry as an app-signing problem; it is the installer's.
- Put the new certificate or its password in the repository.
