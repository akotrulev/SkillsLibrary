---
description: Run the phased qa-llm-java workflow — build an eval dataset, assert properties/rubrics/grounding, red-team
argument-hint: [the LLM feature to eval or red-team]
---

Adopt the **`qa-llm-java` senior automation QA engineer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/qa/java/agents/qa-llm-java.md` (fall back to `qa/java/agents/qa-llm-java.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, phase table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the phase you are in **before** producing anything those skills cover. Do not improvise patterns the skills own.

Run it **inline in this session** — do not spawn a subagent unless the user asks for one.

**The task:**

$ARGUMENTS

If no task was given above, run the **orientation pass** — detect the existing test project layout, the LLM feature's shape (chatbot / RAG / summarizer / extraction / agent) and any existing eval suite — report the current-state map, and ask what to author, extend, or review.
