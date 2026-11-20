---
name: supply-chain-security
description: Use when signing images, verifying SLSA provenance and attestations, or defending against dependency confusion. Triggers "sign our images", "SLSA level 3". Not for CVE scanning (image-infra-scan).
disable-model-invocation: true
---

# DevOps — Supply-Chain Security (Signing, Provenance & Build Integrity)

Everything upstream of a running service is an attack surface: the packages the build pulls, the machine that runs the build, the registry the artifact lands in, and the gap between "an image with our name on it" and "the image *we* built." This skill owns the **integrity half** of the supply chain (OWASP **A08 Software and Data Integrity Failures**): **cryptographic signing** (cosign / sigstore, keyless via OIDC), **build provenance and attestations** (SLSA build levels, in-toto), **dependency-confusion and typosquat defense**, and **build-pipeline integrity** (pinned actions and digests, protected registries, verification enforced at deploy). Its boundary partner `qa-<stack>:image-infra-scan` owns the **A03 Software Supply Chain Failures** (vulnerability) surface.

> **The SBOM boundary.** `qa-<stack>:image-infra-scan` (Trivy) **generates and scans** the SBOM: *what is in this artifact, and does any of it have a known CVE?* This skill **signs and attests** it: *is this artifact the one we built, from the source and by the pipeline we think, and is this SBOM really the SBOM for this digest?* An unsigned SBOM in a release bucket is an unverified claim anyone can swap, and a scan of a swapped SBOM is a green light for the wrong artifact. The chain: Trivy emits `sbom.cdx.json` → this skill runs `cosign attest --type cyclonedx --predicate sbom.cdx.json <image>@sha256:…` → the deploy gate runs `cosign verify-attestation`. A signed image full of Critical CVEs is authentic and vulnerable; a clean scan of an unsigned image says nothing about who built it.

> **The sibling boundary, `devops:iac-security`.** It owns IaC misconfiguration and policy-as-code (is the declared infrastructure configured safely). This skill owns artifact integrity and provenance (is the thing we are about to run the thing we built). They meet at the admission policy that enforces signature verification: `devops:iac-security` or `devops:kubernetes-security` authors it, and the verification rule it encodes (which identity, issuer and builder id) comes from here.

## Decision matrix — sign vs attest vs verify vs detect

| Need | Use | Produces / checks | Where it runs |
|------|-----|-------------------|---------------|
| Prove an **image is ours** and unmodified since build | `cosign sign` (keyless) | a signature + Fulcio cert + Rekor entry, bound to the **digest** | build pipeline, after push |
| Prove a **release binary or file** is ours | `cosign sign-blob --bundle` | a `.sigstore.json` bundle beside the artifact | release pipeline |
| Bind the **SBOM** to the artifact it describes | `cosign attest --type cyclonedx` | a signed in-toto attestation carrying the SBOM | build pipeline, after Trivy emits it |
| Prove **how and where it was built** | **SLSA provenance**: `actions/attest-build-provenance`, `slsa-github-generator`, or `docker buildx --provenance=mode=max` | a signed in-toto **SLSA Provenance v1** predicate | build pipeline |
| **Block unsigned or unattested images** | `cosign verify` / `verify-attestation` in the deploy job **+** admission (`policy-controller` `ClusterImagePolicy`, Kyverno `verifyImages`) | pass/fail on identity + issuer + digest | deploy gate **and** cluster admission |
| Verify a **third-party** artifact before consuming it | `cosign verify`, `slsa-verifier verify-image`, `gh attestation verify` | pass/fail against the *publisher's* identity | build pipeline, pre-pull |
| Stop an **internal package name resolving from a public registry** | scoped registries, namespace reservation, source mapping | a resolution that cannot reach the public index for your namespaces | build config, permanently |
| Detect a **typosquat or confusable** dependency | `confused`, OSSF Scorecard, malicious-package feeds (Socket, OSV-Scanner) | a name-similarity and publish-anomaly finding | PR gate |
| Find **CVEs**, generate the SBOM | **`qa-<stack>:image-infra-scan`** (Trivy) | CVE list, CycloneDX/SPDX SBOM | separate gate; **run both** |

**Sign the digest**, attest the SBOM and the provenance to that same digest, and verify at deploy. Detection (dependency confusion, typosquat) is a separate, earlier gate: signing proves your build was faithfully reproduced into an artifact, and says nothing about whether the build pulled a malicious package in.

**Green ≠ safe.** A verified signature proves authenticity and integrity, not safety: nothing about the CVEs inside (`qa-<stack>:image-infra-scan`), the Terraform that deploys it (`devops:iac-security`), the cluster RBAC it lands in (`devops:kubernetes-security`) or the app's own flaws (`qa-security`). Every report states which surface it covered (signing, provenance, dependency integrity, build-pipeline integrity) and hands the rest off by name.

## SLSA build levels — the ladder

**SLSA v1.0** is the stable spec; its Build track has three levels. v1.0 deferred the source and "L4" requirements, so never quote a "SLSA Level 4" as achievable.

| Level | Requirement | In practice |
|---|---|---|
| **Build L1** | Provenance **exists** and is distributed with the artifact | `docker buildx --provenance=mode=max`, published |
| **Build L2** | Provenance is **signed** by a **hosted** build platform | hosted CI with keyless OIDC; `actions/attest-build-provenance` clears it |
| **Build L3** | Isolated build on a **reusable, non-user-modifiable** definition; **signing material unreachable from user build steps** | a reusable workflow or `slsa-github-generator` holds the build definition |

The jump that matters is **L2 → L3**: at L2 a malicious build step can forge its own provenance, because it runs in the job that holds the signing token. State the level achieved and what the next one needs; never claim L3 while the build definition lives in the repo being built. The three generation paths, the L2→L3 procedure and what to assert inside a provenance document are in `references/slsa-provenance.md`.

The OWASP, SLSA, NIST SSDF and CIS mapping for each finding class is the table in `references/slsa-provenance.md`; state it once per report.

## Setup — pin the tooling

```bash
curl -sSfL -o /usr/local/bin/cosign \
  https://github.com/sigstore/cosign/releases/download/v3.1.3/cosign-linux-amd64
chmod +x /usr/local/bin/cosign

curl -sSfL -o /usr/local/bin/slsa-verifier \
  https://github.com/slsa-framework/slsa-verifier/releases/download/v2.7.1/slsa-verifier-linux-amd64
chmod +x /usr/local/bin/slsa-verifier
```

In GitHub Actions use `sigstore/cosign-installer@v4` with `cosign-release: 'v3.1.3'`: installer v3.x cannot install cosign v3.x. Also pinned: `actions/attest-build-provenance@v4`. Pin every version for the reason `qa-<stack>:image-infra-scan` pins Trivy: a silent upgrade that changes verification semantics turns a green gate red, or a red gate green, with nobody having decided. In a high-assurance pipeline pin third-party actions by **full commit SHA** (`references/dependency-integrity.md`). The cosign v2 → v3 breaking changes and the `--new-bundle-format=false` escape hatch are in `references/cosign-sigstore.md`.

## Keyless signing — no static keys

**Generate no long-lived cosign key pair.** `cosign generate-key-pair` produces a durable secret that lives in a CI secret store, gets copied to laptops and never expires; a static signing key in CI is a **blocker** finding. Keyless signing has no key to steal: the CI job's OIDC token (`id-token: write` in GitHub Actions, the GitLab `id_tokens:` block, an Azure DevOps workload-identity-federation connection) is exchanged at **Fulcio** for a ~10-minute certificate whose subject is the workflow identity, cosign signs the **digest**, and the signature plus certificate go to **Rekor**, the public transparency log that proves the signature happened while the certificate was valid.

**Verification asserts an identity, not a key**, and both flags are mandatory: identity alone is worthless without the issuer, because anyone can stand up an OIDC provider that mints the string you match on.

```bash
IMAGE=ghcr.io/myorg/api
DIGEST=sha256:0d1c9e...

cosign sign --yes "$IMAGE@$DIGEST"

cosign verify "$IMAGE@$DIGEST" \
  --certificate-identity "https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Sign, attest, verify and deploy the **digest**, never a tag: a tag is mutable, so a signature on `api:1.4.2` can be made to cover a different image. The issuer is never a wildcard, and an identity regexp is anchored and org-scoped. Where keyless cannot work, key-based signing needs a recorded reason and a KMS or HSM key. The full command surface (`sign-blob`, `cosign tree`, Rekor lookups, private Fulcio and Rekor, air-gapped `--trusted-root`) is in `references/cosign-sigstore.md`.

## Attesting the SBOM — where Trivy hands off

```bash
trivy image --format cyclonedx --output sbom.cdx.json "$IMAGE@$DIGEST"

cosign attest --yes --type cyclonedx --predicate sbom.cdx.json "$IMAGE@$DIGEST"

cosign verify-attestation "$IMAGE@$DIGEST" \
  --type cyclonedx \
  --certificate-identity "https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Trivy generates (not this skill's job), `attest` binds, `verify-attestation` proves the SBOM belongs to this image and was signed by our pipeline. When the next Log4Shell drops, you rescan the stored, signed SBOM to answer "which shipped artifacts are affected?" with evidence. Use `cosign attest`, not the deprecated `cosign attach sbom`, which stores the SBOM unsigned as an ordinary OCI layer.

## Dependency confusion & typosquatting — the earlier gate

Signing cannot tell you the build pulled `@myorg/auth-client` from your private registry rather than an attacker's `99.0.0` published to the public one. The fix is resolution configuration, not a scanner:

- **Scope every internal package** (`@myorg/*`, a reserved group id, a company prefix) and **bind the scope to one registry, exclusively**: `.npmrc` `@myorg:registry=`, NuGet `packageSourceMapping`, Gradle `content { includeGroupByRegex }` with `exclusiveContent`, a single pip `--index-url`.
- **Reserve the namespace publicly** with a placeholder scope, group id or prefix, so the name cannot be squatted.
- **Pin with hashes and install locked**: `npm ci`, `pnpm install --frozen-lockfile`, `dotnet restore --locked-mode`, Gradle `verification-metadata.xml`, `pip --require-hashes`. An unlocked `npm install` resolves fresh, so the integrity hashes never get checked.
- **Detect**: `confused` in CI for claimable internal names; name-similarity and publish-anomaly feeds (Socket, OSV malicious advisories) and OSSF Scorecard for confusable names.
- **`--extra-index-url` is dependency confusion as a config setting.** pip queries every configured index and takes the highest version, with no trusted source per package. Point a single `--index-url` at an internal proxy that mirrors upstream and lets the proxy decide.

Per-ecosystem config, the `confused` invocation and gating flags, hash-pinning recipes, the Scorecard checks worth gating on and the namespace-reservation runbook are in `references/dependency-integrity.md`.

## Build-pipeline integrity

The build machine is a production system.

- **OIDC everywhere, no static credentials.** Registry pushes, cloud deploys and signing use federated short-lived identity; a long-lived registry password or cosign private key in CI secrets is a **blocker**.
- **Pin every input.** Base images by digest, third-party actions by full commit SHA (always in a job that holds signing or deploy privileges), toolchains to the project's target. An unpinned mutable reference is a permanent write-access grant to whoever controls it (`devops:docker`, `devops/{github-actions,gitlab-ci,azure-pipelines}` own the mechanics).
- **Hermetic builds.** No network fetch beyond the declared, pinned dependency set: no `curl | sh`, no `ADD https://…` without a checksum, no `latest` installers. Everything consumed is a resolved dependency recorded in the provenance's `resolvedDependencies`.
- **Reproducible where cheap.** Byte-identical rebuilds (`SOURCE_DATE_EPOCH`, sorted inputs, no embedded timestamps) let a second builder confirm the artifact. It is a goal, not a gate; a failing check is a lead to investigate.
- **Least-privilege workflow tokens.** `permissions: {}` at workflow level, escalated per job to exactly `id-token: write`, `attestations: write` or `packages: write`. Blanket `write-all` can rewrite the branch it claims to have built from.
- **Protected registries.** Immutable tags (ECR tag immutability, ACR locks, GHCR retention rules) so a digest is never re-pointed; push restricted to the CI identity.
- **Guard the untrusted-input triggers.** `pull_request_target`, `workflow_run` and self-hosted runners on public repos run privileged with attacker-influenced inputs. Never grant them `id-token: write`.

## Verify at deploy — the gate that makes signing matter

Signing without enforcement is theatre. Two enforcement points, both required:

```bash
cosign verify "$IMAGE@$DIGEST" \
  --certificate-identity "https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  || { echo "::error::unsigned or untrusted image — refusing to deploy"; exit 1; }
```

1. **The deploy-job gate** above fails the pipeline before rollout. Gate on `cosign verify-attestation` or `slsa-verifier` too, asserting the predicate's source repo and builder: a signed image with missing or forged provenance still deploys if only the signature is checked.
2. **Cluster admission** is the backstop for anything reaching the cluster by another path (`kubectl`, a stale GitOps commit, a second pipeline): a `policy-controller` `ClusterImagePolicy` or Kyverno `verifyImages`, authored with `devops:kubernetes-security`. `policy-controller` enforces only in namespaces labelled `policy.sigstore.dev/include: "true"`, so a namespace created after the policy lands bypasses it silently. The policy YAML, the Kyverno choice and the rollout ladder (warn-only deploy gate → failing deploy gate → admission `warn` → `enforce` on one namespace → cluster-wide) are in `references/cosign-sigstore.md`; cluster-wide `enforce` on day one gets the policy deleted at the first outage.

To wire build → scan → sign → attest → verify into a pipeline, read `references/ci-wiring.md`. It lives in the deploy pipeline, not the `qa/cicd/*` test lane. GitLab CI and Azure Pipelines run the same shape (`devops/{gitlab-ci,azure-pipelines}`).

## Cross-references

- **`qa-<stack>:image-infra-scan`**: the boundary partner. Trivy generates the SBOM and owns CVE scanning (A03); this skill signs and attests it (A08). Run both.
- **`devops:iac-security`**: authors the admission policy; this skill supplies the verification rule inside it.
- **`devops:kubernetes-security`**: owns admission enforcement (`ClusterImagePolicy`, `verifyImages`, namespace labels, RBAC around the policy). The rule is here, the mechanism is there.
- `devops:container-runtime-security` (a verified image can still be exploited running) · `devops:cloud-posture` (registry tag immutability, IAM on push) · `devops:threat-modeling` (STRIDE Tampering scopes which surfaces a system needs) · `devops:controls-validation` (are the CI/CD hardening controls effective).
- **`devops/agents/infra-security-tester`** loads this skill and reports findings with their A08 / SLSA mapping. **`devops-engineer`** applies every fix; this skill finds and gates. **`devops-auditor`** covers static conformance (sections G and I); proving a signature verifies is here.
- `devops:docker` (`buildx --provenance/--sbom`, base-image digest pinning) · `devops/{github-actions,gitlab-ci,azure-pipelines}` (OIDC permissions, action pinning).
