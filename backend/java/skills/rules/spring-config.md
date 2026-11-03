---
paths:
  - "**/{application,bootstrap}*.{yml,yaml,properties}"
---

<!-- be-java rules v1 (2026-11-03): Spring config. Installed by /be-java:rules; edit to fit this project. -->

# Spring Boot configuration standards

Severity tags as in the core Java rules: **blocker**, **major**, **minor**, **nit**.

- No secret in any committed config file: no password, client secret, API key or connection string with credentials. Reference an environment variable (`${DB_PASSWORD}`) or a secret store. *blocker*
- `spring.jpa.hibernate.ddl-auto` is `validate` in every profile but a developer laptop, never `update` or `create`; Flyway or Liquibase owns the schema. *blocker*
- Chatty loggers (`org.springframework`, `org.hibernate`, `org.apache.kafka`) capped at `WARN`; no `DEBUG` or `TRACE` as a production default. *minor*
- Service identity and endpoints that differ per environment come from environment variables or profile files, not hard-coded hosts. *major*
