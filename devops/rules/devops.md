---
paths:
  - "**/Dockerfile*"
  - "**/*.Dockerfile"
  - "**/*compose*.{yml,yaml}"
  - "**/{k8s,kubernetes,manifests,deploy,charts,helm,overlays}/**/*.{yml,yaml}"
  - "**/kustomization.{yml,yaml}"
  - "**/*.{tf,tfvars,bicep,bicepparam}"
  - ".github/workflows/*.{yml,yaml}"
  - ".github/actions/**/action.{yml,yaml}"
  - "**/.gitlab-ci.yml"
  - "**/.gitlab/ci/**/*.{yml,yaml}"
  - "**/azure-pipelines*.{yml,yaml}"
  - "**/{.azure-pipelines,.azuredevops}/**/*.{yml,yaml}"
---

<!-- devops rules v1 (2026-11-03): core. Installed by /devops:rules; its paths are the union of the image, Kubernetes, IaC and pipeline files, so widen it whenever you widen one of those. -->

# Delivery infrastructure standards

Apply these to every Dockerfile, compose file, manifest, IaC file and pipeline you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Image, Kubernetes, IaC, pipeline and config rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the lane before writing: the service's runtime (TFM in `*.csproj`, JDK and Spring Boot BOM in `build.gradle(.kts)`/`pom.xml`, Node major in `engines`/`packageManager`), the CI host, the cloud and the IaC tool already in the repo. Never put a base image or a CI job on a newer runtime than the project targets, and never flag a down-level project for lacking an up-level feature.

## Identity and credentials (first invariant)

- No static cloud credential anywhere: not in code, an image, a compose file, a manifest, an IaC input, a pipeline variable or a Kubernetes `Secret`. Pipelines reach the cloud through OIDC / Workload Identity Federation; workloads through Managed Identity, IRSA, a task or execution role, or Workload Identity. *blocker*
- A federated trust names the repository **and** the branch, tag or environment, never `*`. *blocker*
- Least privilege: no `Action: "*"` with `Resource: "*"`, no `Owner` for a deploy or runtime identity; grant the actions the job needs on the resources it touches. *major*
- Signing is keyless (OIDC). A long-lived signing key in CI secrets is a static credential. *blocker*

## Pinning and reproducibility (second invariant)

- Base and job images by exact tag or digest, never `:latest` or a bare major; what is deployed is an immutable tag (`:sha-<commit>`) or a digest. *blocker in production, major elsewhere*
- CI actions, tasks, reusable workflows, templates and `include:` refs are pinned: never `@main`, `@master` or `@*`. *major*
- Terraform providers and modules carry version constraints, and `.terraform.lock.hcl` is committed. *major*
- Runtime and package-manager versions come from the project (`global.json`, the Gradle toolchain, `engines`, `packageManager`) and are never pinned a second time in CI or a Dockerfile. *major*
- Lockfiles are committed and every install is locked (`npm ci`, `pnpm install --frozen-lockfile`, `dotnet restore --locked-mode`, Gradle dependency verification). *major*
- Every tool a pipeline runs (scanner, linter, CLI) is pinned to an exact version. *major*

## Secrets

- No secret in any committed file: a Dockerfile `ARG`/`ENV`, compose `environment:`, a manifest, an IaC default or `*.tfvars`, pipeline YAML. Reference the secret store. *blocker*
- A secret is resolved at runtime from the store by the workload's identity. A value pasted into deployment YAML or a pipeline variable is configuration, not a secret store. *major*
- Terraform state and `terraform plan` output contain secrets: never committed, never a public artifact, never echoed to a log. *blocker*

## Change safety

- Nothing is changed by hand in a cloud portal or with `kubectl patch`; every change is a reviewed change to these files, and drift is reconciled by codifying or reverting it. *major*
- One deployer per target: a cluster is applied by CI or reconciled by GitOps, never both; infrastructure by one IaC tool, never Bicep and Terraform on the same resources. *major*
