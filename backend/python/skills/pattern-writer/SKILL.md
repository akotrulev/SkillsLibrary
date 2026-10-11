---
name: patterns-apply
description: Use when scaffolding Python 3.13/3.14 backend or worker code into the repo — a src-layout uv + ruff + mypy --strict package, a tagged-union Result, Protocol-injected collaborators, pydantic-settings, frozen dataclasses, JSON logging, a composition root. Triggers "set up the Python worker package", "add a Result type here". Do NOT use for explanations (`pattern-guide`), review (`code-review`), image/SVG/model code (`media-processing`) or the Dockerfile (`sandboxed-worker`).
---

# Python Design Patterns — Generator

Scaffolds idiomatic Python (3.13 primary; 3.12 and 3.14 supported) into the active repo. Prefers language features — `match` on tagged unions, `Protocol`, decorators, generators, context managers — over class-heavy GoF translations.

## Version policy

Detect the interpreter first: `requires-python` in `pyproject.toml`, `.python-version`, then the Dockerfile base image. **3.13 is the default for an ML worker** because `onnxruntime` / `rembg` / `vtracer` wheels lag a new interpreter; move to 3.14 only when `uv lock` resolves every dependency to a wheel for it. Never up-level an existing project's `requires-python`. Never use the 3.12 `type X = ...` statement or PEP 695 generics in a project pinned below 3.12.

## When to use

- A new package or worker needs its skeleton (`pyproject.toml`, `src/` layout, tooling)
- Replacing `if`/`elif` chains or a class hierarchy with a tagged union + `match`
- Introducing a domain `Result` where callers currently catch exceptions to branch
- Extracting a `Protocol` so a collaborator (time, randomness, model session, storage) can be injected and faked
- Replacing scattered `os.environ` reads with one settings object
- Adding structured logging to a process that prints

## When NOT to use

- Explanations → `pattern-guide`
- Reviewing → `code-review`
- Anything that opens an image, parses SVG, or runs a model → `media-processing`
- Dockerfile, compose, runtime hardening → `sandboxed-worker`
- Tests for what you generate → `unit-testing` (you still write them; that skill owns the conventions)

## Inputs needed

1. Which pattern, and the concrete variants or collaborators
2. The existing call site to refactor, if any
3. Package name and whether the project is a library, a CLI worker, or an HTTP service
4. Interpreter version (detected, see above)

## Recipes

### Project skeleton (uv + src layout)

```toml
[project]
name = "upload-worker"
version = "0.1.0"
requires-python = ">=3.13,<3.15"
dependencies = [
  "pillow>=12,<13",
  "pydantic>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "defusedxml>=0.7,<1",
]

[project.optional-dependencies]
ml = ["rembg[cpu]>=2.0.67,<3", "vtracer>=0.6.11,<1"]

[dependency-groups]
dev = ["pytest>=8.4", "pytest-cov>=6", "mypy>=1.17", "ruff>=0.12", "hypothesis>=6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "S", "ANN", "RUF", "PTH", "SIM", "T20"]
ignore = ["ANN401"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "ANN"]

[tool.mypy]
strict = true
python_version = "3.13"
warn_unreachable = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"
markers = ["model: needs baked model weights; skipped when U2NET_HOME is unset"]
```

Layout:

```
pyproject.toml
uv.lock
src/upload_worker/
  __init__.py
  __main__.py          composition root + CLI entry
  settings.py
  result.py
  logging.py
  validation.py        media-processing owns the contents of these
  sanitize_svg.py
  metadata.py
  ...
tests/
  conftest.py
  fixtures.py          hostile-fixture builders (unit-testing skill)
  test_validation.py
```

`uv sync` creates the lock; `uv run pytest`, `uv run mypy src`, `uv run ruff check .` are the gates. Pin the `ruff`, `mypy` and `uv` versions in CI so a gate never changes under a PR.

### Tagged-union `Result`

```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Ok[T]:
    value: T


@dataclass(frozen=True, slots=True)
class Rejected:
    reason: RejectionReason
    detail: str


type RejectionReason = Literal[
    "unsupported-format", "polyglot", "too-large", "too-many-pixels", "truncated",
    "unsafe-svg", "animated", "timeout", "resource-exceeded",
]


type Result[T] = Ok[T] | Rejected
```

Consumer:

```python
def handle(job: Job, validate: Callable[[bytes, str], Result[Sniffed]]) -> Verdict:
    match validate(job.payload, job.declared_type):
        case Ok(value=sniffed):
            return Verdict.accepted(sniffed)
        case Rejected(reason=reason, detail=detail):
            return Verdict.rejected(reason, detail)
```

No `case _`. Adding a variant to `Result` makes every `match` a `mypy --strict` error until it is handled, which is the point. `reason` is a `Literal` so the set of rejection codes is closed and the TypeScript side can mirror it verbatim.

### Protocol-injected collaborator

Declare the protocol beside the consumer, with only the methods the consumer uses:

```python
from typing import Protocol


class BackgroundRemover(Protocol):
    def remove(self, rgba: Image.Image) -> Image.Image: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class Pipeline:
    remover: BackgroundRemover
    clock: Clock

    def run(self, job: Job) -> Verdict: ...
```

The real implementation (`RembgRemover` in `media-processing`) never imports `BackgroundRemover`; structural typing binds them. A test passes a fake that returns a fixed image. No `unittest.mock.patch` of the module the code imports — patching is the Python analogue of `vi.mock` and hides the seam instead of exposing it.

### Settings read once

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_", frozen=True)

    max_upload_bytes: int = Field(default=25_000_000, gt=0)
    max_pixels: int = Field(default=40_000_000, gt=0)
    job_timeout_seconds: int = Field(default=60, gt=0)
    job_memory_bytes: int = Field(default=2_000_000_000, gt=0)
    model_home: Path = Field(default=Path("/models"))
    log_level: str = "INFO"
```

Constructed exactly once in `__main__.py`; nothing else touches `os.environ`. A missing or malformed value fails at startup with the field name in the error, never at the first job.

### Composition root

```python
def build_pipeline(settings: Settings) -> Pipeline:
    session = new_session("u2net")
    return Pipeline(
        remover=RembgRemover(session),
        clock=SystemClock(),
        limits=Limits.from_settings(settings),
    )


def main(argv: Sequence[str]) -> int:
    settings = Settings()
    configure_logging(settings.log_level)
    pipeline = build_pipeline(settings)
    job = Job.model_validate_json(Path(argv[1]).read_bytes())
    verdict = pipeline.run(job)
    sys.stdout.write(verdict.model_dump_json())
    return 0
```

This is the only file that knows concrete classes. The model session is loaded once here, not per job; loading `u2net` costs seconds and hundreds of MB.

### Structured logging to stdout

The sandboxed worker has no network, so logs on stdout are its whole telemetry. One JSON object per line, message templates with fields, never f-strings in the call:

```python
import logging
import json


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


log = logging.getLogger(__name__)
log.info("job rejected", extra={"fields": {"job_id": job.id, "reason": reason}})
```

`structlog` is fine when the project already uses it; do not add it for one worker. Never log the payload bytes, a file path outside the job directory, or the raw SVG — log the job id, sizes, the verdict, and durations.

### Decorator for timing / retry (one concern each)

```python
def timed[**P, R](name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def wrap(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            started = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                log.info("step finished", extra={"fields": {"step": name, "ms": round((time.perf_counter() - started) * 1000)}})
        return inner
    return wrap
```

Retry belongs only around I/O that can transiently fail; there is none inside a no-network worker, so do not scaffold one there.

## Rules

- `mypy --strict` clean; no `Any` escaping a boundary, no `# type: ignore` without an error code and a reason
- Frozen `dataclass(slots=True)` for internal values; pydantic only at the boundary
- `pathlib.Path` everywhere; never string concatenation for paths
- `match` with no wildcard on every tagged union
- Constructor injection via dataclass fields or keyword arguments; no module-level mutable state; no `global`
- `with` for every file, image, and session handle Pillow or the OS hands you
- Synchronous code for CPU-bound work; `asyncio` only in an I/O adapter, bridging with `asyncio.to_thread`
- Logging via `logging` + JSON formatter; message templates; no `print` in library code

## What NOT to do

- No `from x import *`, no circular imports papered over with function-level imports
- No `except Exception: pass`; no bare `except:`; catch the exception you can act on and re-raise or return `Rejected`
- No mutable default arguments; no `Optional[X]` where a default exists
- No `subprocess` with `shell=True`; no `os.system`; no `eval`/`exec`/`pickle.loads` on anything from a job
- No `Singleton`, `Manager`, `Utils` classes; no `ABC` with one subclass
- No `time.sleep` for synchronisation; no `signal.alarm` as a timeout for C-extension work (see `pattern-guide`)

## Generation outputs

1. `pyproject.toml` + `uv.lock` (new project) or the additions to the existing ones
2. The module(s) under `src/<package>/`
3. Unit tests for every logic-bearing unit — conventions and fixture builders per `unit-testing`
4. The composition-root edit that wires the new collaborator in

## Validation

Run the checks below — unless you are inside a plan task marked `Gate: none`, which runs none of them and reports "written, not run":

- `uv run ruff check . && uv run ruff format --check .` — clean
- `uv run mypy src tests` — clean
- `uv run pytest` — green
- Old call sites swept: the `if`/`elif` chain or `try/except` branching the new pattern replaced is gone

## Handoffs

- Image, SVG, EXIF, rembg, VTracer, DPI, colours, resize → `media-processing`
- Dockerfile + runtime limits → `sandboxed-worker`
- Tests → `unit-testing`
- Review → `code-review`
