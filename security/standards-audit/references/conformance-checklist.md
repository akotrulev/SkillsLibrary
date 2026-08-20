# security-governance Conformance Checklist — the 14 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`C2`, `H7`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number.

**Every row is about a GOVERNANCE ARTIFACT** — a detection rule, a header/CSP/WAF policy, a secret-store wiring or rotation runbook, an evidence register, a posture report. Application code, infrastructure code, and the vulnerabilities in them belong to `be-*` / `fe-*` / `devops-auditor` / `qa-security` (see the skill's fence). If a row tempts you toward the app, stop.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a hit is never a finding — read the file). *Sev* = the default severity; adjust for real impact and say why.

## The absence rule — read this before Phase 1

**A control the repo has never adopted produces no finding.** No detection repo, no CSP, no WAF, no rotation runbook, no compliance scope → those sections are **N/A**, and the absence is recorded in the applicability matrix as a **coverage note routed to `security-architect`**, never as a conformance finding. Conformance audits an artifact that exists against the rules it must follow; *whether a control should exist at all* is a posture question and posture is the architect's lane.

**The one deliberate edge — partial adoption of a defined baseline is a finding.** A header block that ships HSTS and `nosniff` but no CSP is a finding (F1/E-section): the artifact exists and violates the plugin's "full baseline, each authored with intent" rule. The line is *nothing adopted* → N/A + coverage note; *adopted and incomplete* → finding.

## The version lane — a standards-and-tooling pin lane, and it inverts

There is no TFM here. The lane is the set of **standards and tool versions the repo pins**, and the rule is not "never flag down-level" but **"pin it, and stay valid under the pin"**:

| State | Verdict |
|---|---|
| Pinned and current | conforms |
| Pinned to an older-but-supported edition (ATT&CK v19.0, CRS **4.25.x LTS**, ASVS 4.0.3) | **deviation**, not a finding — unless a rule or mapping in the repo is *invalid* under that pin |
| Pinned to a **withdrawn/retired** edition (ISO 27001:**2013**, PCI DSS **3.2.1**/**4.0**, `sigmac`, CRS 3.x) | finding |
| Unpinned, or silently mixed across files | finding |

**Verified current as of 2026-08-20** — re-verify before citing, these move:

| Standard / tool | Current | Notes |
|---|---|---|
| MITRE ATT&CK Enterprise | **v19.2** (2026-08-06) | v19 (2026-04-28) retired `Defense Evasion`: **Stealth** keeps **TA0005**, **Defense Impairment** is the new **TA0112**. 15 tactics · 222 techniques · 475 sub-techniques at v19.0 |
| sigma-cli / pySigma | **3.1.0** (2026-07-07) | 3.x is the supported line. The legacy `sigmac` converter is **dead** |
| OWASP CRS | **4.29.0** (2026-08-17) | **4.25.x is the CRS-4 LTS line** — a deliberate LTS pin is a deviation, not staleness |
| OWASP Top 10 | **2025** | A01 Broken Access Control · **A02 Security Misconfiguration** · **A03 Software Supply Chain Failures** · A04 Cryptographic Failures · **A05 Injection** · A06 Insecure Design · **A07 Authentication Failures** · A08 Software/Data Integrity Failures · **A09 Security Logging and Alerting Failures** · A10 Mishandling of Exceptional Conditions |
| OWASP ASVS | **5.0.0** (2025-05-30) | ~350 requirements, 17 chapters, L1/L2/L3 — the bridge, not a certifiable framework |
| PCI DSS | **4.0.1** | The only active version (4.0 retired 2024-12-31); all requirements in scope for 2026 assessments |
| ISO/IEC 27001 | **:2022** | 93 Annex A controls; the 2013 edition is withdrawn (transition ended 2025-10-31) |
| SOC 2 | 2017 TSC + **2022 revised points of focus** | CC1–CC9 mandatory |
| NIST CSF | **2.0** | 6 functions incl. **Govern**, 106 subcategories |
| NIST OSCAL | **1.2.x** | the **Mapping Model** landed in 1.2.1 (Mar 2026) |

> **The skills and this table agree — keep it that way.** The `secgov-*` skills were reconciled against the sources above on 2026-08-20 (the OWASP ids were on 2021 numbering, the sigma-cli pin was two majors behind, the CRS pin claimed "current" for what is actually the LTS line, and one ATT&CK tactic id — `TA0060` for Stealth — did not exist). If they ever drift apart again, the engine's "the owning skill wins, and report the disagreement" rule settles *rule* conflicts, **not** factual errors in a cited standard: audit against the verified table above, and raise the skill text as an **open question for the maintainer**, never as a finding against the audited repo. **Re-verify the whole table before each round** — every row in it moved at least once in the twelve months before this was written.

**Recipes** use `rg` (ripgrep), which honours `.gitignore`. Without it, `grep -rn --exclude-dir=node_modules --exclude-dir=.git` is equivalent. Set the artifact roots once:

```bash
DET=$(ls -d detections rules sigma 2>/dev/null | tr '\n' ' ')      # the detection repo, wherever it lives
SEC=$(ls -d docs/security 2>/dev/null)                              # posture, runbooks, compliance, hardening
rg -n "<pattern>" $DET -g '*.yml' -g '*.yaml'
```

> **Guard the empty path variable before running anything.** `rg PATTERN` with **no** path argument searches the whole working tree. So an unset `$DET` on a repo with no detection folder silently turns `rg --files-without-match "^id:" $DET -g '*.yml'` into *"every YAML in the repo that lacks an `id:` field"* — hundreds of false leads that look like section-C findings. **If `$DET` is empty, sections B–D are N/A and their recipes must not run at all**; same for `$SEC` and sections J–M. Make that structural rather than remembering it:
>
> ```bash
> [ -n "$DET" ] || DET=/dev/null   # empty ⇒ sections B-D are N/A; never let rg fall back to the whole repo
> [ -n "$SEC" ] || SEC=/dev/null   # empty ⇒ sections J-M are N/A
> ```
>
> `/dev/null` makes the recipe a guaranteed no-op instead of a repo-wide sweep. This is the same class of bug `CONFORMANCE-AUDIT-PLAN.md` §9 records for the react build ("shell-recipe bugs") — the variable is fine, the *unset* variable is not.

**Owning skills:** [`secgov-detection-engineering`](../../detection-engineering/SKILL.md) · [`secgov-security-hardening`](../../security-hardening/SKILL.md) · [`secgov-secrets-hardening`](../../secrets-hardening/SKILL.md) · [`secgov-compliance-evidence-mapping`](../../compliance-evidence-mapping/SKILL.md) · the [`security-architect`](../../agents/security-architect.md) agent contract (section L) · [`ep-code-comments`](../../../engineering-practices/code-comments/SKILL.md) (section N).

---

## A — Adoption map, standards pins & version lane
*Owning skills: all four `secgov-*` skills + the `security-architect` agent contract*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | The governance artifacts that exist are discoverable in one stated place | Detections, policy, runbooks, and the register scattered with no stated home, so a reader cannot tell *adopted* from *absent* | `ls -d detections rules sigma waf $SEC $SEC/{runbooks,hardening,compliance,posture} 2>/dev/null`; read any security README | minor |
| A2 | The ATT&CK version is pinned in the detection repo | No version recorded anywhere — technique and tactic ids move between releases and nothing says which one the tags were authored against | `rg -ni "attack.?version\|ATT&CK v1[89]\|enterprise-attack-1[89]" $DET $SEC` | major |
| A3 | Tactic slugs are valid under the pinned version **[ATT&CK]** | `attack.defense-evasion` on a repo pinned to v19+ — TA0005 was renamed **Stealth** and **Defense Impairment (TA0112)** split out | `rg -n "attack\.defense-evasion" $DET` + the pin from A2 | major |
| A4 | Sigma tooling is pinned and on a supported line | No pinned `sigma-cli`/pySigma version, or the dead `sigmac` converter still in the pipeline (3.1.0 current) | `rg -ni "sigma-cli\|sigmac\b\|pysigma" -g '!*.lock' .`; read `requirements*.txt`, `pyproject.toml`, the CI files | major |
| A5 | The WAF ruleset is pinned to a supported CRS 4 line | CRS unpinned, floating `latest`, or still on CRS 3.x — 4.29.0 current, **4.25.x LTS is a deviation not a finding** | `rg -ni "coreruleset\|owasp.?crs\|crs.?4\." -g '*.conf' -g '*.yml' -g '*.yaml' -g 'Dockerfile*'` | major |
| A6 | No withdrawn compliance edition is cited | **ISO/IEC 27001:2013**, **PCI DSS 3.2.1 / 4.0**, or SOC 2 without the 2022 revised points of focus | `rg -n "27001:2013\|27002:2013\|PCI DSS 3\.2\|PCI DSS 4\.0[^.]" $SEC` | major |
| A7 | OWASP ids use the current Top 10 edition consistently | 2021 numbering presented under a 2025 label — **A03:2025 is Software Supply Chain Failures**, Injection is **A05:2025** | `rg -n "A0[0-9]:20(21\|25)" $SEC $DET`; then `rg -ni "A03.*injection\|A05.*misconfig\|A07.*identification" $SEC $DET` | major |
| A8 | ASVS is cited at 5.0 **and** the verified level is stated | "ASVS-aligned" with no version and no L1/L2/L3 — the claim is unfalsifiable | `rg -n "ASVS" $SEC` | minor |
| A9 | One pinned edition per standard across the whole repo | The same standard pinned two ways in two files (ATT&CK v19 in the rules, v18 in the posture report) | compare every hit from A2–A8 against each other | major |
| A10 | A version bump re-maps, it does not just bump | A commit that moved the pin but touched no rule tag or framework mapping | `git log --oneline -20 -- $DET $SEC`; read the bump commit's diff | major |

---

## B — Detection repository & the detection-as-code pipeline
*Owning skill: [`secgov-detection-engineering`](../../detection-engineering/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | Detections live in version control, not a SIEM console | Rules referenced in runbooks/reports with no rule files in the repo; "configured in Splunk/Sentinel" treated as the source of truth | `ls -d $DET 2>/dev/null`; `rg -ni "created in (splunk\|sentinel\|the console)\|configured in the (siem\|portal)" $SEC` | major |
| B2 | CI lints the ruleset | No `sigma check` (or equivalent) step, so schema errors, duplicate UUIDs, and missing ATT&CK tags reach `main` | `rg -n "sigma check" .github/workflows .gitlab-ci.yml azure-pipelines.yml 2>/dev/null` | major |
| B3 | CI converts to the deployed backend(s) | Rules authored as Sigma but the SIEM query hand-maintained beside them — the two drift and the YAML stops being the source of truth | `rg -n "sigma convert" .github/workflows .gitlab-ci.yml 2>/dev/null`; `rg -l -g '*.spl' -g '*.kql' "" $DET` | major |
| B4 | The field-mapping pipeline is applied, not assumed | `sigma convert -t <backend>` with no `-p <pipeline>` — the query compiles cleanly against field names the logs never use | `rg -n -A1 "sigma convert" .github/workflows .gitlab-ci.yml 2>/dev/null` | major |
| B5 | `status` tracks maturity through promotion | Every rule `status: stable` on first commit, or every rule stuck at `experimental` forever | `rg -h "^status:" $DET \| sort \| uniq -c` | minor |
| B6 | There is a rollback path | Rules deployed by a manual console push with no commit to revert and no redeploy job | read the deploy job in CI; `git log --oneline -- $DET \| head` | major |
| B7 | The community ruleset is extended, not enabled wholesale | A vendored SigmaHQ tree imported entire (3,000+ rules) in one commit with no selection or tuning after it | `rg -l "" $DET -g '*.yml' \| wc -l`; `git log --oneline --stat -- $DET \| head -30` | major |
| B8 | Each rule names the hypothesis that produced it | `references:` empty or carrying only the ATT&CK URL — no threat-model entry, pentest finding, or incident behind it | `rg -n -A3 "^references:" $DET` | minor |
| B9 | Non-Sigma detections are still code | A Sentinel analytics rule, an Elastic detection, or a saved search clicked in and never represented in the repo | `rg -ni "savedsearches\.conf\|analytics_rule\|detection_rules\|Microsoft.SecurityInsights" .`; read the deploy path | major |

---

## C — Sigma rule anatomy, ATT&CK mapping & correlations
*Owning skill: [`secgov-detection-engineering`](../../detection-engineering/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | Every rule carries a stable UUID `id`, never regenerated on edit | `id:` missing, or a diff showing the id changed alongside a content edit — tuning history and SIEM deployment state detach from the rule | `rg --files-without-match "^id:" $DET -g '*.yml' -g '*.yaml'`; `git log -p -- $DET \| rg "^[-+]id:"` | major |
| C2 | UUIDs are unique across the ruleset | Two rules sharing an `id` (a copy-pasted seed) — the SIEM treats them as one and the second silently replaces the first | `rg -h -o "^id: .*" $DET \| sort \| uniq -d` | blocker |
| C3 | Every rule maps to ≥1 ATT&CK technique | `tags:` absent, or carrying a tactic with no `attack.tNNNN` — the primary spine is missing and `sigma check` should already fail it | `rg --files-without-match "attack\.t[0-9]" $DET -g '*.yml' -g '*.yaml'` | major |
| C4 | Technique tags are well-formed and resolve in the pinned version | `attack.t1021.1` (malformed sub-technique), a retired id, or a sub-technique that does not exist in the pin | `rg -h -o "attack\.t[0-9.]+" $DET \| sort -u`, then check each against the A2 pin | major |
| C5 | `title` and `description` say what is detected and why it matters | `title: rule 4`; a description that restates the `detection:` block in prose | read every rule surfaced by C3 | minor |
| C6 | `level` is honest | Every rule `critical` (or every rule `low`) — the SIEM's triage priority becomes decoration | `rg -h "^level:" $DET \| sort \| uniq -c` | minor |
| C7 | Multi-event logic uses Sigma Correlations, not a hand-written backend query | A raw SPL/KQL blob committed as "the rule" because the author needed a rate, a sequence, or a join | `rg -ln "stats count\|summarize \|eventstats\|\| where " $DET` | major |
| C8 | A correlation references base rules by `id`, and those rules exist | `correlation.rules:` naming an id with no file behind it — the correlation compiles to nothing | `rg -n -A6 "^correlation:" $DET`; cross-check every referenced id against C1's list | major |
| C9 | Logic a backend cannot compile is documented, not silently dropped | `sigma convert` warns on a correlation type the target backend lacks and the pipeline ignores the warning | read the CI convert step's failure policy; run the repo's own convert (opt-in only) | major |

---

## D — Detection testing, tuning & the telemetry contract
*Owning skill: [`secgov-detection-engineering`](../../detection-engineering/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | Every rule declares a `logsource` | `logsource:` absent, or a bare `product:` with no `service`/`category` — the telemetry contract is unstated | `rg --files-without-match "^logsource:" $DET -g '*.yml' -g '*.yaml'` | major |
| D2 | Every declared `logsource` is actually collected | A rule querying `windows/security` on a stack that ships only container stdout — it converts cleanly and can never fire, while the coverage map counts it | `rg -h -A3 "^logsource:" $DET \| sort -u` vs the shipped pipeline (`rg -n "scrape_configs\|loki\|filebeat\|fluent\|winlogbeat" -g '*.yml' -g '*.yaml'`) | major |
| D3 | Every rule has a true-event sample and it fires | No `tests/` beside the rules, or samples present for a fraction of them | `rg -l "" $DET -g '*.yml' \| wc -l` vs `ls $DET/**/tests/ 2>/dev/null` | major |
| D4 | Every rule has a benign sample and stays quiet on it | Only a positive fixture — the false-positive half of the merge gate was skipped, which is the half that matters at 3am | inspect each `tests/` dir for a benign/negative fixture per rule | major |
| D5 | The sample run is a merge gate, not a local convenience | Fixtures committed but no CI step executes them, so nothing enforces D3/D4 | `rg -n "tests/\|pytest\|sigma test" .github/workflows .gitlab-ci.yml 2>/dev/null` | major |
| D6 | Every rule states a specific `falsepositives` entry | `falsepositives: - Unknown` — the tuning contract the reviewer holds you to was not thought through | `rg -n -A2 "^falsepositives:" $DET \| rg -ni "unknown\|none\|n/a\|tbd"` | major |
| D7 | Tuning is expressed in the rule, not in a console mute | A rule whose noise was handled by muting the alert channel, with no exclusion or refined selection in the file | read `git log` on the noisiest rules; check any suppression/mute config against the rule set | major |
| D8 | Test fixtures carry no real secret, credential, or PII | Sample logs lifted from a real incident with the token, hash, or customer identifier left in | `rg -ni "(password\|secret\|token\|api.?key\|authorization)\s*[:=]" $DET -g '*test*'` | blocker |
| D9 | Authored vs validated is stated per technique | A coverage claim ("we detect T1003") with no `purple-team-engineer` validation artifact behind it — authoring is half the loop | `rg -n "T[0-9]{4}" $SEC/posture $SEC/*coverage* 2>/dev/null` vs `ls $SEC/*purpleteam* 2>/dev/null` | major |

---

## E — Content-Security-Policy
*Owning skill: [`secgov-security-hardening`](../../security-hardening/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | `script-src` is nonce-based with `strict-dynamic`, not an origin allowlist | `script-src 'self' https://cdn.example.com …` — allowlists are routinely bypassed via JSONP or an open redirect on an allowed host | `rg -n "script-src"` | major |
| E2 | The nonce is per-request, from a CSPRNG | A literal nonce baked into a committed policy string or config template — a reused nonce is decoration | `rg -n "nonce-[A-Za-z0-9+/=]{8,}"` | blocker |
| E3 | The hard-stop directives are present and `'none'` | `object-src`, `base-uri`, or `frame-ancestors` missing — the three cheapest high-value stops (plugin injection, `<base>` hijack, clickjacking) | `rg -n "object-src\|base-uri\|frame-ancestors"` | major |
| E4 | Reporting uses `report-to` + `Reporting-Endpoints` | `report-uri` alone — deprecated, and violations may never be collected | `rg -n "report-uri\|report-to\|Reporting-Endpoints"` | major |
| E5 | The reporting endpoint is real and monitored | `report-to` naming a group with no matching `Reporting-Endpoints` entry, or an endpoint nothing consumes — a policy no one watches drifts | `rg -n -A1 "Reporting-Endpoints"`, then trace the receiver | major |
| E6 | `Report-Only` is a rollout stage, not the finished state | `Content-Security-Policy-Report-Only` shipped with **no** enforcing header on the same route — it parses clean and blocks nothing | `rg -n "Content-Security-Policy(-Report-Only)?"` — compare the two sets route by route | major |
| E7 | No `<meta>` CSP silently overriding the header | `<meta http-equiv="Content-Security-Policy">` in a template alongside a header policy | `rg -n "http-equiv=[\"']Content-Security-Policy"` | major |
| E8 | The policy applies on every response, not one route | Middleware registered behind a route filter, or a static-file branch that returns before it | read the middleware registration order at the composition root | major |
| E9 | `'unsafe-eval'` absent; `'unsafe-inline'`/`https:` appear only as nonce-context fallbacks | `'unsafe-eval'` present, or `'unsafe-inline'` in a policy with **no** nonce — where it really does disable the protection | `rg -n "unsafe-eval\|unsafe-inline"`, then read the whole directive | major |
| E10 | The policy has a block-proof, not just a clean parse | "CSP hardened" claimed with no `client-side-security` dynamic block-proof artifact — the authoring half marked itself done | `rg -ni "csp\|content-security" $SEC`; `ls $SEC/**/*client-side* 2>/dev/null` | major |

---

## F — The secure-headers baseline
*Owning skill: [`secgov-security-hardening`](../../security-hardening/SKILL.md)*

> **Applies only where the repo emits headers it controls** (app middleware, reverse-proxy/ingress, CDN config). A library with no HTTP surface is N/A. A repo that emits *some* of the baseline is **in scope and incomplete** — see the absence rule.

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | The core baseline is complete where headers are emitted at all | HSTS + `nosniff` shipped, `Referrer-Policy` and `Permissions-Policy` absent — the artifact exists and misses the baseline | `rg -n "Strict-Transport-Security\|X-Content-Type-Options\|Referrer-Policy\|Permissions-Policy"` | major |
| F2 | HSTS `max-age` is meaningful | `max-age=0`, or a few-hundred-second age shipped as "HSTS on" | `rg -n "Strict-Transport-Security"` | major |
| F3 | `preload` only where every subdomain is HTTPS-ready, with the prerequisite stated | `preload` cargo-culted — a one-way door that hard-fails HTTP for the whole domain tree for the `max-age` | `rg -n "preload"`, then read the accompanying note or ADR | major |
| F4 | `X-Content-Type-Options: nosniff` | absent | `rg -n "X-Content-Type-Options"` | minor |
| F5 | `Referrer-Policy` set and not leaking | `unsafe-url` or `no-referrer-when-downgrade` sending full URLs cross-origin | `rg -n "Referrer-Policy"` | minor |
| F6 | `Permissions-Policy` denies the features the app does not use | Header absent, or a powerful feature left at `*` | `rg -n "Permissions-Policy"` | minor |
| F7 | `X-Frame-Options: DENY` kept as the legacy backstop | `frame-ancestors` only, while legacy-browser support is claimed | `rg -n "X-Frame-Options"` | nit |
| F8 | COOP/CORP set; COEP `require-corp` **only** where cross-origin isolation is needed | `require-corp` enabled with no `SharedArrayBuffer`/high-res-timer use — it silently breaks cross-origin resources that omit CORP | `rg -n "Cross-Origin-(Opener\|Embedder\|Resource)-Policy"`; `rg -n "SharedArrayBuffer\|crossOriginIsolated"` | major |
| F9 | Version banners removed | `Server:` or `X-Powered-By:` shipping a version — free recon | `rg -ni "X-Powered-By\|expose_php\|server_tokens"` | minor |
| F10 | Headers set in one authoritative place | The same header set at the app **and** the reverse proxy with different values — the effective value is whichever wins and nobody knows which | compare app middleware against ingress/proxy/CDN config side by side | major |

---

## G — WAF ruleset & rollout discipline
*Owning skill: [`secgov-security-hardening`](../../security-hardening/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| G1 | CRS config, custom rules, and exclusions are in Git | A WAF configured in a cloud console with nothing version-controlled — no review, no rollback | `ls -d waf crs 2>/dev/null`; `rg -n "SecRule\|coreruleset" -g '*.conf' -g '*.yml' -g '*.yaml'` | major |
| G2 | Paranoia level and engine mode are stated, not defaulted | No `blocking_paranoia_level` and no `SecRuleEngine` anywhere — nobody can say what the WAF is doing | `rg -n "paranoia_level\|SecRuleEngine"` | major |
| G3 | Rollout followed PL1 `DetectionOnly` → tune → raise → block | `SecRuleEngine On` at PL2+ in the first commit with no tuning history — false positives break real traffic and the WAF gets disabled, which is worse than none | `rg -n "SecRuleEngine\|paranoia_level"`; `git log -p -- <those files>` | major |
| G4 | Exclusions are targeted, not blanket | `SecRuleRemoveById` stripping whole rule ranges, or `ctl:ruleEngine=Off` for a path | `rg -n "SecRuleRemoveById\|SecRuleRemoveByTag\|ctl:ruleEngine=Off"` | major |
| G5 | Each exclusion records the false positive that justified it | An exclusion list with no reason per entry — nobody can ever safely remove one | read the exclusion file | minor |
| G6 | Anomaly-scoring thresholds are set deliberately | Inbound/outbound thresholds left at defaults while the paranoia level was raised | `rg -n "inbound_anomaly_score_threshold\|outbound_anomaly_score_threshold"` | minor |
| G7 | The engine is a currently-recommended one | ModSecurity v2 on a **new** deployment where Coraza is the current recommendation — a stated, deliberate choice is a deviation; an unexamined one is a finding | `rg -ni "modsecurity\|coraza\|crowdsec" -g '*.conf' -g 'Dockerfile*' -g '*.yml' -g '*.yaml'` | minor |
| G8 | The WAF is not standing in for the code fix | A custom rule blocking injection on an endpoint that has an open injection finding routed nowhere — the vulnerability is hidden, not fixed | cross-read the findings in `$SEC` against the custom rules | major |
| G9 | WAF blocks are observable | Blocking enabled with no audit-log or alert path — you cannot tell an attack from a false positive | `rg -n "SecAuditLog\|SecAuditEngine"`; trace the log pipeline | major |

---

## H — Secret store & the leak channel
*Owning skill: [`secgov-secrets-hardening`](../../secrets-hardening/SKILL.md)*

> **Fence:** *detecting* a committed secret is `qa-security-secrets-scan`'s lane. This section audits the **hardening artifacts** — the store wiring, the gates, the credential lifetime. H2/H7 are here because a live secret found while reading a config is a blocker you report wherever you find it, not because this audit is a scanner.

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | A secret store is named and wired, not implied | Secrets read from a committed file or a bare env var with no store behind it | `ls .env* 2>/dev/null`; `rg -ni "ExternalSecret\|vault\|SecretsManager\|KeyVault\|sops" -g '*.yml' -g '*.yaml' -g '*.tf'` | major |
| H2 | No secret value committed in config | A real value in `appsettings.json` / `application.yml` / `.env` / a chart `values.yaml` | `rg -ni "(password\|secret\|token\|api.?key\|connectionstring)\s*[:=]\s*[\"']?[A-Za-z0-9+/=_-]{12,}"` — **a hit is a lead**; placeholders, LocalStack fixtures, and test doubles are not findings | blocker |
| H3 | A pre-commit secret hook is installed | No `gitleaks protect --staged` or `git-secrets` hook — the cheapest gate is missing, and a secret that never reaches the remote never needs rotating | `cat .pre-commit-config.yaml 2>/dev/null`; `ls .githooks 2>/dev/null`; `rg -n "core.hooksPath" .git/config` | major |
| H4 | The CI secret gate runs full history and fails the build | Gitleaks/TruffleHog wired but `continue-on-error: true` or advisory-only — a gate that cannot fail is not a gate | `rg -n -A5 -i "gitleaks\|trufflehog" .github/workflows .gitlab-ci.yml 2>/dev/null` | major |
| H5 | Runtime injection actually closes the leak channel | A store wired **and** a committed `.env` still read as a fallback — the channel the store was meant to close is open | trace the config-load order at the composition root | major |
| H6 | Dynamic / short-lived credentials preferred over static-and-rotated | A static DB password on a rotation schedule where Vault dynamic creds or an OIDC-assumed role is available — you keep the long-lived risk and add toil | `rg -n "database/creds\|AssumeRoleWithWebIdentity\|workload.?identity\|azure.?workload"` against the static credential list | major |
| H7 | No static cloud keys anywhere | `AWS_SECRET_ACCESS_KEY`, a service-account JSON key, or an Azure client secret in CI or IaC — the `devops` invariant | `rg -ni "aws_secret_access_key\|client_secret\|private_key_id\|-----BEGIN.*PRIVATE KEY"` | blocker |
| H8 | Every issued credential has a TTL and a least-privilege scope | A Vault role or IAM policy with `*` actions and no `ttl`/`max_ttl` — an undetected leak is unbounded | `rg -n "\"Action\": ?\"\\*\"\|max_ttl\|default_ttl" -g '*.tf' -g '*.hcl' -g '*.json'` | major |
| H9 | SOPS, where used, comes with stated key governance | SOPS adopted at scale with no per-secret access control and no note on KMS key custody — repo access + key access equals every secret | `ls .sops.yaml 2>/dev/null`; read the accompanying doc | major |

---

## I — Rotation runbooks
*Owning skill: [`secgov-secrets-hardening`](../../secrets-hardening/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | A runbook exists per credential **type**, not per incident | One ad-hoc write-up from the last leak, nothing generalized — the next rotation improvises | `ls $SEC/runbooks 2>/dev/null` | major |
| I2 | The runbook is two-slot: create → roll → verify → revoke | A single in-place overwrite step — it races every running instance and some requests hit the revoked credential mid-roll | read each runbook's ordered step list | blocker |
| I3 | A verify step gates revocation | Steps run create → roll → revoke with no confirmation that consumers moved — revoking early causes the outage the runbook exists to avoid | read each runbook | blocker |
| I4 | Rotate-first-purge-second is stated for the leak path | A runbook that purges git history first, or only — the credential stays compromised and the purge is theatre | `rg -ni "filter-repo\|BFG\|purge" $SEC/runbooks 2>/dev/null`; read the ordering around each hit | blocker |
| I5 | The emergency path and the scheduled path are distinct | One procedure serving both, so the leaked-now case inherits a change-window it cannot afford | read each runbook | major |
| I6 | A named owner and a defined RTO per credential type | "Rotate promptly", no owner, no hours | `rg -ni "owner\|RTO\|within [0-9]" $SEC/runbooks 2>/dev/null` | major |
| I7 | The scheduled path is automated where the platform offers it | Manual quarterly rotation on RDS where AWS managed rotation exists, or on Key Vault where native cert rotation does | `rg -n "rotation_rules\|RotationLambdaARN\|rotation_period\|rotate_automatically" -g '*.tf' -g '*.bicep'` | minor |
| I8 | The rotation log records who/when/why and never the value | A step that echoes, prints, or stores the new credential "to verify it took" — the audit trail is not a secret store | `rg -ni "echo \\\$\|print.*secret\|log.*value\|tee.*secret" $SEC/runbooks 2>/dev/null` | blocker |
| I9 | Every consumer of the credential is enumerated | The roll step says "update the app" with no consumer inventory, so step 3's verify cannot actually be performed | read each runbook against the services that hold the credential | major |

---

## J — Compliance scope & crosswalk authority
*Owning skill: [`secgov-compliance-evidence-mapping`](../../compliance-evidence-mapping/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | The frameworks in play are stated, and only those are mapped | A GDPR column on a US-only product with no EU data — speculative columns dilute the real gaps | read the register header; `rg -n "GDPR\|SOC 2\|PCI\|ISO 27001" $SEC/compliance 2>/dev/null` | minor |
| J2 | Framework editions are pinned and current | see **A6** — a withdrawn edition in a compliance register is worse than in prose, because someone will assess against it | (A6's recipe, scoped to `$SEC/compliance`) | major |
| J3 | The crosswalk cites SCF or a published OSCAL mapping as its authority | A framework-to-framework mapping with no source — an invented crosswalk is a silent, confident compliance error | `rg -ni "SCF\|Secure Controls Framework\|OSCAL\|crosswalk" $SEC/compliance 2>/dev/null` | major |
| J4 | ASVS is the bridge, with the verified level stated | ASVS presented as a fifth certifiable framework, or cited with no L1/L2/L3 | `rg -n "ASVS" $SEC/compliance 2>/dev/null` | minor |
| J5 | The register never claims certification | "SOC 2 compliant" / "PCI compliant" asserted rather than "evidence for assessment" — this lane maps, a QSA or auditor certifies | `rg -ni "we are (soc\|pci\|iso)\|fully compliant\|certified" $SEC 2>/dev/null` | major |
| J6 | A machine-readable form exists where the org consumes it | Markdown only in an org that consumes OSCAL — a stated deviation is fine, silence is not | `ls $SEC/compliance/*.json $SEC/compliance/*.xml 2>/dev/null` | nit |
| J7 | PCI 6.4.3 and 11.6.1 are addressed where card data is in scope **[PCI]** | Payment pages present and the two most under-prepared 4.0.1 controls absent from the register | `rg -n "6\.4\.3\|11\.6\.1" $SEC/compliance 2>/dev/null` — only when PCI is in the stated scope | major |
| J8 | NIST CSF 2.0 frames the posture view | The CISO view organized ad hoc rather than by CSF function, with **Govern** missing entirely | `rg -n "CSF\|Govern\|Identify\|Protect\|Detect\|Respond\|Recover" $SEC/posture 2>/dev/null` | minor |

---

## K — The evidence register & gap list
*Owning skill: [`secgov-compliance-evidence-mapping`](../../compliance-evidence-mapping/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| K1 | Every row names an evidence artifact by path | "We have SAST" with no SARIF, report, or config path an auditor can open — a claim, not evidence | read the register's rows end to end | major |
| K2 | Every cited artifact exists | A row pointing at a path that is not in the repo — the register outlived the artifact | for each cited path: `ls <path>` | major |
| K3 | Status is tiered `#present` / `#partial` / `#gap`, read from the artifact | Rows marked "met" or "yes", or a tier assigned from intent rather than from opening the artifact | `rg -n "#present\|#partial\|#gap\|\bmet\b\|\byes\b" $SEC/compliance 2>/dev/null` | major |
| K4 | `#present` never silently means "effective" | A row claiming the control works with no validation artifact behind it — mapped ≠ effective, and proving it is `devops-infra-controls-validation`'s / the test lanes' job | cross-check every `#present` row against a validation report | major |
| K5 | A green pipeline is never the evidence | A row citing a CI badge or "pipeline passing" instead of the run's artifact | `rg -ni "pipeline\|badge\|green\|passing" $SEC/compliance 2>/dev/null` | major |
| K6 | Every `#partial` / `#gap` names the closing lane | Gaps recorded but unrouted — the routed gap list is the deliverable's whole point | read every non-`#present` row | major |
| K7 | The gap list is prioritized, not just enumerated | An unordered list with no leverage ordering, so the reader picks by position | read the gap list | minor |
| K8 | One control maps once and fans out to every framework | The same control re-derived per framework with divergent wording, so an edit updates one column and the others rot | scan for duplicate control names across framework sections | minor |
| K9 | No placeholders | "TBD", "various", "assess as appropriate" with no owner and no date | `rg -n "TBD\|TODO\|various\|as appropriate" $SEC` | major |

---

## L — Posture reports, rounds & lane handoffs
*Owning source: the [`security-architect`](../../agents/security-architect.md) agent contract*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| L1 | Reports follow `docs/security/posture/<NNN>-security-posture-r<N>.md` | Ad-hoc filenames, or a posture report written outside `docs/security/` | `ls $SEC/posture 2>/dev/null` | minor |
| L2 | `<NNN>` is minted once per system and reused across rounds | A second round with a fresh `<NNN>` — the lineage breaks and "14 high-risk at r1 → 5 at r2" stops being a comparable claim | `ls $SEC/posture`; read each report header | major |
| L3 | Rounds are additive; no round is overwritten | `git log` showing `r1` rewritten in place instead of an `r2` added | `git log --oneline --stat -- $SEC/posture` | major |
| L4 | `RISK-nnn` ids are permanent across rounds | Ids renumbered between rounds, destroying the trend the rounds exist to produce | diff the registers across consecutive rounds | major |
| L5 | Every register item carries ATT&CK id, risk band, CSF function, and owning lane | Rows missing the routing column — nothing says who fixes it, so nothing gets fixed | read the register | major |
| L6 | A `Resolved` verdict cites lane evidence re-read that round | Resolved claimed from a commit, a ticket, or a green pipeline | read each `Resolved` item's evidence line | major |
| L7 | An absent lane is a reported gap, never treated as clean | A posture picture that omits a lane which never ran, with no "no assessment — route to `<agent>`" row | compare the lanes named in the header against the artifacts actually in `$SEC` | major |
| L8 | Cross-lane duplicates are one item with two evidences | One weakness listed once from SAST and again from the pentest, double-counted in the totals | scan the register for duplicate titles / CVE ids | minor |
| L9 | Normalization is stated, and a proven path outranks a detected one | CVSS and library severities averaged, or silently flattened, with no stated mapping | read the normalization section | major |
| L10 | The executive summary is plain language | Tool names, ATT&CK ids, and CVSS vectors in the section written for a decision-maker | read the exec summary | minor |

---

## M — Redaction & sensitive material in committed security artifacts
*Owning source: [`secgov-secrets-hardening`](../../secrets-hardening/SKILL.md)'s never-log-the-value rule + the loot-redaction rule every `security/` skill opens with*

> **This is the one section that sweeps artifacts the governance lane did not author.** It covers everything under `docs/security/**` and `detections/**` — including the `penetration-tester` and `purple-team-engineer` reports that land beside the governance artifacts — because the offensive lane's runtime gates stop the *act*, and nothing re-checks the *file* after it lands. **Only the redaction rule crosses that boundary.** The offensive findings themselves, their CVSS scores, and their kill-chain conclusions stay `penetration-tester`'s and are never re-verdicted here.

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| M1 | No credential, hash, token, or key material in any committed security artifact | An NTLM hash, a bearer token, or a private-key block pasted into a finding as "proof" | `rg -ni "BEGIN [A-Z ]*PRIVATE KEY\|eyJ[A-Za-z0-9_-]{20,}\|[a-f0-9]{32}:[a-f0-9]{32}\|aws_secret" $SEC $DET` | blocker |
| M2 | No PII value in a finding or a log sample | Real customer names, emails, or card fragments used to demonstrate an access-control finding | `rg -n "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" $SEC`; `rg -n "\b4[0-9]{12}([0-9]{3})?\b" $SEC` | blocker |
| M3 | Findings state blast radius and source, never contents | "We recovered the admin password: …" — the report becomes the breach | read every finding that mentions a recovered secret | blocker |
| M4 | Authorization is recorded redacted — scope, authorizer, window | An engagement scope file carrying a test account's password so the run is reproducible | `rg -ni "authoriz" $SEC`; read each engagement/scope file | blocker |
| M5 | Screenshots and attachments are redacted too | An image or pasted terminal capture with a token visible — grep never sees it | `rg -no "\!\[[^]]*\]\([^)]*\)" $SEC`, then open each referenced attachment | major |
| M6 | Internal host/IP inventories are scoped, not dumped wholesale | A full internal CIDR + hostname inventory committed to a repo with wider read access than the engagement had | read the recon sections of each report | minor |
| M7 | The repo's read access matches what the artifacts warrant | Engagement artifacts in a public or widely-mirrored repo | `git remote -v`; confirm repo visibility with the owner — `Unverifiable` if you cannot | major |
| M8 | Detection test fixtures are redacted | see **D8** — the same rule, and fixtures are the likeliest place a real incident log gets committed | (D8's recipe) | blocker |

---

## N — Artifact structure, config hygiene & comments
*Owning sources: [`ep-code-comments`](../../../engineering-practices/code-comments/SKILL.md) + the global **Comments** rules in `CLAUDE.md`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| N1 | One rule per file, and the filename matches the rule | Several rules in one YAML document stream, or a filename unrelated to the `title` | `rg -c "^title:" $DET -g '*.yml' -g '*.yaml' \| rg -v ":1$"` | minor |
| N2 | A consistent, stated directory convention | Rules organized three ways in three folders with nothing saying which is current | `find detections rules sigma -type d 2>/dev/null` | minor |
| N3 | Every config and rule file parses | A `.yml`/`.conf` that no longer loads, so the control is silently absent while the repo looks covered | opt-in only: `python3 -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" $(rg -l "" $DET -g '*.yml' -g '*.yaml')` | major |
| N4 | No dead or commented-out rules and directives shipped | Large commented-out `SecRule` blocks, or disabled rules kept "just in case" | `rg -n "^\s*#\s*(SecRule\|detection:\|selection:\|condition:)"` | nit |
| N5 | No inline comments inside a rule's or a policy's body | Step markers and line-restating comments inside a `detection:` block or a middleware body — the field names are the explanation | `rg -n "^\s+#" $DET waf 2>/dev/null`, then read the hits that sit inside a block | minor |
| N6 | Surviving comments are true and load-bearing | A comment describing a selection the rule no longer has, or an exclusion note naming a false positive that was fixed — the comment is the defect and deletion is the fix | read the code around every comment N4/N5 surfaced; grep cannot decide this one | major |
| N7 | Sigma's own prose fields are used instead of comments | `description` / `falsepositives` / `references` left empty while the same content sits in a `#` block above the rule, where no tool can read it | compare each rule's comment block against its populated fields | minor |
| N8 | No secret-shaped placeholder that reads as real | `password: CHANGEME_prod_2026` — indistinguishable from a real value at a glance, and it trains the reader to skim past H2 | (H2's recipe) then read each hit | minor |

**N4–N7 are the audit face of [`ep-code-comments`](../../../engineering-practices/code-comments/SKILL.md)** — read it for the rule, the complex-flow test, and the never-comment-the-trivial list. Two local notes. **The reporting split:** N5 ("no inline comments") is reported as **one finding family** — a count, 3–5 representative `file:line`s, the worst offender, one fix direction — while each **N6** stale comment is **its own finding**, because each is a distinct false statement. **What is not a comment:** a Sigma `description`/`falsepositives`/`references` field, a `# ------` separator generated by `sigma convert`, and an analyzer/linter directive are structured content or tool directives, not prose — leave them alone. And **N4 already owns commented-out rules**; do not double-file them under N5.

---

## Section index — for the report's applicability matrix

| Letter | Section | Applies when |
|---|---|---|
| A | Adoption map, standards pins & version lane | always — it is the gate |
| B | Detection repository & the detection-as-code pipeline | a detection repo exists |
| C | Sigma rule anatomy, ATT&CK mapping & correlations | Sigma rules exist |
| D | Detection testing, tuning & the telemetry contract | Sigma rules exist |
| E | Content-Security-Policy | a CSP is emitted anywhere |
| F | The secure-headers baseline | the repo emits response headers it controls |
| G | WAF ruleset & rollout discipline | a WAF config exists |
| H | Secret store & the leak channel | always — every repo has a config surface |
| I | Rotation runbooks | a runbook exists, **or** static long-lived credentials are in use |
| J | Compliance scope & crosswalk authority | a compliance scope is stated or a register exists |
| K | The evidence register & gap list | an evidence register exists |
| L | Posture reports, rounds & lane handoffs | a posture report exists |
| M | Redaction & sensitive material in committed security artifacts | anything exists under `docs/security/` or `detections/` |
| N | Artifact structure, config hygiene & comments | any section B–M is applicable |

**A section marked N/A produces no findings and no false confidence** — name the probe that decided it, and record the absence as a coverage note routed to `security-architect` per the absence rule above.
