---
name: be-python-media-processing
description: Use when writing the Python code that processes customer-uploaded images with Pillow 12, hostile input assumed — content-sniffed validation, SVG sanitising, EXIF/GPS/XMP strip, rembg, VTracer tracing, print-DPI verdict, dominant colours, resize ladders. Triggers "validate this upload", "strip GPS from photos", "sanitise the SVG", "is this 300 DPI". Do NOT use for the Dockerfile (`sandboxed-worker`), package skeleton (`pattern-writer`) or tests (`unit-testing`).
---

# Media Processing — Generator

Writes the image-pipeline modules of a Python upload worker. Every function here assumes the bytes are hostile: a polyglot, a decompression bomb, an SVG with a script, a JPEG that lies about its size. **The pipeline is a fixed order** — validate → normalise → strip → the requested operation → encode — and no operation runs on bytes that did not pass the step before it.

## Version policy

Pillow **12.x primary, 11.x supported** (detect via `uv lock` / `PIL.__version__`); the metadata behaviour below is pinned by tests precisely because `save()` fallbacks have moved between minors. `rembg` 2.0.x, `onnxruntime` 1.2x, `vtracer` 0.6.x, `defusedxml` 0.7. Interpreter per `pattern-writer`.

## When to use

- Any function that opens, parses, converts, or encodes an upload
- Deciding the rejection reasons and the verdict shape the TypeScript side consumes
- Choosing rembg model / VTracer parameters for a logo or a photo

## When NOT to use

- Process isolation, memory / CPU / time limits, `--network none` → `sandboxed-worker` (this skill assumes it runs inside that)
- Package layout, `Result`, settings, logging → `pattern-writer`
- Fixture builders and the hostile suite → `unit-testing`

## Inputs needed

1. Allowed formats for this upload class (logo: `png svg jpeg webp`; venue photo: `jpeg png webp heic?`)
2. Size ceilings: bytes, pixels, SVG bytes and element count
3. Which operations the job may request and their parameters (print size for the DPI verdict, colour count, resize ladder)
4. Output encoding the consumer expects (PNG for cut-outs, SVG for traces, WebP + JPEG for photos)

## Pipeline contract

```python
type Operation = RemoveBackground | TraceToSvg | DpiVerdict | DominantColours | ResizeLadder


@dataclass(frozen=True, slots=True)
class Sniffed:
    format: Literal["png", "jpeg", "webp", "svg"]
    width: int
    height: int
    byte_size: int


type ValidationResult = Ok[Sniffed] | Rejected
```

Rejection reasons are a closed `Literal` (`unsupported-format` · `polyglot` · `too-large` · `too-many-pixels` · `truncated` · `unsafe-svg` · `animated` · `timeout` · `resource-exceeded`) mirrored in the TypeScript contract. The last two are produced by the isolation layer (`sandboxed-worker`), not by the pipeline. A new reason is a contract change on both sides.

## Step 1 — Content-sniffed validation

The declared MIME / extension is a claim. The bytes decide.

```python
def sniff(payload: bytes, declared: str, limits: Limits) -> ValidationResult:
    if len(payload) > limits.max_bytes:
        return Rejected("too-large", f"{len(payload)} bytes")
    if looks_like_xml(payload):
        return sniff_svg(payload, declared, limits)
    return sniff_raster(payload, declared, limits)


def sniff_raster(payload: bytes, declared: str, limits: Limits) -> ValidationResult:
    try:
        with Image.open(io.BytesIO(payload)) as probe:
            fmt = (probe.format or "").lower()
            width, height = probe.size
            frames = getattr(probe, "n_frames", 1)
    except Image.DecompressionBombError:
        return Rejected("too-many-pixels", "header exceeds pixel ceiling")
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        return Rejected("unsupported-format", type(exc).__name__)
    if fmt not in limits.raster_formats:
        return Rejected("unsupported-format", fmt or "unknown")
    if fmt != declared_to_pillow(declared):
        return Rejected("polyglot", f"declared {declared}, sniffed {fmt}")
    if width * height > limits.max_pixels:
        return Rejected("too-many-pixels", f"{width}x{height}")
    if frames > 1:
        return Rejected("animated", f"{frames} frames")
    try:
        with Image.open(io.BytesIO(payload)) as check:
            check.verify()
        with Image.open(io.BytesIO(payload)) as decode:
            decode.load()
    except (OSError, SyntaxError) as exc:
        return Rejected("truncated", type(exc).__name__)
    return Ok(Sniffed(fmt, width, height, len(payload)))
```

Rules the code above encodes:

- **Set `Image.MAX_IMAGE_PIXELS` explicitly at import** to the project ceiling (`limits.max_pixels`); Pillow's default is ~89 M and only warns at 1× and raises at 2×. Rely on the explicit `width * height` check anyway — the ceiling applies to the *header*, and the header is what a bomb lies in.
- **`ImageFile.LOAD_TRUNCATED_IMAGES` stays `False`.** A truncated file is a rejection, not something to render half of.
- **`verify()` and `load()` need fresh handles**; `verify()` invalidates the image. Both run, in that order: `verify` catches structural damage cheaply, `load` proves the pixel data decodes.
- **Polyglots**: a file whose sniffed format differs from the declared one is rejected, not silently re-labelled — the mismatch is the attack signal (`GIFAR`, PNG-with-trailing-SVG, JPEG-with-PHP).
- **Animated inputs are rejected** for logos and photos; `n_frames > 1` on PNG (APNG), WebP and GIF.
- Formats outside the allowlist (TIFF, BMP, PSD, ICO, HEIC) are `unsupported-format` even though Pillow can open some of them: each extra decoder is attack surface.
- **A polyglot whose leading bytes match the declared type passes the sniffer** (a real PNG with an SVG appended is, to Pillow, a PNG). The defence is Step 3: every output is built from decoded pixels, never from the input bytes, so the trailing payload never leaves the worker. The sniffer catches the mismatch class; the re-encode neutralises the rest. Both are tests.

`looks_like_xml` checks the first non-whitespace bytes for `<?xml`, `<svg`, or a UTF-8 BOM followed by either; never trust the extension.

## Step 2 — SVG sanitising

There is no maintained Python DOMPurify; sanitise by **allowlist**, with a hardened parser.

```python
import xml.etree.ElementTree as ET
from defusedxml import DefusedXmlException
from defusedxml import ElementTree as SafeET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ALLOWED_ELEMENTS = frozenset({"svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline",
                              "polygon", "text", "tspan", "defs", "linearGradient", "radialGradient",
                              "stop", "clipPath", "mask", "title", "desc", "symbol", "use"})
ALLOWED_ATTRIBUTES = frozenset({"id", "class", "d", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r",
                                "rx", "ry", "width", "height", "viewBox", "fill", "stroke",
                                "stroke-width", "stroke-linecap", "stroke-linejoin", "opacity",
                                "fill-opacity", "stroke-opacity", "transform", "points", "offset",
                                "stop-color", "stop-opacity", "gradientUnits", "clip-path", "mask",
                                "font-family", "font-size", "font-weight", "text-anchor", "href"})
FORBIDDEN_ELEMENTS = frozenset({"script", "foreignObject", "image", "a", "animate", "set", "style",
                                "iframe", "video", "audio", "feImage"})


def sanitize_svg(payload: bytes, limits: Limits) -> Ok[bytes] | Rejected:
    if len(payload) > limits.max_svg_bytes:
        return Rejected("too-large", f"{len(payload)} bytes")
    try:
        root = SafeET.fromstring(payload, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (DefusedXmlException, SafeET.ParseError) as exc:
        return Rejected("unsafe-svg", type(exc).__name__)
    if local(root.tag) != "svg":
        return Rejected("unsupported-format", f"root <{local(root.tag)}>")
    element_count = 0
    for element in list(root.iter()):
        element_count += 1
        if element_count > limits.max_svg_elements:
            return Rejected("unsafe-svg", "element ceiling")
        name = local(element.tag)
        if name in FORBIDDEN_ELEMENTS or name not in ALLOWED_ELEMENTS:
            return Rejected("unsafe-svg", f"<{name}>")
        for attribute in list(element.attrib):
            attr_name = local(attribute)
            value = element.attrib[attribute]
            if attr_name.startswith("on") or attr_name not in ALLOWED_ATTRIBUTES or unsafe_reference(attr_name, value):
                return Rejected("unsafe-svg", f"{name}@{attr_name}")
    return Ok(SafeET.tostring(root, encoding="utf-8", xml_declaration=True))
```

- **Reject, do not strip.** A logo with a `<script>` in it is not a logo with a bug; it is an attack, and the verdict says so. Stripping produces "sanitised" files whose behaviour nobody can predict.
- `unsafe_reference` rejects `href` / `xlink:href` unless it is a same-document fragment (`#id`); rejects any `url(` in a style-bearing attribute that is not `url(#id)`; rejects `data:` URIs; rejects `javascript:` case-insensitively after entity decoding.
- `forbid_dtd` kills XXE and billion-laughs; `forbid_external` kills remote entity fetches even though the sandbox has no network. Defence in depth is the point of a sandbox, not a substitute for it.
- Depth: `root.iter()` is already bounded by the element ceiling; add an explicit depth walk when nested `<g>` count matters for a renderer.
- `<style>` is forbidden; presentation attributes carry everything a logo needs. `<use>` survives only with a fragment `href`.
- Namespaces: compare on the local name; reject any element or attribute in a namespace other than SVG or xlink. `register_namespace` at import is what keeps `tostring` from emitting `ns0:svg`, which some renderers refuse.

Every SVG that leaves the worker — including one VTracer produced — passes through `sanitize_svg`. That invariant is a test.

## Step 3 — Normalise orientation, strip metadata

Order matters: apply orientation **before** stripping, or the strip throws the rotation away.

```python
def normalised_pixels(payload: bytes, target_mode: Literal["RGB", "RGBA"]) -> Image.Image:
    with Image.open(io.BytesIO(payload)) as original:
        icc = original.info.get("icc_profile")
        oriented = ImageOps.exif_transpose(original).convert(target_mode)
        clean = Image.frombytes(oriented.mode, oriented.size, oriented.tobytes())
    if icc:
        clean.info["icc_profile"] = icc
    return clean
```

- `Image.frombytes(...)` builds an image with an **empty `info`**: no EXIF, no GPS, no XMP, no JPEG comment, no PNG `tEXt` / `iTXt`, no thumbnail. This is deliberate over `copy()` (keeps every `info` key) and over `save(exif=b"")` — measured on Pillow 11.3: a JPEG saved with `exif=b""` still carries the original **comment**, because `save` falls back to `im.info` for it. One extra memory copy is the cost.
- **Convert mode before `frombytes`**, not after: a palette (`P`) image loses its palette through `frombytes`, and `LA` / `CMYK` / `I;16` are not what any operation wants. `RGBA` for transparency-bearing classes (logos), `RGB` for photos, decided by the upload class.
- The ICC profile is the one metadatum to keep: dropping it shifts colours. It carries no location or identity.
- Encode with an explicit argument list and nothing else: `clean.save(buf, "PNG", optimize=True)`; `clean.save(buf, "JPEG", quality=85, optimize=True, progressive=True, icc_profile=clean.info.get("icc_profile"))`; `clean.save(buf, "WEBP", quality=82, method=6, icc_profile=...)`. Never pass `exif=` or `xmp=`.
- The test that proves it (unit-testing skill): a fixture JPEG with a GPS IFD and an XMP packet goes in; the output's `getexif()` is empty, `info` contains none of `exif` `xmp` `comment` `gps`, and the pixel data still matches the oriented input. **Any Pillow upgrade that changes fallback behaviour turns that test red**, which is what pins the recipe.

## Step 4 — The operations

### Background removal (rembg)

```python
class RembgRemover:
    def __init__(self, session: BaseSession) -> None:
        self._session = session

    def remove(self, rgba: Image.Image) -> Image.Image:
        return remove(rgba, session=self._session, post_process_mask=True)
```

- The session is created **once**, at the composition root: `new_session("u2net")` (or `isnet-general-use` for finer edges on logos; `birefnet-general` is larger and slower — choose per upload class and pin it). Creating a session per job re-reads a 170 MB model.
- **Weights are baked into the image at build time** under `U2NET_HOME` (`sandboxed-worker`); at runtime the first `new_session` must find them on disk, and a missing file is a startup failure, never a download attempt. There is no network to download from, and a worker that starts anyway and fails on the first job is a false-healthy container.
- Input to `remove` is the *normalised* RGBA image, never the raw upload. Output is RGBA with a soft alpha; `alpha_matting=True` improves hair and fine edges at ~3× the cost — expose it per upload class, not per request.
- Output encoding is PNG (alpha). Cut-outs are never re-encoded to JPEG.
- The call is CPU-bound and can take seconds on a large photo; it runs inside the per-job subprocess with the memory and time limits from `sandboxed-worker`, and the caller downsizes to the ceiling (long edge ≤ 2048) before inference. Inference output is upscaled only for the mask, never the RGB.

### Raster-to-vector tracing (VTracer)

```python
def trace_to_svg(rgba: Image.Image, params: TraceParams, scratch: Path) -> Ok[bytes] | Rejected:
    source = scratch / "in.png"
    target = scratch / "out.svg"
    rgba.save(source, "PNG")
    vtracer.convert_image_to_svg_py(
        str(source), str(target),
        colormode=params.colormode, hierarchical="stacked", mode="spline",
        filter_speckle=params.filter_speckle, color_precision=params.color_precision,
        layer_difference=params.layer_difference, corner_threshold=params.corner_threshold,
        length_threshold=params.length_threshold, splice_threshold=params.splice_threshold,
        path_precision=params.path_precision,
    )
    return sanitize_svg(target.read_bytes(), limits)
```

- Logos: `colormode="color"`, `filter_speckle=4`, `color_precision=6`, `layer_difference=16`, `corner_threshold=60`. Single-colour marks: `colormode="binary"`. These are starting points; expose them as a frozen `TraceParams` with defaults, not as free-form kwargs from the job.
- Tracing a photograph produces megabytes of paths; the caller enforces `max_svg_bytes` on the result and reports `too-large`, and the `sandboxed-worker` CPU limit ends a pathological trace. Quantise (`Image.quantize(colors=16)`) before tracing anything above 512 px on the long edge.
- The scratch directory is the job's `tmpfs` (`sandboxed-worker`), never a shared path, and is removed with the job.
- The result passes through `sanitize_svg` like any other SVG (Step 2 invariant).

### DPI verdict

Metadata DPI is a hint; the print size is the truth.

```python
@dataclass(frozen=True, slots=True)
class DpiVerdict:
    effective_dpi: float
    metadata_dpi: float | None
    grade: Literal["print-ready", "acceptable", "web-only"]


def dpi_verdict(width: int, height: int, print_width_mm: float, print_height_mm: float, metadata_dpi: float | None) -> DpiVerdict:
    effective = min(width / (print_width_mm / 25.4), height / (print_height_mm / 25.4))
    grade = "print-ready" if effective >= 300 else "acceptable" if effective >= 150 else "web-only"
    return DpiVerdict(round(effective, 1), metadata_dpi, grade)
```

- `metadata_dpi` comes from `im.info.get("dpi")` (Pillow converts PNG `pHYs` pixels/metre to inches for you); it is reported so the UI can say "the file claims 72 DPI but has enough pixels", never used for the grade.
- A vector upload (SVG) has no DPI; the verdict is `print-ready` with `effective_dpi = inf` or the operation is not offered for SVG — pick one in the contract, do not return `None` grades.
- Thresholds are constants with names (`PRINT_READY_DPI = 300`), not literals inside the comparison.

### Dominant colours

```python
def dominant_colours(rgba: Image.Image, count: int) -> list[Swatch]:
    sample = rgba.convert("RGBA")
    sample.thumbnail((200, 200), Image.Resampling.LANCZOS)
    opaque = [px[:3] for px in sample.getdata() if px[3] >= 128]
    if not opaque:
        return []
    flat = Image.new("RGB", (len(opaque), 1))
    flat.putdata(opaque)
    quantised = flat.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    palette = quantised.getpalette()[: count * 3]
    counts = sorted(quantised.getcolors() or [], reverse=True)
    total = sum(n for n, _ in counts)
    return [Swatch(hex=rgb_to_hex(palette[i * 3 : i * 3 + 3]), share=round(n / total, 3)) for n, i in counts]
```

- Transparent pixels are excluded before quantising, or every cut-out's dominant colour is black.
- Thumbnail first: colour share does not need 20 M pixels, and `getdata` on the full image is the slowest line in the worker.
- Median-cut in Pillow needs no numpy; use k-means only when the project already ships numpy and the palette quality complaint is real.
- `share` sums to 1.0 across the returned swatches; the UI decides what "near-white background" means, the worker reports.

### Venue-photo resize ladder

```python
LADDER = ((320, "thumb"), (1024, "card"), (2048, "hero"))


def resize_ladder(rgb: Image.Image, scratch: Path) -> list[Rendition]:
    renditions = []
    for long_edge, name in LADDER:
        copy = rgb.copy()
        copy.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
        webp = scratch / f"{name}.webp"
        copy.save(webp, "WEBP", quality=82, method=6, icc_profile=rgb.info.get("icc_profile"))
        jpeg = scratch / f"{name}.jpg"
        copy.save(jpeg, "JPEG", quality=85, optimize=True, progressive=True, icc_profile=rgb.info.get("icc_profile"))
        renditions.append(Rendition(name, copy.size, webp, jpeg))
    return renditions
```

- `thumbnail` never upscales; a 600 px photo yields a 600 px "hero", and the verdict reports the actual size so the UI can warn.
- Input is the normalised (oriented, stripped, `RGB`) image. `draft("RGB", (2048, 2048))` on the original JPEG before `load()` halves decode time for very large photos; apply it inside `normalised_pixels` when the class is photo.
- Colour: if the ICC profile is not sRGB, convert with `ImageCms.profileToProfile(..., ImageCms.createProfile("sRGB"))` once, then keep no profile. Web renderers assume sRGB.
- WebP is the primary rendition, JPEG the fallback; both from the same resized copy so they match pixel for pixel.

## Verdict shape (what leaves the worker)

```python
class Verdict(BaseModel):
    job_id: str
    status: Literal["accepted", "rejected"]
    reason: RejectionReason | None = None
    detail: str | None = None
    sniffed: SniffedOut | None = None
    outputs: list[OutputRef] = []
    timings_ms: dict[str, int] = {}
```

Written as one JSON document to stdout (or the HTTP response); output files go to the job's output directory and are referenced by relative path only. No absolute paths, no hostnames, no stack traces — the exception class name in `detail` is enough for the TypeScript side; the traceback goes to the structured log.

## Rules

- Every function takes the normalised `Image.Image`, not bytes, except the two that own bytes: `sniff` and `sanitize_svg`
- `with Image.open(...)` always; no handle outlives its `with`
- No format inferred from the extension; no `Image.open(path)` on a user-controlled path — open from bytes the sniffer accepted
- Explicit `save()` argument lists; never forward `**im.info`
- Constants for every threshold (`MAX_LONG_EDGE_FOR_INFERENCE`, `PRINT_READY_DPI`, `LADDER`)
- No numpy, opencv, scikit-image, cairosvg, or libmagic unless the project already depends on them — each is a native decoder with its own CVE history

## What NOT to do

- No `bleach` / `lxml.html.clean` for SVG — one is deprecated, the other is HTML-shaped and misses SVG vectors
- No `cairosvg` / `resvg` / a browser to rasterise user SVG inside the worker — rendering untrusted SVG is a different threat model; if a PNG preview of an SVG is needed, trace the other direction or render outside this container
- No `Image.MAX_IMAGE_PIXELS = None`
- No `LOAD_TRUNCATED_IMAGES = True`
- No re-labelling a polyglot to its sniffed type
- No stripping a bad SVG into a "safe" one
- No model download at runtime; no `rembg` CLI subprocess where the library call exists

## Handoffs

- Package skeleton, `Result`, settings, logging → `pattern-writer`
- Process isolation, limits, weights baked into the image, `--network none` → `sandboxed-worker`
- Fixture builders (GPS JPEG, header-only bomb, polyglot, script SVG) and the suite → `unit-testing`
- Review of the pipeline → `code-review`
