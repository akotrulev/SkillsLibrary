# fastlane — match, API key, lanes

fastlane 2.240.1 (verified 2026-10-10; re-verify 2026-12-31). Docs: docs.fastlane.tools. Use for native iOS and bare React Native; Expo managed apps use EAS instead.

## Auth: App Store Connect API key, not an Apple ID

- Create the key in App Store Connect (Users and Access → Integrations): `.p8`, key id, issuer id. Role: App Manager (upload) or Admin (cert management).
- Load it in a lane with `app_store_connect_api_key(key_id:, issuer_id:, key_content:, is_key_content_base64: true)`; the three values come from CI secrets. No `FASTLANE_PASSWORD`, no `FASTLANE_SESSION` cookie.

## Signing: `match`

- `match` stores certs and profiles **encrypted** in a private git repo (or S3 / GCS / Azure); the passphrase (`MATCH_PASSWORD`) is a CI secret held apart from the store.
- CI runs `match(type: "appstore", readonly: true)` — **`readonly: true` in CI**, so a build can never mint or revoke certificates; creation is a deliberate local step by a named person.
- One `Matchfile` per repo; `git_url`, `type`, `app_identifier`. Nothing secret in it.

## Build number and upload

- `latest_testflight_build_number` + 1 → `increment_build_number`, or the CI run number. Never a committed counter two branches edit.
- `build_app` (gym) with an explicit scheme and `export_method: "app-store"`; `upload_to_testflight` (pilot) with `skip_waiting_for_build_processing` only when a later step polls.
- `upload_to_app_store` (deliver) for metadata and submission; set `phased_release: true`.
- Phased release halt: App Store Connect → pause (or `deliver` cannot pause — it is a console / API action). Note the pause limit: 30 days, and manual Update still works.

## Symbols

- `upload_symbols_to_crashlytics(dsym_path:)` or `sentry_upload_dsym` after `build_app`, using the archive's dSYM (`lane_context[SharedValues::DSYM_OUTPUT_PATH]`).

## Android lane (optional)

- `supply` uploads an AAB to a track with `rollout:`; a service-account JSON from a CI secret. Prefer `gradle-play.md`'s plugin when the project is already Gradle-first.

## Traps

- `match` without `readonly` in CI — a parallel build revokes the cert another job is using.
- `gym` signing from the login keychain on a shared runner — use a temporary keychain (`setup_ci`).
- The pipeline that calls these lanes is `devops-engineer`'s YAML; the lane bodies are the app's.
