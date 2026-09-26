---
name: qa-messaging-testing-dotnet
description: Use when a .NET / NUnit test suite must produce, consume, or assert messages against the project's broker — Kafka/Redpanda, AWS SQS/SNS, RabbitMQ, or Azure Service Bus. Triggers "assert the service published event X", "test the consumer's side-effect", "DLQ/DLT assertions", "seed a topic/queue in a test". Pick the broker in the matrix, then read its reference file. Not for HTTP APIs (`api-test-author/writer`), message contracts (`api-contract-testing`), or email (`email-testing`).
---

# QA — Messaging Testing (.NET 8 / C#)

One registered skill, 4 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/kafka.md` | Apache Kafka / Redpanda — offsets, consumer groups, partitions, key routing, app-level DLT |
| `references/sqs.md` | AWS SQS / SNS — visibility timeout, redrive-policy DLQ, FIFO dedup, SNS fan-out |
| `references/rabbitmq.md` | RabbitMQ — exchange/binding topology, routing keys, manual ack/nack, DLX |
| `references/service-bus.md` | Azure Service Bus — peek-lock settlement, DLQ sub-queue, sessions, SQL filters |

## Decision matrix — pick the tool

| Need | Use | Why |
|------|-----|-----|
| Assert against **Apache Kafka** (offsets, consumer groups, partitions, key routing, app-level DLT, compaction) | **`references/kafka.md`** | Log-based, not a queue; `Confluent.Kafka` is the first-class .NET client; Kafka/Redpanda Testcontainers run locally |
| Assert against an **Azure Service Bus** queue/topic (peek-lock, DLQ sub-queue, sessions, SQL filters) | `references/service-bus.md` | Azure-native queue/topic; explicit peek-lock settlement + DLQ sub-queue — not offsets |
| Assert against **AWS SQS / SNS** (visibility timeout, redrive-policy DLQ, FIFO dedup, SNS fan-out) | `references/sqs.md` | AWS-native queue; delete-to-ack + visibility timeout — not a log you re-read |
| Assert against **RabbitMQ** (exchanges, routing keys, manual ack/nack, DLX) | `references/rabbitmq.md` | AMQP broker; exchange/binding topology + per-message ack |
| Assert a row was written, with no broker in the flow | `qa-db-connection-dotnet` | Pure DB verification; reuse its `WaitForAsync` for the eventual-consistency side here |

**Rule of thumb:** *A partitioned log you read by offset, with consumer groups and an app-level DLT?* → Kafka.
*A different broker?* → the matching sibling. *No broker at all?* → DB/API-mocking. All four messaging
siblings share the **same eventual-consistency condition-wait discipline** — only the broker model differs.

> **The queue-vs-log boundary in one line.** Service Bus and SQS are **queues**: you **consume-and-settle**
> (peek-lock complete / delete), a record leaves the queue, and the broker owns the **DLQ**. Kafka is a
> **log**: you **read at an offset and commit your position**, the record **stays** (other groups re-read it),
> there is **no per-message ack** and **no broker DLQ** — a DLT is something **your app produces to**. Same
> *condition-wait discipline*, **fundamentally different** broker model.

## Shared rules (every tool in this family)

- Eventual consistency: every broker assertion sits behind a condition-wait — never a sleep.
- Unique per-test topics/queues (or a test-run prefix) plus cleanup; any test runs alone, in any order.
- Assert message content and observable side-effects, never broker internals or timing.
- Local broker via Testcontainers/LocalStack — never a shared environment's broker.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
