---
paths:
  - "**/Dockerfile*"
  - "**/*.Dockerfile"
  - "**/.dockerignore"
  - "**/*compose*.{yml,yaml}"
---

<!-- devops rules v1 (2026-11-03): images. Installed by /devops:rules; edit the paths above to fit this project. -->

# Container image standards

Severity tags as in the core devops rules. Where a stack plugin's container rules govern one image (be-python's sandboxed worker), they add to these and their stricter choice wins for that image.

- Multi-stage: the build stage compiles; the runtime stage is a runtime image carrying only the artifact, never `*-sdk` or `*-jdk`. *major*
- The runtime stage runs as a non-root user (chiseled and `nginx-unprivileged` images already do). *major*
- Health is declared: the service exposes `/health`, and a `HEALTHCHECK` exists only where the image has a tool to run it. On chiseled, distroless or curl-less images use the platform probe or an exec-form probe binary, never a shell-form probe that reports unhealthy forever. *major*
- `CMD`/`ENTRYPOINT` in exec form, so signals reach the process; Node runs under an init such as tini. *major*
- Copy the dependency manifests and lockfile, restore with a cache mount, then copy the source; `COPY . .` before the restore defeats layer caching. *minor*
- `apt-get install --no-install-recommends` and `rm -rf /var/lib/apt/lists/*` in the same `RUN`; never `apt` and `apk` in one image. *minor*
- No `.env` or secret file copied into an image, and no secret passed as a build arg. *blocker*
- No `ADD <url>` without a checksum. *major*
- `.dockerignore` keeps the context small and secret-free: `.git`, `node_modules`, `bin`/`obj`, coverage, `.env`. *minor*
- OCI labels: `org.opencontainers.image.{title,description,source,version,revision,licenses}`. *nit*
- An app image over 1 GB is a misconfigured build (an SDK base, dev dependencies, extra packages). *minor*
- A compose service follows the same rules: pinned `image:`, non-root `user:`, secrets from an uncommitted env file or the store. *major*
