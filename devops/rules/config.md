---
paths:
  - "**/.env*"
  - "**/appsettings*.json"
  - "**/{application,bootstrap}*.{yml,yaml,properties}"
---

<!-- devops rules v1 (2026-11-03): environment config. Installed by /devops:rules; edit the paths above to fit this project. -->

# Environment configuration and secrets standards

Severity tags as in the core devops rules. Stack plugins' config rules (appsettings, Spring, `.env` in a service) add framework detail to these and agree with them.

- Three layers, last wins: committed defaults, committed per-environment non-secret values, then secrets read from the store at runtime. *major*
- No secret in any committed config file. `.env.example` and development files are committed with placeholders only; personal overrides (`.env.local`, `appsettings.Local.json`) are gitignored. *blocker*
- Secrets kept encrypted in the repo only through SOPS or Sealed Secrets, decrypted at deploy. *major*
- No demo, empty or null default for a required value (`API_KEY=demo-key`); missing required config fails startup. *major*
- One secret store per environment, never shared across environments; secret bundles named per service and environment (`secrets/orders/prod`). *major*
- Keys are hierarchical and spelled one way across the project (`Orders:PricingMode`, `orders.pricing-mode`, `ORDERS_PRICING_MODE`), and per-environment files follow one naming scheme. *nit*
