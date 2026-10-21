# Instance Metadata Service — IMDSv1/v2, SSRF→credentials, T1552.005

The instance metadata service (IMDS) is the single most important **SSRF-to-credentials** primitive in cloud pentesting. A compute instance with an attached role/identity exposes temporary credentials on a link-local, non-routable address the workload itself is expected to read — which means any server-side request forgery (SSRF) or remote-code-execution bug on that workload reaches the credentials too. ATT&CK Cloud: **T1552.005 — Unsecured Credentials: Cloud Instance Metadata API.**

## Per-cloud endpoints and required headers

| Cloud | Endpoint | Credential path | Anti-SSRF guard |
|---|---|---|---|
| AWS | `http://169.254.169.254/latest/meta-data/` | `.../iam/security-credentials/<role-name>` (`AccessKeyId`/`SecretAccessKey`/`Token`) | IMDSv2 token/header (below) |
| Azure | `http://169.254.169.254/metadata/instance?api-version=...`, `.../metadata/identity/oauth2/token?resource=...` | token endpoint above | **requires header `Metadata: true`** — a bare GET with no header fails |
| GCP | `http://metadata.google.internal/computeMetadata/v1/` | `.../instance/service-accounts/default/token` | **requires header `Metadata-Flavor: Google`** |

Azure and GCP both reject a request missing their required header outright, which already blunts the most common SSRF shape (one that can only force a plain GET with no custom headers). AWS's defense is more involved — IMDSv2 — and is the one worth detailing.

## IMDSv1 vs IMDSv2 (AWS)

- **IMDSv1 — the flaw.** A bare, unauthenticated `GET` to the credentials path returns the role's temporary keys directly. No header, no token, no handshake. Any SSRF primitive that can issue a GET to `169.254.169.254` harvests credentials outright.
- **IMDSv2 — session-oriented defense-in-depth.** Two steps:
  1. `PUT http://169.254.169.254/latest/api/token` with header `X-aws-ec2-metadata-token-ttl-seconds: 21600` → returns a session token.
  2. Every `GET` must carry `X-aws-ec2-metadata-token: <token>`.
  This blocks the common SSRF shape because most SSRF primitives can only force a **GET** and cannot set arbitrary headers or issue a **PUT** — so they can neither obtain nor present the token.
- **Hop limit.** The token/response packets carry a configurable IP TTL (hop limit), **default 1** — the response cannot be forwarded off the instance, so it dies before reaching a reverse proxy or a neighbouring container/pod. **A container on the host counts as an extra hop**, so a container needs the instance configured with hop limit **2** to reach IMDS at all — which re-widens the SSRF/proxy path. This is a deliberate trade-off to **flag**, not a default to recommend.
- **Enforcement gap — the actual finding.** Setting `HttpTokens=required` in `MetadataOptions` enforces v2 and disables v1 fallback entirely. **Many instances still launch with v1 optional** (both v1 and v2 accepted) — that dual-accept state is the finding, and it is detected by **reading the instance's `MetadataOptions` on the control plane** (`aws ec2 describe-instances` / ScoutSuite's flagged output), not by repeatedly hammering the live endpoint.
- **Fully disabling IMDS** (`HttpEndpoint=disabled`) removes the surface entirely for a workload that doesn't need role creds at all — worth naming as the hardest-but-cleanest fix in a report, even though it's the provider/owner's remediation, not this skill's action.
- **Live-risk note:** IMDSv2 has been the EC2-console default since November 2023, but brownfield instances launched earlier (or via IaC that never set `HttpTokens`) commonly still accept v1. An active SSRF→IMDSv1 credential-theft campaign was reported in the wild in March 2025 — v1-optional is not a theoretical risk, it is the live one.

## The SSRF chain (the attack shape, for awareness)

1. App with an SSRF vulnerability → force a request to `169.254.169.254` (AWS) / `metadata.google.internal` (GCP) / the Azure metadata address.
2. **IMDSv1:** read role credentials directly from the response.
   **IMDSv2:** only reachable if the SSRF can *also* issue a PUT and inject the token header, **and** the response can leave the instance (hop limit allows it) — most SSRF primitives can't, which is why v2-enforced instances are not exploitable via this chain.
   Azure/GCP: the SSRF additionally has to be able to set the provider's required header — an SSRF limited to plain GETs with no custom headers is already blunted on both.
3. Load the recovered credentials into the provider CLI/SDK and run `sts get-caller-identity` (or the Azure/GCP equivalent) to confirm the principal.
4. Enumerate that principal's permissions — hand off to `enumerate-iam.md`.

Report the outcome as the **role's blast-radius** (what it can reach, per the IAM enumeration that follows) — **never the key material itself**.

## What to actually check in a recon pass

This skill's job is detection, not repeated live exploitation:

- Read each in-scope instance's metadata configuration on the control plane (`describe-instances` `MetadataOptions`, the Azure/GCP equivalents) — is v1 still accepted, is the hop limit raised for container workloads, is the endpoint disabled entirely?
- Only exercise the actual SSRF chain against a lab target built for the purpose (e.g. a CloudGoat/flaws.cloud scenario) — never by repeatedly hammering a live production instance's metadata endpoint, which risks destabilizing a fragile workload for no additional information the control-plane read didn't already give you.
- Hand a confirmed-reachable chain to the matching provider skill (`cloud-attack-aws` names EC2 metadata/user-data/snapshot credential theft explicitly) for the privilege-escalation follow-through.

## Anti-patterns

- **Repeatedly probing a live instance's metadata endpoint instead of reading its configuration.** Adds risk, adds nothing the control-plane read didn't answer. *Fix:* `describe-instances`/ScoutSuite first; exercise the live chain only in a lab.
- **Reporting the recovered credential's value.** *Fix:* report that it was recovered and the blast-radius of what the role can reach.
- **Recommending hop-limit 2 as a blanket fix for container reachability without flagging the trade-off.** It re-widens the exact SSRF path IMDSv2 narrows. *Fix:* name both sides — containers need it, but it costs the one thing hop-limit-1 buys.
- **Assuming IMDSv2-console-default means every instance is enforced.** The console default is not retroactive. *Fix:* detect `HttpTokens` per instance; never assume.
