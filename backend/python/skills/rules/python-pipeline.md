---
paths:
  - "**/src/**/*.py"
---

<!-- be-python rules v1 (2026-11-03): upload pipeline. Installed by /be-python:rules; edit the paths above to where this project keeps its worker package. -->

# Upload pipeline standards (Pillow, SVG, rembg)

Severity tags as in the core Python rules. The codebase wins where it consistently does otherwise.

- Order is fixed: validate → normalise → strip → operation → encode. Only `sniff` and `sanitize_svg` take bytes; every other step takes the normalised `Image.Image`. *blocker*
- Bytes decide the format, never the extension or declared type. A mismatch is `polyglot`, never re-labelled; a format outside the class allowlist is `unsupported-format`. *blocker*
- `Image.MAX_IMAGE_PIXELS` is the ceiling, never `None`, plus an explicit `width * height` check. *blocker*
- `LOAD_TRUNCATED_IMAGES` stays `False`; `verify()` then `load()` on fresh handles; `n_frames > 1` is `animated` for logos and photos. *major*
- SVG parses with `defusedxml` (`forbid_dtd`, `forbid_entities`, `forbid_external`), never `xml.etree`, `lxml` or `bleach`. *blocker*
- SVG passes an element and attribute allowlist on local names; `on*`, `<style>`, `style=`, foreign namespaces, `data:`, `javascript:` and any non-`#id` `href` or `url(` are rejected. A bad SVG is rejected, never stripped. *blocker*
- Every SVG leaving the worker passes `sanitize_svg`, VTracer's too; user SVG is never rasterised here. *major*
- Metadata strip: `exif_transpose`, then `convert(mode)`, then `Image.frombytes`; never `copy()`, `save(exif=b"")` or `**im.info`. ICC is the one key kept; `save()` gets an explicit argument list with no `exif=` or `xmp=`. *blocker*
- DPI is graded from pixels against the print size, never `info["dpi"]`; colours exclude alpha < 128 after a thumbnail; the ladder uses `thumbnail` (never upscales) and makes WebP and JPEG from one copy; rembg gets a downsized input and writes PNG. *major*
- Weights load only from the baked `U2NET_HOME`, checked at startup; no download, no `rembg` CLI. *major*
- Each job runs in a spawned child that sets `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_FSIZE`, `RLIMIT_NPROC` before loading the model, under a wall-clock kill; never `fork` with a loaded session. *major*
- The verdict holds relative output paths and an exception class name: no absolute path, hostname, traceback or payload. *major*
- Rejection reasons are a closed `Literal` mirrored in the TypeScript contract; a new one is reported as a two-sided change. *major*
