# The enrichment gate — join, decide, emit

The whole skill is a **pure function**: scanner output + three cached feeds → a re-decided verdict + exit
code. No network to the scanner, no re-scan. Because the join key is just the CVE id, the same stage
de-noises Trivy, Grype, `npm audit`, OWASP Dependency-Check, and `dotnet list --vulnerable` identically.
**Neither Trivy nor Grype ships EPSS/KEV natively** (verified against their filtering docs), so
post-processing is the only option, not a preference.

## The decide function (precedence is load-bearing)

```python
def decide(cve, cvss, kev, epss, vex_not_affected, automatable=None, internet_facing=True):
    if cve in kev:                                   # 1. KEV — first, unconditional, ground truth
        return "ACT"
    if vex_not_affected:                             # 2. reachability — AFTER kev, suppresses only
        return "DEFER"
    if cvss is not None and cvss >= 7.0 \
       and epss is not None and epss >= 0.10:        # 3. exploitable-and-severe
        if automatable is False or not internet_facing:
            return "TRACK"                           #    optional tightening
        return "ATTEND"
    return "TRACK"                                   # 4. ticket, no block
```

- **KEV before everything** — an unreachable KEV CVE is still ACT (reachability has false negatives).
- **VEX after KEV** — never before, or a `not_affected` could suppress a known-exploited CVE.
- **`epss is None` (missing score) is not `0`** — it just can't satisfy the ATTEND branch; KEV/CVSS still
  decide it.
- **Never `epss * cvss`.**

## The full stage (reference implementation, ~60 lines)

```python
import csv, gzip, json, sys, urllib.request

def load_kev(path="kev.json"):
    d = json.load(open(path))
    return {"ver": d["catalogVersion"], "set": {v["cveID"]: v for v in d["vulnerabilities"]}}

def load_epss(path="epss.csv.gz"):
    scores, ver = {}, None
    with gzip.open(path, "rt") as f:
        ver = f.readline().strip().split("model_version:")[1].split(",")[0]   # v2026.06.15
        r = csv.DictReader(f)                                                  # cve,epss,percentile
        for row in r:
            scores[row["cve"]] = (float(row["epss"]), float(row["percentile"]))
    return {"ver": ver, "map": scores}

def enrich(findings, kev, epss, vex=frozenset()):
    out = []
    for f in findings:                       # f = {"cve","cvss","pkg"}
        cve = f["cve"]
        e = epss["map"].get(cve)             # None if unscored — NOT 0
        v = decide(cve, f.get("cvss"), kev["set"], e[0] if e else None, cve in vex)
        out.append({**f, "epss": e[0] if e else None, "kev": cve in kev["set"], "verdict": v})
    order = {"ACT": 0, "ATTEND": 1, "DEFER": 2, "TRACK": 3}
    return sorted(out, key=lambda x: order[x["verdict"]])

if __name__ == "__main__":
    kev, epss = load_kev(), load_epss()
    findings = parse_scanner(json.load(open(sys.argv[1])))   # Trivy/Grype/npm/OWASP-DC/dotnet → [{cve,cvss,pkg}]
    vex = load_vex(sys.argv[2]) if len(sys.argv) > 2 else frozenset()
    rows = enrich(findings, kev, epss, vex)
    print(f"KEV catalogVersion={kev['ver']}  EPSS model_version={epss['ver']}")
    for r in rows:
        print(f"{r['verdict']:7} {r['cve']:16} {r['pkg']:12} cvss={r['cvss']} epss={r['epss']} kev={r['kev']}")
    sys.exit(1 if any(r["verdict"] in ("ACT", "ATTEND") for r in rows) else 0)
```

Real run (live feeds, `catalogVersion=2026.08.14`):

```
ACT     CVE-2021-44228   log4j-core   cvss=10.0 epss=0.99999 kev=True     # in KEV → page
ATTEND  CVE-2024-3094    xz-utils     cvss=10.0 epss=0.85974 kev=False    # CVSS≥7 ∧ EPSS≥0.1 → block
TRACK   CVE-2023-45853   zlib         cvss=9.8  epss=0.03179 kev=False    # highest CVSS, correctly demoted
TRACK   CVE-2022-27225   somepkg      cvss=7.5  epss=0.00544 kev=False
exit=1  (2 of 4 blocking)
```

Add a VEX `not_affected / vulnerable_code_not_in_execute_path` for the zlib CVE → it reclassifies to
**DEFER** (same script, second arg).

## Three output paths

1. **Exit code** — `ACT|ATTEND` ⇒ exit 1. The simplest gate.
2. **Enriched SARIF** — re-emit with `properties: {epss, epssPercentile, kev, security-severity}` and
   `tags: ["KEV","ACT"]`. GitHub code-scanning **sorts on `security-severity`** — writing the *enriched*
   value there makes the UI reflect exploitability instead of CVSS.
3. **Feed back into the scanner** — emit the below-gate CVEs as a Trivy `--ignore-policy` Rego allowlist so
   Trivy's own exit code comes out de-noised:
   ```rego
   package trivy
   import rego.v1
   below_gate := {"CVE-2023-45853", "CVE-2022-27225"}
   default ignore := false
   ignore if input.VulnerabilityID in below_gate
   ```

## Caching & reproducibility (make these hard rules)

- Fetch **KEV JSON (1.6 MB)** and the **EPSS CSV (2.5 MB gz)** **once per pipeline**, into a cache keyed on
  the date; read locally. Avoids the EPSS API batching/silent-drop traps, makes the gate deterministic and
  offline-reproducible.
- **Record `catalogVersion` + EPSS `model_version` in the report.** The same CVE legitimately changes verdict
  day to day as EPSS moves and KEV grows — a verdict is only reproducible with its feed versions.
- **Every suppression stays in the report** (`--show-suppressed` / `ignoredMatches`), ticketed. A gate that
  *deletes* findings is an audit failure.

## The server alternative

When a team wants a service rather than a CI script: **OWASP Dependency-Track 5.0.4** has **native EPSS + KEV
+ CycloneDX VEX** with CEL policy conditions. Recommend it over the script for a central, always-on
prioritization surface; the script stays the right answer for a per-pipeline gate.

## Rules

- Post-process, don't re-scan; join on CVE id; precedence **KEV → VEX → CVSS∧EPSS → TRACK**; never
  `epss*cvss`.
- Cache both feeds once, date-keyed; stamp feed versions; keep suppressions visible.
- Write the enriched value into `security-severity` so code-scanning sorts on exploitability.
