# Photo operations — dominant colours, resize ladder

## Dominant colours

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
- `share` sums to 1.0 across the returned swatches; the UI decides what "near-white background" means, the worker reports.

## Venue-photo resize ladder

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
