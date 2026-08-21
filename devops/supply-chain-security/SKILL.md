---
name: devops-supply-chain-security
description: Use when signing container images/artifacts, verifying SLSA provenance / attestations, attesting an SBOM, verifying signatures at deploy time, defending against dependency-confusion/typosquat, or hardening build-pipeline integrity — the OWASP A08 surface. Triggers "sign our images", "SLSA level 3", "dependency confusion". Do NOT use for CVE scanning or SBOM generation (`qa-security-image-infra-scan`), IaC misconfig (`devops-iac-security`), Dockerfile authoring (`devops-docker`), or CI YAML.
---

# DevOps — Supply-Chain Security (Signing, Provenance & Build Integrity)

Everything upstream of a running service is an attack surface: the packages the build pulls, the machine
that runs the build, the registry the artifact lands in, and the gap between "an image with our name on it"
and "the image *we* built." This skill owns the **integrity half** of the software supply chain —
**cryptographic signing** (cosign / sigstore, keyless via OIDC), **build provenance & attestations**
(SLSA build levels, in-toto), **dependency-confusion and typosquat defense**, and **build-pipeline
integrity** (hermetic + reproducible builds, pinned actions and digests, protected registries, verification
enforced at deploy).

This skill is **language-agnostic** — every tool here is a Go binary, a CI action, or a registry setting, so
it is one shared skill routing to `references/<topic>.md`, not a per-stack triplication. It is the
**A08 Software and Data Integrity Failures** surface; its boundary partner
`qa-security-image-infra-scan` owns the **A03 Software Supply Chain Failures** (vulnerability) surface.

> **⚠️ The SBOM boundary — be precise; this is the whole reason both skills exist.**
> **`qa-security-image-infra-scan` (Trivy) GENERATES and SCANS the SBOM.** It answers *"what is in this
> artifact, and does any of it have a known CVE?"* — `trivy image --format cyclonedx`,
> `trivy sbom --exit-code 1`. **This skill SIGNS and ATTESTS it.** It answers *"is this artifact the one we
> built, from the source we think, by the pipeline we think — and is this SBOM really the SBOM for
> **this** digest?"* An unsigned SBOM sitting in a release bucket is an unverified claim: anyone can swap
> it, and a scan of a swapped SBOM is a green light for the wrong artifact. So the chain is: **Trivy emits
> `sbom.cdx.json` → this skill runs `cosign attest --type cyclonedx --predicate sbom.cdx.json <image>@sha256:…`
> → the deploy gate runs `cosign verify-attestation`.** Neither half is optional and neither replaces the
> other: a signed image full of Critical CVEs is authentic *and* vulnerable; a clean scan of an unsigned
> image says nothing about who built it.

> **⚠️ The sibling boundary — `devops-iac-security`.** Both skills sit at build/artifact posture, so they
> get conflated. **`devops-iac-security` = IaC misconfiguration + policy-as-code** (Checkov/tfsec/Terrascan/
> KICS/OPA over Terraform, Bicep, Helm, manifests — *is the declared infrastructure configured safely*).
> **This skill = artifact integrity + provenance** (*is the thing we are about to run the thing we built*).
> They meet at exactly one place — the **admission policy** that enforces signature verification is
> policy-as-code authored by `devops-iac-security` / `devops-k8s-security`, and the **verification rule it
> encodes** (which identity, which issuer, which builder ID) comes from here.

## Decision matrix — sign vs attest vs verify vs detect

| Need | Use | Produces / checks | Where it runs |
|------|-----|-------------------|---------------|
| Prove an **image is ours** and unmodified since build | `cosign sign` (keyless) | a signature + Fulcio cert + Rekor entry, bound to the **digest** | build pipeline, after push |
| Prove a **release binary / file** is ours | `cosign sign-blob --bundle` | a `.sigstore.json` bundle beside the artifact | release pipeline |
| Bind the **SBOM** to the artifact it describes | `cosign attest --type cyclonedx` | a signed in-toto attestation carrying the SBOM as its predicate | build pipeline, after Trivy emits it |
| Prove **how and where it was built** (source repo, commit, workflow, builder) | **SLSA provenance** — `actions/attest-build-provenance`, `slsa-github-generator`, or `docker buildx --provenance=mode=max` | a signed in-toto **SLSA Provenance v1** predicate | build pipeline |
| **Block unsigned / unattested images from running** | `cosign verify` / `cosign verify-attestation` in the deploy job **+** admission (`policy-controller` `ClusterImagePolicy` / Kyverno `verifyImages`) | pass/fail on identity + issuer + digest | deploy gate **and** cluster admission |
| Verify a **third-party** artifact before consuming it | `cosign verify` / `slsa-verifier verify-image` / `gh attestation verify` | pass/fail against the *publisher's* identity | build pipeline (pre-pull) |
| Stop the build resolving an **internal package name from a public registry** | scoped registries + namespace reservation + source mapping (`.npmrc`, `packageSourceMapping`, Gradle `content` filters) | a resolution that *cannot* reach the public index for your namespaces | build config, permanently |
| Detect a **typosquat / confusable** dependency name | `confused`, OSSF Scorecard, malicious-package feeds (Socket / OSV-Scanner malicious advisories) | a name-similarity + publish-anomaly finding | PR gate |
| Find **CVEs** in the artifact / generate the SBOM | **`qa-security-image-infra-scan`** (Trivy) | CVE list, CycloneDX/SPDX SBOM | separate gate — **run both** |

**Rule of thumb:** **sign the digest**, **attest the SBOM and the provenance to that same digest**, and
**verify at deploy**. Detection (dep-confusion, typosquat) is a *separate, earlier* gate — signing proves
your build was faithfully reproduced into an artifact; it says nothing about whether the build pulled a
malicious package in the first place. **Both halves, or neither is worth much.**

## The four surfaces, and what each proves

| Surface | Question it answers | Mechanism | Spine |
|---|---|---|---|
| **Artifact signing** | "Did *we* produce this exact digest?" | cosign keyless (Fulcio cert + Rekor transparency log) | A08 |
| **Provenance / attestation** | "From what source, commit, workflow, and builder?" | in-toto + SLSA Provenance v1 predicate | A08 · SLSA Build L1–L3 |
| **Dependency integrity** | "Did the build pull what we meant to pull?" | scoped registries, namespace reservation, lockfile + hash pinning, name-confusion detection | A08 (+ A03 for the CVE half) |
| **Build-pipeline integrity** | "Could someone have tampered *during* the build?" | hermetic builds, pinned actions/digests, OIDC-only credentials, isolated + protected builders, protected registries | A08 · SLSA Build L2–L3 |

**Green ≠ safe.** A verified signature proves **authenticity and integrity**, not **safety**. It says the
artifact is the one your pipeline produced — nothing about the CVEs inside it
(`qa-security-image-infra-scan`), the misconfigured Terraform that deploys it (`devops-iac-security`), the
cluster RBAC it lands in (`devops-k8s-security`), or the app's own flaws (`qa-security`). Every report from
this skill states which of the four surfaces above it covered and hands the rest off by name.

## SLSA build levels — the ladder, and what each actually requires

**SLSA v1.0** is the stable spec; its **Build track** defines three levels (v1.0 deferred the source and
"L4" requirements to a future version — do not quote a "SLSA Level 4" as achievable today).

| Level | Requirement | In practice | Typical effort |
|---|---|---|---|
| **Build L1** | Provenance **exists** and is distributed with the artifact | emit a provenance document from the build (`docker buildx --provenance=mode=max`), publish it | hours |
| **Build L2** | Provenance is **signed** by a **hosted** build platform; consumers can authenticate it | run on hosted CI (GitHub Actions / GitLab / Azure DevOps), sign with keyless OIDC — `actions/attest-build-provenance` clears this trivially | a day |
| **Build L3** | The build runs in an **isolated** environment on a **reusable, non-user-modifiable** build definition; **signing key material is unreachable from user build steps** | a *reusable workflow* (or `slsa-github-generator`) holds the build definition; the signing step runs where a compromised build step cannot reach it | a sprint |

The jump that matters is **L2 → L3**. At L2 a malicious build step can still forge its own provenance,
because it runs in the same job that holds the signing token. **L3 moves the build definition out of the
repo** (a shared reusable workflow, vetted centrally) **and isolates the signing material** from
user-controlled steps. GitHub artifact attestations + a reusable workflow, or `slsa-github-generator`, are
the two supported paths — depth in **`references/slsa-provenance.md`**.

**Framework mapping** (state it once per report; do not re-derive):

| This skill's finding | OWASP Top 10:2025 | SLSA | Other |
|---|---|---|---|
| Unsigned artifact deployed | **A08** Software and Data Integrity Failures | Build L2 unmet | CIS SSC 4.x |
| No build provenance | **A08** | Build L1 unmet | NIST SSDF PO.3 / PS.3 · EO 14028 |
| Provenance forgeable by a build step | **A08** | Build L3 unmet | SLSA threat "forged provenance" |
| Dependency confusion / typosquat exposure | **A08** (+ **A03** where it lands a vulnerable dep) | — | NIST SSDF PW.4 · OSSF Scorecard `Pinned-Dependencies` |
| Floating tags / unpinned actions | **A08** | Build L1–L2 unmet | Scorecard `Pinned-Dependencies` |
| No verification at deploy | **A08** | the whole ladder unenforced | CIS K8s 5.x (admission) |

## Setup — pin the tooling

```bash
# cosign — the v3 line is current; the v2 line is still maintained for pipelines not yet migrated.
brew install cosign
# or, pinned, in CI:
curl -sSfL -o /usr/local/bin/cosign \
  https://github.com/sigstore/cosign/releases/download/v3.1.3/cosign-linux-amd64
chmod +x /usr/local/bin/cosign
cosign version

# slsa-verifier — verify provenance produced by slsa-github-generator or other SLSA builders.
curl -sSfL -o /usr/local/bin/slsa-verifier \
  https://github.com/slsa-framework/slsa-verifier/releases/download/v2.7.1/slsa-verifier-linux-amd64
chmod +x /usr/local/bin/slsa-verifier
```

```yaml
# In GitHub Actions, prefer the official installer action — PINNED (the library's pinning invariant).
# NOTE: cosign-installer v3.x CANNOT install cosign v3.x. Use installer v4 for the cosign v3 line.
- uses: sigstore/cosign-installer@v4
  with:
    cosign-release: 'v3.1.3'
```

> **Pin every version** — `cosign@v3.1.3`, `sigstore/cosign-installer@v4`, `slsa-verifier@v2.7.1`,
> `actions/attest-build-provenance@v4` — for the same reason `qa-security-image-infra-scan` pins Trivy: a
> silent tool upgrade that changes verification semantics turns a green gate red (or, far worse, a red gate
> green) with nobody having made a decision. In a high-assurance pipeline, pin third-party actions by
> **full commit SHA**, not tag — see `references/dependency-integrity.md`.
>
> **cosign v2 → v3 breaking changes** (bite on migration): `--bundle` is now **required** on
> `cosign sign-blob`; `--output-certificate` / `--output-signature` are **removed** in favour of the
> bundle; the standardized Sigstore **bundle format is the default** for both signing and verification;
> container signatures are stored as an OCI 1.1 referring artifact. If a registry or downstream verifier
> only understands the legacy layout, `--new-bundle-format=false` is the escape hatch — record *why*.

## Keyless signing — the no-static-keys invariant

**Never generate a long-lived cosign key pair.** `cosign generate-key-pair` produces exactly the thing the
library's **no-static-credentials invariant** forbids: a durable secret that must live in a CI secret store,
gets copied to laptops, and never expires. **Keyless (identity-based) signing has no key to steal.**

The flow, end to end:

1. The CI job requests an **OIDC token** from its host (`id-token: write` in GitHub Actions; the GitLab
   `id_tokens:` block; the Azure DevOps workload-identity federation service connection).
2. cosign exchanges that token at **Fulcio** for a **short-lived (≈10 min) X.509 certificate** whose
   subject *is the workflow identity* — e.g.
   `https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main`.
3. cosign signs the artifact **digest**, then the signature + certificate go to **Rekor**, the public
   **transparency log** — an append-only, tamper-evident record that a signature was made at a point in
   time. Rekor is what makes the ephemeral certificate usable after it expires: the log entry proves the
   signature happened *while the cert was valid*.
4. The private key is discarded before the job ends. There is nothing to rotate and nothing to leak.

**Verification therefore asserts an identity, not a key** — this is the part teams get wrong:

```bash
IMAGE=ghcr.io/myorg/api
DIGEST=sha256:0d1c9e...           # ALWAYS sign and verify a digest, never a mutable tag

# Sign — keyless by default in cosign v2+; --yes skips the interactive confirmation.
cosign sign --yes "$IMAGE@$DIGEST"

# Verify — BOTH flags are mandatory. Identity alone is worthless without pinning the issuer:
# anyone can stand up an OIDC provider that mints the string you are matching on.
cosign verify "$IMAGE@$DIGEST" \
  --certificate-identity "https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

> **`--certificate-identity-regexp` is a footgun with a legitimate use.** A regexp is correct when you
> genuinely accept many workflows (a monorepo, a release matrix) — anchor it (`^…$`) and scope it to your
> org. A regexp of `.*`, or an unanchored one that a fork's ref can satisfy, verifies *nothing*.
> `--certificate-oidc-issuer` is **never** a wildcard.

Full command surface, private-Fulcio/Rekor deployments, `sign-blob`/`verify-blob`, `cosign attest`,
`cosign tree`/`triangulate`, Rekor lookups, air-gapped verification via `--trusted-root`, and the
key-based fallback for the cases where keyless genuinely cannot work →
**`references/cosign-sigstore.md`**.

## Attesting the SBOM — where Trivy hands off

```bash
# 1. qa-security-image-infra-scan (Trivy) GENERATES the SBOM. Not this skill's job.
trivy image --format cyclonedx --output sbom.cdx.json "$IMAGE@$DIGEST"

# 2. THIS skill binds it to the digest as a signed in-toto attestation.
cosign attest --yes --type cyclonedx --predicate sbom.cdx.json "$IMAGE@$DIGEST"

# 3. The deploy gate proves the SBOM belongs to THIS image and was signed by OUR pipeline.
cosign verify-attestation "$IMAGE@$DIGEST" \
  --type cyclonedx \
  --certificate-identity "https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

The payoff is the A03 story `qa-security-image-infra-scan` describes, finally trustworthy: when the next
Log4Shell drops, you rescan the **stored SBOM** to answer "which shipped artifacts are affected?" — and a
*signed* SBOM means the answer is evidence rather than a hopeful assumption about a file in a bucket.

> Use `cosign attest`, **not** the deprecated `cosign attach sbom`. `attach` stores the SBOM unsigned as an
> ordinary OCI layer; `attest` wraps it in a signed in-toto statement bound to the digest.

## Build provenance — generation and verification

Three supported generation paths, in increasing order of assurance:

```yaml
# --- Path A: buildx inline provenance (SLSA Build L1). Cheapest; cross-ref `devops-docker`. ---
# Attaches a provenance + SBOM attestation to the image at build time. mode=max includes the
# full build steps and materials; the default `mode=min` records almost nothing useful.
- run: |
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      --provenance=mode=max --sbom=true \
      --tag ghcr.io/myorg/api:${{ github.sha }} --push .

# --- Path B: GitHub artifact attestations (SLSA Build L2; L3 with a reusable workflow). Default choice. ---
permissions:
  id-token: write        # OIDC token for keyless signing
  attestations: write    # write the attestation to the attestation store
  contents: read
  packages: write
steps:
  - id: push
    run: |
      docker buildx build --push --tag ghcr.io/myorg/api:${{ github.sha }} . \
        --metadata-file meta.json
      echo "digest=$(jq -r '."containerimage.digest"' meta.json)" >> "$GITHUB_OUTPUT"
  - uses: actions/attest-build-provenance@v4
    with:
      subject-name: ghcr.io/myorg/api
      subject-digest: ${{ steps.push.outputs.digest }}
      push-to-registry: true

# --- Path C: slsa-github-generator (SLSA Build L3 by construction). ---
# The build definition lives in a vetted, reusable, non-user-modifiable workflow, and the signing
# material is unreachable from user build steps — which is exactly what L3 requires.
# uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.1.0
```

Verification, matched to how it was produced:

```bash
# Path B — GitHub artifact attestations, verified with the GitHub CLI.
gh attestation verify "oci://ghcr.io/myorg/api@$DIGEST" --repo myorg/api

# Path C — slsa-github-generator provenance, verified against source + builder.
slsa-verifier verify-image "ghcr.io/myorg/api@$DIGEST" \
  --source-uri github.com/myorg/api \
  --source-tag v1.4.2

# Any path — the underlying attestation is a cosign-verifiable in-toto statement.
cosign verify-attestation "ghcr.io/myorg/api@$DIGEST" \
  --type slsaprovenance \
  --certificate-identity-regexp '^https://github\.com/myorg/api/\.github/workflows/release\.yml@refs/.+$' \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Predicate anatomy (`buildDefinition` / `runDetails`, `externalParameters`, `resolvedDependencies`), the
L2→L3 upgrade procedure, GitLab and Azure DevOps equivalents, and what to *assert on* inside a provenance
document rather than merely checking it exists → **`references/slsa-provenance.md`**.

## Dependency confusion & typosquatting — the earlier gate

Signing proves the build faithfully produced the artifact. It cannot tell you the build pulled
`@myorg/auth-client` from your **private** registry rather than an attacker's package of the same name
published to the **public** one with version `99.0.0`. That is **dependency confusion**, and the fix is
resolution configuration, not a scanner:

| Control | Mechanism | Ecosystem |
|---|---|---|
| **Scope every internal package** | `@myorg/*` (npm) · a reserved group id (Maven/Gradle) · a company prefix (NuGet/PyPI) | all |
| **Bind the scope to one registry, exclusively** | `.npmrc` `@myorg:registry=` · NuGet **`packageSourceMapping`** · Gradle repository `content { includeGroupByRegex }` + `exclusiveContent` · pip **single** `--index-url` (never `--extra-index-url`) | all |
| **Reserve the namespace publicly** | publish a placeholder `@myorg` scope / group id / prefix on the public registry so the name cannot be squatted | all |
| **Pin with hashes** | `package-lock.json` `integrity` + `npm ci` · `pnpm-lock.yaml` + `--frozen-lockfile` · `packages.lock.json` + `--locked-mode` (NuGet) · Gradle `verification-metadata.xml` · `pip --require-hashes` | all |
| **Detect exposure** | `confused` (checks whether your manifest's internal names are claimable publicly) in CI | npm/pip/Maven/NuGet/Go |
| **Detect confusable names** | name-similarity + publish-anomaly feeds (Socket, OSV malicious advisories); OSSF **Scorecard** for OSS repos | mostly npm/PyPI |

> **`--extra-index-url` is dependency confusion as a config setting.** pip queries *every* configured index
> and takes the highest version, with no notion of a trusted source per package. Use a single `--index-url`
> pointed at an internal proxy that mirrors upstream, and let the proxy decide.

Per-ecosystem config, the `confused` invocation and its gating flags, hash-pinning recipes, the OSSF
Scorecard checks worth gating on, and the "reserve the namespace" runbook →
**`references/dependency-integrity.md`**.

## Build-pipeline integrity

The build machine is a production system; treat it like one.

- **OIDC everywhere, no static credentials.** Registry pushes, cloud deploys, and signing all use
  federated short-lived identity — the library's **no-static-cloud-credentials invariant**. A long-lived
  registry password or cosign private key in CI secrets is a **blocker** finding.
- **Pin every input.** Base images by digest (`image@sha256:…`), third-party actions by full commit SHA,
  toolchain versions to what the project targets, package managers to the manifest's declared version.
  This is the library's **pinning invariant** (`devops-docker`, `devops/{github-actions,gitlab-ci,azure-pipelines}`)
  — this skill's contribution is naming *why*: an unpinned mutable reference is a permanent write-access
  grant to whoever controls it.
- **Hermetic builds.** No network fetches at build time beyond the declared, pinned dependency set: no
  `curl | sh`, no `ADD https://…` without a checksum, no `latest` toolchain installers. Everything the
  build consumes is a resolved dependency recorded in the provenance's `resolvedDependencies`.
- **Reproducible where cheap.** Byte-identical rebuilds (`SOURCE_DATE_EPOCH`, sorted inputs, no embedded
  timestamps) let a second builder *independently confirm* the artifact — the strongest available check on
  a compromised builder. Treat it as a goal, not a gate: many stacks cannot reach it, and a failing
  reproducibility check is a lead to investigate, not automatically a defect.
- **Least-privilege workflow tokens.** Default `permissions: {}` at workflow level, escalated per job to
  exactly `id-token: write` / `attestations: write` / `packages: write` where needed. A workflow with
  blanket `write-all` can rewrite the branch it claims to have built from.
- **Protected registries.** Immutable tags (ECR tag immutability, ACR locks, GHCR retention rules) so a
  digest can never be re-pointed; push restricted to the CI identity; no human push to production repos.
- **Guard the untrusted-input triggers.** `pull_request_target`, `workflow_run`, and self-hosted runners on
  public repos execute in a privileged context with attacker-influenced inputs — the classic build-system
  compromise. Never grant them `id-token: write`.

## Verify at deploy — the gate that makes signing matter

Signing without enforcement is theatre. **Two enforcement points, and you want both:**

```bash
# 1. Deploy-job gate — fail the pipeline before rollout. Cheap, immediate, easy to reason about.
cosign verify "$IMAGE@$DIGEST" \
  --certificate-identity "https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  || { echo "::error::unsigned or untrusted image — refusing to deploy"; exit 1; }
```

```yaml
# 2. Cluster admission — the backstop for anything that reaches the cluster by another path
#    (kubectl, a stale GitOps commit, a second pipeline). Authored with devops-k8s-security.
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata:
  name: require-signed-and-attested
spec:
  images:
    - glob: "ghcr.io/myorg/**"
  authorities:
    - keyless:
        url: https://fulcio.sigstore.dev
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subject: https://github.com/myorg/api/.github/workflows/release.yml@refs/heads/main
      attestations:
        - name: must-have-provenance
          predicateType: slsaprovenance
```

> **The policy-controller opt-in trap.** `policy-controller` only enforces in namespaces labelled
> `policy.sigstore.dev/include: "true"` — so a namespace created after the policy lands **bypasses it
> silently**. Either enforce the label via a separate admission policy, or use Kyverno's `verifyImages`
> (which matches by resource selector, not namespace opt-in) when the cluster already runs Kyverno for
> other policy. Choosing between them: **Kyverno** if you want one policy engine for everything;
> **policy-controller** if you are sigstore-deep and want the project that tracks cosign most closely.

**Adoption ladder — ratchet, don't big-bang** (same discipline as Trivy's severity ratchet):
**warn-only verification in the deploy job** → **fail the deploy job** → **admission in `warn` mode** →
**admission in `enforce` mode on one namespace** → **cluster-wide enforce**. Flipping straight to
cluster-wide enforce on an estate with unsigned legacy images gets the policy deleted by the first person
paged at 02:00.

## CI wiring — the deploy pipeline, not the test lane

**Signing and attestation happen in the build/deploy pipeline** owned by
`devops/{github-actions,gitlab-ci,azure-pipelines}` — **not** the `qa/cicd/*` test lane. Same fence the
library already draws for image scanning: the test lane runs the suite and publishes Allure; the deploy
lane builds, scans, signs, attests, and gates.

```yaml
# .github/workflows/release.yml — cross-link devops-github-actions
name: Build · Scan · Sign · Attest
on:
  push:
    tags: ['v*']

permissions: {}            # deny by default; escalate per job

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write        # push to GHCR
      id-token: write        # OIDC → Fulcio (keyless signing) + registry federation
      attestations: write    # write the provenance attestation
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@v5
      - uses: sigstore/cosign-installer@v4
        with: { cosign-release: 'v3.1.3' }

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}   # scoped, job-lived — not a static PAT

      # Build and push by digest. mode=max provenance gives SLSA L1 for free (devops-docker).
      - id: push
        run: |
          docker buildx build --push \
            --platform linux/amd64,linux/arm64 \
            --provenance=mode=max --sbom=true \
            --tag ghcr.io/myorg/api:${{ github.ref_name }} \
            --metadata-file meta.json .
          echo "digest=$(jq -r '."containerimage.digest"' meta.json)" >> "$GITHUB_OUTPUT"

      # CVE gate + SBOM generation are qa-security-image-infra-scan's job — it hands us sbom.cdx.json.
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: image
          image-ref: ghcr.io/myorg/api@${{ steps.push.outputs.digest }}
          exit-code: '1'
          severity: HIGH,CRITICAL
          ignore-unfixed: true
          format: cyclonedx
          output: sbom.cdx.json

      # Sign the DIGEST (never the tag — a tag can be re-pointed after signing).
      - run: cosign sign --yes ghcr.io/myorg/api@${{ steps.push.outputs.digest }}

      # Bind the SBOM to that same digest as a signed in-toto attestation.
      - run: |
          cosign attest --yes --type cyclonedx --predicate sbom.cdx.json \
            ghcr.io/myorg/api@${{ steps.push.outputs.digest }}

      # SLSA build provenance (L2 here; L3 once this job body moves into a reusable workflow).
      - uses: actions/attest-build-provenance@v4
        with:
          subject-name: ghcr.io/myorg/api
          subject-digest: ${{ steps.push.outputs.digest }}
          push-to-registry: true

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: sigstore/cosign-installer@v4
        with: { cosign-release: 'v3.1.3' }
      # The gate: refuse to deploy anything this pipeline did not sign.
      - run: |
          cosign verify ghcr.io/myorg/api@${{ needs.build.outputs.digest }} \
            --certificate-identity-regexp '^https://github\.com/myorg/api/\.github/workflows/release\.yml@refs/tags/v.+$' \
            --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'
```

**GitLab CI** runs the identical shape with an `id_tokens:` block minting the OIDC token cosign consumes;
**Azure Pipelines** uses a workload-identity-federation service connection. Both are documented in
`references/cosign-sigstore.md` and wired by
`devops/{gitlab-ci,azure-pipelines}`.

## Anti-patterns

- **Signing a tag instead of a digest.** `cosign sign myorg/api:1.4.2` signs whatever that tag pointed at
  *then*; the tag is mutable, so the signature can be made to "cover" a different image. *Fix:* resolve to
  `@sha256:…` and sign, attest, verify, and deploy the **digest**, always.
- **Generating a long-lived cosign key pair and storing it in CI secrets.** Recreates exactly the static
  credential the library's invariant forbids — and a stolen signing key is worse than a stolen deploy
  credential, because it forges trust rather than merely spending it. *Fix:* keyless OIDC signing; there
  is no key to steal, rotate, or leak.
- **Verifying with `--certificate-identity` but no `--certificate-oidc-issuer` (or a `.*` issuer).**
  Anyone can operate an OIDC provider that mints the subject string you match on. *Fix:* pin **both**;
  the issuer is never a wildcard, and identity regexps are anchored and org-scoped.
- **Signing but never verifying.** The signature is decorative until something refuses to run an unsigned
  artifact. *Fix:* a deploy-job `cosign verify` gate **and** cluster admission; ratchet warn → enforce.
- **`push-to-registry` / attestations produced but the deploy gate only checks the signature.** A signed
  image with a *missing or forged* provenance still deploys. *Fix:* gate on
  `cosign verify-attestation` / `slsa-verifier` too, and assert on the predicate's source repo and builder,
  not merely that a document exists.
- **Attaching an unsigned SBOM (`cosign attach sbom`) and calling it provenance.** An unsigned SBOM is an
  unverified claim that anyone with registry write access can swap. *Fix:* `cosign attest --type cyclonedx`.
- **Claiming "SLSA Level 3" while the build definition lives in the repo being built.** A compromised build
  step can rewrite it and forge its own provenance. *Fix:* move the build into a vetted **reusable
  workflow** or `slsa-github-generator` so the definition and the signing material are outside user
  control — that *is* the L3 requirement.
- **`--extra-index-url` / an unscoped internal package name.** Dependency confusion configured in, by hand.
  *Fix:* one index (an internal proxy), scoped names, `packageSourceMapping` / repository content filters,
  and reserve the namespace publicly.
- **`npm install` / unlocked restore in CI.** Resolves fresh, so the lockfile's integrity hashes never get
  checked and yesterday's audit is irrelevant. *Fix:* `npm ci` / `pnpm install --frozen-lockfile` /
  `dotnet restore --locked-mode` / Gradle dependency verification.
- **Unpinned third-party actions (`@main`, `@v3`) in a workflow that holds `id-token: write`.** Whoever
  controls that tag can mint signatures in your name. *Fix:* pin by full commit SHA in any job with
  signing or deploy privileges; never grant `id-token: write` to a `pull_request_target` job.
- **Treating a verified signature as "the artifact is safe."** It proves authorship and integrity, nothing
  more. *Fix:* run the CVE gate (`qa-security-image-infra-scan`), the IaC gate (`devops-iac-security`), and
  the app-layer gates (`qa-security`) alongside; state coverage per report.
- **Cluster-wide `enforce` admission on day one.** The first unsigned legacy image causes an outage and the
  policy gets deleted. *Fix:* ratchet — warn-only → one namespace → cluster-wide.

## Rules (hard constraints)

- **Sign the digest, never a tag.** Every `sign` / `attest` / `verify` / deploy reference is
  `image@sha256:…`.
- **Keyless (OIDC) signing only.** No long-lived cosign key pair in CI secrets — a static signing key is a
  **blocker** finding under the library's no-static-credentials invariant. Key-based signing is permitted
  only where keyless is genuinely impossible (air-gapped/self-hosted Fulcio unavailable), with the reason
  recorded and the key in a KMS/HSM, never a repo secret.
- **Verification pins BOTH `--certificate-identity` (anchored, org-scoped if a regexp) AND
  `--certificate-oidc-issuer` (never a wildcard).**
- **Signing without enforcement does not count as done.** Ship a deploy-job `cosign verify` gate **and** a
  cluster admission policy (`policy-controller` / Kyverno), ratcheted warn → enforce.
- **Attest, don't attach.** The SBOM (generated by `qa-security-image-infra-scan`) is bound to the digest
  with `cosign attest --type cyclonedx`; the deploy gate runs `cosign verify-attestation`.
- **Emit build provenance and verify it** — `actions/attest-build-provenance` / `slsa-github-generator` /
  `buildx --provenance=mode=max`. State the **SLSA Build Level achieved** and what the next level requires;
  never claim L3 while the build definition is user-modifiable, and never claim a "Level 4".
- **Every internal package namespace is scoped, exclusively source-mapped, and publicly reserved**;
  installs are lockfile-locked with integrity hashes (`npm ci`, `--frozen-lockfile`, `--locked-mode`,
  Gradle verification metadata). **No `--extra-index-url`.**
- **Pin everything the build consumes** — base images by digest, actions by SHA in privileged jobs,
  toolchains to the project's targeted version. **Deny-by-default workflow `permissions`**, escalated per
  job.
- **No secrets in signing config.** OIDC tokens are minted per job; registry creds are federated or
  job-scoped; nothing durable is written to the repo.
- **CI home is the deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`), **not** the
  `qa/cicd/*` test lane.
- **Green ≠ safe.** A passing verification means the **integrity** surface passed. Name the handoffs —
  CVEs (`qa-security-image-infra-scan`), IaC (`devops-iac-security`), cluster (`devops-k8s-security`),
  app (`qa-security`) — in every report.
- **This skill finds and gates; it does not remediate.** `devops-engineer` applies the pipeline and
  registry changes, per the library's auditor↔engineer handshake.

## Cross-references

- **`qa-security-image-infra-scan`** — **the boundary partner.** Trivy **generates** the SBOM and owns
  **CVE scanning** (A03 Software Supply Chain Failures) for the image, OS packages, and IaC; this skill
  **signs and attests** what Trivy produced and owns **A08 Software and Data Integrity Failures**. Run
  both — authenticity and vulnerability are orthogonal.
- **`devops-iac-security`** — the beside-partner in the same Stage-1 lane: IaC misconfiguration +
  policy-as-code. It authors the admission policy; this skill supplies the verification rule inside it.
- **`devops-k8s-security`** — owns **admission enforcement** (`policy-controller` `ClusterImagePolicy`,
  Kyverno `verifyImages`, namespace opt-in labels, RBAC around the policy). The deploy-time verification
  gate is jointly owned: the *rule* is here, the *enforcement mechanism* is there.
- **`devops-container-runtime-security`** — the runtime half; a verified image can still be exploited once
  running.
- **`devops-cloud-posture`** — registry-level controls (ECR tag immutability, ACR locks, IAM on push) live
  in the cloud posture sweep; the *requirement* for them is stated here.
- **`devops-threat-modeling`** — STRIDE **T**ampering on the build pipeline is what motivates this whole
  skill; the threat model scopes which of the four surfaces a given system actually needs.
- **`devops-infra-controls-validation`** — validates that the CI/CD hardening controls named here are
  present *and effective*, and re-tests after remediation.
- **`devops/agents/infra-security-tester`** — the step-by-step orchestrator that loads this skill in its
  IaC-&-image-posture step and reports findings with their A08 / SLSA mapping.
- **`devops-docker`** — image build and `buildx --provenance/--sbom`; the image this skill signs is the one
  that skill authors. Base-image **digest pinning** is stated in both.
- **`devops/{github-actions,gitlab-ci,azure-pipelines}`** — the **deploy pipeline** that wires the
  build → scan → sign → attest → verify chain, the OIDC permissions block, and action pinning.
- **`devops-engineer`** — the peer that **applies** every fix this skill identifies (pipeline changes,
  registry settings, admission policy rollout). This skill does not edit infrastructure.
- **`devops-auditor`** — the static conformance sibling; its sections **G identity & credentials** and
  **I pinning & reproducibility** overlap this skill's build-integrity surface. Static rule-conformance
  stays with the auditor; *proving* a signature verifies (or does not) is here.
- `references/cosign-sigstore.md` · `references/slsa-provenance.md` · `references/dependency-integrity.md`
  — the deep dives.
