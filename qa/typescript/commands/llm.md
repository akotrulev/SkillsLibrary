---
description: Run the step-by-step qa-llm-typescript workflow — build an eval dataset, assert properties/rubrics/grounding, red-team
argument-hint: [the LLM feature to eval or red-team]
---

Adopt the **`qa-llm-typescript` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/typescript/agents/qa-llm-typescript.md` (fall back to `qa/typescript/agents/qa-llm-typescript.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

**The task:**

$ARGUMENTS

If no task was given above, run the **orientation pass** — detect the existing test project layout, the LLM feature's shape (chatbot / RAG / summarizer / extraction / agent) and any existing eval suite — report the current-state map, and ask what to author, extend, or review.
