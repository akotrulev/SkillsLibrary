# Metasploit Pro — reference (licensed product; agent-drives the API only)

Metasploit **Pro** is Rapid7's commercial product built on the Framework: a project-based web application that adds automation (auto-exploitation, task chains, MetaModules), the Vulnerability Validation workflow with InsightVM/Nexpose, social-engineering campaigns, a reporting engine, team collaboration, and REST + RPC APIs. It is licensed and mostly driven through a browser.

> **Divergence, stated once.** The `penetration-testing` plugin is **Framework-first** — `initial-access` still gains the foothold with the open-source Framework, and `metasploit-setup`'s default is the Framework + MCP server. Pro is covered here because the engagement may run on a licensed Pro install, but the split is sharp: **the agent drives Pro only through its REST/RPC API, under the same nine controls.** Pro's **web UI and the operator wizards are operator-run, not agent-driven** — the agent plans and reads, a human clicks the irreversible buttons. Everything below is still gated by `docs/security/engagement-<NNN>.md`, logged in the action log, loot-redacted, and never run against production without the second sign-off. No DoS, ever.

## Pro vs Framework — what Pro adds

| Capability | Framework | Pro |
|---|---|---|
| Console / modules / payloads / sessions | ✅ `msfconsole` | ✅ + the **Pro Console** (`pro_` commands) |
| Workspace DB | ✅ `msfdb` | ✅ projects (multi-user, RBAC) |
| **Auto-exploitation** (match host+vuln → fire suitable exploits) | manual (`analyze`, per-module) | ✅ one action, ranked, bounded |
| **Vulnerability Validation Wizard** (InsightVM/Nexpose import → validate → push back) | manual import | ✅ closed loop |
| **MetaModules** (packaged multi-step workflows) | — | ✅ (§MetaModules) |
| **Task chains** (scheduled/orchestrated task sequences) | resource scripts | ✅ GUI + API, scheduled |
| **Social-engineering campaigns** (phishing, web, USB, email) | aux modules | ✅ campaign engine + tracking |
| **Reporting engine** (templated exec/technical/compliance) | manual | ✅ many report types + MetaModule reports |
| **APIs** | RPC (MessagePack/JSON) | ✅ REST (`:3790`) + RPC `pro.*` methods |
| Licensing | free/open | **licensed** (key + activation; some features gated, e.g. InsightGovCloud limits) |

Where a workflow is in both, prefer the Framework path for the agent's hands (it is scriptable, free, and what `initial-access` teaches); use Pro's where the engagement is standardised on Pro and the automation (task chains, the InsightVM loop, campaign tracking, templated reports) is the reason Pro is there.

## Access surfaces

- **Web UI** — `https://<host>:3790`, project-based. Operator-run. Administration > Global Settings holds license keys, API keys, and early-access toggles (e.g. the AD CS MetaModule).
- **Pro Console** — a CLI *inside* Pro: all of `msfconsole` plus `pro_` commands (e.g. project/report/task management). Launched from the Pro install; the scriptable operator surface.
- **REST API** — the modern programmatic surface; the agent's hands on Pro (below).
- **RPC API** — the older programmatic surface, with the `pro.*` method group; what the Framework's own MCP server also speaks to Metasploit.

## REST API — the agent-drivable surface

The clean way for the agent to drive Pro. Requires an **active Pro license**.

```bash
# 1. Generate a key in the web UI: Administration > Global Settings > API Keys.
#    The token does NOT expire — treat it as a secret (chmod 600, secret store, never the repo).
# 2. Send it in the `token` header. Base sanity check:
curl -H "token:<API_KEY>" https://localhost:3790/rest_api/v2/base

# Resources are nouns: hosts, services, vulns, sessions, credentials, loot, campaigns, tasks, reports...
curl -H "token:<API_KEY>" https://localhost:3790/rest_api/v2/hosts?workspace=engagement-<NNN>
```

- Port **3790** (the Pro web service, TLS). Scope it to the in-scope Pro host; the API token is loot-grade (control 7) — never commit it, never log it.
- The REST surface maps to the same objects the MCP server's read-only tools expose; prefer the read endpoints for enumeration and let a human run the irreversible exploitation actions in the UI when the install is Pro.

## RPC API

```
# Temporary token: auth.login(user, pass) -> token valid 5 minutes.
# Permanent token: generated at Pro startup, stored in the service.key file (non-expiring API key).
# Calls are arrays with the token as the 2nd element (MessagePack or JSON):
["core.version", "<token>"]
["pro.start_import", "<token>", { ... }]
["pro.report_list", "<token>"]
```

Method groups: `auth.*` (login/logout), `core.*` (version, module mgmt), `console.*` (drive a console), `pro.*` (Pro-only: imports, reports, tasks). Some published RPC docs are old (they still show `/api/1.0` and a legacy `msfrpc` client) — verify endpoint paths against the install's version before relying on them.

## Task chains — orchestrated, scheduled runs

A **task chain** is a sequence of preconfigured tasks that runs on a schedule or on demand — Pro's answer to resource scripts, with a GUI and a scheduler, but **it cannot query data, refine search results, or run Ruby** (use a resource script for those). Task types a chain can include:

`Discovery scan` · `Import` · `Vulnerability scan` · `Web scan` · `Bruteforce` · `Auto-exploitation` · `Single module run` · `MetaModule run` · `Evidence collection` · `Resource script execution`.

Typical chain: discover → auto-exploit → open sessions → collect evidence → Collected Evidence Report → cleanup, scheduled weekly. Under the nine controls, a **scheduled** offensive chain is a standing authorization risk — it must stay inside the engagement window, and anything availability-risking (auto-exploitation of memory-corruption modules) needs the per-act posture, so scheduled auto-exploitation against production is out.

## MetaModules — packaged workflows

Guided, multi-step workflows with their own report. The six a task chain's **MetaModule run** can launch:

| MetaModule | Does |
|---|---|
| **Single Password Testing** | tries one password across many accounts/hosts (spray) — lockout-aware, credential-attacks discipline applies |
| **Known Credentials Intrusion** | reuses recovered creds across the network to find where they work (the Pro form of cred-reuse) |
| **SSH Key Testing** | tests recovered SSH private keys across hosts |
| **Pass the Hash** | authenticates with NTLM hashes without cracking them |
| **Firewall Egress Testing** | probes which outbound ports a segment allows (egress filtering map) |
| **Passive Network Discovery** | sniffs to map hosts/services without active packets |

Plus **AD CS Workflows** (early access; Pro 4.22.7+, enabled in Global Settings; ESC-family certificate abuse incl. ESC9/ESC10/ESC16 in 4.22.9+). The MetaModule catalog shifts by version — read the install's Modules/MetaModules list rather than assuming. Credential-touching MetaModules are loot-redacted and bounded by the scope file's blast-radius cap exactly like the Framework credential-attacks.

## Vulnerability Validation Wizard

The reason many teams run Pro: import an InsightVM/Nexpose scan → Pro auto-exploits to **validate** which findings are truly exploitable → pushes the validation (exploited/not) back as an exception/tag. It turns a scanner's "potential" list into a proven one. It is auto-exploitation under the hood, so the availability-risk gate and the owned/lab-only rule apply; it is operator-run from the wizard.

## Social-engineering campaigns

Phishing emails, cloned web pages, malicious files/USB, with open/click/submit tracking. In-scope only when the scope file lists social engineering as an allowed technique **and** names the authorized recipients/targets — human targets are a separate, explicit authorization. Operator-run.

## Reporting

Templated reports (Audit, Collected Evidence, Compromised Hosts, Credentials, Services, Social Engineering, plus MetaModule-specific and compliance templates — PCI, FISMA), exportable, listable via `pro.report_list`. The engagement's report of record is still `security/pentest-reporting`'s format (CVSS + ATT&CK, redacted loot, action log, cleanup verification); a Pro report is an input/attachment to it, not a replacement — its raw loot never lands in the repo.

## Gate (the nine controls, applied to Pro)

- The API token and `service.key` are secrets — `chmod 600`, secret store, never the assessed repo, never logs; rotate at teardown.
- The agent drives **read** endpoints freely (enumeration maps to recon); **write/exploit** actions (auto-exploitation, the Validation Wizard, campaigns, session commands) are per-act, gated, logged with the ATT&CK id, and against production only with the second sign-off.
- Scheduled task chains must not outlive the authorization window; remove them at teardown and list them in cleanup verification.
- Pro loot (creds, evidence, campaign results) is reported as *that it was recovered* + blast radius, redacted.
