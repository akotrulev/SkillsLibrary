# VEX & reachability tooling — the "is the vulnerable code on the execute path" layer

KEV+EPSS answers *"is this CVE exploited / likely-exploited."* Reachability answers a different question:
*"is the vulnerable function actually called in this build."* The interop layer between a reachability tool
and a gate is **VEX** — a machine-readable `not_affected` statement with a justification. Reachability
**suppresses, never promotes** (it has false negatives; KEV stays ground truth), and VEX runs **after** the
KEV check.

## VEX — the interop format

**OpenVEX** (`github.com/openvex/spec`, spec tag **v0.2.0**, context `https://openvex.dev/ns/v0.2.0`; tooling
current — `openvex/vexctl` **v0.4.4**, 2026-06-16). Statuses: `not_affected`, `affected`, `fixed`,
`under_investigation`. A `not_affected` needs a `justification` **or** an `impact_statement`; the five
justifications:

- `component_not_present`
- `vulnerable_code_not_present`
- **`vulnerable_code_not_in_execute_path`** ← the reachability justification
- `vulnerable_code_cannot_be_controlled_by_adversary`
- `inline_mitigations_already_exist`

**CSAF v2.0** is the OASIS Standard (2022; Errata 01 2024). **CSAF 2.1 is still a committee draft — do not
present it as ratified.**

```json
{ "@context": "https://openvex.dev/ns/v0.2.0",
  "statements": [{
    "vulnerability": {"name": "CVE-2023-45853"},
    "products": ["pkg:oci/myimage"],
    "status": "not_affected",
    "justification": "vulnerable_code_not_in_execute_path",
    "impact_statement": "call-graph analysis: the vulnerable function is not called" }] }
```

## The reachability→VEX→gate loop (fully OSS)

This is a real production pattern — Aqua machine-generates the VEX in its own VEX Hub from **govulncheck**
reachability output (`status: not_affected`, `justification: vulnerable_code_not_in_execute_path`,
`impact_statement: "Govulncheck determined that the vulnerable code isn't called"`).

```bash
# 1. Compute reachability and EMIT OpenVEX (Go example).
govulncheck -format openvex ./... > govulncheck.openvex.json

# 2. Feed the VEX to a consumer so unreachable CVEs are suppressed (but kept visible).
grype myimage:tag --vex govulncheck.openvex.json
trivy image myimage:tag --vex govulncheck.openvex.json --show-suppressed
```

## Static reachability tools (OSS)

| Tool | Version | Langs | Notes |
|---|---|---|---|
| **govulncheck** | v1.7.0 (2026-08-13) | Go | symbol-level call graph; `-format openvex`; emits only `affected`/`not_affected`, never `fixed` (golang/go#68338) |
| **osv-scanner** | v2.5.0 (2026-08-07) | Go (default-on, wraps govulncheck) + experimental Rust/Java | flag is `--call-analysis=<lang|all>` / `--no-call-analysis=`; **Rust mode compiles the project → runs `build.rs` (arbitrary code exec)** — trusted code only |
| **OWASP dep-scan** | 6.3.0 (2026-07-23) | Java, JS/TS, Python, PHP, Rust, Go, .NET | broadest OSS coverage; reachability on by default; `--reachability-analyzer off\|FrameworkReachability\|SemanticReachability` |
| **Grype** | v0.117.0 (2026-08-10) | — | **consumes** OpenVEX (no CSAF); `not_affected`/`fixed` → `ignoredMatches`; `vex-add` surfaces them back. **Has no reachability of its own.** |

```bash
osv-scanner scan source --call-analysis=rust --no-call-analysis=go ./project   # know it compiles Rust
```

## VEX consumers already in the library

**Trivy v0.74.0** consumes VEX four ways — `--vex repo` (VEX Hub, `trivy vex repo init|list|download`),
`--vex <file>` (OpenVEX or CSAF), `--vex oci`, `--vex sbom-ref`; repeatable, order = priority. `--show-suppressed`
reveals what was filtered. **CycloneDX VEX** works for SBOM scanning only.

## Runtime reachability — the honest map

Category naming has not converged; the fault line that matters is **file-access→package mapping ≠
loaded-into-memory ≠ function-level execution**.

- **Kubescape / ARMO — the only OSS runtime-reachability product** (Apache-2.0, CLI **v4.0.12**): an eBPF
  node-agent watches file activity over a learning period, then emits a **filtered SBOM of only the packages
  whose files were touched** (needs kernel ≥5.4 + BTF).
- **Commercial** (name-only): Sysdig Risk Spotlight (file-access→package), Upwind, Oligo, Aqua, Datadog
  Runtime SCA (an in-process APM tracer, not eBPF).

## Myth-busters (state these)

- **Grype computes no reachability** — it consumes VEX; the reachability comes from govulncheck upstream.
- **Falco 0.44 and Tetragon v1.7 are NOT SCA de-noisers** — eBPF *threat detection* with no SBOM to filter a
  CVE list. Tetragon's file-access tracing is the right primitive (Kubescape rests on it) but ships no
  de-noising product.
- **Semgrep Supply Chain is proprietary** (not the CE engine) and does **no reachability on transitive
  dependencies** — where most CVEs live. **Snyk's Runtime Sensor is discontinued** (archived 2026-05).
- Commercial static-reachability (Endor, Backslash — 80–90% actionable-noise-reduction claim, Checkmarx
  Exploitable-Path) always cover **far fewer languages than plain SCA**; **Go support is the sharpest
  discriminator** (present in Endor/Backslash/Semgrep/JFrog, absent from Snyk/Sonatype/Mend/Checkmarx).

## Rules

- Reachability **suppresses, never promotes**; VEX runs **after** the KEV check.
- A `not_affected` needs a justification; `vulnerable_code_not_in_execute_path` is the reachability one.
- Keep suppressions visible (`--show-suppressed` / `ignoredMatches`) — VEX has false positives and needs
  human review; never let it silently delete a finding.
- OpenVEX is the OSS interop default; CSAF 2.0 (not 2.1) where required. Grype = OpenVEX only.
- `osv-scanner --call-analysis=rust` compiles the project — trusted code only.
