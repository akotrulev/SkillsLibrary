# Code Quality Reviewer Prompt Template

Use this template **only** when the user has approved escalating to a dedicated reviewer subagent (it pushes you past the 2-agent gate). By default the controller runs this review inline instead — see the inline review rubric in `SKILL.md`.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance is ✅.**

```
Task tool (general-purpose):
  description: "Code quality review for Task N"
  prompt: |
    Review the code quality of the change between BASE_SHA and HEAD_SHA.

    DESCRIPTION: [task summary, from implementer's report]
    PLAN_OR_REQUIREMENTS: Task N from [plan-file]
    BASE_SHA: [commit before task]
    HEAD_SHA: [current commit]

    Read the actual diff (git diff BASE_SHA HEAD_SHA). Do not trust any report.
    Check the standard code-quality concerns plus:
    - Does each file have one clear responsibility with a well-defined interface?
    - Are units decomposed so they can be understood and tested independently?
    - Is the implementation following the file structure from the plan?
    - Did this change create new files that are already large, or significantly
      grow existing files? (Don't flag pre-existing sizes — only what this change added.)

    Report findings in the repo review format (see CLAUDE.md):
    | Severity | Location | Issue | Suggested fix |
    with severities blocker / major / minor / nit. Point to the fix; do NOT rewrite
    the code. End with an overall assessment (approved / changes required).
```
