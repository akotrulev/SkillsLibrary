# Pacu & enumerate-iam — AWS exploitation framework + keyless permission discovery

Feeds Step 1 (enumeration) and Step 2 (privesc) of `../SKILL.md`. **Pacu** (`RhinoSecurityLabs/pacu`) is
the Metasploit-of-AWS: a modular exploitation framework with 50+ modules across enum / privesc /
persistence / exfil, backed by a session database that lets one module reason over another's output.
**enumerate-iam** (`andresriancho/enumerate-iam`) is the narrow, keyless companion for the common
"I have keys but cannot read my own policy" case. Both touch only in-scope accounts named in the cloud
scope file; every call is attributable in CloudTrail.

> **Roster note:** Pacu's module set keeps growing — confirm the exact module names against the installed
> version (`help` / `list`) at engagement time rather than trusting a pinned list here.

## enumerate-iam — the permission map without `iam:` read

When a scoped test principal is denied `iam:GetPolicy`/`List*`, you still learn its permissions by firing
read-only `get*`/`list*`/`describe*` verbs and recording which return data vs `AccessDenied`. The success
set **is** the permission map. Non-destructive by construction — only read verbs, never a mutating call.

```bash
# Read-only brute of allowed get/list/describe verbs for a key pair (owned account only).
python enumerate-iam.py --access-key AKIA... --secret-key ... --session-token ...   # token for ASIA creds
```

- Each attempted call lands in CloudTrail as the principal; expect a burst of `AccessDenied` noise. This
  is the awareness point, not a reason to avoid it under authorization — confirm the key is in-scope first.
- Report the discovered action set as the principal's **effective reach**, feeding the privesc triage below.

## Pacu — session, keys, enumeration

```bash
pacu                                  # starts; create/pick a named session
set_keys                             # store the in-scope key pair (and session token for ASIA creds)
run aws sts get-caller-identity       # who am I — always first
run iam__enum_permissions             # pulls attached/inline/group policies into the session DB (needs iam:List*/Get*)
run ec2__enum ; run s3__enum ; run rds__enum ; run secrets__enum   # resource inventory into the DB
```

- `iam__enum_permissions` is the richer alternative to enumerate-iam **when** `iam:List*`/`Get*` are held —
  it stores the full policy set so `iam__privesc_scan` can reason over it. When those reads are denied,
  fall back to enumerate-iam for the inferred set.
- The session DB is what makes Pacu more than a script runner: enum output persists and privesc/exfil
  modules read it.

## Pacu — privilege escalation

```bash
run iam__privesc_scan                 # matches the held permission set against the 21 Rhino privesc paths
run iam__enum_action_query            # "which principals can do action X" — triage privesc_scan output
```

- `iam__privesc_scan` enumerates which of the **21** methods (see `pmapper.md` for the full edge list) the
  current principal can execute, and **can auto-exploit**. In a lab, run it for the **finding**, read it,
  then exploit a single path by hand to see the CloudTrail trail it leaves — never let the auto-exploit run
  against anything not in the scope file.
- Each path is `permission(s) → action → more powerful principal`, mapping to `T1098`/`T1098.001`/`T1548`/
  `T1078.004`. Report the path (holder → permission → target principal), not just the destination.

## Detection footprint (awareness, not evasion — D5)

- `set_keys`/enum verbs log as the principal (`userAgent` carries `aws-cli`/`Boto3`/`pacu`). Recon is not
  invisible.
- A privesc mutation (`AttachUserPolicy`, `CreateAccessKey`, `UpdateAssumeRolePolicy`, a `PassRole`+service
  launch) is a **management event**, on by default, and tends to trip
  `PrivilegeEscalation:IAMUser/AnomalousBehavior` / `Persistence:IAMUser/AnomalousBehavior`. Report the
  `eventName` and finding each path trips so the defender knows what should have fired.

## Cleanup (no-DoS / demonstrated-then-reverted)

Any principal, policy, policy version, access key, or resource created to prove a path is **deleted in
cleanup**. A persistence demo is removed. A minted access key is revoked. Record the teardown in the action
log alongside the exploit.

## What this feeds

The confirmed privesc path is the headline finding for `penetration-testing:reporting` (CVSS + ATT&CK
Cloud id), and the lead `security/cloud-incident-response` builds its AWS runbook around — "if this
`eventName` sequence fires, here is the CloudTrail/GuardDuty response."
