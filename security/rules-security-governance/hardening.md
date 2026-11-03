---
paths:
  - "docs/security/hardening/**"
  - "waf/**"
  - "crs/**"
  - "**/crs-setup.conf*"
  - "**/*modsecurity*.conf"
  - "**/coraza*.conf"
---

<!-- security-governance rules v1 (2026-11-03): hardening. Installed by /security-governance:rules; edit to fit this project. -->

# CSP, secure-header and WAF policy standards

Severity tags as in the core security-governance rules. These judge the policy; the middleware that emits it follows the app's own rules, and only a real-browser test proves it blocks.

## Content-Security-Policy

- `script-src` is nonce-based with `'strict-dynamic'`, never an origin allowlist. *major*
- The nonce is fresh per response from a CSPRNG; a literal nonce in a committed policy is a *blocker*.
- `object-src`, `base-uri` and `frame-ancestors` are present and `'none'`. *major*
- Reporting is `report-to` plus `Reporting-Endpoints` to a monitored receiver, not `report-uri` alone. *major*
- `Report-Only` is a rollout stage before enforcing, never the end state; no `<meta>` CSP beside a header policy. *major*
- No `'unsafe-eval'`; `'unsafe-inline'` and `https:` only as fallbacks beside a nonce. *major*
- The policy covers every response, not one route. *major*

## Secure headers

- Where headers are emitted, the baseline is complete: HSTS with a real `max-age`, `nosniff`, a non-leaking `Referrer-Policy`, a `Permissions-Policy` denying unused features. *major*
- HSTS `preload` and COEP `require-corp` only where their prerequisite holds, stated. *major*
- No version banner (`Server`, `X-Powered-By`). *minor*
- Each header is set in one place, not at the app and the proxy with different values. *major*

## WAF

- OWASP CRS 4 pinned to the current release or the 4.25.x LTS line, stated; never `latest`, never 3.x. *major*
- Paranoia level and `SecRuleEngine` stated; rollout is PL1 `DetectionOnly`, tune, raise, then block. *major*
- Exclusions are targeted and each names the false positive behind it; no rule-range removal, no `ctl:ruleEngine=Off` for a path. *major*
- Anomaly thresholds set deliberately once the paranoia level rises. *minor*
- Coraza for a new deployment; ModSecurity v2 there is a stated choice. *minor*
- Blocks reach an audit log or alert. *major*
- A WAF rule fronts a vulnerability, never replaces its code fix. *major*
- Payment pages in scope: PCI DSS 6.4.3 and 11.6.1 named. *major*
