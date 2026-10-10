# Xcode Cloud

Apple's hosted CI/CD, configured in Xcode / App Store Connect. Docs: developer.apple.com/documentation/xcode/xcode-cloud. Strongest when the team is iOS-only and wants cloud signing with nothing exported.

## Workflows

- A workflow = start condition (branch / tag / PR), environment, actions (build, test, archive), post-actions (TestFlight internal / external, notify).
- **Pin the environment** — Xcode version and macOS — in the workflow's Environment section, to a named version, not "Latest Release". Re-verify when Apple retires an Xcode version.
- Tag-triggered archive → TestFlight is the normal release path; the tag is the release record.

## Signing

- **Cloud-managed signing**: Xcode Cloud signs with Apple-held certs; nothing is exported or stored in the repo. Do not export the distribution cert to work around a build error — fix the capability / entitlement.
- Third-party private dependencies need an SSH key or token added as a workflow **secret environment variable**.

## Build numbers

- Xcode Cloud sets `CI_BUILD_NUMBER`, monotonic per workflow; use it in `ci_scripts/ci_post_clone.sh` (`agvtool new-version -all "$CI_BUILD_NUMBER"`) so the build number is machine-assigned.
- If another system also uploads builds (a fastlane lane), they share one counter per version at App Store Connect — collisions are rejected. One system owns upload.

## `ci_scripts`

- `ci_post_clone.sh`, `ci_pre_xcodebuild.sh`, `ci_post_xcodebuild.sh` at the repo's `ci_scripts/`. Use for dependency install (CocoaPods / `npm ci` + `pod install` for bare RN), build-number set, dSYM upload (`$CI_ARCHIVE_PATH` → Sentry / Crashlytics).
- Scripts must be executable and carry no secrets; secrets come from workflow environment variables.

## Limits

- iOS / Apple platforms only. Android, shared-package tests and non-Apple steps stay in `devops-engineer`'s pipeline.
- Compute-hour quota comes with the Developer Program; check current numbers at developer.apple.com/xcode-cloud before sizing.
