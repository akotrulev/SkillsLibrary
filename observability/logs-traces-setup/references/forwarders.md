# Log forwarders other than Alloy

Read this when the project already standardizes on Vector or Fluent Bit, or needs a sink beside Loki. Grafana Alloy stays the default; the labels it may attach are the four in `SKILL.md` "Index labels", whichever forwarder ships them.

## Vector

Vector handles routing, filtering, dropping noisy logs, batching and multiple sinks. Use it when one tool must ship to Loki and another sink (for example an archive in S3), or when the logs need richer transforms.

## Fluent Bit

CNCF-graduated, with a smaller footprint than Fluentd. Use it when the organization already standardizes on it.

## One forwarder per cluster

Pick one per cluster and keep it. Two forwarders on a node ship every line twice.
