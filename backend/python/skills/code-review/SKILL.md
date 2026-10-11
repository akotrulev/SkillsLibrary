---
name: conventions-review
description: Use when reviewing Python 3.12–3.14 worker or backend code for typing leaks, swallowed exceptions, module state, blocking async, unsafe subprocess/path/deserialisation, Pillow metadata mistakes, SVG sanitiser gaps, missing per-job isolation. Triggers "review this Python module", "is this worker hardened". Do NOT use for explanations (`pattern-guide`), generating code (`pattern-writer` / `media-processing`), or the Dockerfile beyond its checklist row (`sandboxed-worker`).
---

# Python — Reviewer

Reviews Python code against `pattern-writer`, `media-processing`, `sandboxed-worker`, `unit-testing` and the global rules in `CLAUDE.md`. Produces the findings table; does not rewrite. Loads `backend/_shared/code-review` for pattern-stacking and architecture-altitude concerns.

## When to use

- A diff or module submitted (validator, sanitiser, pipeline step, composition root, tests)
- Pre-merge gate on anything under `src/` or `tests/` of the worker
- "Is this safe to point at customer uploads"

## When NOT to use

- Conceptual questions → `pattern-guide`
- Writing the fix → `pattern-writer` / `media-processing`
- Container scanning, DAST → `qa-security`

## Review checklist

### Typing and structure

| Check | Bad sign | Severity |
|---|---|---|
| `mypy --strict` clean | `Any` in a signature, `# type: ignore` without code + reason, `cast` to silence | major |
| Tagged unions exhaustive | `case _:` on a `Result`; `if isinstance` chains where `match` was meant | major |
| Protocol sized to the consumer | a `Protocol` mirroring a whole concrete class | minor |
| Frozen internal values | mutable dataclass passed across steps; a `dict` where a dataclass carries the shape | minor |
| Composition root is the only constructor site | `new_session(...)` inside a function called per job; `Settings()` built in a module body | major |
| No module-level mutable state | `_cache = {}`, `_session = None` + lazy init, `global` | major |
| Unearned abstraction | ABC with one subclass, `*Manager` / `*Utils` class, a layer that forwards | major — inline it |
| Comments per `engineering-practices/code-comments` | inline comment, commented-out code, docstring restating the signature | minor; wrong or covering-for-unclear-code → major |

### Errors and control flow

| Check | Bad sign | Severity |
|---|---|---|
| Expected outcomes are `Rejected`, bugs raise | `raise ValueError("unsupported")` for a customer's bad file; `Rejected` for a missing model file | major |
| No swallowed exceptions | `except Exception: pass`, bare `except:`, `except ... : return None` | blocker |
| Exception narrowed to what is handled | `except Exception` around `Image.open` when `UnidentifiedImageError` / `OSError` are the cases | major |
| Resource lifetime | `Image.open` without `with`; a handle used after `verify()`; `BytesIO` never closed in a loop | major |
| No blocking inside `async def` | Pillow / onnxruntime / vtracer called directly in a coroutine; no `to_thread` | major |
| Timeouts kill processes | `signal.alarm`, `threading.Timer`, `asyncio.wait_for` around C-extension work | major |

### Untrusted input (the worker's reason to exist)

| Check | Bad sign | Severity |
|---|---|---|
| Format decided by bytes | branching on extension / declared MIME; re-labelling a polyglot | blocker |
| Pixel ceiling explicit | `MAX_IMAGE_PIXELS = None`; no `width * height` check; relying on the default warning | blocker |
| Truncated input rejected | `LOAD_TRUNCATED_IMAGES = True`; skipping `verify()` or `load()` | major |
| Animated / multi-frame rejected for logo and photo classes | `n_frames` never read | major |
| SVG parsed hardened | `xml.etree` / `lxml` instead of `defusedxml`; `forbid_dtd` missing | blocker |
| SVG allowlisted, rejected not stripped | denylist of elements; stripping `<script>` and returning "clean"; `<style>` allowed; `href` not checked for scheme after decoding | blocker |
| Every emitted SVG passes the sanitiser | VTracer output returned as-is | major |
| Metadata strip is total | `im.copy()` then save; `save(exif=b"")` relied on; `**im.info` forwarded; XMP / comment untouched | blocker |
| Orientation applied before strip | strip first, then no `exif_transpose` | major |
| ICC kept, nothing else | profile dropped (colour shift) or `pnginfo` / `xmp` passed through | minor / major |
| Paths confined | `Path(job.filename)` joined without `resolve().is_relative_to(job_dir)`; a path from the job opened directly | blocker |
| No shell, no eval, no pickle | `subprocess(..., shell=True)`, `os.system`, `pickle.loads`, `yaml.load` without `SafeLoader` | blocker |
| No network primitives | `requests` / `httpx` / `urllib` / `socket` imported anywhere in the worker | blocker |
| Model loaded from baked weights only | download path reachable; `new_session` without `U2NET_HOME` asserted at startup | major |
| Per-job isolation | pipeline runs in the parent; no `RLIMIT_AS` / `RLIMIT_CPU` / wall clock; `fork` start method with a loaded session | major |
| Verdict leaks nothing | absolute paths, hostnames, tracebacks, payload bytes in the JSON or the log | major |
| Rejection reasons closed | a free-form string where the `Literal` set is; a new reason not mirrored in the TypeScript contract | major |

### Operations

| Check | Bad sign | Severity |
|---|---|---|
| DPI graded from pixels vs print size | grade computed from `info["dpi"]` | major |
| Dominant colours exclude transparency | `getcolors()` on RGBA including alpha < 128; no thumbnail before quantising | major / minor |
| Ladder never upscales, both renditions from one copy | `resize` where `thumbnail` was meant; WebP and JPEG resized separately | major |
| rembg input downsized, session reused, PNG out | full-resolution inference; session per call; cut-out saved as JPEG | major |
| Thresholds named | `>= 300` inline; `(2048, 2048)` inline | minor |
| Dependencies earned | numpy / opencv / cairosvg / libmagic added for one call Pillow already does | major |

### Tests (`unit-testing`)

| Check | Bad sign | Severity |
|---|---|---|
| Fixtures prove themselves | a GPS strip test whose fixture has no test asserting it carries GPS | major |
| One expected condition | `assert reason in (...)`; `or` in an assertion | major |
| No `try`/`except`, no `if`/`for` in a test body | any | major |
| No `mock.patch` on the module under test | `patch("upload_worker.metadata.Image")` | major — inject a Protocol |
| `model` tests marked and skipped honestly | a rembg test in the default lane; a skip reason that hides a missing weights file as "passed" | major |
| Every `Rejected.reason` reachable from a test | a literal no test expects | minor |
| Checked-in binaries | `tests/data/evil.jpg` | minor — replace with a builder |

## Output

The standard table from `CLAUDE.md`:

```
| Severity | Location | Issue | Suggested fix |
```

Each fix names the skill section that has the recipe (`media-processing` Step 3, `sandboxed-worker` per-job isolation) rather than restating it. Blockers first; a review of upload-handling code with no row from the untrusted-input table should say explicitly that the table was applied and passed.

## Handoffs

- Fixes → `pattern-writer` / `media-processing` / `sandboxed-worker`
- Missing tests → `unit-testing`
- Cross-stack pattern concerns → `backend/_shared/code-review`
- Container / image scan findings → `qa-security`, `devops/docker`
