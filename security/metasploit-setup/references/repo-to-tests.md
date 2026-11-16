# Repo → setup & tests — the decision flow

How the agent turns "here is a repo" into "here is the Metasploit setup and the exact tests to run." The output is a **plan**, produced by reading the repo statically; it is executed only against the **deployed lab target** named in the scope file, after the gate.

> **The repo is not the target.** Metasploit exploits a *running* host/service, not source. The repo is read to derive the **deploy profile** — what this code stands up, on which ports, with which stack and dependencies — which is the attack surface the modules then test against the lab deployment. A finding is proven against the running target, never inferred from source (source-only vuln proof is `qa-security`'s lane; this chains it into a foothold on the deployment).

## The five steps

1. **Read the repo → deploy profile** *(static, touches no live target, no gate yet).* From the repo, derive: the exposed services and ports, the stack/framework and versions, the auth model, and the dependency CVE leads. Sources below.
2. **Profile → attack surface → test plan.** Map each surface to the module families and MetaModules that test it (tables below), and pick the payload shape from the network posture. Output a setup + test plan: workspace name, modules to `check` then `run`, payloads/handlers, and what a "proven" result looks like per item.
3. **Gate** *(blocking).* Require `docs/security/engagement-<NNN>.md` naming the **deployed lab target** (host/CIDR/URL), the window, the authorizer, allowed techniques and the blast-radius cap. No scope file → stop, present the shape, help write it. The repo being local is **not** authorization to attack its deployment.
4. **Provision & execute.** `metasploit-setup` stands up the toolchain; `recon-enumeration` confirms the live surface against the profile (the deployment may differ from the code); `initial-access` runs the planned modules; priv-esc/lateral/post follow. Drive via the MCP read-only tools + logged `msfconsole`/dangerous-tools-in-window.
5. **Report.** `pentest-reporting` — each finding CVSS + ATT&CK, loot redacted, action log, cleanup verification.

## Step 1 — repo signals → deploy profile

| Repo artifact | Tells you |
|---|---|
| `Dockerfile`, `docker-compose.yml`, `k8s/*.yaml`, Helm charts | **Exposed ports/services** (`EXPOSE`, `ports:`, Service/Ingress), base images (→ OS/runtime CVEs), env/secrets shape |
| IaC — Terraform, CloudFormation, Pulumi, Ansible | Security groups / open ports, load balancers, managed services (RDS/S3), the real network posture |
| Dependency manifests — `pom.xml`/Gradle, `package.json`/lock, `requirements.txt`/`uv.lock`, `*.csproj`, `Gemfile.lock`, `go.mod`, `Cargo.ltoml` | **Known-CVE leads** — pin versions, cross-ref to `search cve:` (the highest-signal input: a vulnerable Struts/Log4j/Spring/Rails version is a direct module) |
| Framework fingerprints — Spring/Struts, Rails, Django/Flask, Express/Nest, Laravel, ASP.NET, WordPress/Drupal | Which web-exploit family applies; default routes, admin panels, management ports |
| App config — `application.yml`, `web.xml`, `appsettings.json`, nginx/apache conf, `.env.example` | Ports, management/actuator endpoints, debug surfaces, auth scheme, default creds patterns |
| Auth code / IdP config | Auth model (form, JWT, OAuth, LDAP/AD, SSH) → which credential tests and login scanners apply |
| CI/CD, `README`, `Makefile` | How it deploys and where (the lab target to point recon at), service start commands, default ports |

Output a one-screen profile: *services + ports · stack + versions · auth model · top CVE leads · how/where it deploys.*

## Step 2 — surface → modules & tests

**By service/port** (confirm live with recon first — `check` before `run`):

| Surface | msf path / module | Test |
|---|---|---|
| SMB (445) | `auxiliary/scanner/smb/smb_ms17_010`, `exploit/windows/smb/ms17_010_*`, `smb_login`, `smb_enumshares` | check MS17-010; enum shares; cred login (lockout-aware) |
| HTTP/S app | `auxiliary/scanner/http/*` (dir, login, specific CVEs), the framework's exploit module | version/route/auth scan → the matching RCE exploit |
| Struts / Spring / Rails / Laravel | `exploit/multi/http/struts2_*`, `spring_*`, `rails_*`, `..._deserialization` | the framework-specific RCE if the version matches |
| Log4j (any Java service) | `exploit/multi/http/log4shell_header_injection` + `auxiliary/scanner/http/log4shell_scanner` | scan then exploit JNDI |
| SSH (22) | `auxiliary/scanner/ssh/ssh_login`, `ssh_login_pubkey` | credential/key test — bounded, lockout-aware |
| RDP (3389) | `auxiliary/scanner/rdp/*`, `exploit/windows/rdp/*` | version/vuln check; cred test |
| Databases (3306/5432/1433/27017/6379) | `auxiliary/scanner/<db>/<db>_login`, `_hashdump`, `_schemadump` | default/weak creds; enum — never a DoS module |
| SNMP/SMTP/FTP/Telnet/DNS | `auxiliary/scanner/<svc>/*` | enum + default creds |
| WordPress/Drupal/Joomla | `auxiliary/scanner/http/wordpress_*`, `exploit/unix/webapp/*` | plugin/theme/core version → exploit |
| Deserialization (Java/.NET/PHP) | the app-specific `..._deserialization` exploit | if the sink is reachable |

**By CVE lead** (from the manifests): `search cve:<id>` → `info` → `check`. A pinned vulnerable dependency is the single strongest input — it turns "scan everything" into "test this one module."

**Credential tests across the surface** (coordinate with `credential-attacks`): `*_login` scanners and the Pro MetaModules (Single Password Testing, Known Credentials, SSH Key Testing, Pass the Hash) — all bounded by the blast-radius cap and the target's lockout policy, loot redacted.

**Payload shape** (from the deploy profile's network posture):
- **`reverse_*`** when the target can reach the attacker (default; beats inbound firewalls) — `LHOST` = the lab-bridge/`tun0` interface. **`bind_*`** only when there is an inbound path and no egress.
- **Stageless** (`..._meterpreter_reverse_tcp`) across flaky/filtered links; **staged** (`.../meterpreter/reverse_tcp`) for the smaller initial footprint.
- Egress-filtered segment? Confirm with the **Firewall Egress Testing** MetaModule (or `auxiliary/scanner/portscan`) which outbound port is open, and set `LPORT` to it (443/53 often survive).

## Step 3 — what "proven" means (per item, pin it)

Each planned test states its single expected outcome (no "maybe"): *MS17-010 → a SYSTEM meterpreter session on `10.10.0.5`*; *Struts CVE → RCE confirmed via `id` output*; *SSH spray → valid cred `svc_app` on `10.10.0.9` (redacted)*. Prove at the minimum footprint — `check` or one-command proof over a full dump; count rows, don't exfiltrate.

## When Pro automation fits (if the engagement runs on Pro)

- A scanner report already exists (InsightVM/Nexpose) → the **Vulnerability Validation Wizard** validates it in one loop instead of per-module `check`.
- Many hosts, repeatable → **auto-exploitation** (ranked, bounded) and a **task chain** (discover → auto-exploit → evidence → report), inside the window only.
- Credential reuse at scale → the credential MetaModules.
Otherwise the Framework path (this guide) is the default — scriptable, free, and what `initial-access` teaches. Pro's irreversible buttons are operator-run; the agent plans and reads via the REST/RPC API.

## Gate (restated — it is the load-bearing step)

Static repo reading needs no authorization. **Every live act does.** The scope file names the deployed target, not the repo; without it, the flow stops at Step 2 with a plan and an offer to help author the scope file. Re-read the scope file before each target-touching command; a module or route that would reach an excluded host is control-9 abort.
