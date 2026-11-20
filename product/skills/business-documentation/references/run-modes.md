# Run modes — REFRESH, AREA and CAPTURE

Read by `be-documenter` when its run is not FULL. A FULL run (no KB yet, or the whole system) runs Steps 1–6 as the agent file states them.

**Done when** the run has run exactly the steps its mode lists below, and its report names the mode.

- **REFRESH** — reconcile the KB against moved code.
  1. Fold the answers, then re-trace the areas in scope.
  2. Verdict every existing statement per `references/reconcile.md`, and escalate each contradiction.
  3. Sweep the class: a system-wide convention change (tenancy, rounding) invalidates every area that assumed the old one.
  4. Update, never rewrite. Re-run examples whose numbers changed; re-capture tasks whose screen or steps changed (with an environment, else `pending`).
  5. A guide in an earlier shape follows reconcile step 3. Close with `doc-lint.py --kept-from <old sha> --dir docs/business-model`, restoring each `fact-kept` WARN or naming the code change that removed it.
- **AREA** — one new or changed area in an existing KB with an area map.
  1. Confirm the area belongs in the map, or extend the map with the next free `AREA-nnn`. Never renumber an id.
  2. Run Steps 2–6 for that area alone, reusing the glossary, the actors and the cross-area flows.
- **CAPTURE** — screenshots for named guides whose `**Screenshots:**` line is `pending`.
  1. Fold the answers, then run the capture pass of *Screenshots* in `SKILL.md` for each named guide and nothing else: sign in as each role, check every bold label against the screen (the screen wins: fix the guide, raise an open question), capture, replace the `pending` line.
  2. No survey, trace or model. With no environment: ask and stop.
