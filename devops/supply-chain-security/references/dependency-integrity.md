# Dependency integrity — confusion, typosquats, and pinning

The output-side controls (cosign, SLSA) prove *your* build is intact. This is the **input** side: proving what
you pulled in is what you meant to pull in. Two attacker moves dominate — **dependency confusion** (publishing
a public package with the name of your *internal* one at a higher version, so the resolver prefers it) and
**typosquatting** (`reqeusts`, `lodahs` — a name a hair off a popular one). Both are OWASP **A03 Software
Supply Chain Failures**; the mitigations are configuration and pinning, not a scanner you run once.

## Dependency confusion — the config fix, per ecosystem

The root cause is a resolver that queries multiple indexes and takes the **highest version** with no notion of
a *trusted source per package*. The fix is to make the source unambiguous.

**npm** — scope internal packages and pin the scope to your registry:

```ini
# .npmrc — the @myorg scope ONLY ever resolves from the internal registry.
@myorg:registry=https://npm.internal.myorg.com
//npm.internal.myorg.com/:_authToken=${NPM_TOKEN}
registry=https://registry.npmjs.org        # everything else from the public registry
```

- Unscoped internal package names are the vulnerability — anyone can publish `myorg-utils` publicly. **Scope
  every internal package** (`@myorg/utils`) and reserve the scope on the public registry so the name can't be
  squatted.

**Python / pip** — the trap is `--extra-index-url`:

```bash
# WRONG — pip queries BOTH indexes and takes the highest version from EITHER. Confusion by config.
pip install -i https://pypi.org/simple --extra-index-url https://pypi.internal.myorg.com/simple mypkg

# RIGHT — a single index pointed at an internal proxy that mirrors upstream and decides per-package.
pip install --index-url https://pypi.internal.myorg.com/simple mypkg
```

Use one `--index-url` to an internal proxy (Artifactory / Nexus / a devpi) that mirrors PyPI and enforces the
per-package source. `--extra-index-url` is dependency confusion as a setting.

**NuGet** — map package-source patterns so `MyOrg.*` can only come from the internal feed:

```xml
<!-- nuget.config -->
<packageSourceMapping>
  <packageSource key="internal">
    <package pattern="MyOrg.*" />
  </packageSource>
  <packageSource key="nuget.org">
    <package pattern="*" />
  </packageSource>
</packageSourceMapping>
```

## Typosquat + malicious-package detection

```bash
# `confused` — checks your manifests for names NOT present on the public registry (i.e. internal names an
# attacker could claim). Run per ecosystem; gate on a non-empty result.
confused -l npm package-lock.json         # also: pip, composer, mvn, rust
confused -l pip requirements.txt
```

- **`confused`** flags internal package names that don't exist publicly — the exact set an attacker would
  register for a confusion attack. A non-empty list is a "reserve these names now" action, not a build break
  by itself.
- **Name-similarity + publish-anomaly feeds** (Socket, OSV malicious advisories, GitHub Advisory) catch
  typosquats and known-malicious versions the moment they're flagged. Wire the OSS ones as an advisory gate
  alongside the SCA `dependency-scan`.
- **OSSF Scorecard** grades an OSS dependency's *repo* on integrity signals worth gating on:
  `Pinned-Dependencies`, `Signed-Releases`, `Dangerous-Workflow`, `Branch-Protection`, `Maintained`. A
  dependency scoring low on `Pinned-Dependencies` is one whose own supply chain is soft.

## Pinning — the backstop under everything

Confusion and typosquats both exploit *version float*. Pinning removes the float:

```bash
# Lockfiles committed AND enforced — resolve nothing at CI time.
npm ci                                    # not `npm install` — installs the lockfile exactly
pip install --require-hashes -r requirements.txt    # hashes, not just versions
```

- **Commit the lockfile and install *from* it** (`npm ci`, `pip --require-hashes`, `--frozen-lockfile`) so CI
  never silently resolves a new version. This is the library's pinning invariant applied to app deps.
- **Hash-pin** where the ecosystem supports it (`--require-hashes`, `integrity` in `package-lock.json`,
  `<PackageReference>` with a lockfile) — a hash mismatch fails the install, which catches a repointed version
  a version pin alone would accept.
- **Pin third-party CI actions by full commit SHA, not tag**, in a high-assurance pipeline: a tag is mutable,
  and a compromised action tag (the KICS Action compromise of March 2026 is the recent case) runs in your
  build with your secrets. `uses: actions/checkout@<40-char-sha>  # v5.0.0`.

## The runbook — reserve the namespace

1. Enumerate internal package names (`confused` output + your manifests).
2. **Register each name on the public registry** as a placeholder you own (an empty `@myorg`-scoped stub, or a
   reserved PyPI/NuGet name) so no attacker can claim it.
3. Scope + source-map internal packages (above) so even a claimed public name can't win resolution.
4. Commit lockfiles, enforce `ci`/`--require-hashes`, SHA-pin actions.
5. Gate `confused` + the advisory feed in the **deploy pipeline**; re-run on every dependency change.

## Cross-references

- `../SKILL.md` — the router; this owns the "did we pull in what we meant to" (dependency confusion /
  typosquat) row and the pinning invariant.
- `cosign-sigstore.md` · `slsa-provenance.md` — the output-side integrity controls (your build); this is the
  input side.
- `qa-security-testing-dependency-scan-{java,dotnet,typescript}` — the SCA sibling that gates *known CVEs* in
  the same dependency graph; this lane gates *integrity* (confusion, squats, pinning). Run both.
- `devops/{github-actions,gitlab-ci,azure-pipelines}` — where action-SHA pinning and the internal-proxy
  registry config live.
