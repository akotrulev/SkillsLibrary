---
name: metasploit-setup
description: Use when standing up Metasploit before recon/exploitation — pinned Docker image, workspace DB, MCP server. Triggers "set up Metasploit for this engagement". Not for running exploits (initial-access).
disable-model-invocation: true
---

# Penetration Testing — Metasploit Toolchain Setup (Docker · msfdb workspace · Metasploit MCP server)

Setup is the step that turns "we have an authorized engagement" into "the attacker box has a pinned, reproducible Metasploit, a workspace database wired to recon, and the Metasploit MCP server registered with this agent under the right gate." Every other skill in this plugin — `recon-enumeration` feeding the workspace, `initial-access` running exploit modules, `post-exploitation` driving sessions — **assumes** this toolchain already exists. This skill provisions it once per engagement; it runs no exploit itself.

> **⚠️ Authorized self-testing only — owned/lab targets, under a committed scope file.** Setting up offensive tooling is not neutral: a Metasploit install wired to the MCP server is a loaded weapon pointed at whatever the config names. You provision it **only** for an engagement whose scope file exists, whose `#volatile` authorization line covers now, and whose target is a lab/owned host. The MCP server's config, workspace name and any RPC endpoint point **only** at in-scope infrastructure. **Read the scope file before wiring anything; if the toolchain would be aimed outside it — a target host not listed, an RPC endpoint on a box you do not own — halt and report.**

```
Authorization: engagement=<NNN>  in-scope=<hosts/CIDRs>  exclusions=<never-touch>
               authorized-by=<name>  window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** and is loaded by the **`penetration-tester`** agent as its **provisioning** step, before Recon — or on demand from `recon-enumeration` / `initial-access` when `msfconsole`, the workspace, or the MCP server is not yet available. It owns *standing up the tool*; it does not *find* the surface (`recon-enumeration`), *gain the foothold* (`initial-access`), or *escalate* (`privilege-escalation`). Setup actions do not carry an ATT&CK id — no act touches the target. The first act that touches the target is Recon's, under its own gate.

## What this produces

| Artifact | Where | Consumed by |
|---|---|---|
| A pinned Metasploit (image digest recorded) | the attacker box / a container | every kill-chain skill |
| A workspace database, engagement-named | `msfdb` (local Postgres) | `recon-enumeration` imports into it; the report reads from it |
| The Metasploit MCP server registered with the agent | `.mcp.json` on the attacker box (never the assessed repo) | the agent, as `msf_*` tools |
| A tools line in the engagement record | `docs/security/engagement-<NNN>.md` → *Allowed techniques / tooling* | the report's reproducibility section |

## 1. Install — Docker image, pinned by digest

Metasploit Framework is a **rolling release** (updated via `msfupdate` / the package manager), so a semver tag is not reproducible. Pin the **image digest** your engagement uses — the same deliberate, reviewable-upgrade discipline the scanners and `initial-access` apply — and record it in the engagement record so the report says exactly what ran.

```bash
# Resolve the current digest once, review it, then pin to it for the whole engagement.
docker pull metasploitframework/metasploit-framework:latest
docker inspect --format='{{index .RepoDigests 0}}' metasploitframework/metasploit-framework:latest
# -> metasploitframework/metasploit-framework@sha256:<digest>   (record THIS in engagement-<NNN>.md)

# From here on, every run names the digest, never :latest.
docker run --rm -it \
  metasploitframework/metasploit-framework@sha256:<digest> ./msfconsole -q
```

- **Network:** put the container on a bridge network that reaches **only** the in-scope lab (`--network <lab-net>`), never the attacker's full LAN. The scope file's exclusions must be unreachable from it.
- **Upgrading mid-engagement** is a decision, not a side effect: re-resolve the digest, record the change and why, re-run the setup. Never silently take a newer `:latest`.
- **Native fallback** (a dedicated Kali/attacker VM where msf ships preinstalled, or the nightly installer from the get-started page): acceptable, but pin the **distro package version** and record it the same way. The get-started installer is a rolling release — do not leave it unpinned.

## 2. Workspace database — one workspace per engagement

The workspace DB is what makes recon reproducible and feeds the report: hosts, services, vulns, creds and loot land in it, and the MCP server's read-only tools read from it. Stand it up before recon runs.

```bash
msfdb init          # first time: creates the Postgres instance + schema
msfdb start

# inside msfconsole — one workspace named for the engagement (restricted charset: letters, digits, _ , -)
workspace -a engagement-<NNN>
workspace engagement-<NNN>
db_status           # confirm "connected to msf. Connection type: postgresql."
```

- **Loot never lands in the repo** (control 7). The workspace DB is local to the attacker box; the report cites *that* a credential/host was found and its blast radius, never its contents, and never the DB file.
- `recon-enumeration` imports its nmap/httpx output here (`db_import`, `db_nmap`); keep every engagement in its own workspace so a retest reads a clean, scoped history.

## 3. The Metasploit MCP server (`msfmcpd`)

The official MCP server is middleware between this agent and the Framework: it exposes **16 MCP tools** over stdio or HTTP (JSON-RPC 2.0), talking to Metasploit through its RPC API (MessagePack on `55553` by default). It is the clean way to drive Metasploit from the agent — the agent calls `msf_*` tools instead of scraping `msfconsole` text.

**The 16 tools split exactly along this plugin's safety line:**

| Class | Tools | Maps to | Default |
|---|---|---|---|
| **Read-only (12)** | `msf_search_modules`, `msf_module_info`, `msf_host_info`, `msf_service_info`, `msf_vulnerability_info`, `msf_note_info`, `msf_credential_info`, `msf_loot_info`, `msf_module_results`, `msf_running_stats`, `msf_session_list`, `msf_session_read` | Recon / enumeration / reading the workspace + live sessions | **always enabled** — no target-touching act |
| **Dangerous (4)** | `msf_module_execute` (run a module), `msf_module_check` (run a module's check), `msf_session_stop`, `msf_session_write` (≤10 000 chars/call) | Initial access / post-exploitation — acts that touch the target | **disabled by default** |

### Start it

```bash
# config lives OUTSIDE the assessed repo, on the attacker box; chmod 600.
cp config/mcp_config.yaml.example config/mcp_config.yaml   # (JSON-RPC variant: mcp_config_jsonrpc.yaml.example)
chmod 600 config/mcp_config.yaml

# Default: localhost + MessagePack. msfmcpd auto-starts msfrpcd if nothing is on 55553
# and generates random RPC creds — fine for a local lab run.
./msfmcpd --config config/mcp_config.yaml

# Read-only by default. The 4 dangerous tools are OFF unless you explicitly enable them (§4).
```

`config/mcp_config.yaml` (MessagePack, stdio — the Claude-client default):

```yaml
msf_api:
  type: messagepack
  host: localhost          # in-scope / loopback only — never an out-of-scope box
  port: 55553
  ssl: true
  endpoint: /api/
  user: msfuser
  password: CHANGEME        # from a secret store / env, not committed
  auto_start_rpc: true      # localhost MessagePack only
mcp:
  transport: stdio          # http only when the attacker box is remote (§4)
rate_limit:
  enabled: true
  requests_per_minute: 60   # keep the default — a scan is rate-bounded like recon
  burst_size: 10
logging:
  enabled: false            # if enabled: chmod 600 the log; the server redacts secrets
```

- **Remote attacker box:** set `mcp.transport: http` + `auth_token: <strong token>` (or `MSF_MCP_AUTH_TOKEN`), and the client sends `Authorization: Bearer <token>`. `auto_start_rpc` does not apply to remote hosts or JSON-RPC — start `msfrpcd -U <u> -P <p> -p 55553` yourself and supply the creds. Never disable the auth token (`auth_token: null`): any client that reaches the port could then drive Metasploit.

## 4. Register with the agent, and the two-gate policy

Register the server with Claude Code on the **attacker box**, in that machine's `.mcp.json` — **not** in the assessed repo, where a committed RPC password or token would be a secret leak (control 7).

```json
{
  "mcpServers": {
    "metasploit": {
      "command": "/path/to/metasploit-framework/msfmcpd",
      "args": ["--config", "/path/to/config/mcp_config.yaml"],
      "env": {}
    }
  }
}
```

### The gate reconciliation — two gates stacked, by design

The MCP server has its **own** dangerous-actions gate; this plugin has the **nine-control** engagement gate. They compose — you do not drop one for the other:

1. **Default posture: read-only.** Provision and run recon with the 4 dangerous tools **off**. The 12 read-only tools cover search, module info, and the whole workspace (hosts/services/vulns/creds/loot/sessions) — everything Recon and the report need, with zero target-touching act. This is how the server runs for most of an engagement.
2. **Enabling the 4 dangerous tools is scoped to the exploitation window.** Enable them (`--enable-dangerous-actions`, or `MSF_MCP_DANGEROUS_ACTIONS=true`, or `mcp.dangerous_actions: true`) **only** once initial access begins, **only** inside the live authorization window, and turn them **off** again at teardown. The server prints a startup warning when they are on; that warning is expected and logged.
3. **Even with them on, every `msf_module_execute` is a per-act offensive act.** It does not bypass control 3: the agent re-reads the scope file before the call, confirms the target is in-scope and the module's technique is allowed, and — for anything that risks an in-scope service's availability (a memory-corruption module) — takes the separate per-act go-ahead, never against production. The MCP call and its result go in the action log (control 8) with the ATT&CK id, exactly as a `msfconsole` act would.

> **Policy in one line:** the MCP server's read-only tools are the agent's default hands on Metasploit; the 4 dangerous tools are enabled only for the exploitation step, and each target-touching call still passes the nine-control gate. When in doubt, drive the actual exploit through logged `msfconsole` Bash instead — same gate, same action log.

- **Secrets:** config and `.mcp.json` carrying the RPC password / auth token are `chmod 600` and live on the attacker box only. Nothing sensitive (RPC creds, bearer token, recovered loot) is committed to the assessed repo or written to `docs/security/`. The MCP server does not cache or log credentials; if logging is on, it redacts them.
- **Input safety the server already enforces** (lean on it, do not re-implement): strict JSON schemas, IP/CIDR validation, restricted workspace names, port-range checks, a 500-char search cap, datastore caps, and 60 req/min rate limiting.

## Operator handoff — the blocked-step fallback

The engagement never stalls on a step the assistant cannot perform. A live act may be unavailable to the assistant for two reasons, and both resolve the same way: the nine-control gate makes it a **per-act, human-authorized** action (control 3), or the model's own safety layer declines to run that specific tool call. Either way, the **authorized human operator** runs it — they hold the authorization; the assistant plans, sequences and reads results. This is the division of labour the whole lane assumes, not an exception to it.

**The protocol, at each such step:**

1. **State the exact next action** — the precise command and nothing vague: the `msfconsole` lines (`use …`, every `set …`, `check`/`run`), or the `msf_module_execute` module + options, or the `msfvenom` line, with the in-scope target and the `LHOST`/`LPORT` already filled from the plan.
2. **Hand it to the operator to run**, and say exactly what to paste back — the session id, the module result, the one proof line — **redacted of loot** (a hash/cred/PII is reported as *that* it came back, never its value; control 7).
3. **On their result, record it in the action log** (command, target, time, ATT&CK id, outcome — control 8) and continue with the next step, re-reading the scope file first.

The handoff is a checkpoint, not a dead end: the assistant keeps ownership of the sequence and the report, and resumes the moment the operator reports back. A step the operator declines or that returns "no" is logged as attempted-and-failed with the evidence, exactly like any other negative result — never retried silently, never worked around.

## 5. Teardown — feeds cleanup verification (control 4)

Setup is reversible, and its reversal is part of the report's cleanup section:

```bash
# stop the MCP server (Ctrl-C the msfmcpd process), then:
docker rm -f <msf-container>           # throwaway container goes
msfdb stop                             # or keep the workspace DB for the report, then drop it after
```

- Disable the dangerous tools (drop `--enable-dangerous-actions`) the moment exploitation ends.
- Remove the MCP server entry from `.mcp.json` when the engagement closes; rotate any RPC/auth token that was issued.
- Enumerate each of the above in the report's **cleanup verification** with the command that confirmed removal — the container is gone, the server is down, the token is rotated — exactly as the agent does for any planted artifact.

## Given a repo — decide the setup and the tests

When the engagement starts from a repository, the toolchain and the test plan are *derived from the code*, then run against the deployment. The repo is read statically (no target touched, no gate yet) to produce a **deploy profile** — exposed services/ports, stack and versions, auth model, dependency-CVE leads — which maps to the exact modules, MetaModules and payload shape to run. **The repo is not the target: Metasploit tests the running deployment the scope file names, never the source.** The full decision flow — repo-signal tables, surface→module mapping, payload selection, and what "proven" means per test — is `references/repo-to-tests.md`. It ends at the same gate: static reading is free, every live act needs the scope file and authorization.

## Driving Metasploit — the operational references

This skill provisions; the depth of *using* Metasploit lives in the references, so the agent operates the tool without leaving the engagement:

- **`references/framework-operations.md`** — the open-source Framework, CLI + MCP: the msfconsole loop, the workspace DB, module taxonomy, payloads & `msfvenom`, meterpreter & post-exploitation, routing/pivoting, resource scripts, and the full 16-tool MCP server reference. This is the agent's default surface.
- **`references/metasploit-pro.md`** — Metasploit **Pro** (licensed GUI product): auto-exploitation, the Vulnerability Validation Wizard, MetaModules, task chains, social-engineering campaigns, reporting, and the REST (`:3790`, `token:` header) + RPC (`pro.*`) APIs. **Divergence, stated once:** the plugin is Framework-first; the agent drives Pro **only through its REST/RPC API under the nine controls**, while Pro's web UI and irreversible wizards are **operator-run, not agent-driven**. `initial-access` still gains the foothold with the Framework.
- **`references/repo-to-tests.md`** — the repo → deploy-profile → test-plan decision flow above.

## Hand-off

The toolchain is up → `recon-enumeration` imports into `workspace engagement-<NNN>` and the agent reads it through the read-only `msf_*` tools; `initial-access` runs exploit modules (via the dangerous tools, enabled for that step, or logged `msfconsole`) against the foothold. Record the pinned digest and the MCP registration in `docs/security/engagement-<NNN>.md` so the report is reproducible.
