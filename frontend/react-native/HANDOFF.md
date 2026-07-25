# `fe-react-native` — session handoff

**Last session:** 2026-07-12 — completed **Node 0 (Groundwork)** + **Node 1 (Foundations A)**.
**Full build plan + node breakdown + version policy + web→native delta table:** see `PLAN.md` (read it first).

## What exists now

```
frontend/react-native/
  PLAN.md                              # the build plan — READ FIRST
  HANDOFF.md                           # this file
  vendor/react-native-guidelines/      # the Vercel seed (restructured, fenced)
    SKILL.md   (name: vercel-react-native-skills, "Do NOT use directly" clause added)
    metadata.json  (organization → "Vercel Engineering")
    rules/     (35+ impact-ranked rules; AGENTS.md = compiled full doc)
    AGENTS.md, README.md
  skills/
    reference/SKILL.md                 # DONE — RN mental model, no-RSC, New Arch, threads, atomic taxonomy, web↔RN map, rules index
    project-scaffold/SKILL.md          # DONE — create-expo-app, Expo Router, dev-client/EAS, app.json/config plugins, folder layout, quality gates
  agents/                              # empty — agent is Node 6
```

## Locked decisions (do not re-litigate)

- **Full stack adaptation** (not a vendored-seed-only path) — user chose this on 2026-07-12.
- **Version policy:** Expo SDK 56 primary (RN 0.85 / React 19.2 / Hermes v1) · SDK 54–55 supported · SDK 53 floor. New Architecture is the always-on baseline (never author an old-arch primary recipe). Expo Router primary (its own RN-Navigation fork; don't co-install `react-navigation`) / bare React Navigation fallback. Expo-managed + dev client + EAS primary / bare fallback.
- **20 skills** (parity map to fe-react's 21 in PLAN.md): dropped `seo-discoverability` + `pwa-offline`; added `navigation` + `offline-first`.
- **Testing:** Jest + React Native Testing Library (dev-side); E2E (Maestro/Detox) is the `qa-mobile-typescript` peer.
- **testID** replaces `data-testid`; `missing-testids.md` handshake preserved.

## Authoring rules (apply to every remaining skill)

- Mirror the matching `frontend/react/skills/<same-name>/SKILL.md` shape/voice, RN-adapted; research current Expo/RN docs first.
- Frontmatter `name: fe-react-native-<skill>`, description **≤ 1000 chars** (verified with the python snippet below), Triggers + When-NOT-to-use routing to siblings, no SKILL.md > 500 lines.
- Seed-fed skills (see PLAN's seed column: performance, motion, ui-conventions, navigation, styling, responsive-design, state-management, generator, localization, reference, project-scaffold) point into `../../vendor/react-native-guidelines/rules/<rule>.md` by exact filename (list them from `ls vendor/react-native-guidelines/rules/`).

## Next session → **Node 2 — Foundations B**

Build: `state-management` · `component-library` · `styling` · `responsive-design`. Then tick Node 2 in PLAN.md and rewrite this HANDOFF.

Remaining after that: Node 3 (feature build A) → Node 4 (feature build B) → Node 5 (quality) → Node 6 (test+review+agent) → Node 7 (marketplace + CLAUDE.md wiring + verification). Nothing is wired into any plugin or CLAUDE.md yet — the stack stays under-construction until Node 7.

## Description-length check
```bash
python3 -c "
import re
t=open('SKILL.md').read()
m=re.search(r'^description:\s*(.*?)\n(?=[a-z_]+:|---)',t,re.S|re.M)
print(len(' '.join(m.group(1).split())))"
```
