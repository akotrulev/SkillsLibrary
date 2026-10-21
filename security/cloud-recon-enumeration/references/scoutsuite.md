# ScoutSuite — multi-cloud config audit as recon

**ScoutSuite** (NCC Group, `nccgroup/ScoutSuite`) pulls resource configuration across AWS, Azure, GCP (and Oracle/Aliyun) through each provider's read-only API and renders it as one browsable, interactive HTML report, ranked by risk. In this skill it is the recon lane's **"where should I even look" pass**: before hand-enumerating storage or IAM, a ScoutSuite run tells you which services exist, which are flagged, and where the dense misconfiguration clusters are.

> `devops:cloud-posture` already owns ScoutSuite as a **defensive CSPM** tool — a scheduled, read-only benchmark run for its own sake. Here, the same tool and the same read-only credential model are run **as a recon step inside an authorized offensive engagement**: the report's findings become enumeration leads the rest of this skill (and the provider-specific exploitation skills) chase down and prove reachable. The posture↔exploitation handoff runs both ways — see `SKILL.md`'s cross-references.

## Invocation

```bash
python3 -m venv .scout && source .scout/bin/activate
pip install scoutsuite==5.14.0        # pin the version — a new check turning the report redder is a deliberate bump
scout --help

# AWS — a named, in-scope profile only; never the default/shared profile
scout aws --profile <in-scope-scope-profile> --report-dir ./out

# Azure — service-principal auth, scoped to the in-scope subscription
scout azure --cli --report-dir ./out

# GCP — Application Default Credentials, scoped to the in-scope project
scout gcp --project-id <in-scope-project> --report-dir ./out
```

- **Pin the version** (`scoutsuite==5.14.0`, never an unpinned `pip install scoutsuite`) — same discipline as every other scanner pin in this library: a check turning green→red on upgrade is a reviewable bump, not a surprise.
- **Credentials are read-only.** `SecurityAudit`/`ViewOnlyAccess`-equivalent access only — ScoutSuite never needs write access to audit, and granting it anyway is an anti-pattern even under authorization.
- **One scope, one run.** Point ScoutSuite at exactly the account/subscription/project the cloud scope file names; never a shared "all profiles" sweep.

## What it answers

"Where are the misconfigurations across the whole in-scope account, ranked by risk, browsable by service?" — public storage, over-permissive IAM, disabled encryption, missing logging, open network rules, unused credentials. ScoutSuite groups findings by AWS/Azure/GCP service in its HTML output, each annotated with a rule description and severity.

## How it feeds the rest of the recon pass (A1–A3 feedstock)

- **A ScoutSuite "public bucket" or "public blob" finding** is handed to `cloud-enum.md`'s workflow to confirm the exact object/listing exposure, and from there to the matching provider skill's storage-abuse section.
- **A ScoutSuite "overly permissive IAM policy" or "unused admin" finding** is a starting node for `enumerate-iam.md`'s permission-brute-force pass and the provider skill's privilege-escalation-graph tooling (PMapper for AWS).
- **A ScoutSuite "IMDSv1 enabled" / "metadata options" finding (AWS)** routes straight to `metadata-service.md` — ScoutSuite flags the configuration state; this skill's metadata-service reference details what that configuration state actually means for exploitability.
- **A ScoutSuite finding with no further enumeration path** (e.g. a logging gap) is reported as a **defensive/awareness** finding — informs detection-surface awareness, not an offensive lead.

## Anti-patterns

- **Running ScoutSuite with write-capable credentials.** It never needs them; a write-capable scan credential is itself a blocker finding, not a convenience.
- **Pointing ScoutSuite at every profile/subscription available in the shell's credential store.** Scope it explicitly to the in-scope account named by the cloud scope file.
- **Treating the HTML report as the deliverable.** It is a map of where to look next — every finding worth reporting is confirmed reachable (storage listing, assumable role, live credential) before it becomes a recon-handoff lead.
