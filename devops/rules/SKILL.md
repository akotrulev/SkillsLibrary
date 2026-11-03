---
name: rules
description: Use when installing or updating the devops standards as path-scoped rules in .claude/rules/devops/. Triggers "install the devops rules". Not for auditing infrastructure (devops-auditor).
disable-model-invocation: true
---

# Install the devops rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a backend session that edits a Dockerfile gets the image rules without loading the devops agent, and a session that never touches Terraform never pays for the IaC rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `devops.md`: lane detection, no static credentials, pinning, secrets, change safety | any Dockerfile, compose file, manifest, IaC file or pipeline the files below match (not config files) |
| `docker.md`: stages, non-root, health, layers, `.dockerignore`, compose | `Dockerfile*`, `*.Dockerfile`, `.dockerignore`, `*compose*.yml` / `.yaml` |
| `kubernetes.md`: resources, probes, security context, isolation, identity, availability | YAML under `k8s/`, `kubernetes/`, `manifests/`, `deploy/`, `charts/`, `helm/`, `overlays/`; `kustomization.yaml` |
| `iac.md`: state, modules, tags, deletion protection, exposure, suppressions | `*.tf`, `*.tfvars`, `*.bicep`, `*.bicepparam`, `.terraform.lock.hcl` |
| `pipelines.md`: permissions, action pinning, deploy gating, secrets scope, image and IaC jobs | `.github/workflows/`, `.github/actions/`, `.gitlab-ci.yml`, `.gitlab/ci/`, `azure-pipelines*.yml`, `.azure-pipelines/`, `.azuredevops/` |
| `config.md`: config layers, committed vs ignored env files, store per environment | `.env*`, `appsettings*.json`, `application*` / `bootstrap*` `.yml` `.yaml` `.properties` |

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/devops/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all six rule files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/devops` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to where this project keeps its infrastructure.** Kubernetes YAML has no fixed location, and pipeline templates often live outside the default folders.
   - **Manifests**: `git grep -l -E '^(apiVersion|kind):' -- '*.yml' '*.yaml'`, plus `git ls-files '*Chart.yaml' '*kustomization.y*ml' '*.tpl'`. Drop CI files, compose files and anything already matched. For each folder left (for example `ops/apps/`, `platform/`), propose a glob such as `"ops/apps/**/*.{yml,yaml}"` for `kubernetes.md`. Name YAML the grep found that is not a manifest (a CRD-shaped test fixture, an OpenAPI file) so it is left out, and name any default folder (`deploy/`) that here holds YAML which is not Kubernetes, so its glob can be narrowed.
   - **Pipeline templates**: the files an existing pipeline pulls in, from `git grep -h -E '^\s*-?\s*(template|local):' -- '*.yml' '*.yaml'` (Azure `- template:`, GitLab `include: local:`). Propose a folder glob for `pipelines.md` for any that sit outside the defaults.
   - **Images**: `git ls-files '*Dockerfile*' '*.dockerfile' '*compose*.y*ml'`; propose a glob for any image file the defaults miss.
   - **Pulumi**: when `Pulumi.yaml` exists, say these rules have no Pulumi file; offer to add the program's folder to `devops.md` only, so the credential, pinning and secrets rules apply there.
   - Every glob added to `kubernetes.md`, `docker.md` or `pipelines.md` is added to `devops.md` too, because the core's paths are their union.
   Change the installed copies only with the user's agreement.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/devops/devops.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for overlaps and conflicts.** List the other plugins' folders in `<root>/.claude/rules/`. Several share files with these rules and agree with them: the qa plugins' CI rules load on the same pipeline files and govern test-suite jobs while `pipelines.md` governs build and deploy jobs; be-python's container rules load on the same Dockerfiles and are stricter for the worker image; the backend plugins' config rules add framework detail to `config.md`. Then read the project's `CLAUDE.md` (root and `.claude/`) for infrastructure rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
devops rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/devops/
Paths widened: none | <file>: <globs>   (and devops.md)
Committed: yes | ignored by git
Other rule sets loading on the same files: none | <plugin>: <files>
Conflicts with CLAUDE.md: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
