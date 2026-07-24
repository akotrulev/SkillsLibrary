---
name: devops-docker
description: Use when the user asks to author or improve Dockerfiles / container images for .NET (8/9/10) / Java 21 / Node 22-24 services, build multi-stage images, choose a base image, pin versions, optimize layers, set non-root + healthcheck, or wire image scanning. Triggers: "write a Dockerfile for X", "shrink this image", "multi-stage build for service Y", "non-root user", "what base image should we use", "scan for CVEs". Do NOT use for compose / orchestration (use `devops/kubernetes`), pipelines (use `devops/{github-actions,gitlab-ci,azure-pipelines}`), or app deploy (use `devops/{aws,azure}-deployment`).
---

# DevOps — Docker

Authors production-grade Dockerfiles for the library's three backend stacks (.NET 10 primary, 8/9 supported / Java 21 / Node 24 LTS) and for SPA frontends. Standardizes on multi-stage builds, distroless or minimal base images, pinned versions, non-root execution, OCI labels, `HEALTHCHECK`, and image-level CVE scanning.

**Version policy:** .NET 10 is primary (noble-based images); .NET 8/9 remain supported — detect the project's `TargetFramework` and match the base-image channel (`8.0-jammy-*` / `9.0-*` / `10.0-noble-*`). Never put a project on a newer runtime image than its TFM. Node 20 is EOL (Apr 2026) — use 24 (active LTS) or 22.

## When to use

- New service needs a Dockerfile
- Image is too large / slow to pull / slow to build
- Refactoring to multi-stage / distroless
- Adding `HEALTHCHECK`, non-root user, OCI labels
- Setting up image scanning (Trivy / Grype / Snyk) in CI

## When NOT to use

- Kubernetes manifests / Helm → `devops/kubernetes`
- Pipeline YAML → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- App deploy specifics → `devops/{aws,azure}-deployment`
- Local docker-compose dev workflow → out of scope here (this skill is production-shaped images). **No skill owns this yet** — the only deliberately unowned fence in the domain; improvise from the Dockerfile guidance below rather than looking for a sibling skill. (Test-fixture containers are a different thing and *are* owned: `qa-db-testing-testcontainers-{java,dotnet,typescript}`.)

## Inputs needed

1. **Stack**: .NET 8/9/10 (match the TFM) / Java 21 + Gradle / Node 24 + pnpm / static SPA
2. **Architecture**: linux/amd64 (default) and/or linux/arm64 (often cheaper on AWS Graviton / Azure ARM)
3. **Where the image runs**: ECS Fargate, Container Apps, Kubernetes — all are fine, the Dockerfile is the same
4. **Image registry**: ECR / ACR / GHCR / Docker Hub
5. **Security posture**: minimal vs distroless vs Alpine; scan threshold (block on `critical` by default)

## Universal rules

- **Multi-stage builds** — `builder` stage compiles; runtime stage carries only the artifact
- **Pin every tag** — `mcr.microsoft.com/dotnet/aspnet:8.0.10-alpine3.20`, never `:latest`
- **Non-root user** — `USER 1000:1000` in the runtime stage
- **Health declared** — every long-running service has a `/health` endpoint; a Dockerfile `HEALTHCHECK` only where the image actually has a probe tool (shell-less/minimal images use platform probes instead — see Healthchecks)
- **OCI labels** — `org.opencontainers.image.{title,description,source,version,revision,licenses}`
- **`.dockerignore`** to keep the build context small (no `node_modules`, no `bin`/`obj`, no `.git`, no `coverage`)
- **No secrets baked in** — runtime config from env / Key Vault / Secrets Manager
- **Build with `--platform` explicit** — `--platform=linux/amd64,linux/arm64` for multi-arch
- **Scan in CI** — Trivy / Grype / cloud-native scanner; fail the build on `critical` CVEs in the runtime image

## Stack templates

### .NET (ASP.NET Core) — net10 primary, net8/9 tagged

```dockerfile
# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM mcr.microsoft.com/dotnet/sdk:10.0-noble AS build    # net8: sdk:8.0-jammy · net9: sdk:9.0-noble
ARG TARGETARCH

WORKDIR /src

# Restore (cache mount keeps the NuGet cache out of layers and across builds)
COPY ["Directory.Packages.props", "Directory.Build.props", "global.json", "nuget.config", "./"]
COPY ["src/OrdersApi/OrdersApi.csproj", "src/OrdersApi/"]
RUN --mount=type=cache,id=nuget,target=/root/.nuget/packages \
    dotnet restore "src/OrdersApi/OrdersApi.csproj" -a $TARGETARCH

# Build + publish
COPY src/ src/
RUN --mount=type=cache,id=nuget,target=/root/.nuget/packages \
    dotnet publish "src/OrdersApi/OrdersApi.csproj" \
    -c Release \
    -a $TARGETARCH \
    --no-restore \
    -o /publish

# ---- Runtime stage ----
FROM mcr.microsoft.com/dotnet/aspnet:10.0-noble-chiseled AS runtime    # net8: aspnet:8.0-jammy-chiseled

ARG VERSION="0.0.0"
ARG REVISION="dev"
LABEL org.opencontainers.image.title="orders-api" \
      org.opencontainers.image.description="Orders API" \
      org.opencontainers.image.source="https://github.com/yourco/orders-api" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.licenses="UNLICENSED"

WORKDIR /app
COPY --from=build /publish .

# Chiseled images already run as non-root (UID 1654 — `app`)
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080 \
    ASPNETCORE_HTTP_PORTS=8080 \
    DOTNET_RUNNING_IN_CONTAINER=true \
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=false

# No HEALTHCHECK here on purpose: chiseled has no shell and no wget/curl, so any shell-form
# probe silently reports unhealthy forever. Health is declared at the platform layer
# (K8s probes / ECS / Container Apps) against the app's /health endpoint — see Healthchecks below.

ENTRYPOINT ["dotnet", "OrdersApi.dll"]
```

**Chiseled** (`mcr.microsoft.com/dotnet/aspnet:10.0-noble-chiseled`; `8.0-jammy-chiseled` for net8) — Ubuntu-based minimal image, ~100 MB, no shell, runs as non-root by default. Default for prod images. If you need ICU/tzdata (globalization), use the `-chiseled-extra` variant instead of flipping to the full image.

Alternatives:

- `*-alpine` (pin the current alpine suffix, e.g. `10.0-alpine3.22`) for the smallest image (~80 MB), but musl quirks can bite (look up `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT` and ICU)
- Full Ubuntu (`10.0-noble` / `8.0-jammy`) when you need shell access / extra tooling — these CAN carry an exec-form `HEALTHCHECK`

### Java 21 + Spring Boot 3

```dockerfile
# syntax=docker/dockerfile:1.7

# ---- Build stage ----
FROM eclipse-temurin:21-jdk-noble AS build
WORKDIR /src

# Warm the Gradle cache (cache mount survives across builds)
COPY gradlew settings.gradle build.gradle ./
COPY gradle gradle
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew dependencies --no-daemon --refresh-dependencies || true

COPY src src
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew bootJar --no-daemon -x test

# Extract layered JAR for better layer caching (Boot 3.3+: jarmode=tools; layertools is deprecated)
RUN java -Djarmode=tools -jar build/libs/*.jar extract --layers --launcher --destination /extracted

# ---- Runtime stage ----
FROM eclipse-temurin:21-jre-noble AS runtime

ARG VERSION="0.0.0"
ARG REVISION="dev"
LABEL org.opencontainers.image.title="orders-api" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"

RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/false app

WORKDIR /app
USER 1000:1000

# Copy layers in dependency-stable order
COPY --from=build --chown=1000:1000 /extracted/dependencies/        ./
COPY --from=build --chown=1000:1000 /extracted/spring-boot-loader/  ./
COPY --from=build --chown=1000:1000 /extracted/snapshot-dependencies/ ./
COPY --from=build --chown=1000:1000 /extracted/application/         ./

EXPOSE 8080
ENV SPRING_PROFILES_ACTIVE=prod \
    JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75 -XX:+UseG1GC -Djava.security.egd=file:/dev/./urandom"

# temurin images do NOT reliably ship wget/curl (curl was dropped from newer tags) —
# don't write a wget HEALTHCHECK that reports unhealthy forever. Prefer platform probes
# against /actuator/health; if you truly need a Docker-level check, install wget explicitly:
# RUN apt-get update && apt-get install -y --no-install-recommends wget && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

Notes:
- **`-Djarmode=tools … extract --layers --launcher`** (Spring Boot 3.3+; replaces the deprecated `layertools`) breaks the fat JAR into separate layers so Docker caches **dependencies** separately from **application** — fast incremental builds.
- `MaxRAMPercentage=75` lets the JVM use 75% of the container memory limit
- `eclipse-temurin:21-jre-noble` is the standard JRE image; consider Azul Zulu, Liberica, or distroless `gcr.io/distroless/java21` for smaller / stricter

### Node 24 + TypeScript (NestJS / Express)

```dockerfile
# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM node:24-alpine AS build
WORKDIR /src

# corepack reads the exact pnpm version from package.json's "packageManager" field —
# pin it there ("packageManager": "pnpm@10.x.y"), not in the Dockerfile
RUN corepack enable && corepack prepare --activate

# Install (pnpm store in a cache mount — survives across builds, keyed on lockfile)
COPY package.json pnpm-lock.yaml .npmrc* ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && \
    pnpm install --frozen-lockfile

COPY tsconfig*.json ./
COPY src src
RUN pnpm build && pnpm prune --prod

# ---- Runtime stage ----
FROM node:24-alpine AS runtime

ARG VERSION="0.0.0"
LABEL org.opencontainers.image.title="orders-api" \
      org.opencontainers.image.version="${VERSION}"

WORKDIR /app
RUN apk add --no-cache tini && \
    addgroup -S app && adduser -S app -G app

COPY --from=build --chown=app:app /src/package.json ./
COPY --from=build --chown=app:app /src/node_modules ./node_modules
COPY --from=build --chown=app:app /src/dist ./dist

USER app
EXPOSE 3000
ENV NODE_ENV=production \
    PORT=3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -q --spider http://localhost:3000/health || exit 1

# Tini reaps zombies & forwards signals — Node alone doesn't
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "dist/main.js"]
```

Notes:
- Pin pnpm via `"packageManager"` in `package.json` — one source of truth for local dev, CI, and the image. Corepack is bundled through Node 24 but is being removed from Node ≥25 images; when you move past 24, install pnpm explicitly (`npm i -g pnpm@<exact>`)
- Node 20 is EOL (Apr 2026); Node 24 is active LTS to Apr 2028, Node 22 maintenance LTS
- `pnpm prune --prod` drops devDependencies from `node_modules` for the runtime stage
- `tini` is the conventional PID 1 in Node containers — handles signals + zombie reaping
- Alpine's busybox ships `wget`, so the `HEALTHCHECK` above actually works here — unlike the chiseled/temurin images
- For tiny images consider `node:24-slim` (Debian) or `gcr.io/distroless/nodejs24-debian12` (no shell, smallest — platform probes only)

### Static SPA (React / Blazor WASM build output)

```dockerfile
# ---- Build stage ----
FROM node:24-alpine AS build
WORKDIR /src
RUN corepack enable && corepack prepare --activate
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && \
    pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# ---- Runtime stage: unprivileged nginx (CDN-friendly) ----
# NOT the stock nginx image: that one needs root-owned pid/cache paths, so
# `USER 101` + stock nginx fails at startup. nginx-unprivileged runs as UID 101
# and listens on 8080 out of the box.
FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime
COPY --from=build /src/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK CMD wget -q --spider http://localhost:8080/index.html || exit 1
```

For SPAs deployed to S3 + CloudFront / Static Web Apps / Front Door, **don't ship an nginx image** — push the build output directly. The Dockerfile above is only for cases where you do run an nginx container (small internal app, on-prem).

`nginx.conf` for SPA (fallback to `index.html` for client-side routing):

```nginx
server {
  listen 8080;
  root /usr/share/nginx/html;
  index index.html;

  # Long cache for static assets, no-cache for index.html
  location ~* \.(js|css|woff2?|png|jpg|svg)$ { expires 1y; add_header Cache-Control "public, immutable"; }
  location / { try_files $uri $uri/ /index.html; }
}
```

## `.dockerignore` (every project)

```
**/.git
**/.github
**/.gitlab-ci.yml
**/.dockerignore
**/Dockerfile*
**/node_modules
**/dist
**/build
**/bin
**/obj
**/coverage
**/.vscode
**/.idea
**/*.md
.env*
.azure
```

Small build context = fast builds and no surprise secrets leaking in. Note `**/dist` / `**/build` are excluded because the image builds from source — if a template copies a locally pre-built output instead, drop those lines for that project.

## Multi-arch & build

```bash
docker buildx create --use --name multiarch || true
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag $REGISTRY/orders-api:$SHA \
  --build-arg VERSION=$VERSION --build-arg REVISION=$SHA \
  --provenance=true --sbom=true \
  --push .
```

`--provenance` and `--sbom` produce build provenance and SBOM attached to the image — supply-chain hygiene that's free.

## Image scanning

Run a scanner in CI **after build** and **block** on critical CVEs:

```bash
trivy image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed \
  $REGISTRY/orders-api:$SHA
```

Pin the scanner to an exact version (`aquasec/trivy:<current release>` — check the release page, don't float `latest`). For Azure / AWS images, the registry's own scanner (Microsoft Defender for Containers / Amazon Inspector) is fine but slower-feedback than running Trivy in CI.

## Healthchecks

- **App-level `/health` endpoint** — required (returns 200 quickly with minimal work)
- **Dockerfile `HEALTHCHECK`** — useful for `docker run` and Docker Swarm; **most platforms ignore it** (Kubernetes uses its own probes; Container Apps + ECS use their own)
- **Declare it only where it can actually run.** Alpine images have busybox `wget` — fine. Chiseled / distroless have **no shell and no wget/curl** — a shell-form probe reports unhealthy forever; temurin images no longer reliably ship curl either. On those images, skip `HEALTHCHECK` and make the platform probe the canonical contract, or ship a tiny compiled probe binary and call it exec-form (`CMD ["/probe", "http://localhost:8080/health"]`)

## Image size budgets

| Stack | Realistic target |
|---|---|
| .NET 8/9/10 chiseled | 100–150 MB |
| Java 21 layered Spring Boot | 200–280 MB |
| Node 22/24 production runtime | 120–180 MB |
| Static SPA via nginx | 25–40 MB |

If you're well above these, look at: extra packages in the runtime stage, dev dependencies in `node_modules`, multiple-runtime base (`*-sdk` running in prod), unused locales.

## Rules

- Multi-stage builds always
- Pinned base image tags (digest pinning for highest security: `image@sha256:...`)
- Non-root user in runtime stage
- OCI labels (title, description, source, version, revision, licenses)
- Health declared — `HEALTHCHECK` where the image has a probe tool, platform probes on shell-less images
- `.dockerignore` keeps context small
- No secrets in image (env, build args used for config only when non-sensitive)
- Image scan in CI; block on critical CVEs
- `--platform=linux/amd64,linux/arm64` for multi-arch
- BuildKit features used (cache mounts for restores; `--mount=type=cache`)

## What NOT to do

- No `:latest` tags
- No root user in runtime
- No `RUN apt-get update && apt-get install …` without `--no-install-recommends` and `&& rm -rf /var/lib/apt/lists/*` cleanup
- No copying `.env` / secret files into the image
- No `npm install` / `dotnet restore` without lockfile mode
- No `ADD https://…` to fetch artifacts at build time without checksums
- No `COPY . .` before installing dependencies — defeats layer caching
- No mixing `apt` and `apk` in one image
- No `CMD` followed by a string with shell expansion (`"npm start"`) when you can `CMD ["node", "dist/main.js"]` — exec form forwards signals correctly
- No production image based on `*-sdk` / `*-jdk` — use the runtime image only
- No image > 1 GB for an app service — almost always a misconfigured build

## Generation steps

1. Confirm stack + version (detect the TFM / `engines` / toolchain — never assume), target architecture, and registry.
2. Pick the base image (chiseled .NET matched to the TFM / temurin JRE noble / node 24-alpine or distroless / nginx-unprivileged).
3. Write the multi-stage Dockerfile from the template.
4. Add `.dockerignore`.
5. Pin the base image tag (and ideally digest).
6. Wire health (HEALTHCHECK or platform probe), non-root user, OCI labels.
7. Build locally; check size and scan for CVEs.
8. Add the build + scan to the CI pipeline (`devops/{github-actions,gitlab-ci,azure-pipelines}`).

## Handoffs

- Kubernetes deployment manifests / Helm → `devops/kubernetes`
- Pipelines that build / push / scan → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- Cloud deploy of the image → `devops/{aws,azure}-deployment`
- App-side config / secrets → `devops/environment-config`
- Observability instrumentation that runs inside the container → `observability/opentelemetry-{stack}`
