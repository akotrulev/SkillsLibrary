---
paths:
  - "**/pyproject.toml"
---

<!-- be-python rules v2 (2026-11-21): pyproject and lint. Ids checked against the tools' documentation on 2026-11-21 (ruff 0.17, mypy 2.4). Installed by /be-python:rules; edit to fit this project. -->

# Python project configuration standards (uv, ruff, mypy, pytest)

Severity tags as in the core Python rules.

- Never raise an existing `requires-python`. 3.13 is the default for an ML worker; 3.14 only once `uv lock` resolves every dependency to a wheel for it. *major*
- `[tool.mypy]` has `strict = true` and `warn_unreachable = true`, with the pydantic plugin when pydantic is used. *major*
- pytest runs with `--strict-markers` and declares the `model` marker. *minor*
- A dependency is earned: no numpy, opencv, scikit-image, cairosvg or libmagic for what Pillow or the standard library already does (each native decoder is attack surface), and no structlog added for one worker. *major*
- The ruff, mypy and uv versions are pinned in CI so a gate never changes under a pull request. *minor*

Each row below is a rule of `python.md` or `python-project.md` that ruff or mypy detects, so the gate catches it before a review does. Rules no stock rule detects stay in those files and get no row: injected collaborators, module-level mutable state other than `global`, the `Rejected` versus raise split, `resolve().is_relative_to(job_dir)`.

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| `mypy --strict` clean over `src` and `tests` (`python.md`, Types and structure) | mypy | `strict = true` in `[tool.mypy]` | setting |
| No `case _` arm after an exhaustive `match` on a closed set, which mypy reports as unreachable (`python.md`, Types and structure) | mypy | `warn_unreachable = true` in `[tool.mypy]` | setting |
| No `Any` in a signature (`python.md`, Types and structure) | ruff | `ANN401` | error |
| A `# type: ignore` names an error code (`python.md`, Types and structure) | ruff | `PGH003` | error |
| `pathlib.Path` for every path, never `open()` or `os.path` (`python.md`, Types and structure) | ruff | `PTH` family, for example `PTH123`, `PTH118` | error |
| No mutable default argument (`python.md`, Types and structure) | ruff | `B006` | error |
| No `global` statement (`python.md`, Injection and state) | ruff | `PLW0603` | error |
| No bare `except:` (`python.md`, Errors and resources) | ruff | `E722` | error |
| Catch what you can act on, never `Exception` or `BaseException` (`python.md`, Errors and resources) | ruff | `BLE001` | error |
| No `except Exception: pass` (`python.md`, Errors and resources) | ruff | `S110` | error |
| A file is opened in a `with` block (`python.md`, Errors and resources) | ruff | `SIM115` | error |
| No `time.sleep` to synchronise, no `signal.alarm`, no `threading.Timer` (`python.md`, Concurrency and timeouts) | ruff | `TID251`, those three in `banned-api` | error |
| No `shell=True` and no `os.system` (`python.md`, Hostile input) | ruff | `S602`, `S604`, `S605` | error |
| No `eval` and no `exec` (`python.md`, Hostile input) | ruff | `S307`, `S102` | error |
| No `pickle.loads` (`python.md`, Hostile input) | ruff | `S301` | error |
| No `yaml.load` without `SafeLoader` (`python.md`, Hostile input) | ruff | `S506` | error |
| `requests`, `httpx`, `urllib` and `socket` are imported nowhere (`python.md`, Hostile input) | ruff | `TID251`, those four in `banned-api` | error |
| A log call takes a message template, never an f-string (`python.md`, Logging and secrets) | ruff | `G004` | error |
| No `print` in library code (`python.md`, Logging and secrets) | ruff | `T201` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Every ruff row is an id in `select` under `[tool.ruff.lint]`, which makes it an error: ruff exits non-zero on any finding. `S`, `ANN` and `PTH` are selected as families, as before; the table names the ids the house rules need. The two mypy rows are keys in `[tool.mypy]`, run as `mypy src tests`. Load the pydantic plugin there when pydantic is used.
- Tests relax only `S101` and `ANN`, in `per-file-ignores` for `tests/**`. Every other row holds in tests too.
- Both `TID251` rows are one `banned-api` table. Banning `urllib` bans its submodules (`urllib.parse` included), and `from socket import socket` is caught the same way.
- `BLE001` skips an `except Exception` that re-raises or calls `logger.exception`, and `S110` flags only `except Exception: pass`, not `except OSError: pass`. The `Rejected` versus raise split stays a review rule.
- `PGH003` checks the error code only; the reason after it stays a review rule. A generated module, such as protobuf `_pb2.py`, is linted like any other: list it in `extend-exclude`.
- A scaffold from `pattern-writer` is a starting point, and this table wins where they differ: drop its `ignore = ["ANN401"]`.

`pyproject.toml`:

```toml
[tool.mypy]
strict = true
warn_unreachable = true
plugins = ["pydantic.mypy"]

[tool.ruff.lint]
select = ["ANN", "B006", "BLE001", "E722", "G004", "PGH003", "PLW0603", "PTH", "S", "SIM115", "T20", "TID251"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "ANN"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"requests".msg = "The worker has no network primitive."
"httpx".msg = "The worker has no network primitive."
"urllib".msg = "The worker has no network primitive."
"socket".msg = "The worker has no network primitive."
"time.sleep".msg = "Never sleep to synchronise."
"signal.alarm".msg = "A timeout kills a process."
"threading.Timer".msg = "A timeout kills a process."
```
