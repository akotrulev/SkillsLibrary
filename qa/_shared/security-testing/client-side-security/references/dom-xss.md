# DOM XSS — Dalfox v3.2.1 · DOM Invader · source→sink · Retire.js

DOM-based XSS is the client-side blind spot: the browser reads attacker input from a **source** and passes
it to a **sink** with no server round-trip, so server-side DAST never sees it (`WSTG-CLNT-01`). This file
covers the maintained tooling for finding and proving it.

## The source→sink model (the concept to encode)

- **Sources** (attacker-controllable): `location.hash` / `.search` / `.href`, `document.URL`,
  `document.referrer`, `document.cookie`, `postMessage` event data, `localStorage` / `sessionStorage`,
  server-inserted `var data = "<...>"`.
- **Sinks** (execute/render): `innerHTML`, `outerHTML`, `document.write()`, `eval`, `Function`,
  `setTimeout(string)`, `location =`, `src`/`href` assignment, jQuery `$()` / `.html()`.
- WSTG's documented method is **manual code examination + crawling** because "automated tools have limited
  effectiveness" — which is why the AST tracer (Dalfox) and the interactive prober (DOM Invader) pair up
  rather than either being sufficient alone.

## Dalfox v3.2.1 — AST source→sink + payload proof

> **v3 is a Rust rewrite (since v3.0.0) — it drives NO browser and speaks no CDP.** The old headless
> verification is gone; DOM XSS is now **static AST tracing** (via `oxc`) plus PoC-URL generation. The
> `url`/`file`/`pipe` modes are legacy aliases under one **`scan`** subcommand; `sxss` is a flag.

**Detection axes** (report fields): `type` — `V` vulnerable (payload in an executable DOM position) · `R`
reflected (position unconfirmed) · `A` AST-detected (source→sink) · `I` informational (vulnerable library);
`detection_method` — reflection · DOM-verification · AST · out-of-band · library; plus `severity`. AST DOM
findings are graded **high/low** on: source attacker-reachable via URL · CSP permits execution · no Trusted
Types interception · no recognized sanitizer.

```bash
# 1. AST-only, sends no payloads — safe every PR, use for triage.
dalfox scan https://app.example.test --dry-run --format sarif --output dalfox-ast.sarif

# 2. Single URL + blind callback (SELF-HOSTED interactsh — separate sign-off, it exfiltrates).
dalfox scan https://app.example.test -b https://oob.example.test

# 3. Batch with an explicit injection marker (query or header).
dalfox scan 'https://app.example.test/?q=FUZZ' --inject-marker FUZZ --format json --output out.json
cat urls.txt | dalfox scan --headers "Authorization: Bearer $TOKEN" --silence

# 4. Stored XSS: inject here, verify there (two sessions).
dalfox scan https://app/comment --sxss --sxss-url https://app/admin/feed \
  --sxss-method GET -H "Cookie: admin=..." --delay 500

# 5. CI-gate shape: exit 0 none / 1 findings / 2 error.
dalfox scan urls.txt --waf-evasion --rate-limit 20 --format sarif --output dalfox.sarif
```

**Flags that matter:** `--input-type {auto,url,file,pipe,raw-http,har}` · `--dedup-urls {exact,signature,off}`
· `--format {plain,json,jsonl,markdown,sarif,toml}` · `--dry-run` (AST only) · `--baseline` (diff vs previous
report — the triage-gate discipline) · `--custom-payload <file>` · `--skip-ast-analysis` /
`--skip-mining` / `--skip-mining-dict` · `--waf-evasion` · `--blind` / `--blind-oob` · `--session-check <regex>`
+ `--on-session-loss {abort,continue}`. `dalfox payload` lists selectors (`dom-clobbering`, `mxss`,
`portswigger`, `all`, …). Config: `~/.config/dalfox/config.toml` or `--config`.

> Use the **AST grade for triage** (it sends nothing), then **confirm a high-confidence DOM finding in a real
> browser** — DOM Invader or ZAP rule 40026 — because v3 can't itself verify execution in a live DOM.

## Burp DOM Invader — the interactive prober

Preinstalled in Burp's built-in browser (a DevTools panel tab); **interactive, not headless/scriptable**. It
covers what the AST tracer can't automate:

- **Canary** — a marker injected into sources; the **augmented DOM view** highlights controllable sinks and
  shows sanitization.
- **Web message (`postMessage`) testing** — log/modify/resend messages, auto-probe with crafted ones
  (`WSTG-CLNT-11`).
- **Client-side prototype pollution** — toggle on under Settings → Attack types → prototype pollution, reload;
  auto-detect sources (URL + JSON web messages) → **Test** → **Scan for gadgets** → **Exploit** (generates a
  working source+gadget+sink PoC). This is the practical tool for prototype pollution — the CLI tools
  (`ppmap`, `ppfuzz`) are stale (2022).
- **DOM clobbering** detection.

## postMessage & open-redirect specifics

- **postMessage (`WSTG-CLNT-11`):** sender must name the target origin (`*` leaks data on redirect); receiver
  must use **strict equality** on `event.origin` — `indexOf(".example.org")` is bypassed by
  `www.example.org.attacker.com`; no check accepts any origin. Message data → `innerHTML` is DOM XSS.
- **DOM open redirect (`WSTG-CLNT-04`):** sink `window.location` from `location.hash`.
  `http://victim/?#//evil` redirects; drop a URL-scheme guard and the same sink takes
  `#javascript:alert(document.cookie)` — a redirect sink is also an XSS sink.

## Retire.js 5.4.3 — vulnerable JS libraries (A03 supply chain)

Scans built JS / node modules for known-vulnerable libraries and emits an SBOM. This is the **shipped browser
bundle** surface — distinct from `dependency-scan` (lockfile CVEs).

```bash
retire --path ./dist --outputformat json --outputpath retire.json
retire --js --jspath ./public/vendor
retire --exitwith 13          # CI gate on findings
```

Maps to **A03:2025 Software Supply Chain Failures**. Also ships a browser extension and Burp/ZAP integrations.

## Rules

- Dalfox AST (`--dry-run`) is safe/every-PR; a `scan` fires payloads → authorized non-prod env; blind/OOB
  callbacks → separate sign-off + self-hosted server.
- Confirm high-confidence DOM findings in a real browser (v3 can't); use DOM Invader for prototype
  pollution / postMessage / clobbering.
- Map DOM XSS → A05:2025 / `WSTG-CLNT-01`; redirect → CLNT-04; web messaging → CLNT-11; vulnerable libs →
  A03:2025. Sink fixes route to the `fe-*` component writers, not here.
- Report the sink + reachable action, redact harvested cookies/tokens.
