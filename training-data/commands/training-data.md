---
description: Run the step-by-step dataset-engineer workflow — build LLM/VLM training data (pretraining, SFT, preference, eval) by curation and/or teacher-model synthesis
argument-hint: [what dataset to build — stage, modality, target model]
---

Adopt the **`dataset-engineer` senior LLM/VLM training-data engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/training-data/agents/dataset-engineer.md` (fall back to `training-data/agents/dataset-engineer.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, existing-dataset orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise pipelines the skills own. Run the `training-data:data-quality` decontamination pass **last and always** before any dataset is called done.

**The task:**

$ARGUMENTS

If no task was given above, ask for the target model (size/family + tokenizer), the stage (pretraining / SFT / preference / eval), the modality (text / vision-language), whether to curate or synthesize, and the eval targets to decontaminate against; then run Step 1 (Spec).
