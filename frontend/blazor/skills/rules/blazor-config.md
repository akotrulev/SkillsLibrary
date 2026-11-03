---
paths:
  - "**/*.Client.csproj"
  - "**/wwwroot/appsettings*.json"
  - "**/wwwroot/{manifest.json,manifest.webmanifest}"
  - "**/wwwroot/service-worker*.js"
---

<!-- fe-blazor rules v1 (2026-11-03): project, config and PWA. Installed by /fe-blazor:rules; add this project's Blazor host .csproj, appsettings and Program.cs to the paths above. -->

# Blazor project, configuration and PWA standards

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**.

- Everything in `wwwroot`, `wwwroot/appsettings*.json` included, ships to the browser: no secret or server-only setting there, and no secret in any committed config. *blocker*
- The `.Client` project references no EF Core or server-only package. *major*
- Base addresses and external links come from configuration, never a literal or `localhost` fallback. *major*
- Nullable, `TreatWarningsAsErrors` and Central Package Management on: no `Version=` on a `PackageReference`. *minor*
- Never raise the TFM or the component library's major as a side effect; the library major is pinned to the TFM's line. *major*
- A localized WASM app keeps `InvariantGlobalization=false` and loads ICU data within the size budget. *major*
- WASM AOT only for measured CPU-bound work, never a CRUD UI. *minor*
- Offline is WASM only; Interactive Server is at most installable. *major*
- Caching lives in `service-worker.published.js`, precaching from `service-worker-assets.js`, never a hand-kept list. *major*
- A new worker reaches users through a skip-waiting prompt or a documented next-launch update. *major*
- Live API data is never cache-first without a freshness policy; an offline write shows as pending until it syncs. *major*
- The manifest carries a maskable icon and `theme_color`. *minor*
