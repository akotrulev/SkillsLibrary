---
paths:
  - "**/*.py"
---

<!-- be-python rules v1 (2026-11-03): core. Installed by /be-python:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# Python worker code standards

Apply these to every Python file you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a bug or breaks a security rule, **major** is a design or correctness problem, **minor** is style, **nit** is preference. Upload-pipeline, test, container and `pyproject.toml` rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the interpreter before writing (`requires-python`, then `.python-version`, then the Dockerfile base image) and the Pillow major from `uv.lock`: never use the `type X = …` statement or PEP 695 generics below 3.12, and never flag a 3.12 project for lacking a 3.13 feature.

## Simplicity

- Write the simplest thing that meets the requirement, then stop. No `Protocol` with one implementer that nothing fakes, no `ABC` with one subclass, no `*Manager` / `*Utils` / `*Helper` / `Singleton` class, no class with `__init__` and one method (write the function), no layer that only forwards, no config knob nothing sets. An abstraction is earned on the second real need. *major, fix by inlining*
- One pattern per problem; Repository + Service + Strategy + Decorator on one pipeline step is stacking. *major*
- Cut structure, never correctness: validation, the metadata strip, the sanitiser, the per-job limits and the tests stay.

## Types and structure

- `mypy --strict` clean over `src` and `tests`: no `Any` in a signature or escaping a boundary, no `cast` to silence an error, no `# type: ignore` without an error code and a reason. *major*
- A closed set of outcomes is a tagged union of frozen dataclasses consumed by `match` with no `case _` arm, never an `isinstance` chain. *major*
- pydantic only where untrusted bytes arrive (a job file, an HTTP body, the environment); frozen `dataclass(slots=True)` inside; no `dict` carrying a shape. *minor*
- A `Protocol` lives beside its consumer with only the methods it uses; the implementation never imports it. *minor*
- `pathlib.Path` for every path, never string concatenation. *minor*
- No mutable default argument. *major* No `from x import *`, no circular import hidden in a function-level import, no `Optional[X]` where a default exists. *minor*

## Injection and state

- Collaborators arrive through dataclass fields or keyword arguments; time, randomness and the model session are injected (`Clock`, `BackgroundRemover`). No service locator, global registry or `importlib` lookup. *major*
- No module-level mutable state: no `_cache = {}`, no `_session = None` with lazy init, no `global`. Constants and frozen values are fine. *major*
- The composition root (`__main__.py`) is the only place that builds collaborators: `Settings()` once at startup, the model session once, never per job or in a module body. Nothing else reads `os.environ`. *major*

## Errors and resources

- A customer's bad file returns `Rejected`; a bug or a missing baked model raises. Never both from one function. *major*
- No `except Exception: pass`, bare `except:`, or `except …: return None`. *blocker*
- Catch what you can act on (`UnidentifiedImageError`, `OSError`), not `Exception`. *major*
- `with` for every file, image and session handle; nothing used after `verify()` or outside its `with`. *major*

## Concurrency and timeouts

- CPU-bound work is synchronous with process-level parallelism. `asyncio` only in an I/O adapter, and Pillow, onnxruntime or vtracer are never called directly in `async def`: use `asyncio.to_thread` or a `ProcessPoolExecutor`. *major*
- A timeout kills a process. No `signal.alarm`, `threading.Timer` or `asyncio.wait_for` around C-extension work; no `time.sleep` to synchronise. *major*

## Hostile input

- No `shell=True`, `os.system`, `eval`, `exec`, `pickle.loads`, or `yaml.load` without `SafeLoader` on anything from a job. *blocker*
- No network primitive in the worker: `requests`, `httpx`, `urllib`, `socket` are imported nowhere. It accepts bytes and a job description, never a URL. *blocker*
- A name from a job is joined to the job directory and checked with `resolve().is_relative_to(job_dir)`; a path from a job is never opened as given. *blocker*
- Every threshold and ceiling is a named constant or a `Settings` field (`PRINT_READY_DPI`, `LADDER`), never an inline `300` or `(2048, 2048)`. *minor*

## Logging and secrets

- `logging` with a JSON formatter to stdout, one object per line; a message template with fields in `extra`, never an f-string in the call; no `print` in library code. *major*
- Log the job id, sizes, the verdict and durations; never payload bytes, raw SVG, a path outside the job directory or a hostname. *major* No secret in code. *blocker*

## Comments

- No comments inside function bodies: no step markers, no restating the next line, no commented-out code, no `TODO`. Extract and name the step instead. *minor; major when the comment is wrong*
- A docstring only where the name cannot carry the meaning: a non-obvious rule, an ordering or lifetime constraint on callers, a deliberate deviation and its reason. Never one restating the signature. *nit*
