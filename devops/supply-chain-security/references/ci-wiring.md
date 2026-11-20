# CI wiring — build, scan, sign, attest, verify

Signing and attestation happen in the build and deploy pipeline owned by `devops/{github-actions,gitlab-ci,azure-pipelines}`, not the `qa/cicd/*` test lane: the test lane runs the suite and publishes Allure; the deploy lane builds, scans, signs, attests and gates. Pins match `../SKILL.md` Setup.

```yaml
name: Build · Scan · Sign · Attest
on:
  push:
    tags: ['v*']

permissions: {}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
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
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: push
        run: |
          docker buildx build --push \
            --platform linux/amd64,linux/arm64 \
            --provenance=mode=max --sbom=true \
            --tag ghcr.io/myorg/api:${{ github.ref_name }} \
            --metadata-file meta.json .
          echo "digest=$(jq -r '."containerimage.digest"' meta.json)" >> "$GITHUB_OUTPUT"
      - uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: image
          image-ref: ghcr.io/myorg/api@${{ steps.push.outputs.digest }}
          exit-code: '1'
          severity: HIGH,CRITICAL
          ignore-unfixed: true
          format: cyclonedx
          output: sbom.cdx.json
      - run: cosign sign --yes ghcr.io/myorg/api@${{ steps.push.outputs.digest }}
      - run: |
          cosign attest --yes --type cyclonedx --predicate sbom.cdx.json \
            ghcr.io/myorg/api@${{ steps.push.outputs.digest }}
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
      - run: |
          cosign verify ghcr.io/myorg/api@${{ needs.build.outputs.digest }} \
            --certificate-identity-regexp '^https://github\.com/myorg/api/\.github/workflows/release\.yml@refs/tags/v.+$' \
            --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'
```

- The CVE gate and SBOM generation are `qa-<stack>:image-infra-scan`'s job; it hands this pipeline `sbom.cdx.json`.
- Sign the digest, never the tag: a tag can be re-pointed after signing.
- Provenance is Build L2 here, and L3 once this job body moves into a reusable workflow.
- `mode=max` provenance gives Build L1 with no further step.
- The deploy job is the gate: it refuses anything this pipeline did not sign.
