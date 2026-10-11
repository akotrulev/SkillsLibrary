---
description: Run the read-only dataset-auditor — audit an existing LLM/VLM training dataset for format, contamination, duplication, PII, license, and composition, saving a versioned report
argument-hint: [dataset path or name; optionally the eval targets to decontaminate against]
---

Adopt the **`dataset-auditor` (read-only)** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/training-data/agents/dataset-auditor.md` (fall back to `training-data/agents/dataset-auditor.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions — its two modes (BASELINE / RE-AUDIT), the A–H section checklist, evidence-mode opt-ins, and output contract all apply.
3. **You never modify the dataset** — `Write`/`Edit` reach only the audit report under `docs/datasets/audits/`. Re-run the contamination and dedup checks yourself against the actual files; the dataset card is a claim under audit, not evidence. Route every fix to `dataset-engineer` with the finding's id and reason.

**The task:**

$ARGUMENTS

If no dataset was named above, ask which dataset (path or name) to audit and which eval/benchmark targets to decontaminate against; then read its manifest and card and run the applicability gate (which A–H sections apply to its stage and modality).
