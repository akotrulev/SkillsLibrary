---
name: pentest-privilege-escalation
description: Use to elevate a foothold's privilege on a single host during an authorized penetration test — user shell to root/SYSTEM via SUID/sudo/kernel chains (Linux) or token/service chains (Windows). Triggers "escalate this foothold to root", "from www-data to root". Not for gaining the foothold (`pentest-initial-access`), moving hosts (`pentest-lateral-movement`), or infra posture benchmarks (`infra-security-tester`). Owned/lab targets only, under a committed scope file.
---

# Penetration Testing — Privilege Escalation (linPEAS/winPEAS · GTFOBins/LOLBAS · kernel/sudo/SUID chains)

Privilege escalation takes the user-level foothold `pentest-initial-access` established and elevates it on the **same host** — `www-data` to `root`, a low-priv user to `SYSTEM`. The method is always the same shape: **enumerate the host thoroughly, identify a misconfiguration or a vulnerable component, exploit the least-risky vector that works.** You escalate to *prove* the path exists and its impact, not to cause damage.

> **⚠️ Authorized self-testing only — owned/lab targets, under a committed scope file.** Escalating privilege on a host is only legitimate on a machine the engagement scope file names, within its window, using techniques its "allowed techniques" list permits. **Read the scope file before every act; halt and report if the next act would fall outside it.** Kernel exploits in particular can panic a host (an availability impact indistinguishable from DoS) — they are a disruptive act, opt-in per the scope file, run against a lab replica first where feasible, and excluded from production without the separate louder sign-off.

```
Authorization: engagement=<NNN>  host=<in-scope foothold>  allowed-techniques=<list>
               authorized-by=<name>  window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** (the enumerators are scripts/binaries; the reference catalogues are sites) and is loaded by the **`penetration-tester`** agent in its **Privilege escalation** phase. It owns *elevating on one host*; it does not gain the foothold (`pentest-initial-access`) or move to another host (`pentest-lateral-movement`).

> **Two spines, stated per finding.** Escalation maps to **MITRE ATT&CK Enterprise** under **Privilege Escalation** — `T1068` Exploitation for Privilege Escalation (kernel/component), `T1548.001` Setuid/Setgid, `T1548.003` Sudo and Sudo Caching, `T1134` Access Token Manipulation (`.001` Token Impersonation), `T1543.003` Windows Service, `T1574` Hijack Execution Flow (`.009` unquoted path). Where the vector is a misconfiguration it also carries **OWASP** A05. Severity is scored **CVSS** in `pentest-reporting`.

## The methodology — enumerate, identify, exploit the least-risky vector

1. **Enumerate exhaustively** (linPEAS/winPEAS) — SUID/SGID binaries, sudo rules, cron jobs, writable files/paths, kernel version, capabilities, stored creds, service configs.
2. **Identify the vector** — read the enumeration output; a misconfiguration (a GTFOBins-abusable sudo rule, a writable service binary) is always preferable to a kernel exploit (lower crash risk).
3. **Exploit the least-risky path that works** — a sudo/SUID/capability abuse over a kernel exploit; a kernel exploit only when nothing safer exists, lab-tested first.

## Enumeration — linPEAS / winPEAS (PEASS-ng)

**PEASS-ng** (carlospolop, current rolling release **20260801** — the project ships date-tagged releases, `YYYYMMDD-<hash>`; pin the release you ran) is the standard privilege-escalation enumerator. **linPEAS** (`linpeas.sh`) covers Linux/Unix; **winPEAS** (`winPEASx64.exe`, `winPEAS.bat`, `.ps1`) covers Windows.

```bash
# linPEAS — run on the compromised Linux host. Colour-codes findings by likelihood.
./linpeas.sh -a                 # -a = all checks (thorough, noisier); default is faster
# 95%-likely PE vectors are highlighted RED+YELLOW; read those first.

# winPEAS — on the compromised Windows host.
winPEASx64.exe                  # or winPEAS.bat where the exe is blocked
```

- **Reading the output:** PEASS colour-codes — a finding highlighted **red background + yellow text is a 95%-likely privilege-escalation vector**; start there. It surfaces SUID binaries, sudo rules, writable cron/service paths, kernel version, capabilities, and readable credential files in one pass.
- **Install (pinned):** download the `linpeas.sh` / `winPEAS*` asset from the `peass-ng/PEASS-ng` release **20260801** (pin it — the scripts change frequently). Transfer to the target in-memory where possible.
- **Footprint:** PEASS is **loud** — it runs hundreds of commands and touches many files; on a monitored host it will generate process/file-access noise (itself a detection-validation signal). It leaves the script on disk unless run in-memory — an artifact to remove at cleanup.

## Abuse lookups — GTFOBins (Unix) / LOLBAS (Windows)

**GTFOBins** (`gtfobins.github.io`) and **LOLBAS** (`lolbas-project.github.io`) are curated **reference sites** (no version — they are living catalogues), not tools. They map a binary you can run in a privileged context (via sudo, as SUID, with a capability) to the exact one-liner that abuses it into a shell / file-read / file-write.

- **The workflow:** enumeration shows, say, `sudo` allows `/usr/bin/find` → look up `find` on GTFOBins under "Sudo" → get `sudo find . -exec /bin/sh \; -quit` → root shell. Same for a SUID binary or a Linux capability (`cap_setuid`).
- **LOLBAS** is the Windows equivalent — living-off-the-land binaries (`certutil`, `msbuild`, signed Microsoft binaries) abused for execution/download/bypass.
- These are the **least-risky vectors** — they abuse *intended* functionality of an already-permitted binary, with no crash risk, so they are always preferred over a kernel exploit.

## Linux kernel / sudo / SUID exploitation chains

When enumeration finds a vulnerable component rather than a misconfiguration, a known local-privesc exploit may apply. Illustrative named classes (the point is the *methodology* — match the target's exact version, lab-test, understand the crash risk — not a copy-paste exploit dump):

- **sudo — "Baron Samedit"** (`CVE-2021-3156`, heap overflow in `sudoedit`) — a classic sudo-version-specific local root; check the sudo version against the advisory before attempting.
- **polkit — "PwnKit"** (`CVE-2021-4034`, `pkexec`) — a memory-corruption local root affecting a very wide range of distros; reliable, but still a code-exec exploit to run with care.
- **Kernel exploits** (Dirty-Pipe-class and successors) — match the *exact* kernel version (`uname -r`) to the advisory; a mismatched kernel exploit is the most likely thing to panic the host.

**Discipline for any of these:** confirm the target's exact version against the advisory, **lab-test first**, understand whether it can crash the host, and treat it as a disruptive act (scope-gated, production-excluded by default). A kernel exploit is the *last* resort after misconfiguration vectors are exhausted.

## Windows privilege escalation

- **Token impersonation — the "Potato" family** (`PrintSpoofer`, `GodPotato`, and the older `JuicyPotato`) — abuse `SeImpersonatePrivilege` (commonly held by service accounts) to escalate to `SYSTEM`. `PrintSpoofer`/`GodPotato` are the current reliable choices on modern Windows; `JuicyPotato` is largely patched out on recent builds. ATT&CK `T1134.001`.
- **Unquoted service paths** (`T1574.009`) — a service whose binary path has spaces and is unquoted, with a writable intermediate directory, lets you plant a binary Windows runs as the service account.
- **Weak service permissions / writable service binaries** (`T1543.003`) — a service whose binary or config you can modify runs your payload at the service's privilege.
- winPEAS surfaces all of these (`SeImpersonatePrivilege` held, unquoted paths, writable service dirs) in its enumeration pass.

## Anti-patterns

- **Jumping to a kernel exploit before enumerating misconfigurations.** A GTFOBins sudo abuse has zero crash risk; a kernel exploit can panic the host. *Fix:* enumerate fully, exhaust misconfiguration vectors first, kernel exploit last and lab-tested.
- **Running a kernel/local exploit without version-matching the advisory.** A mismatched exploit is the most likely thing to crash the box. *Fix:* confirm the exact `uname -r`/sudo/pkexec version against the advisory; lab-test.
- **Leaving linpeas.sh / winPEAS / a compiled exploit on disk.** *Fix:* run in-memory where possible; enumerate every dropped file and remove it at cleanup, logging the removal.
- **Treating a kernel exploit as safe on production.** It is a disruptive, crash-risk act. *Fix:* production-excluded by default; separate louder sign-off if ever authorized, and only after a lab replica proves reliability.
- **Reporting a recovered credential file's contents.** SUID/sudo abuse often yields readable secrets. *Fix:* report *that* it was readable + blast radius; never the contents.

## Rules (hard constraints)

- **The scope file gates every act.** In-scope host, permitted techniques, within the window. Re-read before each act; halt and report if the next act would exceed it.
- **Enumerate before exploiting; prefer the least-risky vector.** Misconfiguration abuse (GTFOBins/LOLBAS, sudo/SUID/capability) over kernel exploitation, always.
- **Kernel/local exploits are disruptive acts** — version-matched, lab-tested first, production-excluded by default, opt-in per the scope file. **No exploit whose effect is a crash. No DoS, ever.**
- **Two spines per finding:** ATT&CK Enterprise (Privilege Escalation tactic) + OWASP A05 where it is a misconfiguration. Score CVSS in `pentest-reporting`.
- **Escalate on one host only** — moving to another host is `pentest-lateral-movement`.
- **Loot redaction + artifact cleanup.** Recovered secrets → blast radius only; every dropped enumerator/exploit removed at cleanup, the removal logged.
- **Log every act** — enumeration run, exploit command, target, timestamp, ATT&CK id — into the engagement action log.

## Cross-references

- **`penetration-tester`** — the orchestrator; runs this in its **Privilege escalation** phase, owns the scope-file gate.
- **`pentest-initial-access`** — the **prior** phase: supplies the user-level foothold this skill elevates.
- **`pentest-lateral-movement`** — the **next** phase: takes the elevated host as a stronger pivot; SYSTEM/root often unlocks credential material (`pentest-credential-attacks`) that enables lateral reuse.
- **`pentest-credential-attacks`** — root/SYSTEM enables LSASS/`/etc/shadow`/keystore harvesting for reuse.
- **`infra-security-tester`** (`devops/`) — the posture sibling that would have *flagged* the misconfiguration statically (a writable service path, a permissive sudoers); this skill *proves* it escalates.
- **`pentest-reporting`** — action log + CVSS/ATT&CK scoring of the escalation.
