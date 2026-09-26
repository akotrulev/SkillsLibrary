---
name: qa-security-client-side-security
description: Use for dynamic client-side security testing the server-side scanners are blind to — DOM-based XSS, CSP validation, and SPA-specific DAST. Language-agnostic, runs against an owned/authorized non-prod env. Triggers "test for DOM XSS", "does our CSP actually block injection", "SPA security scan", "validate our security headers", "client-side prototype pollution". Do NOT use for server-side injection (`active-scan`/`exploit-validation`) or access-control (`permission-testing`).
---

# Security Testing — Client-Side Security (DOM XSS · CSP validation · SPA DAST)

The server-side DAST gates in this family drive HTTP and read responses — they are **structurally blind to
the client layer**: a DOM-based XSS never makes a server round-trip (the source and sink both live in the
browser), a Content-Security-Policy either *is* or *isn't* enforced by the browser regardless of how clean
its text parses, and a single-page app's client-side routes never reach the proxy at all. This skill owns
that layer: **prove a DOM sink is reachable, prove the deployed CSP actually blocks an injected script, and
crawl an SPA the way a browser does.**

This skill is **language-agnostic** (Dalfox, ZAP, Nuclei, the CSP tools are CLI binaries / browser
harnesses) and lives in the **`qa-security` agent's Step 4b** dynamic lane, pairing with
`qa-security-shared` (the OWASP backbone) — load that alongside. It is the **test half of the `fe-*`
handshake**: the `security-hardening` skill *authors* the strict CSP / security headers into the
`fe-react` / `fe-blazor` app; this skill *proves in a real browser that they hold*. Same shape as the
existing `data-testid` / `missing-testids.md` contract — the frontend skill writes the artifact, the test
skill asserts it. Sink findings route **back** to `fe-react-component-writer` / `fe-blazor-component-writer`
(`dangerouslySetInnerHTML` / `MarkupString`), never fixed here.

> **⚠️ Injecting a payload is active testing — authorized non-prod env only.** Everything that *fires a
> payload* — a Dalfox `scan`, ZAP's DOM-XSS active rule (40026) or `activeScan`, a Nuclei headless XSS
> template, a DOM Invader exploit, the CSP block-validation injection — runs **only** against an owned or
> written-authorization'd, **non-production** environment, under a **recorded, per-run, expiring
> authorization line** (never cached — it is `#volatile`). **Static/passive lanes need no gate:** CSP
> Evaluator on a header string, MDN Observatory on a public host, Retire.js on a build output, Dalfox's
> AST-only source→sink analysis (`--dry-run`, sends no payloads). **Blind-XSS callbacks
> (`--blind`/`--blind-oob` → interactsh) exfiltrate to an out-of-band host and need their own separate
> sign-off**, self-hosted per the loot rule.

```
Authorization: target=<owned/lab SPA url>  scope=<in-scope routes/params>
               authorized-by=<name>  window=<start>..<expiry>  env=non-prod(+2nd sign-off for prod)
```

## Two spines, stated per finding

- **OWASP / WSTG** — the primary map here (client-side is a QA-detection lane). **DOM XSS → A05:2025
  Injection** (was A03:2021), `WSTG-CLNT-01`; **client-side URL redirect →** `WSTG-CLNT-04`; **web messaging
  / postMessage →** `WSTG-CLNT-11`; **browser storage →** `WSTG-CLNT-12`. **Missing/weak CSP, `unsafe-inline`,
  permissive frame/CORS headers → A02:2025 Security Misconfiguration** (the number moved from A05:2021, the
  category didn't). **Vulnerable JS libraries (Retire.js) → A03:2025 Software Supply Chain Failures.**
- **MITRE ATT&CK** — thin on this lane and stated only where a proof executes: a confirmed DOM-XSS
  execution maps to `T1059.007` (JavaScript). State it when the finding is an offensive proof handed onward;
  otherwise OWASP/WSTG carries it.

## Decision matrix — which surface, which tool, which gate

| Need | Tool | `references/` | Gate | OWASP / WSTG |
|---|---|---|---|---|
| Map DOM XSS **source→sink** without firing a payload | Dalfox AST analysis (`--dry-run`) | `dom-xss.md` | none (static) | A05 · CLNT-01 |
| **Prove** a DOM XSS fires (reflected/stored/DOM) | Dalfox `scan`; ZAP rule 40026 | `dom-xss.md` | **authorization** | A05 · CLNT-01 |
| Interactive DOM XSS / prototype-pollution / postMessage / DOM-clobbering | Burp **DOM Invader** | `dom-xss.md` | authorization | A05 · CLNT-01/11 |
| Vulnerable JS libraries in the shipped bundle | Retire.js | `dom-xss.md` | none (build output) | **A03** supply chain |
| Does the CSP **text** have bypasses | Google **CSP Evaluator** | `csp-validation.md` | none (static) | A02 |
| Grade the deployed security headers | **MDN HTTP Observatory** | `csp-validation.md` | none (public host, rate-limited) | A02 |
| Does the deployed CSP **actually block** an injected script | browser `securitypolicyviolation` assertion | `csp-validation.md` | **authorization** | A02 / A05 |
| Crawl a **client-routed SPA** a proxy can't see | ZAP **Client Spider** | `spa-dast.md` | passive; active = authorization | A05/A02 |
| Authenticated-SPA DAST with a **real session** | Playwright/Puppeteer → ZAP/Burp proxy | `spa-dast.md` | passive; active = authorization | A05/A02 |
| Headless browser DOM checks in a template | Nuclei `-headless` | `spa-dast.md` | authorization | A05 · CLNT-01 |

**Rule of thumb:** static analysis (Dalfox AST, CSP Evaluator, Observatory, Retire.js) runs freely and every
PR; **anything that injects a script into a running app needs the authorization line** and a non-prod target.

## The parses-clean ≠ blocks distinction (the point of CSP *validation*)

A CSP that scores well in CSP Evaluator proves the **policy text** is sane. It does **not** prove the browser
*enforced* it — the header could be shadowed by a second policy, served only on some routes, weakened by a
`<meta>` tag, or set report-only by mistake. **Validation is dynamic:** on an authorized env, inject a script
at a known reflection point and assert three things:

1. the script did **not** execute (the injected `alert`/side-effect never ran),
2. a `securitypolicyviolation` event fired with the expected `effectiveDirective` and
   `disposition: "enforce"`,
3. the configured report endpoint received a matching `csp-violation` report body.

`Content-Security-Policy-Report-Only` yields `disposition: "report"` and **must not block** — that is a
deliberate negative test for a staged rollout, not a pass. The full recipe (Playwright pre-registering the
listener via `addInitScript`, asserting on collected events + intercepted report POSTs) is in
`csp-validation.md`.

## Why SPA DAST is its own problem

Traditional crawlers follow `href`s and full-page loads; an SPA has **client-side routing** (URI fragments
never reach the proxy), **XHR/fetch-driven state**, and a **DOM built after the response**. A proxy sitting
below the browser sees the API calls but not the routes that trigger them, so the active scanner's site tree
is half-empty. The two documented answers (`spa-dast.md`):

- **ZAP Client Spider** (the current recommendation — the older **AJAX Spider is no longer recommended for
  modern web apps** per ZAP's own docs): a browser extension streams DOM elements, storage, client-side
  events, and **URI fragments** back to ZAP, so the crawl sees the client-side routes.
- **The Playwright/Puppeteer → proxy pattern**: drive the real app with a real browser holding a **real
  authenticated session**, routed through ZAP/Burp — the existing E2E suite *is* the crawl, sidestepping
  ZAP's two weak points (SPA crawling and brittle OAuth config). Passive rules see every XHR; then
  active-scan only what the suite touched.

## Setup — pinned tool versions (2026-08)

```bash
# Dalfox v3.2.1 (Rust rewrite since v3.0.0 — NO headless/CDP engine; DOM XSS is AST source→sink + PoC-URL).
cargo install dalfox   # or the release binary — hahwul/dalfox

# ZAP by Checkmarx 2.17.0 (formerly OWASP ZAP) + the Client Side Integration add-on for the Client Spider.
docker pull zaproxy/zap-stable:2.17.0        # NOT the EOL owasp/zap2docker-* images

# CSP validation — static evaluator (library only, no CLI: write a ~10-line wrapper) + header grader.
npm i csp_evaluator@1.1.8                     # note the UNDERSCORE package name
npx @mdn/mdn-http-observatory@1.6.3 <host>    # Observatory moved to MDN; needs Node >= 24

# Vulnerable-JS-library scan of the build output, and headless DOM templates.
npm i -g retire@5.4.3
# Nuclei v3.11.1 -headless for browser-driven DOM checks.
```

> **Renames / EOL to state honestly.** ZAP left OWASP (2023) → Checkmarx (Sept 2024): call it **"ZAP by
> Checkmarx (formerly OWASP ZAP)"**; use `zaproxy/zap-stable`, never `owasp/zap2docker-*`. **Dalfox v3.x is a
> Rust rewrite that removed the headless browser** — its DOM XSS is now static AST tracing, not a driven
> browser; the old `url`/`file`/`sxss` modes are legacy aliases under one `scan` subcommand. **CSP Evaluator
> ships no CLI** (library `csp_evaluator`, underscore). **Mozilla Observatory is now MDN HTTP Observatory**
> (`@mdn/mdn-http-observatory`, 1 scan/host/60s). Prototype-pollution CLI tools (`ppmap`, `ppfuzz`) are
> **stale (last touched 2022)** — use Burp **DOM Invader** for that surface instead.

## Anti-patterns

- **Calling a green CSP Evaluator score "CSP tested."** That validates the policy *text*, not enforcement —
  a report-only header, a `<meta>` override, or a route that omits the header all parse clean and block
  nothing. *Fix:* run the dynamic `securitypolicyviolation` validation on an authorized env.
- **Pointing a server-side DAST at an SPA and trusting the site tree.** The active scanner never saw the
  client-side routes; a clean run means "the half I crawled was clean." *Fix:* ZAP Client Spider or the
  Playwright→proxy pattern so the browser feeds the routes.
- **Treating Dalfox v3 like the old Go tool.** It no longer drives a browser — `--deep-domxss`/headless
  verification are gone; DOM findings are AST-graded (source reachable · CSP permits · no Trusted Types).
  *Fix:* use the AST grade for triage and confirm high-confidence DOM findings in a real browser (DOM
  Invader / ZAP 40026).
- **Firing a Dalfox `scan` or a blind-XSS callback against prod, or an OOB callback at a public server.**
  Injection is active testing; a blind callback exfiltrates. *Fix:* non-prod authorized env for injection;
  self-hosted interactsh for any data-carrying callback; both under the authorization line.
- **Fixing a DOM-XSS sink inside this skill.** The sink (`innerHTML`/`dangerouslySetInnerHTML`/`MarkupString`)
  is the frontend's code. *Fix:* route it to `fe-react-component-writer`/`fe-blazor-component-writer`; this skill
  proves and reports.
- **Ignoring `report-to` because `report-uri` "works."** `report-uri` is deprecated; `report-to` (CSP L3,
  Baseline Mar 2026) needs the `Reporting-Endpoints` header and is header-only (not `<meta>`). *Fix:* assert
  the report actually lands via `report-to`; a transitional policy specifies both.

## Rules (hard constraints)

- **Injection is active testing → authorized non-prod env only**, under a recorded, expiring
  (`#volatile`) authorization line; **blind/OOB callbacks need a separate sign-off** and a self-hosted
  server. Static/passive lanes (CSP Evaluator, Observatory, Retire.js, Dalfox AST-only) need no gate and run
  every PR.
- **Validate the CSP dynamically, not just statically** — a parses-clean policy is not a blocking policy.
  Assert no-execution **and** a `securitypolicyviolation` with `disposition: "enforce"` **and** a delivered
  `csp-violation` report. Report-only must not block (negative test).
- **SPA crawl through a browser** — ZAP Client Spider (the AJAX Spider is no longer recommended) or the
  Playwright→proxy pattern; never trust a server-side-only crawl's site tree for a client-routed app.
- **Two spines:** OWASP/WSTG primary (A05 DOM XSS · A02 header misconfig · A03 vulnerable libs · CLNT ids);
  ATT&CK `T1059.007` only where a proof executes and is handed onward.
- **The fe-\* handshake:** this skill tests; `security-hardening` + `fe-*` author. Sink fixes route
  back to the frontend generators — never fixed here.
- **Loot redaction:** a proven DOM XSS / prototype-pollution PoC reports the sink and the reachable action,
  not harvested cookies/tokens; nothing sensitive committed under `docs/`.
- **Pin versions** (Dalfox v3.2.1, ZAP 2.17.0, `csp_evaluator` 1.1.8, `@mdn/mdn-http-observatory` 1.6.3,
  Retire.js 5.4.3, Nuclei 3.11.1) and state the renames. No secrets in tool config.

## Cross-references

- `qa-security-shared` — the OWASP backbone (A05 Injection, A02 Misconfiguration, A03 supply chain), the
  authorization rule, triage, SARIF consolidation. **Load alongside.**
- `qa-security-active-scan` — the **server-side** DAST sibling (headers, injection through HTTP). This skill
  owns the **client/browser** layer it is blind to. Run both.
- `qa-security-exploit-validation` — the exploitation sibling for **server-side** injection classes (SQLi,
  SSRF, SSTI…). A confirmed DOM XSS that needs chaining hands off there / to `penetration-testing`.
- `qa/<stack>/skills/security-testing/dependency-scan` — **application** SCA (lockfile CVEs); Retire.js here
  catches vulnerable libs in the **shipped browser bundle** (a different surface). Boundary partners.
- **`security-hardening`** + **`fe-react`** / **`fe-blazor`** — the **authoring half
  of the handshake**: they write the strict nonce CSP, `Reporting-Endpoints`, and sink-safe rendering; this
  skill proves the header blocks and the report lands. Sink findings route to their component writers.
- `qa/manual/bug-report-writer` — write up a confirmed DOM XSS / CSP-bypass with the WSTG id, the PoC URL,
  and the browser evidence (no-execution + violation event + report body).
- `qa/_shared/agents/qa-security.md` — the step-by-step orchestrator that runs this in **Step 4b** dynamic lane.
- Deep dives: **`references/dom-xss.md`** (Dalfox v3.2.1 · DOM Invader · source→sink taint · Retire.js) ·
  **`references/csp-validation.md`** (CSP Evaluator · MDN Observatory · the `securitypolicyviolation`
  dynamic-block recipe · `report-to`) · **`references/spa-dast.md`** (ZAP Client Spider · the
  Playwright→proxy pattern · Nuclei headless · Burp SPA crawl).
