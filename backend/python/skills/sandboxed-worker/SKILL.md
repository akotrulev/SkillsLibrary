---
name: sandboxed-worker
description: Use when containerising a Python worker that handles untrusted uploads — a multi-stage uv Dockerfile with weights baked at build, no outbound network, non-root, read-only rootfs, dropped capabilities, per-job memory/CPU/wall-clock limits. Triggers "Dockerfile for the Python worker", "no network for the upload processor", "limit memory per job". Do NOT use for .NET/Java/Node images (`devops/docker`), Kubernetes manifests (`devops/kubernetes`) or the processing code (`media-processing`).
---

# Sandboxed Python Worker — Generator

Produces the container and the process-isolation layer for a Python worker that processes customer uploads. Two layers, both required: **the container has no way out** (no network, no writable rootfs, no capabilities), and **each job runs in a child process with hard limits** so a hostile file can only kill its own job. `devops/docker` owns the library-wide image conventions (multi-stage, pinning, OCI labels, scanning); this skill owns the Python-and-untrusted-input specifics on top of them.

## Version policy

Base image `python:3.13-slim-bookworm` (3.12 / 3.14 variants when the project pins them; `pattern-writer` says how to detect). `uv` from `ghcr.io/astral-sh/uv` pinned by tag. Model weights pinned by **sha256**, never by "latest". Never `python:3.x-alpine` for an ML worker — musl wheels for onnxruntime do not exist, and a source build pulls a compiler into the image.

## When to use

- The worker needs a Dockerfile, a compose service, or a Kubernetes-side security context
- A model (rembg / onnxruntime) must be available with no network at runtime
- A job must be bounded in memory, CPU, wall clock, or process count
- Deciding how the TypeScript side hands a job in and gets a verdict out without giving the worker egress

## When NOT to use

- The image-processing functions themselves → `media-processing`
- Package layout and settings → `pattern-writer`
- A general service Dockerfile for a .NET / Java / Node app → `devops/docker`
- Cluster-level policy (NetworkPolicy, PodSecurity, seccomp profiles beyond runtime default) → `devops/kubernetes` + `devops/k8s-security`
- Runtime intrusion detection / scanning of the running container → `devops/container-runtime-security`

## Inputs needed

1. How jobs arrive: **batch** (a job dir mounted per invocation, one process per job) or **long-lived** (one container, an internal-only HTTP endpoint the TypeScript service calls)
2. Which model(s) to bake and their pinned checksums
3. The limits: bytes per upload, memory per job, CPU seconds, wall clock, concurrent jobs
4. Where outputs go (a mounted output volume, or the HTTP response body)

## Recipes

### Dockerfile (multi-stage, weights baked, no compiler at runtime)

```dockerfile
FROM ghcr.io/astral-sh/uv:0.8.4 AS uv

FROM python:3.13-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --extra ml
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra ml

FROM build AS weights
ARG U2NET_SHA256
ENV U2NET_HOME=/models
RUN mkdir -p /models \
 && /app/.venv/bin/python -c "from rembg import new_session; new_session('u2net')" \
 && echo "${U2NET_SHA256}  /models/u2net.onnx" | sha256sum -c -

FROM python:3.13-slim-bookworm AS runtime
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONHASHSEED=random \
    OMP_NUM_THREADS=1 ORT_DISABLE_TELEMETRY=1 \
    U2NET_HOME=/models PATH=/app/.venv/bin:$PATH
COPY --from=build --chown=app:app /app /app
COPY --from=weights --chown=app:app /models /models
USER app
WORKDIR /app
ENTRYPOINT ["python", "-m", "upload_worker"]
```

- **Weights are downloaded in a build stage that has network, checksum-verified, and copied into the runtime stage.** The runtime image never runs `new_session` against an empty `U2NET_HOME`; `media-processing` makes that a startup failure so a mis-built image dies at boot, not at the first customer job.
- The runtime stage copies the built `.venv` only: no `uv`, no build tools, no `pip`. `UV_COMPILE_BYTECODE` keeps startup fast without writing to the rootfs at runtime.
- `OMP_NUM_THREADS=1`: onnxruntime otherwise spins one thread per core per session; concurrency comes from job processes, and the job limits below are per process.
- No `HEALTHCHECK` that runs a job; a healthcheck is `python -c "import upload_worker.health; upload_worker.health.check()"` which asserts the weights file exists and the venv imports.
- OCI labels, `.dockerignore` (`tests/`, `.venv/`, `.git/`), and Trivy/Grype scanning per `devops/docker`.

### Runtime: compose (the stricter shape, batch jobs)

```yaml
services:
  upload-worker:
    image: registry.example/upload-worker:${TAG}
    network_mode: none
    read_only: true
    user: "10001:10001"
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    pids_limit: 64
    mem_limit: 3g
    memswap_limit: 3g
    cpus: "2"
    tmpfs:
      - /tmp:size=512m,mode=1777,noexec,nosuid,nodev
    volumes:
      - type: bind
        source: ${JOB_DIR}
        target: /job
        read_only: false
    environment:
      WORKER_MAX_UPLOAD_BYTES: "25000000"
      WORKER_MAX_PIXELS: "40000000"
      WORKER_JOB_TIMEOUT_SECONDS: "60"
      WORKER_JOB_MEMORY_BYTES: "2000000000"
    command: ["/job/job.json"]
```

The TypeScript side writes `job.json` + the upload into a fresh directory, runs the container once, reads `verdict.json` and the outputs back, and deletes the directory. Cold start pays the model load (~2–4 s) per job; acceptable for logo uploads, not for a burst of venue photos.

### Runtime: compose (long-lived, internal-only network)

```yaml
networks:
  worker-net:
    internal: true

services:
  upload-worker:
    image: registry.example/upload-worker:${TAG}
    networks: [worker-net]
    read_only: true
    user: "10001:10001"
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    pids_limit: 256
    mem_limit: 6g
    cpus: "4"
    tmpfs:
      - /tmp:size=2g,mode=1777,noexec,nosuid,nodev
    command: ["serve", "--bind", "0.0.0.0:8080"]

  api:
    networks: [default, worker-net]
```

`internal: true` gives the worker a network with **no default route**: the `api` service can reach it, it can reach nothing. Verify on the host: `docker exec upload-worker python -c "import socket; socket.create_connection(('1.1.1.1', 53), timeout=2)"` must raise. That command is a CI check, not a one-off.

The HTTP adapter is thin: FastAPI + uvicorn, one route, the request body size capped at `WORKER_MAX_UPLOAD_BYTES` by the server config, the handler runs the job via the same `run_job_isolated` below through `asyncio.to_thread`. No auth inside the worker: the network *is* the boundary, and the adapter never accepts a URL to fetch.

### Per-job isolation: child process with rlimits

The container limit bounds the whole worker. A single decompression bomb or a pathological VTracer input must not take the worker down, so each job runs in its own child:

```python
import multiprocessing as mp
import resource


def _run_in_child(job: Job, settings: Settings, pipe: Connection) -> None:
    limits = Limits.from_settings(settings)
    resource.setrlimit(resource.RLIMIT_AS, (limits.job_memory_bytes, limits.job_memory_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (limits.job_cpu_seconds, limits.job_cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits.max_output_bytes, limits.max_output_bytes))
    resource.setrlimit(resource.RLIMIT_NPROC, (limits.job_max_procs, limits.job_max_procs))
    pipeline = build_pipeline(settings)
    pipe.send(pipeline.run(job))


def run_job_isolated(job: Job, settings: Settings) -> Verdict:
    context = mp.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_run_in_child, args=(job, settings, child), daemon=True)
    process.start()
    child.close()
    try:
        if not parent.poll(settings.job_timeout_seconds):
            return Verdict.rejected(job.id, "timeout", f"{settings.job_timeout_seconds}s")
        return parent.recv()
    except EOFError:
        return Verdict.rejected(job.id, "resource-exceeded", f"exit {process.exitcode}")
    finally:
        process.kill()
        process.join(5)
```

- **The child sets its limits first, then loads the model, then runs the job.** `spawn` gives it a fresh interpreter with no inherited threads or locks; the model load it pays (one to three seconds for `u2net`) is the price of a child that a hostile input can only kill itself. Do not reach for `fork` to skip that load: forking a parent that holds an onnxruntime session with its thread pool is undefined behaviour dressed as an optimisation. When the load cost is proven to matter, the next step is a warm pool of pre-loaded children with a per-task kill (`pebble.ProcessPool`), not `fork`.
- **Size `RLIMIT_AS` from a measured run**, not from the image's pixel budget: onnxruntime reserves arena address space on session creation, so a ceiling that fits the pixels alone makes every job fail at model load. Measure `ru_maxrss` of a child running the largest allowed input, add headroom, and put that number in `Settings`.
- `RLIMIT_AS` makes an allocation past the ceiling raise `MemoryError` inside the child, which the pipeline maps to `resource-exceeded`; a child ended by the kernel OOM killer or by `RLIMIT_CPU` (`SIGXCPU`) never sends, the pipe reaches EOF, and the parent reports `resource-exceeded` with the exit code. A child still running at the wall clock is killed and reported as `timeout`. All three are `Rejected`, never a crash of the worker.
- `signal.alarm` or a thread-based timeout cannot interrupt C code inside Pillow, onnxruntime or VTracer; only killing the process can. That is why the child exists.
- Job scratch is `/tmp/<job-id>` on the `tmpfs`; the parent removes it after the verdict, in `finally`.
- `RLIMIT_FSIZE` caps any single output file, so a trace cannot fill the tmpfs.
- `resource.setrlimit` is Linux behaviour; on macOS `RLIMIT_AS` is silently ineffective, so the limit tests run in the Linux CI job and are marked accordingly.

### Kubernetes securityContext (when the platform is k8s)

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities: { drop: [ALL] }
  seccompProfile: { type: RuntimeDefault }
resources:
  limits: { memory: 6Gi, cpu: "4", ephemeral-storage: 4Gi }
```

plus a default-deny egress `NetworkPolicy` for the pod and an `emptyDir` with `medium: Memory` at `/tmp`. The policy objects themselves are `devops/kubernetes`'s; this skill states what they must say.

## Rules

- No outbound route at runtime: `network_mode: none` or an `internal: true` network, verified by a CI check that tries to connect out and expects failure
- Weights baked at build, checksum-verified; runtime never downloads
- Non-root numeric UID, `read_only: true`, `cap_drop: [ALL]`, `no-new-privileges`, `tmpfs` scratch with `noexec`
- Every job in a child process with `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_FSIZE`, `RLIMIT_NPROC` and a wall-clock kill
- All limits come from `Settings` (`pattern-writer`), set in compose / the manifest, never hard-coded in Python
- The worker accepts bytes and a job description; it never accepts a URL, a path outside `/job`, or a shell string

## What NOT to do

- No `pip install` in the runtime stage; no `apt-get` beyond what a wheel needs at runtime (`libgomp1` only if `ldd` on the onnxruntime `.so` proves it is missing)
- No `--privileged`, no `/var/run/docker.sock` mount, no `hostNetwork`
- No `network_mode: host`, no `ports:` on the worker in either shape
- No model download on first use; no `HEALTHCHECK` that performs inference
- No `fork` start method with a loaded onnxruntime session; no `threading.Timer` as the job timeout
- No shared writable volume between jobs; one directory per job, deleted with it

## Validation

Inside a plan task marked `Gate: none`, run none of these and report the image as "written, not run".

- `docker build` succeeds with `--build-arg U2NET_SHA256=<pinned>`; changing one hex digit fails the build
- `docker run --rm --network none <image> python -c "from rembg import new_session; new_session('u2net')"` succeeds (weights present, no download)
- Egress check raises inside the running container
- `docker run --rm --read-only <image> python -c "open('/app/x','w')"` fails with `OSError`
- A header-only decompression bomb (from `unit-testing`'s fixture builders) fed as a job yields `Rejected("too-many-pixels")` and the worker process is still alive
- Trivy / Grype scan per `devops/docker`: no critical findings in the runtime image

## Handoffs

- What runs inside the child → `media-processing`
- Settings and logging shape → `pattern-writer`
- Library-wide image conventions and scanning → `devops/docker`
- Cluster policy objects → `devops/kubernetes`, `devops/k8s-security`
- Tests that prove the limits hold → `unit-testing` (the in-process part) and the `qa-api-typescript` peer (the container-level contract the TypeScript side calls)
