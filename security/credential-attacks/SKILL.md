---
name: pentest-credential-attacks
description: Use to recover and crack credentials during an authorized penetration test — offline/online cracking, LAN capture, secrets harvesting. Every recovered secret is reported as blast radius, never contents. Triggers "crack these captured hashes", "harvest creds from the foothold". Not for reusing creds across hosts (`pentest-lateral-movement`), gaining the foothold (`pentest-initial-access`), or escalating (`pentest-privilege-escalation`). Owned/lab only, under a committed scope file.
---

# Penetration Testing — Credential Attacks (hashcat · hydra · Responder · secrets harvesting)

**This is a dual-use discipline, used here for one purpose: authorized self-testing of the owner's own systems, to prove where weak or exposed credentials would let an attacker in.** Credential recovery and cracking are exactly the capabilities an attacker uses — which is why every technique here leads with, and stays inside, the authorization frame: owned/lab targets, a committed scope file, an expiring authorization line, and **absolute loot redaction** (a recovered credential is reported as *that* it was recovered and *what it unlocks*, never its value). Used this way, the step answers a defensive question the owner cannot answer any other way: *would our credentials survive a real attacker?*

> **⚠️ Authorized self-testing only — owned/lab targets, under a committed scope file, loot always redacted.** The offline half (hashcat) never touches the target, so its gate is *possession of the hashes + the lab boundary*. The online/active half (hydra, Responder) touches live services and networks and carries real blast radius — account lockout, service disruption, network-segment MITM — and is gated hard: recorded, scoped, expiring authorization; production a separate, louder sign-off. **Read the scope file before every act; halt and report if the next act would fall outside it.** No recovered credential's value is ever written to the report or committed under `docs/security/`.

```
Authorization: engagement=<NNN>  target=<in-scope host/segment>  allowed-techniques=<list>
               authorized-by=<name>  window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** and is loaded by the **`penetration-tester`** agent in its **Lateral movement** / post-foothold steps. It *recovers and cracks* credentials; **`pentest-lateral-movement`** *reuses* them (its consumer).

> **Two spines, stated per finding.** Maps to **MITRE ATT&CK Enterprise** under **Credential Access**: `T1110` Brute Force (`.001` Password Guessing, `.002` Password Cracking, `.003` Password Spraying), `T1557.001` LLMNR/NBT-NS Poisoning, `T1003` OS Credential Dumping (`.001` LSASS, `.002` SAM, `.006` DCSync), `T1555` Credentials from Password Stores, `T1552` Unsecured Credentials (`.001` In Files, `.005` Cloud Instance Metadata API). Score CVSS in `pentest-reporting`; the finding's value is the **strength/exposure signal** ("cracked in <1 min under best64 — password policy inadequate"), not the plaintext.

## Offline cracking — hashcat (never touches the target)

**hashcat** (current **v7.1.2**; v7 was a major rewrite — the 6.2.x line is superseded) is GPU offline cracking of *already-obtained* hashes. **It makes zero contact with the target** — no lockout, no service impact, no network noise. The only concern is legitimate possession of the hashes and the lab boundary.

```bash
hashcat -m <hash-type> -a <attack-mode> hashes.txt wordlist.txt -r rules/best64.rule
# attack modes: 0 dict · 1 combinator · 3 mask/brute · 6/7 hybrid
# hash types (-m): 0 MD5 · 1000 NTLM · 22000 WPA · 1800 sha512crypt · 5600 NetNTLMv2 · 5500 NetNTLMv1
hashcat -m 1000 ntlm.txt rockyou.txt -r rules/best64.rule    # NTLM w/ best64 ruleset
hashcat -m 3 -a 3 hashes.txt '?u?l?l?l?l?d?d'                # mask attack
hashcat --show hashes.txt                                    # read the potfile (already-cracked)
hashcat -b                                                    # benchmark
```

- **Install (pinned):** the `hashcat-7.1.2` binary from hashcat.net (run in place; needs OpenCL/CUDA/HIP/Metal).
- **Masks:** `?l` a-z · `?u` A-Z · `?d` 0-9 · `?s` symbols · `?a` all. Rules (`-r`) mutate a wordlist — `best64.rule` ships in `rules/`.
- **Reporting:** the value of a crack is the **policy signal** — mode, time-to-crack, ruleset — never the plaintext. "Recovered the service account's password in 40 s (NTLM, best64) — the policy permits crackable passwords" is the finding.
- **ATT&CK:** `T1110.002` Password Cracking.

## Online brute-force — hydra (touches the live service — lockout/DoS risk)

**hydra** (THC-Hydra, current **v9.7**; the `CHANGES` file is ground truth — Wikipedia lags) brute-forces a **live** login. Every attempt is a real, logged connection, so the danger is intrinsic: noise, **account lockout** (locking out real users is a self-inflicted DoS), and — at high thread counts — **service disruption** (its own docs warn too many tasks "disables the service").

```bash
hydra -L users.txt -P pass.txt -t 4 ssh://10.0.10.5          # -t default 16; LOWER it to avoid lockout/DoS
hydra -l admin -P pass.txt 10.0.10.5 http-post-form \
  "/login:user=^USER^&pass=^PASS^:F=incorrect"              # 3-part: url:body:failstring
```

- **The blast-radius knob is `-t`** — keep it low; a high thread count is what trips lockout and destabilizes the service. **Prefer password *spraying* (few passwords, many accounts) over guessing (many passwords, one account)** to stay under lockout thresholds — but agree the threshold with the owner first.
- **Install (pinned):** build v9.7 from `vanhauser-thc/thc-hydra` (`./configure && make && make install`) with the optional libs for the modules you need; ships in Kali.
- **hydra (online) vs hashcat (offline):** hydra hits the live service every attempt (lockout/DoS/loud); hashcat never touches the target (silent). ATT&CK: hydra → `T1110.001`/`.003`; hashcat → `.002`.
- **Gated hard:** scoped, expiring authorization; agreed lockout threshold; **production a separate, louder sign-off**.

## LAN hash capture — Responder (active MITM — whole-segment blast radius)

**Responder** (lgandx, current **v3.2.2.0**) poisons LLMNR/NBT-NS/mDNS to capture NetNTLM hashes on a LAN segment. **Its blast radius is the entire broadcast domain** — in its default (active) mode it *answers name-resolution queries destined for other hosts*, so it can misdirect legitimate traffic and disrupt production systems on the segment.

```bash
sudo responder -I eth0 -A          # -A = PASSIVE analyze mode: observe + log, DO NOT poison (the safe default)
sudo responder -I eth0             # ACTIVE poisoning (no -A) — answers for other hosts; whole-segment impact
# captured NetNTLMv2 → hashcat -m 5600 ; NetNTLMv1 → -m 5500
```

- **`-A` passive analyze is the safe default** — it proves the exposure (which hosts would have been poisoned) without redirecting anyone's traffic. Active poisoning is a scope-file opt-in against a designated non-production segment only.
- **Relay caveat:** captured auths + impacket `ntlmrelayx` can authenticate to *other* hosts — escalating "capture" into "RCE on a third host." That is a lateral act (`pentest-lateral-movement`) and needs the target in scope.
- **Install (pinned):** `git clone` `lgandx/Responder` at v3.2.2.0 + `pip3 install -r requirements.txt` (needs root); ships in Kali. Captures land in `logs/`.
- **ATT&CK:** `T1557` AiTM, `T1557.001` LLMNR/NBT-NS Poisoning. Report *that* hashes were captured + their reach, never the hash material.

## Post-foothold secrets harvesting

From a foothold (especially post-escalation), credentials sit in memory, files, and metadata endpoints. **Every one of these is loot — reported as blast radius, never contents.**

- **Windows LSASS — mimikatz** (gentilkiwi; last formal release **2.2.0-20220919** — repo not archived but stale, so note builds may lag Windows internals): `privilege::debug` → `sekurlsa::logonpasswords`. **Heavily AV/EDR-signatured** — a block is itself a control-validation signal. ATT&CK `T1003.001`.
- **Local app secrets — LaZagne** (current **v2.4.7**): `lazagne.exe all` recovers browser/wifi/app creds. ATT&CK `T1555`, `T1552.001`.
- **AD hashes — secretsdump.py** (impacket 0.13.1): `secretsdump.py DOM/u:p@target` (SAM/LSA), `-just-dc` (NTDS via **DCSync** — pulls every domain credential incl. **krbtgt**, maximum blast radius, authorized-DC-only). ATT&CK `T1003.002`/`.003`/`.006`.
- **Cloud credentials** — env vars (`AWS_*`, `AZURE_*`, GCP SA), files (`~/.aws/credentials`, `~/.azure/`, `~/.config/gcloud/`, `~/.kube/config`), and the **IMDS endpoint `169.254.169.254`**. **IMDSv1** is an unauthenticated GET, so an app-layer **SSRF** can reach `169.254.169.254/latest/meta-data/iam/security-credentials/<role>` and pull role creds with no local access; **IMDSv2** (PUT session token + hop-limit 1) closes that path — flag "IMDSv2 not enforced" as the finding. ATT&CK `T1552.005`.

## Anti-patterns

- **Any credential value in the report or repo.** The single worst failure of this step. *Fix:* report *that* it was recovered + blast radius (what it unlocks, scope, long-lived vs session) + source location; never the value; nothing sensitive under `docs/security/`.
- **hydra at high `-t` against a live/prod login.** Lockout + service disruption. *Fix:* low `-t`, spray over guess, agreed lockout threshold, production-excluded by default.
- **Responder active poisoning on a shared/production segment.** Whole-broadcast-domain disruption. *Fix:* `-A` passive analyze by default; active only on a designated non-production segment, scope-file opt-in.
- **DCSync without treating krbtgt as crown-jewel loot.** It pulls every domain secret incl. golden-ticket material. *Fix:* authorized-DC-only, redacted, flag krbtgt rotation to the owner.
- **Leaving mimikatz/LaZagne/captured-hash files on the host.** *Fix:* run in-memory where possible; remove every dropped tool and capture file at cleanup, logged.
- **Treating hashcat like it needs a target gate.** It doesn't touch the target. *Fix:* its gate is possession + lab boundary — don't over-gate it, but do redact the crack result to the policy signal.

## Rules (hard constraints)

- **Loot redaction is absolute.** Recovered credentials/hashes/tickets/tokens → blast radius + source only, never contents; segregated per the scope file's data-handling; never committed.
- **The scope file gates every active act.** hydra/Responder/harvesting only against in-scope targets/segments, within the window. Re-read before each act; halt and report on an out-of-scope next act.
- **Online/active is lockout- and disruption-risk** — low thread counts, spray over guess, agreed thresholds, passive Responder by default, production-excluded by default. **No DoS, ever.**
- **hashcat is offline** — no target contact; gate is possession + lab boundary; report the strength signal, not the plaintext.
- **This skill recovers; `pentest-lateral-movement` reuses.** Don't pivot from here.
- **Two spines per finding:** ATT&CK Enterprise (Credential Access tactic) + CVSS in `pentest-reporting`.
- **Log every act** — tool/command, target, timestamp, ATT&CK id — into the engagement action log; remove every dropped tool/capture at cleanup.

## Cross-references

- **`penetration-tester`** — the orchestrator; runs this in its credential/lateral steps, owns the scope-file gate.
- **`pentest-lateral-movement`** — the **consumer**: reuses the hashes (PtH) and cracked passwords (spray) this skill recovers.
- **`pentest-initial-access`** — supplies the foothold from which harvesting runs.
- **`pentest-privilege-escalation`** — root/SYSTEM unlocks LSASS/`/etc/shadow`/keystore access for harvesting.
- **`qa-security`** — the app-layer lane; an SSRF it detects is the path to IMDS credential theft this skill proves.
- **`pentest-reporting`** — action log + CVSS/ATT&CK scoring; the blast-radius (redacted) record of every recovered credential.
