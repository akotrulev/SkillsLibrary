---
name: vision-language-data
description: Use when building image-text training data for a small vision-language model (VLM) — captioning, visual QA, OCR, region grounding, and multi-image/interleaved data. Triggers: "build VLM training data", "image captioning dataset", "visual QA / VQA data", "OCR training data", "grounding / bounding-box data for a VLM", "multimodal SFT". Do NOT use for text-only data (`training-data:instruction-sft` etc.), or the base record envelope/splits (`training-data:dataset-formats`).
---

# Training Data — Vision-Language (VLM)

The image-text data a small vision-language model learns from. VLM data is the text domain plus one hard new axis — **the image and the text must actually correspond, the image must survive the pipeline intact, and the model must see the image token where the architecture expects it.** This skill is the multimodal extension across *all* stages (VLM pretraining pairs, VLM SFT, VLM preference, VLM eval); it builds on the text stage skills and `training-data:dataset-formats`' VLM record shape rather than replacing them.

## When to use

- Building image caption / alt-text pretraining or SFT data
- Visual QA (VQA) — questions about an image
- OCR / document understanding (receipts, forms, charts, screenshots)
- Region grounding — bounding boxes / points tied to referring expressions
- Multi-image or interleaved image-text data
- VLM preference or eval data (chosen/rejected on an image; scored visual eval)

## When NOT to use

- Text-only data of any stage → `training-data:instruction-sft` / `training-data:preference-data` / `training-data:pretraining-corpus` / `training-data:eval-sets`
- The base record envelope, splits, sharding → `training-data:dataset-formats` (this skill adds the image parts)
- Dedup/decontam algorithms → `training-data:data-quality` (this skill adds image dedup)

## The VLM record — image as a typed content part

Use the `training-data:dataset-formats` VLM shape: images are typed parts inside `content`, referenced by **relative `path` to a content-hashed file** in a sibling `images/` directory — never base64 in the JSONL, never a remote URL. The image token placement matters:

- **The image part comes before the text that refers to it** in the message, matching how VLM chat templates interleave `<image>` placeholders. Get the order wrong and the model associates the image with the wrong text.
- **Record `width`/`height`** on the image part — resolution handling (tiling, resize) is architecture-specific and downstream needs the original dimensions, especially for grounding coordinates.
- **`meta.n_images`** and **`meta.task`** (`caption|vqa|ocr|grounding`) drive balancing and let the auditor slice by modality task.

## The stages, multimodally

### VLM pretraining — alignment pairs

Large image-caption corpora align the vision encoder with the language model. Short, factual, densely-descriptive captions; volume matters but **caption-image correspondence matters more** — web alt-text is noisy (SEO junk, "image", filenames). Filter hard (below). Sources: LAION-style pairs, COCO/Conceptual Captions, DataComp, or synthetic dense captions from a teacher VLM (`training-data:synthetic-generation`, with an image input).

### VLM SFT — visual instruction tuning

The LLaVA pattern: an image + an instruction + a grounded answer. Build it by prompting a strong teacher VLM with the image (and any existing annotations — boxes, OCR, captions) to produce diverse QA, reasoning, and description instructions about it. Cover the task taxonomy (`training-data:instruction-sft`) *plus* visual tasks: describe, count, locate, read text, compare regions, reason about the scene, refuse when the image doesn't support the ask. **The answer must be grounded in the image** — a teacher that answers from prior knowledge instead of the pixels produces confident hallucinations the student inherits.

### VLM preference — chosen/rejected on an image

Same prompt+image, two responses, prefer the one that is more **grounded** (describes what's actually there, doesn't hallucinate objects). Object-hallucination is the #1 VLM failure mode; preference data targeting it is high-value. Judge with a VLM judge that *sees the image* — a text-only judge can't tell grounded from hallucinated. Pin and calibrate it (`training-data:synthetic-generation`).

### VLM eval — scored visual tasks

Public: VQAv2, TextVQA, DocVQA, ChartQA, MMMU, POPE (hallucination). Build a domain eval with human-verified answers. Same isolation/canary/decontamination rules as `training-data:eval-sets`. **Image decontamination too** — the same image in train and test leaks even if the question differs.

## Task-specific payloads

- **Captioning** — `assistant` text is the caption. Decide the style (terse alt-text vs dense paragraph) and keep it consistent per dataset.
- **VQA** — `user` asks, `assistant` answers grounded in the image. Include unanswerable questions ("is there a dog?" when there isn't) so the model learns to say no.
- **OCR / documents** — the target is the transcribed text, optionally with layout/structure (Markdown table, key-value pairs). High-resolution images matter; note the resolution the model must support. Charts → the underlying data or a structured reading.
- **Grounding** — referring expression → bounding box. Store boxes in a **stated, consistent coordinate convention**: normalized `[x0,y0,x1,y1]` in 0–1 (resolution-independent, the safe default) or absolute pixels — pick one, put it in the card, and if the model uses a special coordinate-token format, emit that. A box in the wrong convention teaches the model to point at nothing.
- **Multi-image / interleaved** — multiple image parts in order; the text refers to them positionally ("the first image…"). Keep `n_images` and the order stable.

## Image handling — the pipeline that text data doesn't have

- **Dedup images by content hash** (`training-data:data-quality` extended to bytes): the same picture referenced by many records is many `path`s to one file. Near-dup images (resize, re-encode, watermark) via perceptual hash (pHash) or CLIP-embedding similarity — near-duplicate images across the train/test line contaminate the visual eval just like text does.
- **Normalize format and validate every image loads** — a broken/truncated image is a broken example; drop it and its record. Convert to a consistent format (JPEG/PNG), cap dimensions to what the model ingests, but **keep enough resolution for the task** (OCR and small-text VQA die at low resolution).
- **Filter caption-image correspondence** for pretraining pairs: CLIP-score the pair and drop low-alignment pairs (junk alt-text). This is the visual analog of text quality filtering.
- **Strip image PII/EXIF** — faces, license plates, GPS in EXIF, screenshots with credentials. VLMs regurgitate what they see; image PII is a real leak. Record the policy in the card.
- **Image licensing is content licensing** — a permissive caption on a copyrighted image doesn't launder the image. Track the image license in `source`/`license`.

## Quality gate and output

Route through `training-data:data-quality` (text dedup/PII/decontam) *and* the image passes above (content-hash dedup, pHash near-dup, load-validation, CLIP-alignment for pretraining, EXIF/PII strip). Split by dedup cluster over **both** the text and the image (an image and its paraphrased caption both go to one split). Output in the VLM record shape, images content-hashed in `images/`, everything in the card including the coordinate convention, resolution target, and image-license breakdown.

## Hard rules

- **Image-text correspondence is the first quality bar** — CLIP-filter pretraining pairs, ground SFT answers in the pixels, judge preference with a VLM that sees the image.
- **Images referenced by content-hashed relative path**, deduped by content and perceptual hash; **decontaminate images**, not just text.
- **Grounding uses one stated coordinate convention** recorded in the card.
- **Validate every image loads and keep task-appropriate resolution**; drop broken images and their records.
- **Strip image PII/EXIF**; track image licenses separately from caption licenses.
- **Include unanswerable/negative visual cases** — the top VLM failure is hallucinating objects that aren't there.

## References

- `references/vlm-recipes.md` — the LLaVA-style visual-instruction generation prompt, CLIP-alignment and pHash-dedup snippets, the bounding-box normalization helper, and the OCR/chart target formats.
