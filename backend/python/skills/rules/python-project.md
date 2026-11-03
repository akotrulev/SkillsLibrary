---
paths:
  - "**/pyproject.toml"
---

<!-- be-python rules v1 (2026-11-03): pyproject. Installed by /be-python:rules; edit to fit this project. -->

# Python project configuration standards (uv, ruff, mypy, pytest)

Severity tags as in the core Python rules.

- Never raise an existing `requires-python`. 3.13 is the default for an ML worker; 3.14 only once `uv lock` resolves every dependency to a wheel for it. *major*
- `[tool.mypy]` has `strict = true` and `warn_unreachable = true`, with the pydantic plugin when pydantic is used. *major*
- ruff lints with the security (`S`), annotation (`ANN`), pathlib (`PTH`) and print (`T20`) rules on; tests relax only `S101` and `ANN`. *minor*
- pytest runs with `--strict-markers` and declares the `model` marker. *minor*
- A dependency is earned: no numpy, opencv, scikit-image, cairosvg or libmagic for what Pillow or the standard library already does (each native decoder is attack surface), and no structlog added for one worker. *major*
- The ruff, mypy and uv versions are pinned in CI so a gate never changes under a pull request. *minor*
