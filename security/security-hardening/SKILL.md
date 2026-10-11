---
name: hardening
description: Use to author the controls that turn misconfiguration findings into fixes — a strict Content-Security-Policy, the OWASP secure-headers set, and WAF rules (OWASP CRS on Coraza/ModSecurity). The authoring half of the fe-* / client-side-security handshake — author here, test there. Triggers "write a strict CSP", "harden our security headers". Not for testing the CSP blocks (`client-side-security`), nonce wiring (`fe-react`/`fe-blazor`), or exploiting a missing header (`penetration-tester`).
---

# Security Governance — Security Hardening (CSP · secure headers · WAF rules)

This skill **authors** the controls that close Security-Misconfiguration findings: a strict, nonce-based **Content-Security-Policy**, the full **OWASP Secure Headers** set, and **WAF rules** (OWASP Core Rule Set on Coraza or ModSecurity) at the edge. It is the **authoring half of the `fe-*` handshake** — the `qa-security` **`client-side-security`** skill *proves in a real browser that the CSP blocks and the report lands*; this skill *writes the policy it tests*. Same contract as `data-testid` / `missing-testids.md`: one side authors the artifact, the other asserts it.

This skill is **language-agnostic** (a CSP string, an HTTP header set, and a CRS ruleset are configuration, not code in any one stack) and homes in the **`security-governance`** plugin, loaded by the **`security-architect`** agent when the posture roll-up prescribes hardening. It authors the **policy** (the CSP text, the header values, the WAF ruleset); **app-level wiring** — emitting a per-request nonce, the framework middleware that sets the headers — hands off to `fe-react` / `fe-blazor` / `be-*` / `devops-engineer`.

> **Author-then-test — no gate here, but a header that parses ≠ a header that blocks.** Writing a policy touches no live target, so this skill carries no authorization gate. Its discipline is the reverse of the offensive lanes': the proof that the control *works* is `client-side-security`'s dynamic test, not a clean parse. **Never claim a CSP "hardened" on the strength of the string alone** — a report-only header, a `<meta>` override, or a route that omits it all parse clean and block nothing.

## Two spines, stated per control

- **OWASP — the primary spine.** Missing/weak CSP, permissive headers, no HSTS → **A02:2025 Security Misconfiguration** (the number moved from A05:2021). A strict CSP is defense-in-depth for **A05:2025 Injection** (which covers XSS). WAF rules front **A05:2025 Injection** broadly. *(Both were A03 under the 2021 list; the 2025 edition moved Injection to A05 and gave A03 to Software Supply Chain Failures — a mis-numbered control maps to the wrong compliance evidence row.)* Each authored control names the OWASP category it closes and, where it maps, the **ASVS 5.0** requirement (V13/V14 config & headers) — `security-governance:compliance-evidence-mapping` turns those into framework evidence.
- **PCI DSS 4.0.1 — where payment pages are in scope.** Req **6.4.3** (script inventory + integrity) and **11.6.1** (HTTP-header + script-tamper monitoring on payment pages) are directly served by a strict CSP with SRI and a reporting endpoint — the two most under-prepared 4.0.1 controls; name them when the app takes card data.

Severity on the library's **blocker/major/minor/nit** table (a public site with no CSP and no HSTS is **major→blocker** depending on data sensitivity).

## The Content-Security-Policy — author it strict, nonce-based

The goal is a policy that stops injected script from executing even when an XSS sink slips through. **Nonce + `strict-dynamic`** is the current best form — it beats an allowlist (allowlists are routinely bypassable via JSONP/open redirects on allowed origins):

```http
Content-Security-Policy:
  default-src 'self';
  script-src 'nonce-{{RANDOM_PER_REQUEST}}' 'strict-dynamic' https: 'unsafe-inline';
  style-src 'self';
  img-src 'self' data:;
  font-src 'self';
  connect-src 'self';
  frame-ancestors 'none';
  base-uri 'none';
  form-action 'self';
  object-src 'none';
  upgrade-insecure-requests;
  report-to csp-endpoint
Reporting-Endpoints: csp-endpoint="https://example.com/csp-reports"
```

- **`'nonce-…'` is regenerated per request** (a fresh CSPRNG value) and emitted on every first-party `<script>` — **that wiring is the app's job** (`fe-react`/`fe-blazor` middleware): this skill authors the policy and the nonce contract, the framework emits it. A static/reused nonce is worthless.
- **`'strict-dynamic'`** lets a nonced script load its own dependencies without an origin allowlist. `'unsafe-inline'` and `https:` are **fallbacks for old browsers that ignore the nonce** — modern browsers honor the nonce and ignore them; do not remove them thinking they weaken a nonce policy (they don't, in a nonce context).
- **`object-src 'none'` · `base-uri 'none'` · `frame-ancestors 'none'`** are the cheap, high-value hard stops (plugin injection, `<base>` hijacking, clickjacking).
- **`report-to` + `Reporting-Endpoints`** (CSP Level 3) is the current reporting path — **`report-uri` is deprecated**; a transitional policy may specify both, but assert the report actually lands via `report-to`. Route reports so violations are seen (a policy no one monitors drifts).
- **Roll out `Content-Security-Policy-Report-Only` first** on a live-traffic route to collect violations without breaking the app, tune, then flip to the enforcing header. Report-Only **must not block** — that is the staged-rollout tool, never the finished state.

## The OWASP Secure Headers set — author the full baseline

Beyond CSP, the OWASP Secure Headers Project **core + baseline** set, every one authored with intent (not cargo-culted):

| Header | Value (typical) | Closes |
|---|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | downgrade / SSL-strip (A02) |
| `X-Content-Type-Options` | `nosniff` | MIME-sniffing (A02) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | referrer leakage (A02/privacy) |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), …` | powerful-feature abuse (A02) |
| `X-Frame-Options` | `DENY` (legacy backstop for `frame-ancestors`) | clickjacking (A02) |
| `Cross-Origin-Opener-Policy` | `same-origin` | cross-window attacks (Spectre-class) |
| `Cross-Origin-Embedder-Policy` | `require-corp` (only if you need cross-origin isolation) | — |
| `Cross-Origin-Resource-Policy` | `same-origin` | cross-origin resource leaks |
| `X-Permitted-Cross-Domain-Policies` | `none` | Flash/PDF cross-domain (legacy) |

- **HSTS `preload`** is a one-way door — it hard-fails HTTP for the domain + subdomains for the `max-age`; author it only when every subdomain is HTTPS-ready, and say so.
- **COEP `require-corp`** breaks cross-origin resources that don't send CORP — enable it only when you actually need `crossOriginIsolated` (SharedArrayBuffer/high-res timers); it is not a free baseline header.
- **Remove `Server`/`X-Powered-By`** version banners while you are here (A02, and it starves recon).

## WAF rules — OWASP CRS on a modern engine

The WAF is the edge control that blocks attack traffic before it reaches the app — defense in depth, never the primary fix (fix the code too):

- **OWASP Core Rule Set (CRS)** is the engine-agnostic ruleset — generic attack detection for injection, RCE, LFI/RFI, and protocol anomalies. **Two supported pins; state which you are on.** **v4.29.0** is the current release; **v4.25.x is the CRS-4 Long-Term Support line**, so an LTS pin is a deliberate stability choice rather than staleness. CRS **3.x is the EOL line**, and a floating `latest` is a finding in either direction.
- **Engine: prefer Coraza** (Go, cloud-native, 100% CRS-v4 compatible, ~20–40% faster than ModSecurity, integrates with Envoy/Caddy/Traefik) for new deployments. **ModSecurity** (v2/v3) still runs CRS — note Trustwave ended *commercial* support in 2024; it continues as an OWASP community project. **CrowdSec** is the behavior/reputation-based alternative when you want IP-reputation blocking rather than rule-based.
- **Tune with the paranoia level (PL1–PL4) and anomaly scoring.** Start at **PL1** in **`DetectionOnly`** mode, watch for false positives against real traffic, tune exclusions, *then* raise the PL and switch to blocking. Deploying CRS at PL2+ in blocking mode on day one breaks legitimate traffic and gets the WAF disabled — the same failure mode as an untuned detection.
- WAF rules are **as-code**: the CRS config, custom rules, and exclusions live in Git, reviewed and version-controlled; deploy hands off to `devops-engineer` (ingress/edge). A WAF clicked into a cloud console has no review or rollback.

## Anti-patterns

- **Calling a clean CSP string "hardened."** It validates the text, not enforcement — report-only, a `<meta>` override, or a route missing the header all parse clean and block nothing. *Fix:* hand it to `client-side-security` for the dynamic block-proof; author is not test.
- **An allowlist CSP instead of nonce + `strict-dynamic`.** Origin allowlists are routinely bypassed (JSONP/redirects on an allowed host). *Fix:* nonce-based `script-src` with `strict-dynamic`.
- **A static or reused nonce.** A nonce that doesn't change per request is decoration. *Fix:* the app emits a fresh CSPRNG nonce per response; this skill states the contract, `fe-*` wires it.
- **Flipping CSP straight to enforce on production.** It breaks legitimate inline handlers/scripts and gets rolled back wholesale. *Fix:* `Report-Only` first, collect + tune, then enforce.
- **CRS at PL2+ blocking on day one.** False positives break real traffic and the WAF gets disabled — worse than no WAF. *Fix:* PL1 `DetectionOnly` → tune → raise PL → block.
- **`report-uri` only.** Deprecated; violations may not be collected. *Fix:* `report-to` + `Reporting-Endpoints`; monitor the endpoint.
- **Treating the WAF as the fix.** A WAF rule that blocks SQLi hides, not fixes, the injectable query. *Fix:* WAF is defense-in-depth; the code fix routes to `be-*`, the DOM-sink fix to `fe-*`.
- **`HSTS preload` / `COEP require-corp` cargo-culted.** Both are one-way doors that break things when not warranted. *Fix:* author them only when the prerequisites hold, and state the prerequisite.

## Hard rules

- **Author-then-test** — the CSP/header set is not "hardened" until `client-side-security` proves it blocks in a real browser and the report lands. Author here; test there.
- **CSP: nonce + `strict-dynamic`**, per-request nonce (wiring handed to `fe-*`), the hard-stop directives (`object-src`/`base-uri`/`frame-ancestors` `'none'`), `report-to`+`Reporting-Endpoints` (not `report-uri`), **Report-Only → enforce** rollout.
- **The full OWASP Secure Headers baseline**, each authored with intent; HSTS `preload` and COEP only when their prerequisites hold, and stated.
- **WAF: CRS 4.x on Coraza (preferred) / ModSecurity** — pinned to either the current release (**v4.29.0**) or the **v4.25.x LTS** line, stated explicitly; never floating `latest`, never CRS 3.x, PL1 `DetectionOnly` → tune → raise → block; rules as-code in Git.
- **Defense in depth, never the fix** — the WAF/header fronts the vulnerability; the code/DOM-sink fix still routes to `be-*` / `fe-*`.
- **Policy here, wiring there** — this skill authors the language-agnostic policy; per-framework middleware and nonce emission hand off to `fe-react`/`fe-blazor`/`be-*`/`devops-engineer`.
- **PCI 6.4.3 / 11.6.1** on payment pages: name them when card data is in scope; a strict CSP + SRI + reporting endpoint serves both.

## Cross-references

- **`qa-<stack>:client-side-security`** (`qa/_shared/security-testing/client-side-security/`) — the **test half** of the handshake: it proves the CSP blocks (the `securitypolicyviolation` `disposition: "enforce"` proof), grades the deployed headers (MDN Observatory), and crawls the SPA. This skill writes what that one tests; a failing test routes back here.
- **`security-architect`** (`security/agents/security-architect.md`) — the roll-up agent that loads this skill when the posture picture shows a missing/weak CSP, header gaps, or no WAF.
- **`fe-react`** / **`fe-blazor`** *(peers, named not loaded)* — own the app-level wiring: emitting the per-request nonce, the framework middleware, sink-safe rendering. This skill hands them the policy + nonce contract; DOM-sink fixes route to their component writers.
- **`devops-engineer`** (`devops/agents/devops-engineer.md`) — deploys the WAF at the edge (ingress/Envoy/Caddy) and sets headers at the reverse proxy when they belong there rather than in-app.
- **`devops:controls-validation`** (`devops/infra-controls-validation/`) — validates the encryption-in-transit / header controls are present **and effective**; the HSTS/CSP this skill authors is what it retests.
- **`security-governance:compliance-evidence-mapping`** — maps the authored CSP/headers/WAF to A02/ASVS V13-V14/PCI 6.4.3+11.6.1 evidence.
- **`security-governance:detection-engineering`** — the tripwire counterpart: author a detection on CSP-violation reports and WAF blocks, so an attempted injection is *seen*, not just blocked silently.
