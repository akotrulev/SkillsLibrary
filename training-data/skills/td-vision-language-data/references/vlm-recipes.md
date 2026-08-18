# VLM recipes — reference

## Visual-instruction generation (LLaVA-style)

Prompt a strong teacher VLM with the image plus any existing annotations to produce diverse grounded instructions.

```
System: You generate visual instruction/answer pairs for training a vision-language model.
Given the image (and any provided boxes/OCR/caption), write {n} diverse pairs covering:
describe, count, locate, read-text, compare-regions, reason-about-scene, and at least one
UNANSWERABLE question the image does not support. Every answer must be grounded ONLY in the
image — never use outside knowledge. Return JSON [{"q":...,"a":...,"grounded_in":...}].

User: [image] + optional {boxes / ocr / caption}
```

`grounded_in` names the visual evidence — keep it for a groundedness check. Flag `synthetic-review-required`.

## Image dedup — content + perceptual hash

```python
import hashlib, imagehash
from PIL import Image

def content_hash(path):                       # exact-duplicate file dedup
    return hashlib.sha256(open(path,"rb").read()).hexdigest()

def phash(path):                              # near-duplicate (resize/re-encode/watermark)
    return imagehash.phash(Image.open(path))   # cluster at Hamming distance ≤ 6
```

Store each unique image once as `images/<content_hash>.jpg`; records reference it by path. Assign near-dup image clusters to one split (contamination guard).

## CLIP alignment filter (pretraining pairs)

```python
# Score caption-image similarity; drop low-alignment pairs (junk alt-text).
import open_clip, torch
model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
tok = open_clip.get_tokenizer("ViT-B-32")
def clip_score(img, caption):
    with torch.no_grad():
        i = model.encode_image(preprocess(img).unsqueeze(0))
        t = model.encode_text(tok([caption]))
        return torch.cosine_similarity(i, t).item()   # drop below a tuned threshold (~0.25)
```

## Image validation & EXIF/PII strip

```python
from PIL import Image
def clean_image(path, max_side=1024):
    im = Image.open(path); im.verify()             # drop broken/truncated → drop the record too
    im = Image.open(path).convert("RGB")           # drops EXIF (incl. GPS) on re-save
    im.thumbnail((max_side, max_side))             # keep resolution the task needs (OCR: higher)
    return im
```

Also scan for faces/plates/credential screenshots per the dataset's PII policy; record the policy in the card.

## Bounding-box normalization (grounding)

```python
def norm_box(x0, y0, x1, y1, w, h):               # → resolution-independent [0,1]
    return [x0/w, y0/h, x1/w, y1/h]
```

Pick ONE convention per dataset (normalized 0–1 is the safe default) and state it in the card. If the model uses coordinate tokens or a `<box>` string format, emit exactly that.

## OCR / chart targets

- OCR: target = transcribed text; optionally structured (Markdown table, key/value pairs for forms).
- Charts: target = the underlying data table or a structured reading, not just a prose summary.
- Keep source resolution high — small text is unreadable after aggressive downscaling.
