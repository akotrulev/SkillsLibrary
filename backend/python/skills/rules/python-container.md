---
paths:
  - "**/Dockerfile*"
  - "**/*.Dockerfile"
  - "**/*compose*.{yml,yaml}"
---

<!-- be-python rules v1 (2026-11-03): worker container. Installed by /be-python:rules; narrow the paths above to the worker's Dockerfile and compose file when the repo builds other images. -->

# Sandboxed worker container standards

Severity tags as in the core Python rules. These apply to the upload worker's image and service, not to other images in the repo.

- No outbound route at runtime: `network_mode: none`, or an `internal: true` network proved by a CI check that tries to connect out and expects failure. No `network_mode: host`, `hostNetwork` or `ports:` on the worker. *blocker*
- No `--privileged` and no `/var/run/docker.sock` mount. *blocker*
- Non-root numeric UID, `read_only: true`, `cap_drop: [ALL]`, `no-new-privileges`, scratch on `tmpfs` with `noexec`. *major*
- Model weights are baked at build and verified by a pinned `sha256`; a wrong digest fails the build, and nothing downloads at runtime. No `HEALTHCHECK` that runs inference. *major*
- Base `python:3.x-slim`, never alpine (no musl onnxruntime wheels); `uv` pinned by tag. *major*
- Multi-stage: no `pip install` or compiler in the runtime stage, no `apt-get` beyond what a wheel provably needs. *major*
- Memory, CPU, wall clock and concurrency limits are set here or in the manifest and reach Python through `Settings`, never hard-coded. *major*
- One directory per job, deleted with it; no writable volume shared between jobs. *major*
