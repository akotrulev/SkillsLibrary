---
name: be-python-unit-testing
description: Use when Python worker or backend logic needs a dev-side pytest test — what deserves one, the seams to inject (time, model session, filesystem), self-proving hostile fixture builders (GPS JPEG, decompression bomb, polyglot, script SVG), rejection tables, the `model` marker. In-process only. Triggers "unit-test the validator", "build a hostile fixture". Do NOT use for the container-level contract the TypeScript side calls (`qa-api-typescript`) or image scanning (`qa-security`).
---

# Python — Unit Testing (pytest)

Owns **dev-side unit tests of worker and backend logic**: call the function, pass fakes in, assert on the returned value or on the bytes written to `tmp_path`. **In-process only — no container, no network, no `docker run`, no real model unless the `model` marker says so.**

**The boundary, one sentence:** if the test runs the image, calls the worker over HTTP, or asserts what the TypeScript service sees, it belongs to the **peer** `qa-api-typescript`. The `sandboxed-worker` validation list (egress check, read-only rootfs, bomb-survives-the-worker) is that peer's and CI's, not this suite's.

## Version policy

Detect `requires-python` and the Pillow major from `uv.lock` first. pytest 8.x; `hypothesis` optional. Tests run under the same `mypy --strict` as `src` — an untyped test file hides the API's real signatures.

## When to use

- A function `media-processing` or `pattern-writer` produced has behaviour: a sniff, a sanitiser, a strip, a verdict, a ladder, a `match` over a `Result`
- A rejection reason needs pinning before a refactor
- A Pillow behaviour the pipeline depends on must stay pinned across upgrades (metadata fallbacks, `exif_transpose`, `thumbnail` never upscaling)
- Reproducing a defect at the unit level before fixing it (`ep-systematic-debugging` RED)

## When NOT to use

- Running the container, egress / rootfs / capability checks, HTTP contract → **peer** `qa-api-typescript` and CI
- Image vulnerability scanning → **peer** `qa-security`
- Mutation score, suite-scale builders → the `qa-*-typescript` peers (the repo's QA stack is TypeScript)
- Pure type aliases, `Literal` sets, the `Settings` class's field list → don't test them

## Stack

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers -p no:cacheprovider"
markers = ["model: needs baked model weights under U2NET_HOME; skipped when unset"]
```

| Concern | What | Notes |
|---|---|---|
| Runner | pytest 8 | `--strict-markers` so a typo'd marker fails instead of silently running |
| Doubles | a plain class implementing the `Protocol` | never `unittest.mock.patch` on the module under test |
| Filesystem | `tmp_path` | never `tempfile` by hand, never a path outside it |
| Time | injected `Clock` fake | `freezegun` only for code you cannot change |
| Images | **generated in the test run** by builders in `tests/fixtures.py` | a checked-in binary is evidence nobody can read in review |
| Model | `@pytest.mark.model` + `skipif(not os.environ.get("U2NET_HOME"))` | the CI job that has the weights runs them; laptops skip |
| Properties | `hypothesis` for the DPI grade and the colour-share invariant | bounded strategies; no `Image` generation via hypothesis |

## The selection matrix

| Unit | Test it? | Shape |
|---|---|---|
| `sniff` | yes — one parametrised rejection table + one accept case per format | each row: builder → expected `Rejected.reason` |
| `sanitize_svg` | yes — a rejection table over the forbidden vectors + one clean logo that round-trips | assert `reason == "unsafe-svg"` and `detail` names the element/attribute |
| `normalised_pixels` | yes — the metadata-strip test and the orientation test | the fixture proves it carried GPS/XMP; the output proves it does not |
| `dpi_verdict` | yes — boundary rows at 149.9 / 150 / 299.9 / 300 plus a hypothesis property | pure function |
| `dominant_colours` | yes — a two-colour synthetic image, a fully transparent image | shares sum to 1.0; transparent → `[]` |
| `resize_ladder` | yes — sizes, no upscaling, both renditions same pixel size | assert on `Image.open(path).size` |
| `RembgRemover.remove` | `model` marker only — a synthetic circle on white yields alpha 0 at the corners | otherwise fake the `BackgroundRemover` Protocol |
| `trace_to_svg` | yes — a 32 px two-colour square traces to a sanitiser-clean SVG under the byte cap | vtracer is a pure wheel, fast enough for the default lane |
| `run_job_isolated` | one test: a child that sleeps past the timeout yields `Rejected("timeout")` | `multiprocessing` in-process is still in-process |
| `Verdict` serialisation | yes — the JSON has no absolute paths | `model_dump_json()` string assertions |
| `Settings` | one test: a malformed env value names the field | `pydantic.ValidationError` `errors()[0]["loc"]` |

## Fixture builders that prove themselves

Every hostile fixture is built by a function, and **each builder has its own test asserting the fixture is actually hostile**. A strip test against a JPEG that never carried GPS is green forever and proves nothing.

```python
def jpeg_with_gps(size: tuple[int, int] = (64, 48)) -> bytes:
    image = Image.new("RGB", size, "red")
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = 6
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (51.0, 30.0, 0.0)
    gps[ExifTags.GPS.GPSLongitudeRef] = "W"
    gps[ExifTags.GPS.GPSLongitude] = (0.0, 7.0, 0.0)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif.tobytes(), xmp=XMP_WITH_LOCATION, comment=b"camera serial 1234")
    return buffer.getvalue()


def test_jpeg_with_gps_fixture_carries_gps_xmp_and_comment() -> None:
    with Image.open(io.BytesIO(jpeg_with_gps())) as image:
        gps = image.getexif().get_ifd(ExifTags.IFD.GPSInfo)
        assert gps[ExifTags.GPS.GPSLatitudeRef] == "N"
        assert b"exif:GPSLatitude" in image.info["xmp"]
        assert image.info["comment"] == b"camera serial 1234"
```

```python
def png_header_only_bomb(width: int = 100_000, height: int = 100_000) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00")) + chunk(b"IEND", b"")


def polyglot_png_svg() -> bytes:
    return tiny_png() + b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"


def truncated_jpeg() -> bytes:
    whole = jpeg_plain((256, 256))
    return whole[: len(whole) // 2]


def svg_with(vector: str) -> bytes:
    return f"<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>{vector}</svg>".encode()
```

`chunk` computes the CRC; `tiny_png` is a real 1×1 PNG from Pillow. The bomb is 66 bytes and makes Pillow raise `DecompressionBombError` from the header, which is exactly the behaviour under test — no 10 GB file is ever allocated. GPS rationals are floats (or `IFDRational`), not `(num, den)` tuples — Pillow's writer rejects the tuple form with a `TypeError`.

The SVG vector table is data, one row per attack class:

```python
SVG_ATTACKS = [
    pytest.param("<script>alert(1)</script>", "script", id="script-element"),
    pytest.param("<rect onload='alert(1)'/>", "rect@onload", id="event-handler"),
    pytest.param("<image href='http://x/y.png'/>", "image", id="external-image"),
    pytest.param("<use href='http://x/#a'/>", "use@href", id="external-use"),
    pytest.param("<a href='javascript:alert(1)'><rect/></a>", "a", id="javascript-href"),
    pytest.param("<foreignObject><body/></foreignObject>", "foreignObject", id="foreign-object"),
    pytest.param("<style>@import 'http://x'</style>", "style", id="style-import"),
    pytest.param("<rect fill=\"url('http://x')\"/>", "rect@fill", id="external-url-fill"),
    pytest.param("<rect fill='url(#g)' style='x'/>", "rect@style", id="style-attribute"),
]
DTD_ATTACKS = [
    pytest.param(b"<!DOCTYPE svg [<!ENTITY x SYSTEM 'file:///etc/passwd'>]><svg>&x;</svg>", id="xxe"),
    pytest.param(b"<!DOCTYPE l [<!ENTITY a 'aaaa'><!ENTITY b '&a;&a;&a;&a;'>]><svg>&b;</svg>", id="billion-laughs"),
]
```

## Conventions

- Name: `test_should_<outcome>_when_<condition>`; the Arrange / Act / Assert shape is the explanation, no comments
- One expected condition per assertion — `assert verdict.reason == "polyglot"`, never `in ("polyglot", "unsupported-format")`; a wobbling expectation is split into rows
- No `try`/`except` in a test body; expected exceptions use `pytest.raises(Type, match=...)`; unexpected ones reach the runner
- No `if` / `for` driving assertions — `@pytest.mark.parametrize` with `id=`s that read as the case name
- Every fixture builder returns `bytes` or an `Image.Image`; the test writes to `tmp_path` only when the unit under test takes a `Path`
- A failed deserialisation says what broke: assert on `ValidationError.errors()[0]["loc"]` and `["type"]`, never on the message string
- Tests are order-independent: no module-level image, no shared `BytesIO`, no environment mutation outside `monkeypatch`
- `model`-marked tests assert one geometric fact (corner alpha is 0, centre alpha is 255), never a pixel-exact mask — models drift between wheel versions

## Doubles policy

| Collaborator | Double | Why |
|---|---|---|
| `BackgroundRemover` | a class returning a fixed RGBA image | the Protocol has one method; a fake is four lines |
| `Clock` | a class returning a fixed `datetime` | timestamps in the verdict become assertable |
| `Limits` | the real frozen dataclass with small numbers | it is a value; use it |
| Filesystem | `tmp_path` | real, isolated, deleted |
| `vtracer` | the real wheel | pure, fast, deterministic for a 32 px input |
| `rembg` session | never faked at the session level | fake the Protocol above it instead |

`unittest.mock.patch("upload_worker.metadata.Image")` is the trap: it patches the seam the code should have exposed, proves the test's own wiring, and breaks on the next refactor. If a unit cannot be tested without patching, the fix is a Protocol or a parameter — a `pattern-writer` edit that is in scope for the test task.

## Property tests worth having

```python
@given(width=st.integers(1, 20_000), height=st.integers(1, 20_000),
       print_mm=st.floats(10, 3000, allow_nan=False, allow_infinity=False))
def test_dpi_grade_is_monotonic_in_pixels(width: int, height: int, print_mm: float) -> None:
    smaller = dpi_verdict(width, height, print_mm, print_mm, None)
    larger = dpi_verdict(width * 2, height * 2, print_mm, print_mm, None)
    assert GRADE_ORDER[larger.grade] >= GRADE_ORDER[smaller.grade]
```

Bounded strategies keep the run under a second; never generate images with hypothesis.

## Gate

Inside a plan task marked `Gate: none`, run none of these and report the tests as "written, not run".

- `uv run pytest` green on a laptop with no weights (`model` tests skip, and the skip is reported, not hidden)
- `uv run pytest -m model` green in the CI job that has `U2NET_HOME`
- `uv run mypy src tests` clean
- Every `Rejected.reason` literal appears in at least one test's expected value — a rejection nobody can produce is dead contract

## Handoffs

- Seams that block a test → `pattern-writer`
- The function under test is wrong → `media-processing`
- Container-level checks → `sandboxed-worker` validation list, executed by CI / `qa-api-typescript`
- Review of the tests → `code-review`
