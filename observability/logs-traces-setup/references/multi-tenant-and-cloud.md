# Multi-tenant stacks and Grafana Cloud

Read this when one stack serves several teams, or when the team does not want to operate Loki and Tempo itself. Most projects in this library are single-tenant; skip multi-tenant unless it is needed, since it adds operational complexity.

## Multi-tenant

Loki and Tempo both support tenant headers:

- The forwarder or Collector sets `X-Scope-OrgID: team-orders`.
- Loki keeps streams separate per tenant.
- Per-tenant limits and retention come from the runtime config.
- Grafana uses one data source per tenant, or auth that pins the header.

Apply `X-Scope-OrgID` on every writer and reader of the stack, or on none: a single-tenant assumption anywhere in a multi-tenant deployment breaks isolation.

## Grafana Cloud as a managed alternative

Grafana Cloud offers the same APIs with paid limits: the same query language and the same Grafana, with less ops. Pay for it when the time saved is worth it. The recipes in `SKILL.md` work against self-hosted or Grafana Cloud; only the endpoint and auth differ.
