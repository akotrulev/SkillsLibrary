# SLSA provenance — attest and verify how the artifact was built

**SLSA** (Supply-chain Levels for Software Artifacts, "salsa") is a framework for **build integrity**: it
answers *"was this artifact built by the pipeline we think, from the source we think, without tampering?"*
The evidence is **provenance** — a signed, machine-readable in-toto attestation the build system emits,
recording the builder identity, the source repo + commit, the build parameters, and the resulting artifact
digest. The control is not "we have provenance" but **"we verify the provenance and reject anything whose
provenance doesn't match"** — a document generated and never checked is theater.

## The levels (SLSA v1.0) — what each buys

| Level | Requirement | What it stops |
|---|---|---|
| **L1** | Provenance exists and is distributed | Nothing on its own — but you can now *see* how things were built |
| **L2** | Provenance is **signed** by the build platform; build runs on a hosted service | A developer forging provenance by hand |
| **L3** | **Non-falsifiable** provenance — the build runs in an isolated, ephemeral environment the build script cannot tamper with | A compromised build step forging its own provenance (the SolarWinds class) |

Target **L3** for anything you ship. On GitHub, the `slsa-github-generator` reusable workflow produces L3
provenance because it runs the provenance generation in a separate, isolated job the build cannot reach.

## Generate — three paths, in increasing assurance

**Path A: buildx inline provenance (Build L1).** `mode=max` records the build steps and materials; the default `mode=min` records almost nothing useful. See `devops:docker`.

```yaml
- run: |
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      --provenance=mode=max --sbom=true \
      --tag ghcr.io/myorg/api:${{ github.sha }} --push .
```

**Path B: GitHub artifact attestations (Build L2; L3 with a reusable workflow). The default choice.**

```yaml
permissions:
  id-token: write
  attestations: write
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
```

**Path C: slsa-github-generator (Build L3 by construction).** The build definition lives in a vetted, reusable, non-user-modifiable workflow, and the signing material is unreachable from user build steps.

```yaml
# .github/workflows/release.yml — L3 provenance via the reusable generator.
jobs:
  build:
    outputs:
      digest: ${{ steps.build.outputs.digest }}
    steps:
      - id: build
        run: |
          docker build -t myorg/api .
          echo "digest=$(docker push myorg/api | awk '/digest:/{print $3}')" >> "$GITHUB_OUTPUT"

  provenance:
    needs: [build]
    permissions:
      id-token: write          # OIDC — the generator signs keyless, no stored key
      packages: write
      actions: read
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.1.0
    with:
      image: myorg/api
      digest: ${{ needs.build.outputs.digest }}
```

The provenance is signed keyless (Fulcio + Rekor, the same trust root as cosign) and bound to the **digest**.
Pin the generator by tag/SHA — an unpinned reusable workflow is the exact supply-chain hole this lane exists
to close.

## Verify — the gate that makes it real

```bash
gh attestation verify "oci://ghcr.io/myorg/api@$DIGEST" --repo myorg/api

cosign verify-attestation "ghcr.io/myorg/api@$DIGEST" \
  --type slsaprovenance \
  --certificate-identity-regexp '^https://github\.com/myorg/api/\.github/workflows/release\.yml@refs/.+$' \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

slsa-verifier verify-image "myorg/api@sha256:<digest>" \
  --source-uri github.com/myorg/api \
  --builder-id 'https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@refs/tags/v2.1.0'
```

Path B verifies with `gh attestation verify`, Path C with `slsa-verifier`; any path's attestation is also a cosign-verifiable in-toto statement. Assert on the predicate's source repo and builder, not merely that a document exists.

- `--source-uri` pins **which repo** was allowed to produce this artifact — the check that stops a fork or an
  unrelated repo from shipping under your name.
- `--builder-id` pins **which builder** — the check that enforces the L3 isolated builder was actually used,
  not a hand-rolled job.
- The verification is the control. Wire it as a **deploy-time gate** (or fold it into the cosign
  `verify-attestation` step, since SLSA provenance is an in-toto attestation cosign can also verify). An
  artifact that fails verification never deploys.

## Where it sits relative to cosign and Trivy

- **Trivy** generates the SBOM (what's *in* the artifact) and finds CVEs.
- **cosign** signs the artifact and attaches attestations (proves *we* produced this digest).
- **SLSA provenance** records and proves *how* it was built (which builder, which source, which parameters) —
  the build-integrity layer. cosign is often the transport (`cosign attest --type slsaprovenance`), SLSA is
  the predicate.

Together they answer the three A08 questions: *is it ours* (cosign), *how was it built* (SLSA), *what's in it*
(Trivy SBOM). Run all three; each is blind to the others' surface.

## What the levels need in practice

At L2 a malicious build step can still forge its own provenance, because it runs in the same job that holds the signing token. L3 moves the build definition out of the repo (a shared reusable workflow, vetted centrally) and isolates the signing material from user-controlled steps. GitLab runs the same shape with an `id_tokens:` block minting the OIDC token cosign consumes; Azure Pipelines uses a workload-identity-federation service connection.

## Finding → framework mapping

| This skill's finding | OWASP Top 10:2025 | SLSA | Other |
|---|---|---|---|
| Unsigned artifact deployed | **A08** | Build L2 unmet | CIS SSC 4.x |
| No build provenance | **A08** | Build L1 unmet | NIST SSDF PO.3 / PS.3 · EO 14028 |
| Provenance forgeable by a build step | **A08** | Build L3 unmet | SLSA threat "forged provenance" |
| Dependency confusion / typosquat exposure | **A08** (+ **A03** where it lands a vulnerable dep) | — | NIST SSDF PW.4 · Scorecard `Pinned-Dependencies` |
| Floating tags / unpinned actions | **A08** | Build L1–L2 unmet | Scorecard `Pinned-Dependencies` |
| No verification at deploy | **A08** | the whole ladder unenforced | CIS K8s 5.x (admission) |

## Cross-references

- `../SKILL.md` — the router; SLSA owns the "how was this built, and can we prove it" (build provenance) row.
- `cosign-sigstore.md` — the signing/attestation transport and the admission-gate enforcement.
- `dependency-integrity.md` — provenance covers *your* build; dependency integrity covers what you pulled in.
- `qa-<stack>:image-infra-scan` — the SBOM generator SLSA provenance is often bundled with.
- `devops/{github-actions,gitlab-ci,azure-pipelines}` — where the isolated builder and the verify gate are
  wired (the deploy pipeline, not `qa/cicd/*`).
