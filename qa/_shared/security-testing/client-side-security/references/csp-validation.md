# CSP validation — static evaluation vs dynamic block-proof

A Content-Security-Policy that *parses clean* is not a policy that *blocks*. This file covers both halves:
static evaluation of the policy text, and the dynamic proof that the deployed browser actually enforced it.
Maps to **A02:2025 Security Misconfiguration**.

## Static — Google CSP Evaluator (the policy text)

> **There is no CLI** — `csp_evaluator` (npm, **underscore**, v1.1.8, Apache-2.0) is a library. Write a
> ~10-line wrapper, or use the web tool at `csp-evaluator.withgoogle.com`.

```js
import {CspEvaluator} from "csp_evaluator/dist/evaluator.js";
import {CspParser}    from "csp_evaluator/dist/parser.js";
const csp = new CspParser("script-src 'self' 'unsafe-inline' *; object-src 'none'").csp;
console.log(new CspEvaluator(csp).evaluate());   // findings array
```

```bash
node -e 'import("csp_evaluator/dist/evaluator.js").then(async e=>{const p=await import("csp_evaluator/dist/parser.js");
  const csp=new p.CspParser(process.argv[1]).csp;
  console.log(JSON.stringify(new e.CspEvaluator(csp).evaluate(),null,2));})' \
  "script-src 'self' 'unsafe-inline' *; object-src 'none'"
```

Flags: `'unsafe-inline'`, `'unsafe-eval'`, wildcard `*` / overly broad host allowlists, missing `object-src`,
missing `base-uri`, and **allowlist bypasses** (JSONP/AngularJS endpoints on an allowlisted host — a
built-in corpus "based on a large-scale study"). `'strict-dynamic'` makes host allowlists ignored for scripts
(a good sign — the policy leans on nonces/hashes, not a host list).

## Static — MDN HTTP Observatory (the deployed headers, graded)

> **Mozilla Observatory moved to MDN.** npm `@mdn/mdn-http-observatory` (v1.6.3, **Node ≥ 24**); the public
> API is rate-limited to **1 scan/host/60s** (exceeding returns a cached result).

```bash
npx @mdn/mdn-http-observatory mdn.dev
mdn-http-observatory-scan --headers '{"X-Custom":"value"}' example.com:8080/path
curl -X POST 'https://observatory-api.mdn.mozilla.net/api/v2/scan?host=example.com'   # → grade, score, details_url
```

Scoring: baseline 100, penalties applied, bonuses only if ≥90; range 0–145 (A+ ≥100, A 90–99, B 70–79).

## Modern CSP the validation asserts against

MDN is explicit: **strict (nonce/hash) CSP > allowlist CSP** (adding Google Analytics via an allowlist needs
187 domains). The target shape:

```http
Content-Security-Policy: script-src 'nonce-{RANDOM}' 'strict-dynamic'; object-src 'none'; base-uri 'none'
Reporting-Endpoints: csp-endpoint="https://app.example.test/csp-reports"
Content-Security-Policy: default-src 'self'; report-to csp-endpoint; report-uri https://app.example.test/csp-reports
```

- Nonce = per-response, random, unpredictable (server-rendered); `'sha256-...'` hash = static/CSR.
  `'unsafe-inline'` / `'unsafe-eval'` defeat the policy.
- **`report-uri` is deprecated; `report-to` is CSP L3 (Baseline Mar 2026)** and needs the
  `Reporting-Endpoints` header; it is **header-only** (not `<meta>`). A transitional policy specifies both —
  browsers that support `report-to` ignore `report-uri`.
- Report POSTs as `application/reports+json`, `type: "csp-violation"`, with `blockedURL`,
  `effectiveDirective`, `disposition` (`enforce`|`report`), `documentURL`, `sample`, `sourceFile`,
  `lineNumber`.

## Dynamic — prove the browser BLOCKED an injection (authorized env)

The in-browser hook is the **`securitypolicyviolation`** event (`SecurityPolicyViolationEvent`, Baseline
since Oct 2018; fires on `document`/`window`, not the offending element):

```js
window.addEventListener("securitypolicyviolation", e => {
  console.log(e.blockedURI, e.violatedDirective, e.effectiveDirective, e.disposition,
              e.sourceFile, e.lineNumber, e.originalPolicy);
});
```

**Test shape (Playwright, authorized non-prod env):** pre-register the listener via `page.addInitScript`,
inject a script at a known reflection point, and assert **three** conditions:

```js
// 1. Collect violations from the page.
await page.addInitScript(() => {
  window.__cspViolations = [];
  addEventListener("securitypolicyviolation", e =>
    window.__cspViolations.push({ dir: e.effectiveDirective, disp: e.disposition }));
});
// 2. Intercept the report endpoint.
const reports = [];
await page.route("**/csp-reports", async r => { reports.push(await r.request().postDataJSON()); r.fulfill({status:204}); });

// 3. Drive the app to a reflection point with an injected inline script, then assert:
//    (a) the script did NOT execute  (b) a violation fired enforce  (c) a report landed.
await expect.poll(() => page.evaluate(() => window.__sideEffectRan)).toBeFalsy();
const v = await page.evaluate(() => window.__cspViolations);
expect(v.some(x => x.dir === "script-src-elem" && x.disp === "enforce")).toBe(true);
expect(reports.some(r => r.type === "csp-violation")).toBe(true);
```

- **`Content-Security-Policy-Report-Only`** yields `disposition: "report"` and **must not block** — a
  deliberate negative test for a staged rollout, not a pass.
- A policy that scores A+ statically but whose `securitypolicyviolation` never fires (served only on some
  routes, shadowed by a `<meta>` tag, or accidentally report-only) is a **failed** validation — the whole
  reason this dynamic step exists.

## Rules

- Static evaluation (CSP Evaluator, Observatory) proves the text; **dynamic `securitypolicyviolation`
  validation proves enforcement** — assert no-execution + enforce-disposition + delivered report.
- Injection to validate blocking is active testing → authorized non-prod env under the authorization line.
- `report-to` over `report-uri`; assert the report actually lands. Map every finding to A02:2025.
- The CSP itself is authored by `security-hardening` + `fe-*` — this file only tests it.
