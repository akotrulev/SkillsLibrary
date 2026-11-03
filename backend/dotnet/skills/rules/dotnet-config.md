---
paths:
  - "**/*.{Api,WebApi,Worker}/**/appsettings*.json"
---

<!-- be-dotnet rules v1 (2026-11-03): appsettings. Installed by /be-dotnet:rules; edit the paths above to this project's API and worker host projects. -->

# ASP.NET Core configuration standards

Severity tags as in the core .NET rules: **blocker**, **major**, **minor**, **nit**.

- No secret in any committed `appsettings*.json`: no password, client secret, API key, token or connection string with credentials. Read it from an environment variable or a secret store (Key Vault, Secrets Manager, user-secrets locally). *blocker*
- No `Debug` or `Verbose` as the production minimum level. *blocker*
- Hosts, URLs and the OTLP endpoint that differ per environment come from environment variables or `appsettings.{Environment}.json`, not one hard-coded value. *major*
- Every section binds to a typed options class validated at startup. *major*
- Section keys are consistent and namespaced (`Orders:MaxLines`), one spelling across projects. *nit*
