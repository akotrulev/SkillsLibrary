# PMapper & the 21 IAM privilege-escalation paths — the AWS privesc graph

Feeds Step 2 of `../SKILL.md`. **PMapper** (`nccgroup/PMapper`, pip `principalmapper`) models an account's
IAM principals and the edges between them as a graph, then computes **who can escalate to admin and by what
chain** — accounting for `Deny`, SCPs, and permission boundaries that a flat permission list misses. The
edges it computes are the **21 Rhino Security Labs privilege-escalation methods** (Rhino's own count is
**21**; secondary sources inflate to 41). Every method is a *configuration weakness, not a CVE* —
`permission(s) held → action → more powerful principal` — and the evidence is the exact permission chain.

## PMapper — build the graph, query the paths

```bash
pmapper graph create                                   # enumerate IAM, build the principal/edge graph
pmapper query 'preset privesc *'                       # every principal that can escalate, and how
pmapper query 'who can do iam:CreateUser'              # reverse: who holds a given action
pmapper visualize                                      # render the graph (DOT/PNG) for the report
```

- `graph create` needs IAM read (`iam:Get*`/`List*`, `GetAccountAuthorizationDetails`); when denied, fall
  back to the enumerate-iam inferred set (`pacu.md`) to seed the reasoning by hand.
- `preset privesc` returns the reachability result as **holder → edge (permission) → target principal** —
  report the whole path, never just "can reach admin", so a reviewer retests by re-running the same query.
- CloudFox `cape` consumes PMapper graph data to extend the paths **across accounts**.

## The 21 paths — four families

### A. Direct policy / permission grant to self
1. `iam:CreatePolicyVersion` — new **default** version (`--set-as-default`) with `Action:*`/`Resource:*`; bypasses attach rights.
2. `iam:SetDefaultPolicyVersion` — roll the default back to an existing, more-permissive version (CloudGoat `iam_privesc_by_rollback`).
3. `iam:AttachUserPolicy` — attach `AdministratorAccess` to yourself.
4. `iam:AttachGroupPolicy` — attach admin to a group you belong to.
5. `iam:AttachRolePolicy` — attach admin to a role you can assume.
6. `iam:PutUserPolicy` — inline admin onto yourself.
7. `iam:PutGroupPolicy` — inline admin onto your group.
8. `iam:PutRolePolicy` — inline admin onto an assumable role.
9. `iam:AddUserToGroup` — add yourself to a more-privileged group.

### B. New credential / new identity (`T1098.001`)
10. `iam:CreateAccessKey` (on another user) — mint a second key for a higher-privileged user.
11. `iam:CreateLoginProfile` — set a console password on a password-less (possibly higher-priv) user.
12. `iam:UpdateLoginProfile` — reset another user's console password.
13. `iam:CreateUser` + attach/put policy — create a fresh admin user (privesc + persistence).

### C. Trust-policy / assume-role abuse
14. `iam:UpdateAssumeRolePolicy` (+ `sts:AssumeRole`) — rewrite a privileged role's trust policy to trust you, then assume it (`T1098`).
15. `sts:AssumeRole` chains — follow existing A→B→C trust edges to a more-privileged role (the reachability PMapper computes; CloudFox `cape` surfaces cross-account hops).

### D. `iam:PassRole` + a service that runs code
Each needs `iam:PassRole` plus the service action, and a target role more privileged than you:
16. `iam:PassRole` + `ec2:RunInstances` — launch an instance with a privileged profile; read its creds from IMDS/user-data.
17. `iam:PassRole` + `lambda:CreateFunction` + `lambda:InvokeFunction` — a function assumes a privileged exec role and exfils its STS creds.
18. `iam:PassRole` + `lambda:CreateFunction` + `lambda:CreateEventSourceMapping` — same, event-triggered, when `InvokeFunction` is denied.
19. `iam:PassRole` + Glue (`glue:CreateDevEndpoint`/`UpdateDevEndpoint`) — run code on a Glue dev endpoint as the passed role.
20. `iam:PassRole` + CloudFormation (`cloudformation:CreateStack`) — a template that creates privileged resources/roles under a passed role.
21. `iam:PassRole` + Data Pipeline / SageMaker (`datapipeline:CreatePipeline`, `sagemaker:CreateNotebookInstance`/`CreateTrainingJob`) — the same primitive via other code-running services.

> **Companion lab:** **IAM Vulnerable** (Bishop Fox / Seth Art) deploys 250+ IAM resources with ~31
> supported privesc paths — the hands-on exercise ground for this list and for `pmapper graph create` /
> Pacu `iam__privesc_scan` (see `lab-setup.md`).

## Working the chain end to end

1. Build the graph (`pmapper graph create`) or the inferred permission set (enumerate-iam) against an
   in-scope account.
2. Run `preset privesc *` (or cross-check Pacu `iam__privesc_scan`) to find which of the 21 paths are open.
3. Walk one path by hand against a lab target — record the `eventName` each step logs (Step 4 awareness).
4. Report the **path** (holder → permission → target), tagged `T1098`/`T1098.001`/`T1548`/`T1078.004`,
   scored CVSS.
5. If a step created a principal/policy/key/resource, **tear it down in cleanup** (no-DoS /
   demonstrated-then-reverted).

## Detection footprint (awareness, not evasion — D5)

Each exploited edge is a CloudTrail **management event** (`CreatePolicyVersion`, `AttachUserPolicy`,
`UpdateAssumeRolePolicy`, `PassRole`+`RunInstances`/`CreateFunction`) and tends to trip
`PrivilegeEscalation:IAMUser/AnomalousBehavior`. Name the `eventName` + finding per path so the report
states what should have fired.

## What this feeds

The confirmed escalation graph is the engagement's headline finding (`penetration-testing:reporting`) and
the lead `security/cloud-incident-response` keys its AWS IAM-abuse runbook on.
