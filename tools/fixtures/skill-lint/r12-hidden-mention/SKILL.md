---
name: r12-hidden-mention
description: Use when a hidden skill is named but not invoked. Triggers "lint r12 mention". Not for invocations (r12-hidden-invoke).
disable-model-invocation: true
---

# Hidden mentions

- Conflicts go to the `business-analyst` agent (it loads `dev:secret-skill`, which you cannot invoke yourself).
- When running against a cloud account, `dev:secret-skill` supplies the token.
- A failing run names the alerts (cross-link `dev:secret-skill`).
- Never run `dev:secret-skill` from a main session.
