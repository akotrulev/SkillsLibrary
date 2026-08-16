---
name: pentest-recon-enumeration
description: Use to map the in-scope attack surface at the start of an authorized penetration test — subdomains, live hosts, open ports, running services, and web technologies — passive-first, rate-bounded, and never outside the engagement scope file. Covers amass/subfinder (subdomain enum), httpx (HTTP probing/tech-detect), nmap (service/version/NSE), masscan (fast async port sweep), and Shodan/Censys (passive third-party index reads). Language-agnostic, any target. Triggers "enumerate the attack surface", "recon this authorized target", "find the subdomains and open ports of our lab environment". Not for exploiting what you find (`pentest-initial-access`), infra posture benchmarks (`infra-security-tester`), or proving a single app vuln (`qa-security`). Owned/lab targets only, under a committed engagement scope file.
---

# Penetration Testing — Recon & Attack-Surface Enumeration (amass · subfinder · httpx · nmap · masscan · Shodan/Censys)

Recon is the first phase of an authorized kill chain: turn "here is a scope" into "here is exactly what is reachable and running inside it." You enumerate subdomains, resolve live hosts, sweep ports, fingerprint services and web tech — **only against assets the engagement scope file names**, passive-first, and rate-bounded so a sweep never becomes a denial-of-service. Everything you find is a lead for `pentest-initial-access`; recon itself sends no exploit.

> **⚠️ Authorized self-testing only — owned/lab targets, under a committed scope file.** This skill enumerates the surface of **your own** systems (or a designated throwaway/lab environment) to find the holes before an attacker does. It is the defensive act of attacking yourself under authorization. Every run is gated by the engagement scope file and its `#volatile` authorization line; the scope file's in-scope hosts/CIDRs are the **only** things you may touch, its hard exclusions are never touched even if reachable, and its blast-radius cap bounds every sweep. Active scanning against a third party you do not own or have written authorization to test is not testing — it is an attack. **Read the scope file before every act; if the next act would fall outside it, halt the run and report.**

```
Authorization: engagement=<NNN>  in-scope=<hosts/CIDRs/domains>  exclusions=<never-touch>
               authorized-by=<name>  window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** (every tool is a Go/C/CLI binary — no per-stack split, per the library's anti-triplication rule) and is loaded by the **`penetration-tester`** agent in its **Recon** phase. It owns *finding* the surface; it does **not** exploit it (`pentest-initial-access`), benchmark its posture (`infra-security-tester`), or prove an app vuln (`qa-security`).

> **Two spines, stated per finding.** Recon actions map to the **MITRE ATT&CK Enterprise** matrix under the **Reconnaissance** and **Discovery** tactics — `T1595` Active Scanning (`.001` Scanning IP Blocks, `.002` Vulnerability Scanning), `T1592` Gather Victim Host Information, `T1590` Gather Victim Network Information, `T1595.003`/`T1596` for passive index reads, `T1046` Network Service Discovery, `T1594` Search Victim-Owned Websites. Where a finding is a *misconfiguration* (an exposed admin panel, a stale subdomain) it additionally carries its **OWASP** category (A05 Misconfiguration). Severity is scored **CVSS** in the final report, not the blocker/major/minor/nit table (see `pentest-reporting`).

## Passive-first — the ordering that bounds blast radius

Run recon in order of increasing noise, and stop escalating the moment you have what the next phase needs:

1. **Passive index reads** (Shodan/Censys, passive amass) — you query a *third party's* pre-built index; you never touch the target. Zero target-side footprint. `T1596` Search Open Technical Databases.
2. **Passive subdomain enum** (subfinder, `amass enum -passive`) — pulls from OSINT sources/APIs; no packets to the target's infrastructure beyond DNS resolution. `T1590.002` DNS.
3. **Live-host probing** (httpx) — one lightweight HTTP request per candidate to see what resolves and responds. Low noise. `T1595`.
4. **Active port sweep** (masscan/nmap) — packets to the target's ports. This is the loud, rate-sensitive step; it is bounded by the scope file's CIDRs, an exclude file, and a rate cap. `T1595.001`, `T1046`.
5. **Service/version + NSE** (nmap `-sV -sC`) — the loudest and most detailed; run it only on the ports the sweep found open, never a full re-scan of the world.

> **Green ≠ clear.** An empty recon result means *nothing was reachable from where you scanned, within this scope, in this window* — it says nothing about an authenticated surface, an internal segment you couldn't reach, or a host the scope excluded. State what you did not cover and hand it off.

## Decision matrix — which tool, which mode, which spine

| Need | Tool + mode | Footprint | ATT&CK |
|------|-------------|-----------|--------|
| Read what a third-party index already knows about an owned asset | `shodan`/`censys` CLI query | none (index read) | T1596 |
| Enumerate subdomains without touching target infra | `subfinder -d <domain>` · `amass enum -passive -d <domain>` | passive | T1590.002 |
| Deeper active subdomain enum (brute/resolve) | `amass enum -active -d <domain>` | active DNS | T1595 |
| Probe which hosts are alive + fingerprint web tech | `httpx -title -status-code -tech-detect` | low (1 req/host) | T1595 / T1592 |
| Fast async port sweep of an in-scope CIDR | `masscan <cidr> --rate <capped> --excludefile <exc>` | **loud, rate-sensitive** | T1595.001 / T1046 |
| Service + version detection on found-open ports | `nmap -sV -sC -p <ports> <host>` | loud, detailed | T1046 / T1592 |
| OS + traceroute + aggressive detail | `nmap -A` (opt-in — noisy) | loudest | T1592.002 |

**Rule of thumb:** subfinder/amass find the names, httpx says which are alive, masscan sweeps the ports fast, nmap tells you exactly what is listening. Pipe them: `subfinder → httpx → nmap`. Run passive before active; cap every active sweep.

## Subdomain enumeration — subfinder + amass

**subfinder** (ProjectDiscovery, current **v2.15.0**) is passive-only — it pulls from OSINT sources and never brute-forces, so it is the safe first pass. **amass** (OWASP, current **v5.1.1** — note the v3→v4 reorg *removed* the `viz`/`db`/`track` subcommands, and v5 moved to the asset-db engine; older tutorials referencing `amass viz` are stale) does passive *and* active (DNS brute/resolution).

```bash
# subfinder — passive, config the API keys in $HOME/.config/subfinder/provider-config.yaml
subfinder -d example.com -all -silent -o subs.txt      # -all = every source; -recursive for depth

# amass — passive first (no target-infra contact beyond resolution)
amass enum -passive -d example.com -o amass-passive.txt
# amass — active ONLY when scope allows brute/resolution against the target's DNS
amass enum -active -d example.com -brute -o amass-active.txt
```

- **Install (pinned):** `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.15.0` · `go install github.com/owasp-amass/amass/v5/...@v5.1.1` (or the pinned release binary / `docker` image). Both ship in Kali.
- **Scope discipline:** enumerate only domains the scope file lists. A discovered subdomain that resolves to an IP **outside** the in-scope CIDRs is recorded as out-of-scope and **not** probed further.
- **API keys** (subfinder `provider-config.yaml`, amass `config.yaml`) are secrets — env-injected, never committed. No key in the report.

## Live-host probing + tech fingerprint — httpx

**httpx** (ProjectDiscovery, current **v1.10.0**) is the fast HTTP prober. **Name-collision warning:** ProjectDiscovery's `httpx` is a Go recon binary and is **not** the Python `httpx` HTTP-client library — pin the Go tool by module path so a `pip install httpx` does not shadow it.

```bash
# Pipe subfinder → httpx: which subdomains are alive, what they run, redirect chains, titles.
subfinder -d example.com -silent | \
  httpx -silent -status-code -title -tech-detect -web-server -follow-redirects -o live.txt

# Probe a host list on specific ports.
httpx -l subs.txt -ports 80,443,8080,8443 -status-code -title -o live-ports.txt
```

- **Install (pinned):** `go install github.com/projectdiscovery/httpx/cmd/httpx@v1.10.0`.
- Low footprint (one request per host), but it *is* a request to the target — inside scope only. `-rl <n>` rate-limits if the target is fragile.
- Output feeds `pentest-initial-access`: a live host + its tech stack + an interesting title (`admin`, `login`, a framework version) is a lead.

## Fast port sweep — masscan (rate-capped, exclude-file-bounded)

**masscan** (current **v1.3.2**, 2026-01-31) is an asynchronous scanner that can sweep the entire in-scope range far faster than nmap — which is exactly why it is the most dangerous recon tool for blast radius. **Its `--rate` flag is a firehose control.** An uncapped `--rate` can saturate a link and knock a service over (an accidental DoS — never acceptable). Always cap the rate and always pass an `--excludefile` carrying the scope file's hard exclusions.

```bash
# Sweep an in-scope CIDR, rate-capped, with the scope's exclusions honored at the packet level.
masscan 10.0.10.0/24 -p1-65535 \
  --rate 1000 \                    # CAP — start low; never uncapped against a live/prod target
  --excludefile scope-exclusions.txt \   # the scope file's hard exclusions — masscan never touches these
  --open-only -oL masscan.txt

# masscan finds ports fast; hand the open ports to nmap for detail (do NOT let masscan do version detection).
```

- **Install (pinned):** build from `github.com/robertdavidgraham/masscan` at the **1.3.2** tag (`make`), or the pinned distro package. Still maintained by Robert Graham.
- **The blast-radius knobs are mandatory here:** `--rate` (cap it — 1000 pkt/s is a conservative start; production, if authorized at all, is far lower), `--excludefile` (the scope exclusions, enforced by masscan itself), and a CIDR that is a subset of the in-scope ranges. **masscan's own docs warn it can be mistaken for a SYN-flood** — the rate cap and exclude file are what keep it a scan, not an attack.
- masscan answers "which ports are open" fast; it is a poor service-fingerprinter. Hand the open-port list to nmap.

## Service & version detection — nmap (loud, run last, on found-open ports)

**nmap** (pin the current stable from `nmap.org/changelog` — the 7.9x line; pin the exact build your runner ships, the same "silent scanner upgrade" discipline the Trivy skill applies) is the detailed, authoritative fingerprinter. Run it **last**, only on the ports masscan/httpx flagged, never as a blind full-range full-detail scan.

```bash
# Service + version + default NSE scripts on the specific open ports found — not a re-sweep of the world.
nmap -sV -sC -p 22,80,443,8080 -Pn --open -oA nmap-example 10.0.10.5

# Timing/politeness: -T2 is polite (slow, quiet); -T4 is faster but louder. Never -T5 on a fragile/prod target.
# -Pn skips host-discovery ping (use when ICMP is filtered). --script for targeted NSE.
```

- **Scan-type flags:** `-sS` SYN (default, needs root), `-sT` full-connect (no root), `-sU` UDP (slow — scope it tightly), `-sV` version, `-sC` default scripts, `-O` OS detect, `-A` aggressive (OS+version+scripts+traceroute — opt-in, loud).
- **NSE (`--script`):** targeted scripts only (`--script http-title,ssl-cert`), never `--script vuln` blindly against production (some scripts are intrusive). Treat an intrusive NSE script as an active probe, not passive recon.
- **Output `-oA`** writes all three formats (`.nmap`/`.xml`/`.gnmap`) — the `.xml` feeds Metasploit's `db_nmap` workspace in the next phase; the `.gnmap` greps cleanly.
- **Timing/politeness (`-T0`–`-T5`)** is a blast-radius knob: `-T2` for anything fragile or production, `-T4` on a robust lab, **never `-T5`** (it will trip rate limits and can destabilize weak services).

## Passive index reads — Shodan / Censys

Shodan and Censys have already scanned the internet; querying their **API/CLI** reads that index without you sending a single packet to the target — the quietest recon there is. The nuance: **you are reading a third-party index, but the assets you look up must be your own / in scope.** Looking up your own exposed IP is fine; the scope discipline is about *acting on* what you find, not the lookup itself.

```bash
shodan host 203.0.113.10                      # what Shodan already knows about an owned IP
shodan search 'org:"Your Org" port:3389'      # your org's exposed RDP, from the index
censys search 'services.service_name: RDP and ip: 203.0.113.10'
```

- **Install:** `pip install shodan` (`shodan init <API-KEY>`); Censys via `pip install censys` or the platform CLI. The API key is a secret — env-injected, never committed.
- Great for a zero-footprint first look (exposed services, certificates, banners) and for spotting **shadow assets** the org forgot — each of which, if in scope, becomes an active-recon target and, if out of scope, a finding to report to the owner.

## Anti-patterns

- **An uncapped `masscan --rate` against a live target.** This is the single most likely way recon becomes an accidental DoS. *Fix:* always `--rate <capped>` (start low) + `--excludefile` + an in-scope CIDR subset; production gets the lowest rate or is excluded.
- **Skipping the scope exclude file.** masscan/nmap will happily hit an excluded host if it is inside the CIDR. *Fix:* pass the scope file's exclusions as `--excludefile` (masscan) / `--exclude` (nmap) on every active sweep.
- **`nmap -A` / `--script vuln` blindly on production.** Aggressive detection and intrusive NSE scripts are active probes that can destabilize fragile services. *Fix:* targeted `-sV -sC` on found-open ports; intrusive scripts only on a lab with authorization.
- **Probing a discovered subdomain that resolves out of scope.** A subdomain enum finds names that point anywhere. *Fix:* resolve first; anything outside the in-scope CIDRs is recorded out-of-scope and not touched.
- **Treating passive index data as authorization to attack.** Finding an exposed service in Shodan does not make it in scope. *Fix:* the scope file decides what is touched, not what an index reveals.
- **Committing API keys / recon output with secrets.** provider-config and scan output can carry keys and internal hostnames. *Fix:* keys are env-injected; recon artifacts holding sensitive internal detail follow the scope file's data-handling rules, redacted, never committed raw under `docs/security/`.
- **Full-detail re-scanning the whole range.** Running `nmap -sV -sC` on every port of every host is slow and loud. *Fix:* sweep fast (masscan/httpx), then detail only the open ports.

## Rules (hard constraints)

- **The engagement scope file gates every act.** Only in-scope hosts/CIDRs/domains are touched; hard exclusions are never touched even if reachable; the blast-radius cap bounds every sweep. Re-read the scope file before each act; halt and report if the next act would exceed it.
- **Passive before active.** Index reads and passive enum first; active port sweeps and version detection last, only on what the earlier passes surfaced.
- **Cap every active sweep.** `masscan --rate` capped + `--excludefile`; `nmap` politer timing (`-T2` for fragile/prod, never `-T5`); rate-limit httpx against fragile targets. **No sweep may risk availability — no DoS, ever.**
- **Production is a separate, louder gate than lab** (per the engagement scope file). Default target is lab/throwaway; a production sweep needs the second sign-off and the lowest rates.
- **Two spines per finding:** ATT&CK Enterprise technique id (Recon/Discovery tactic) + OWASP where it is a misconfiguration. Score CVSS in the final report.
- **Recon finds; it does not exploit.** An open port, a live admin panel, a stale subdomain is a *lead* handed to `pentest-initial-access` — this skill never sends an exploit.
- **Loot/secret redaction + no secrets in tooling config.** API keys env-injected; internal detail in recon output handled per the scope file, never committed raw.
- **Log every act.** Each sweep/probe — command, target, timestamp, ATT&CK id — goes into the engagement action log as it runs (per `pentest-reporting`).
- Green ≠ clear — an empty result means *this scope, this window, from here*. State the coverage and hand off.

## Cross-references

- **`penetration-tester`** (`security/agents/penetration-tester.md`) — the orchestrator that runs this skill in its **Recon** phase and owns the scope-file gate this skill enforces.
- **`pentest-initial-access`** — the **next** phase: it takes the live hosts, open ports, and services this skill found (plus a `qa-security` `exploit-validation` proof) and chains them into a foothold. Recon feeds it; it does the exploiting.
- **`infra-security-tester`** (`devops/`) — the **posture** sibling: it benchmarks and probes infrastructure config (CIS, kube-hunter, CSPM). Its findings can scope this recon; it does not run the offensive chain.
- **`qa-security`** (`qa/_shared/agents/qa-security.md`) — the app-layer detect/validate lane; its `exploit-validation` single-vuln proof is exploitation feedstock for the next phase, not recon.
- **`pentest-reporting`** — where every recon act is logged (action log) and every surface finding is scored (CVSS) and mapped (ATT&CK).
