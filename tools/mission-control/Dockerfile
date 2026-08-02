# syntax=docker/dockerfile:1

# Mission Control container.
#
# Two things drive this image's shape:
#
# 1. Dependencies are installed INSIDE the image, never copied from the host.
#    The Claude Agent SDK ships a platform-specific bundled CLI, so a
#    node_modules built on an ARM Mac will not run on linux/amd64.
#
# 2. The runtime stage carries a real toolchain (git + the project's language
#    runtime). Implementer agents run unit tests and mutation testing inside
#    this container, so whatever your target project needs must exist here.
#    See "Extending the toolchain" in README.md.

ARG NODE_VERSION=22

# ---- deps: production dependencies only -------------------------------------
FROM node:${NODE_VERSION}-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

# ---- build: full dependencies, compile the Next.js app ----------------------
FROM node:${NODE_VERSION}-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY tsconfig.json next.config.mjs ./
COPY src ./src
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- runtime ----------------------------------------------------------------
FROM node:${NODE_VERSION}-bookworm-slim AS runtime
WORKDIR /app

# git: agents commit and inspect history.
# ripgrep: the SDK's search tooling prefers it over a shell fallback.
# ca-certificates: outbound TLS to the API.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      ripgrep \
 && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=4300 \
    HOSTNAME=0.0.0.0 \
    # Mounted read-only in the run command; see README.
    MISSION_CONTROL_LIBRARY_ROOT=/library \
    # Persist runs/projects on a named volume rather than the container layer.
    MISSION_CONTROL_DATA_DIR=/data

COPY --from=deps  /app/node_modules ./node_modules
COPY --from=build /app/.next        ./.next
COPY package.json next.config.mjs ./

# Declared so `docker run` without an explicit -v still keeps state across
# restarts of the same container.
VOLUME ["/data"]

EXPOSE 4300

# Runs as root by default: the agents write to host directories bind-mounted
# into the container, and a mismatched UID cannot create files in them on
# Linux. Override with `--user "$(id -u):$(id -g)"` if you prefer, and make
# sure /data is writable by that UID.
CMD ["npm", "run", "start"]
