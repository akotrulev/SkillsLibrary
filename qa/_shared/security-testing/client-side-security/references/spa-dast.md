# SPA-specific DAST — crawling a client-routed app

A server-side DAST sits below the browser and sees API calls but not the **client-side routes** that trigger
them — URI fragments never reach the proxy, state is built by XHR/fetch, the DOM appears after the response.
So the active scanner's site tree is half-empty and a "clean" run only covers the half it crawled. Two
documented answers below. Both feed **A05:2025 Injection / A02:2025 Misconfiguration** findings.

> **Naming:** **ZAP by Checkmarx 2.17.0** (left OWASP 2023 → Checkmarx Sept 2024). Never "OWASP ZAP" in new
> material. Images: `zaproxy/zap-stable` (per release), `zap-weekly`, `zap-bare` (CI-minimal, no packaged
> scan scripts); `owasp/zap2docker-*` is **EOL**.

## ZAP Client Spider — the current recommendation

> ZAP's own docs: **"the AJAX Spider is no longer the recommended option for crawling modern web apps."** The
> **Client Spider** (Client Side Integration add-on) replaces it: a **ZAP browser extension** auto-installed
> into the launched Firefox/Chrome streams back **DOM elements** (forms, buttons, inputs, links), **cookies +
> localStorage**, **client-side events** (load/unload, DOM mutations), and **URI fragments** — the client-side
> routes a proxy can't see — building a **Client Map**.

```yaml
# spa-plan.yaml — an SPA-shaped Automation Framework plan.
env:
  contexts:
    - name: app
      urls: [ "https://app.example.test" ]
jobs:
  - type: spiderClient                 # browser-extension-driven SPA crawl (the current recommendation)
    parameters: { context: app, url: "https://app.example.test" }
  - type: passiveScan-wait
  - type: activeScan                   # fires payloads — authorized non-prod env only
    parameters: { context: app }
  - type: report
    parameters: { template: sarif-json, reportDir: /zap/wrk, reportFile: zap-spa }
```

```bash
# Install the add-on then run the plan (Docker).
docker run -v "$PWD:/zap/wrk:rw" -t zaproxy/zap-stable:2.17.0 \
  zap.sh -addonupdate -addoninstall client -cmd -autorun /zap/wrk/spa-plan.yaml

# Packaged baseline (spider + passive only — safe/CI).  Full scan adds the active scanner (authorized env).
docker run -v "$PWD:/zap/wrk:rw" -t zaproxy/zap-stable:2.17.0 zap-baseline.py -t https://app.example.test
```

AF jobs available: `spider`, `spiderAjax`, **`spiderClient`**, `activeScan`, `passiveScan-config/-wait`,
`authentication`, `report`, `exitStatus`, `openapi`/`graphql`/`soap`, … ZAP's **DOM XSS active rule** is alert
id **40026** (`rules.domxss.browserid` = `firefox-headless` default / `chrome-headless`), which drives a real
browser to confirm DOM XSS at URL-fragment and form-input injection points.

## The Playwright/Puppeteer → proxy pattern (authenticated SPA)

Drive the real app with a real browser holding a **real authenticated session**, routed through ZAP/Burp —
the existing E2E suite *is* the crawl. Sidesteps ZAP's two weak points (SPA crawling, brittle OAuth config):
passive rules see every XHR; then active-scan only what the suite touched.

```js
// Playwright: proxy through ZAP, reuse a real session, ignore ZAP's CA in the test env.
const browser = await chromium.launch({ proxy: { server: "http://127.0.0.1:8080" } });
const ctx = await browser.newContext({ ignoreHTTPSErrors: true, storageState: "auth.json" });
```

```bash
# 1. ZAP as a daemon proxy for the browser to feed.
zap.sh -daemon -host 127.0.0.1 -port 8080 -config api.key=$ZAP_KEY &

# 2. Run the E2E suite through it (this IS the crawl).
HTTP_PROXY=http://127.0.0.1:8080 npx playwright test

# 3. Drain passive rules, then active-scan only what the suite touched (authorized env).
curl "http://127.0.0.1:8080/JSON/pscan/view/recordsToScan/?apikey=$ZAP_KEY"
curl "http://127.0.0.1:8080/JSON/ascan/action/scan/?apikey=$ZAP_KEY&url=https://app.example.test&recurse=true"
curl "http://127.0.0.1:8080/OTHER/core/other/htmlreport/?apikey=$ZAP_KEY" -o zap.html
```

Reference implementation: `github.com/kston83/playwright-zap-dast`. State honestly: active scanning + fuzzing
are time-expensive and need an isolated env; OAuth token-refresh flows stay brittle.

## Nuclei 3.11.1 — headless DOM checks in a template

```bash
nuclei -u https://app.example.test -headless -t headless/ -severity high,critical
nuclei -u https://app.example.test -t http/misconfiguration/ -tags csp,headers   # header-misconfig, no browser
```

Headless actions: `navigate`, `script` (with `hook: true`), `click`, `waitload`, `waitdialog`, form
interaction. v3.11.1 improved headless element rendering. Use for templated, repeatable DOM/dialog checks.

## Burp SPA crawl (the commercial companion)

Burp's crawler builds a **directed graph of locations identified by content, not URL** (so ephemeral CSRF
tokens don't fracture the crawl) and uses an **embedded Chromium** (browser-powered scanning) so JS-generated
UI and async requests are seen; it handles same-URL state changes and volatile content by re-recognizing a
location. Authenticated-only crawl and automatic CSRF-token handling are built in.

## Rules

- **Crawl a client-routed SPA through a browser** — ZAP Client Spider or the Playwright→proxy pattern; never
  trust a server-side-only crawl's site tree.
- The AJAX Spider is deprecated for modern apps — use `spiderClient`.
- Baseline/passive is safe & CI; `activeScan` / rule 40026 / Nuclei headless XSS fire payloads → authorized
  non-prod env under the authorization line.
- Reuse the project's real E2E session (`storageState`) rather than reconfiguring auth in ZAP.
- Emit SARIF; consolidate per `qa-<stack>:security-foundations`. Map findings to A05/A02 + the CLNT ids.
