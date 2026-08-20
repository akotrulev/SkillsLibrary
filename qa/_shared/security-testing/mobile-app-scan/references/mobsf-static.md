# MobSF — static analysis invocation (v4.4.6)

[MobSF](https://github.com/MobSF/Mobile-Security-Framework-MobSF) is one self-contained service that
decompiles an APK/AAB/IPA and produces a static report: manifest analysis, code findings (secrets, crypto,
insecure API use), a permission map, a certificate summary, and a security score. **v4.4.6** (March 2026) is
the pinned release — it patched an SQL-injection in the bundled SQLite DB viewer, so pin at or above it.

> **Pin the tag, never `:latest`.** A rolling `opensecurity/mobile-security-framework-mobsf:latest` changes
> the ruleset and the score between runs, so a baseline built one week fails differently the next. Pin the
> exact tag and record it in the report.

## Run it (Docker, the portable path)

```bash
docker run --rm -it -p 8000:8000 \
  opensecurity/mobile-security-framework-mobsf:v4.4.6
# UI at http://localhost:8000 — upload the artifact, read the report.
```

For **CI / headless**, drive the REST API instead of the UI. MobSF prints a `REST API Key` on startup (or set
`MOBSF_API_KEY`); the three-call flow is upload → scan → report:

```bash
API=http://localhost:8000
KEY="$MOBSF_API_KEY"

# 1. upload — returns {"hash": "...", "scan_type": "apk", ...}
HASH=$(curl -s -F "file=@app-release.apk" -H "Authorization: $KEY" \
  "$API/api/v1/upload" | jq -r .hash)

# 2. scan (synchronous — blocks until the static analysis completes)
curl -s -X POST -H "Authorization: $KEY" \
  --data-urlencode "hash=$HASH" "$API/api/v1/scan" > /dev/null

# 3. machine-readable report → gate on it
curl -s -X POST -H "Authorization: $KEY" \
  --data-urlencode "hash=$HASH" "$API/api/v1/report_json" > mobsf-report.json

# PDF for humans (optional)
curl -s -X POST -H "Authorization: $KEY" \
  --data-urlencode "hash=$HASH" "$API/api/v1/download_pdf" -o mobsf-report.pdf
```

`suppress_by_files` / `suppress_by_rules` (POST `/api/v1/suppress_by_rule`) let you baseline a finding — use
them for the **ticketed** suppressions only; keep the ticket id in the suppression note.

## Reading `report_json` — what to gate on

The score (`security_score`, 0–100) and the `appsec` block (`high`/`warning`/`info`/`secure`/`hotspot`
buckets) are the headline. **Gate on the buckets, not the number.** The finding sections worth parsing:

| JSON section | What it holds | MASVS |
|---|---|---|
| `manifest_analysis` (Android) / `ats_analysis`, `ios_permissions` (iOS) | exported components, cleartext/ATS, `debuggable`, `allowBackup` | PLATFORM / NETWORK-config |
| `code_analysis` / `findings` | insecure crypto, weak random, insecure storage APIs, WebView misuse | CRYPTO / STORAGE / CODE |
| `secrets` / `possible_secrets` | hardcoded keys, tokens, URLs | STORAGE-2 |
| `binary_analysis` (iOS Mach-O) | PIE, stack canary, ARC, encrypted | CODE / RESILIENCE |
| `permissions` | dangerous permissions requested | PRIVACY / PLATFORM |
| `trackers` (Exodus) | embedded analytics/ad SDKs | PRIVACY |

A minimal gate that fails the build on any NEW `high` finding not in a baseline file:

```bash
jq -r '.appsec.high[]? | .title' mobsf-report.json | sort > current-high.txt
comm -13 baseline-high.txt current-high.txt > new-high.txt
[ -s new-high.txt ] && { echo "NEW high-severity mobile findings:"; cat new-high.txt; exit 1; } || echo "no new high findings"
```

## Dynamic analysis is a separate mode

MobSF *also* has a dynamic analyzer (an instrumented Android VM / a corellium-or-USB iOS path). That is the
**device half** and belongs to `mobile-runtime-testing` (`references/mobsf-dynamic.md`) — it needs a running
app, an authorization gate, and is never a per-PR gate. This file is the static path only: no device, safe,
CI-gateable.

## Framework note — Flutter / React Native / MAUI

MobSF decompiles the container regardless of framework, but the *code* findings degrade for compiled
cross-platform apps: a Flutter release bundles Dart in `libapp.so` (MobSF sees the native lib, not readable
Dart), React Native ships a JS bundle (`index.android.bundle` — grep it for secrets), MAUI ships .NET
assemblies (decompile with a .NET tool). **The manifest/plist, ATS/network-config, permissions, and
secrets-in-resources findings hold for every framework** — the code-level crypto/API findings are the part
that needs the framework-specific extraction. State the framework in the report so the coverage is honest.
