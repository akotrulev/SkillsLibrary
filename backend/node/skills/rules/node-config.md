---
paths:
  - "apps/api/{package.json,tsconfig*.json,vitest.config.*,.env*}"
  - "**/{server,backend}/{package.json,tsconfig*.json,vitest.config.*,.env*}"
---

<!-- be-node rules v1 (2026-11-03): project config. Installed by /be-node:rules; edit the paths above to this project's backend package roots. -->

# Node backend project configuration standards

Severity tags as in the core be-node rules: **blocker**, **major**, **minor**, **nit**.

- `tsconfig.json` sets `strict`, `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`, and test files are never excluded from strict checking. *major*
- `package.json` sets `"type": "module"` and pins Node 24 or 22 in `engines`; Node 20 is past end of life. *minor; major for Node 20*
- `@types/node` matches the project's Node major. *minor*
- One test runner: Vitest, or Jest where the repo already uses it. *major*
- The unit-test config sets `clearMocks` and `restoreMocks`, and unit and integration tests have separate include patterns. *major*
- No secret in any committed config or `.env` file: no password, API key or connection string with credentials. *blocker*
