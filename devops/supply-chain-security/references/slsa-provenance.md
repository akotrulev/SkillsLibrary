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

## Generate — the isolated builder

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
# slsa-verifier checks the provenance: correct builder, correct source repo, digest match. Pin it.
slsa-verifier verify-image "myorg/api@sha256:<digest>" \
  --source-uri github.com/myorg/api \
  --builder-id 'https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@refs/tags/v2.1.0'
```

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

## Cross-references

- `../SKILL.md` — the router; SLSA owns the "how was this built, and can we prove it" (build provenance) row.
- `cosign-sigstore.md` — the signing/attestation transport and the admission-gate enforcement.
- `dependency-integrity.md` — provenance covers *your* build; dependency integrity covers what you pulled in.
- `qa-security-image-infra-scan` — the SBOM generator SLSA provenance is often bundled with.
- `devops/{github-actions,gitlab-ci,azure-pipelines}` — where the isolated builder and the verify gate are
  wired (the deploy pipeline, not `qa/cicd/*`).
