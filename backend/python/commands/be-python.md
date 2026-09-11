---
description: Run the step-by-step be-python workflow — build, fix, extend or review the sandboxed Python upload worker (validation, SVG sanitising, EXIF strip, rembg, VTracer, DPI, colours, resize, hardened container, pytest)
argument-hint: [what to build, fix, or extend]
---

Adopt the **`be-python` senior Python backend / worker developer** role for this task.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/backend/python/agents/be-python.md` (fall back to `backend/python/agents/be-python.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task — its skill-loading protocol, operating rules, brownfield orientation pass, step table, and output contract all apply.
3. Load the `SKILL.md` files that definition names for the step you are in **before** producing anything those skills cover. Do not improvise the validation, sanitiser, metadata-strip, or isolation recipes the skills pin.

**The task:**

$ARGUMENTS

If no task was given above, run the brownfield **orientation pass** against the current repo (detect the interpreter and Pillow major, the lint/type/test state, the job-ingress shape, the pipeline modules, the seams and fixture builders worth reusing), report the current-state map, and ask what to build, fix, or extend.
