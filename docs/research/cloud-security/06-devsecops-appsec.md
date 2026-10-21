# M12 — Cloud Application Security & DevSecOps

Scope: course module **M12 (deep dive)** — cloud-native app attack surface, DevSecOps, CI/CD pipeline security, and the SAST/DAST/SCA/IaC-scan disciplines. **This is a cross-reference module, not a new-skill module.** The library already owns every discipline below (SAST, DAST, SCA, IaC-scan, CI/CD hardening, supply-chain). This KB documents the *mapping* from the course's language to the existing owning skills, and names the one-line cross-reference notes the plan's **G1** task should add so cloud-app-security points at the existing owners rather than duplicating them.

## Cloud application security fundamentals

What is actually different about securing an app once it runs in the cloud — the course framing, mapped to attack surface:

- **Ephemeral, immutable infrastructure.** Hosts, containers and function instances live for minutes, not months. The security unit is the *image / artifact / IaC definition*, not the running box — you cannot patch a host that will be gone before the ticket is triaged. Controls shift to build time (scan the image, sign the artifact) and to policy-as-code at deploy time. Runtime state is cattle; drift is a signal, not a fix target.
- **Shared responsibility moves up to the app layer.** The provider secures the hypervisor, physical network and managed-service control plane; **the customer always owns identity, data, app code, config and the IAM policies that wire services together.** The frequent breach cause is not a provider CVE — it is a customer misconfiguration: a public bucket, an over-broad IAM role, a secret in an env var, a security group open to `0.0.0.0/0`. "Secure by default" is the provider's floor, not the app's posture.
- **Cloud-native attack surface** — three expanding fronts:
  - **Serverless (FaaS):** no host to harden, so the surface is *function identity + event sources + dependencies*. Each function has its own execution role (over-privileged roles are the dominant risk), event-injection comes from any trigger (queue, object-created, HTTP, stream), and the `node_modules`/`site-packages` pulled at build time are the supply-chain door. No long-running process means traditional host EDR does not apply.
  - **Containers:** the image is a dependency bundle — base-image CVEs, OS packages, app libraries and any secret baked into a layer all ship together. Add orchestration risk (Kubernetes RBAC, pod security, exposed kubelet/dashboard, over-permissive `ServiceAccount` tokens) and the container-escape boundary.
  - **Managed services (PaaS / BaaS):** the vulnerability is the *configuration and the IAM edge*, not the service code — a managed DB reachable from the internet, a message bus with no auth, a storage account with anonymous read, a Key Vault with an over-broad access policy. The attack path is identity and network reachability between services, which classic app scanners never see.
- **Identity is the new perimeter.** East-west movement is IAM-role assumption and token theft, not port scanning. Every service-to-service hop is an authorization decision; the blast radius of a leaked credential is whatever its role can reach.

## DevSecOps

**Shift-left + security-as-code + a culture where security is everyone's shared, continuous responsibility rather than a gate at the end.**

- **Shift-left:** move each control as early in the lifecycle as it can meaningfully run, so defects are found by the author at the cost of minutes, not by a pen-tester weeks later at the cost of a release. Earlier = cheaper = fixed-in-context.
- **Security-as-code:** policies, scans, thresholds and guardrails are version-controlled, reviewed and executed automatically — Policy-as-Code (OPA/Rego, Conftest, admission controllers), pipeline scan steps, and IaC baselines live in the repo next to the app. Nothing depends on a human remembering a checklist.
- **Culture / process:** developers own the findings in their own PRs; security engineers build paved-road guardrails and tune signal, not manual approvals; failures are fast, local and actionable. The anti-pattern DevSecOps replaces is the end-of-cycle security *gate* that blocks the release and gets waived under deadline.
- **Where each control sits across the lifecycle** (the shift-left map):

  | Lifecycle stage | Control that belongs here |
  |---|---|
  | **IDE / pre-commit** | secret-scanning hooks, SAST-lite / linters, IaC linting |
  | **Commit / PR** | SAST (full), SCA (dependency), IaC-scan, secret-scan, license check |
  | **Build** | image/container scan, SBOM generation, artifact signing + provenance (SLSA) |
  | **Deploy (pre-prod)** | DAST, policy-as-code admission gates, config/posture check |
  | **Runtime / prod** | CSPM, runtime/CWPP, DAST on staging, drift detection, telemetry → the observability lane |

## CI/CD pipeline security

The pipeline is now a privileged production system: it holds cloud credentials, pulls untrusted dependencies and executes code from every contributor. It is a prime target. The reference threat model is the **OWASP Top 10 CI/CD Security Risks** (CICD-SEC-1…10).

**Attack classes to name:**

- **Poisoned Pipeline Execution (PPE)** *(CICD-SEC-4):* an attacker who can influence pipeline definition or the files it consumes gets their code to run inside the pipeline with its privileges. *Direct PPE* edits the pipeline config itself (a `Jenkinsfile`, a `.github/workflows/*.yml`); *Indirect PPE* poisons a file the pipeline runs (a `Makefile`, test script, build plugin). The classic vector is a workflow that runs untrusted PR code with access to secrets (e.g. `pull_request_target` misuse).
- **Dependency Chain Abuse / dependency confusion** *(CICD-SEC-3):* the build's `install` step is an execution point for untrusted code with the runner's secrets, cloud tokens and repo access. *Dependency confusion* exploits resolver precedence — a malicious **public** package published under the name of a private internal one gets pulled instead of the real one; typosquatting and malicious transitive deps are the siblings.
- **Secret exposure in CI** *(CICD-SEC-6, insufficient credential hygiene):* long-lived cloud keys stored as CI secrets, secrets echoed into logs, secrets readable by fork PRs, over-scoped tokens. The fix is fewer secrets, shorter lives, tighter scope — which OIDC delivers (below).
- **Runner / build-environment compromise** *(CICD-SEC-7):* shared or self-hosted runners that are not ephemeral let one job's artifacts, caches or processes poison the next. Self-hosted runners on public repos are directly reachable by fork PRs. Hardening: ephemeral single-use runners, no secrets at rest on the runner, network egress controls, least-privilege runner identity.
- **Insufficient flow control / inadequate IAM** *(CICD-SEC-1, -2):* missing branch protection, no required review, unprotected admin of the CI system itself.

**OIDC-to-cloud trust — the modern alternative to long-lived keys.** Instead of storing a static AWS/Azure/GCP key as a CI secret, the CI platform acts as an **OIDC identity provider**: each job requests a short-lived, job-scoped JWT; the cloud validates the JWT signature against the provider's public keys, checks its claims against a trust policy, and exchanges it for **short-lived, auto-rotated** cloud credentials. No secret is ever stored or duplicated.

- Per cloud: **AWS** IAM web-identity federation (trust policy with `sub`/`aud` conditions); **GCP** Workload Identity Federation provider; **Azure** federated identity credentials on an Entra app registration.
- **The single most important control is the subject-claim (`sub`) condition** in the trust policy — scope it to a specific repo **and** branch/environment, and never let `pull_request` / fork workflows assume a production role. Pair with GitHub Environment protection rules (required approval) for prod.

**Supply-chain integrity / SLSA.** [SLSA](https://slsa.dev) ("salsa") is the supply-chain-integrity framework; its **Build track** grades how tamper-resistant a build and its provenance are:

| Level | Requirement | Defends against |
|---|---|---|
| **Build L1** | Provenance exists documenting how the artifact was built (may be unsigned/incomplete) | mistakes, missing documentation |
| **Build L2** | Build runs on a **hosted** platform that produces **signed** provenance tied to its infrastructure | tampering **after** the build |
| **Build L3** | **Hardened, isolated** build platform; a build cannot forge its own provenance (signing keys unreachable to the build) | tampering **during** the build |

Implemented in practice with **SBOM** generation (CycloneDX / SPDX), **artifact signing** (Sigstore / cosign), and provenance attestations. L4 from the older SLSA drafts was dropped in v1.0; the current spec adds a **Source track** alongside Build.

## SAST / DAST / SCA / IaC security

The four scanning disciplines, where each sits, representative current tools, and **which existing library skill owns it** (the point of this KB). Skills live under `qa/{java,dotnet,typescript}/.../security-testing/` and `devops/`.

| Discipline | What it finds | Where in pipeline | Representative tools (current) | Existing owning skill |
|---|---|---|---|---|
| **SAST** (static) | Code-level flaws from source without running it — injection, unsafe deserialization, hardcoded secrets, taint flows | Commit / PR (and IDE) | **Semgrep** (CE) / **Opengrep** (2025 LGPL-2.1 community fork after Semgrep's license shift), CodeQL, SonarQube, Snyk Code | **`qa-{java,dotnet,typescript}:code-scan`** |
| **DAST** (dynamic) | Runtime vulns against a deployed app — reflected/stored XSS, auth/session flaws, server misconfig, injection as observed over HTTP | Deploy / pre-prod (staging), nightly | **OWASP ZAP** (Apache-2.0, Checkmarx-funded; v2.17 Dec 2025 — baseline scan on PR, full active scan nightly), **Nuclei** (template-based, CVEs/misconfig), Burp Suite | **`qa-{java,dotnet,typescript}:active-scan`** (full/authenticated) + **`:passive-scan`** (baseline/proxy) |
| **SCA** (software composition) | Known-vulnerable & malicious dependencies, transitive CVEs, license risk; feeds the SBOM | Commit / PR + build | **Trivy**, **OWASP Dependency-Check**, **Grype**, Snyk Open Source, GitHub Dependabot, `npm/pip/dotnet audit` | **`qa-{java,dotnet,typescript}:dependency-scan`** |
| **IaC / container security** | Misconfigured Terraform/CloudFormation/K8s/Helm/Dockerfile, insecure defaults, exposed resources, over-broad IAM; image CVEs + baked-in secrets | Commit / PR + build | **Trivy** (`trivy config`, `trivy image`), **Checkov** (Prisma/PAN), **Terrascan**; **tfsec is folded into Trivy** — README directs engineering attention to Trivy, legacy rule IDs map to Trivy AVD IDs | **`devops/iac-security`** (IaC config) + **`qa-*:image-infra-scan`** (container/image) |
| **Supply-chain / provenance** | Unsigned artifacts, missing SBOM, no provenance, tampering in the build path (SLSA grading) | Build | Sigstore/**cosign**, SLSA provenance generators, CycloneDX/SPDX SBOM tooling, Dependency-Track | **`devops/supply-chain-security`** |

Notes that matter for citing tools:
- **Opengrep** is the LGPL-2.1 community fork of Semgrep's OSS engine, launched early 2025 by a consortium (Aikido, Endor Labs, Jit, Orca, …) after Semgrep renamed the free tool to Community Edition and moved features (cross-file taint, fingerprinting) behind its commercial platform. Name both; treat as drop-in rule-compatible.
- **tfsec** is not dead but is in maintenance — new misconfiguration rules land in **Trivy**, not tfsec. Prefer `trivy config`; keep tfsec only as a legacy mention.
- **ZAP** remains Apache-2.0 and free; the three project leads were hired by Checkmarx (Sep 2024) and it continues as an active OSS project.

## How it feeds our cross-references

The plan's **G1** task adds these exact one-line notes (no new skill content — pointers only). Each tells the cloud-app-security reader which existing skill already owns the discipline, so M12 resolves to real owners.

Into **`devops/iac-security`** (add a "Cloud application security (M12) cross-references" note):
- `Cloud-native IaC/config scanning is this skill. Prefer \`trivy config\`; tfsec is folded into Trivy (legacy rule IDs map to Trivy AVD). Checkov and Terrascan are the alternatives.`
- `Container/image scanning (base-image CVEs, baked-in secrets) is owned by \`qa-{java,dotnet,typescript}:image-infra-scan\`, not here.`
- `Artifact signing, SBOM and SLSA provenance are owned by \`devops/supply-chain-security\`.`

Into the **DevSecOps / CI-CD lane** (the `devops` pipeline-security surface):
- `SAST → \`qa-{java,dotnet,typescript}:code-scan\` (Semgrep/Opengrep, CodeQL). Runs at commit/PR.`
- `DAST → \`qa-{java,dotnet,typescript}:active-scan\` (full/authenticated) and \`:passive-scan\` (baseline/proxy) — OWASP ZAP, Nuclei. Runs against staging/pre-prod.`
- `SCA/dependency → \`qa-{java,dotnet,typescript}:dependency-scan\` (Trivy, OWASP Dependency-Check, Grype). Runs at commit/PR + build.`
- `IaC config → \`devops/iac-security\`; supply-chain/provenance/SLSA → \`devops/supply-chain-security\`.`
- `CI/CD pipeline threat model is the OWASP Top 10 CI/CD Security Risks (PPE = CICD-SEC-4, dependency confusion = CICD-SEC-3). Prefer OIDC-to-cloud federation over long-lived CI keys; scope the trust policy's \`sub\` claim to repo+branch/environment.`

Into **`cloud-security`** (this KB's own module, as the catalog entry): `M12 is a cross-reference module — it owns no scanner. It maps to \`qa-*:{code-scan,active-scan,passive-scan,dependency-scan,image-infra-scan}\` and \`devops/{iac-security,supply-chain-security}\`.`

## Sources

- SLSA v1.0 Build track levels — https://slsa.dev/spec/v1.0/levels ; current spec https://slsa.dev/spec/v1.2/build-track-basics
- OWASP Top 10 CI/CD Security Risks — https://owasp.org/www-project-top-10-ci-cd-security-risks/
- OWASP CI/CD Part 4 — Poisoned Pipeline Execution (PPE) — https://cloudsmith.com/blog/owasp-ci-cd-part-4-poisoned-pipeline-execution-ppe
- GitHub Actions OIDC — generally available (short-lived auto-rotated tokens) — https://github.blog/security/supply-chain-security/secure-deployments-openid-connect-github-actions-generally-available/
- GitHub Actions OIDC federation across AWS/GCP/Azure — https://www.scrambleid.com/learn/github-actions-oidc-federation-across-clouds
- Opengrep — fork of Semgrep after license shift — https://devops.com/endor-labs-forks-semgrep-to-opengrep-for-static-code-analysis/ ; https://thenewstack.io/opengrep-launches-as-free-fork-after-semgrep-license-shift/
- tfsec folded into Trivy — https://github.com/aquasecurity/tfsec ; https://appsecsanta.com/iac-security-tools/tfsec-vs-trivy
- OWASP ZAP status (Checkmarx-funded, v2.17 Dec 2025) & Nuclei — https://www.appsecsanta.com/owasp-zap ; https://www.appsecsanta.com/dast-tools
