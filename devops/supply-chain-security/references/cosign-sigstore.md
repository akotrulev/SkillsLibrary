# cosign / sigstore — keyless signing, verification, and attestation

**cosign** (Sigstore) signs and verifies OCI artifacts — images, SBOMs, blobs — and attaches attestations.
Its distinctive mode is **keyless signing**: instead of a long-lived private key, cosign gets a **short-lived
certificate from Fulcio** bound to an **OIDC identity** (a GitHub Actions token, a Google/GitLab identity),
signs the artifact's **digest**, and records the signature in **Rekor**, the public transparency log. No key
to store, leak, or rotate — the identity *is* the key, which is exactly why it satisfies the library's
no-static-credentials invariant. Pin everything: `cosign@v3.1.3`, `sigstore/cosign-installer@v4` (the v3
installer cannot install the cosign v3 line), `slsa-verifier@v2.7.1`.

## The keyless flow — what actually happens

1. The pipeline authenticates to an OIDC issuer (GitHub's `id-token: write` mints the token).
2. cosign exchanges that token with **Fulcio** for a ~10-minute X.509 certificate binding the OIDC identity
   (the workflow's `subject`/`issuer`) to an ephemeral keypair.
3. cosign signs the artifact **digest** (never the tag — a tag is mutable, a digest is the content) and pushes
   the signature to **Rekor**, the append-only transparency log.
4. The ephemeral key is discarded. Verification later re-reads the Rekor entry to prove the signature existed
   while the certificate was valid — which is what makes a 10-minute cert usable forever.

## Sign

```bash
# Keyless is the default in cosign v2+. --yes skips the interactive OIDC confirmation (required in CI).
cosign sign --yes myorg/api@sha256:<digest>

# Always sign the DIGEST, not the tag. Resolve it first if you only have a tag.
DIGEST=$(cosign triangulate --type digest myorg/api:1.4.2 2>/dev/null || \
         crane digest myorg/api:1.4.2)
cosign sign --yes "myorg/api@${DIGEST}"
```

Signing a **tag** is the single most common cosign mistake: the tag can be repointed to a different image
after signing, so the signature proves nothing. Sign `name@sha256:…`.

## Verify — the gate (identity is the whole point)

```bash
# Verify a keyless signature. BOTH flags are mandatory — a signature with no identity constraint
# only proves "someone signed it", not "OUR pipeline signed it".
cosign verify \
  --certificate-identity-regexp '^https://github.com/myorg/.+/\.github/workflows/.+@refs/heads/main$' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  myorg/api@sha256:<digest>
```

- **`--certificate-identity` (or `-regexp`) and `--certificate-oidc-issuer` are not optional.** cosign v2
  *fails closed* if you omit them, and rightly so: verifying without pinning the identity accepts any
  Sigstore-signed image on earth. Pin the exact workflow path and ref.
- **cosign v2 → v3 breaking changes** to expect on migration: `--bundle` is now **required** for offline/
  air-gapped verification, and the default output/attachment format shifted to the bundle spec. Pin the cosign
  major and migrate deliberately.

## Attest — bind a statement (SBOM, provenance) to the artifact

```bash
# Attach an SBOM as an in-toto attestation, keyless.
cosign attest --yes --type cyclonedx --predicate sbom.cdx.json myorg/api@sha256:<digest>

# Verify the attestation, pinning identity AND predicate type.
cosign verify-attestation \
  --type cyclonedx \
  --certificate-identity-regexp '^https://github.com/myorg/.+@refs/heads/main$' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  myorg/api@sha256:<digest>
```

An **attestation** is a signed, typed statement *about* the artifact (its SBOM, its SLSA provenance, a vuln
scan result) — the integrity layer on top of the SBOM that Trivy *generates*. Trivy produces the SBOM; cosign
`attest` signs and binds it to the digest; `verify-attestation` proves at deploy time that the SBOM is the one
for this exact image. That handoff is the fence with `qa-security-image-infra-scan`.

## Enforce at admission — sigstore policy-controller

Verification is only a control if something **blocks** an unsigned image from running. In Kubernetes that is
the **policy-controller** admission webhook, which rejects images whose signature/identity does not match a
`ClusterImagePolicy`:

```yaml
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata: { name: require-signed-myorg }
spec:
  images:
    - glob: "myorg/**"
  authorities:
    - keyless:
        url: https://fulcio.sigstore.dev
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subjectRegExp: '^https://github.com/myorg/.+@refs/heads/main$'
```

Deploying the webhook is an **enforcement change to a live cluster** — it belongs to `devops-engineer`, not to
a read-only assessment. This lane *verifies signatures exist and identities are pinned*; the engineer stands
up the gate. (AWS-native alternative: an ECR + Notation/Kyverno path; note it, same shape.)

## CI wiring (GitHub Actions)

```yaml
permissions:
  id-token: write        # OIDC token for keyless signing — the ONLY credential needed
  packages: write
steps:
  - uses: sigstore/cosign-installer@v4      # v4 for the cosign v3 line
    with: { cosign-release: 'v3.1.3' }
  - run: cosign sign --yes "myorg/api@${DIGEST}"
```

No `COSIGN_PRIVATE_KEY` secret exists in this design — the presence of one is a finding, because it re-
introduces the long-lived key keyless signing exists to remove. Signing runs in the **deploy pipeline**, never
the `qa/cicd/*` test lane.

## Cross-references

- `../SKILL.md` — the router; cosign owns the "did *we* produce this exact digest" (artifact signing) row.
- `slsa-provenance.md` — what to put *inside* the attestation: SLSA build provenance, verified with
  `slsa-verifier`, not merely checked for existence.
- `dependency-integrity.md` — the input side (dependency-confusion / typosquat); cosign secures the output
  artifact.
- `qa-security-image-infra-scan` — Trivy **generates** the SBOM; cosign **signs and binds** it. The boundary.
- `devops-kubernetes` — where `devops-engineer` deploys the policy-controller admission gate this lane
  recommends.
