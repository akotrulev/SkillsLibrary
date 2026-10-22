# Attributions — `qa/_shared/`

Provenance for the borrowed artifacts shipped inside the shared QA layer. `qa/_shared/` is bundled into the
`qa-java`, `qa-dotnet` and `qa-typescript` plugins, so this file ships wherever the borrowed material ships.
One section per artifact.

---

## `vendor/security-audit` — Cloudflare's security-audit skill

The whole of `qa/_shared/vendor/security-audit/` — `SKILL.md`, the phase and domain-companion files,
`report-schema.json`, and the two validators with their tests — is vendored from Cloudflare.

- Upstream: `cloudflare/security-audit-skill`, `https://github.com/cloudflare/security-audit-skill`
- Snapshot commit: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8` (2026-09-14)
- Retrieved / vendored: **2026-10-22**
- License: MIT at import time — the upstream notice is kept verbatim at
  `qa/_shared/vendor/security-audit/LICENSE`.
- Vendored from the upstream path `skills/security-audit/`, plus the root `LICENSE`. The upstream `README.md`
  is not vendored.

**Unchanged from upstream, byte for byte.** It is not registered as a skill, so its broad description cannot
out-trigger the house security skills. The house entry point is
[`security-testing/source-audit`](security-testing/source-audit/SKILL.md), which routes into it and holds
every library override in one table; that skill's last section is the refresh procedure.
