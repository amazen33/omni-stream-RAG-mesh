# Health and telemetry operations

## Configuration

The API exposes `/health/live`, `/health/ready`, and `/health/startup`. Liveness
does no network work and is always a process check. Readiness and startup run
only checks whose configuration is present; an absent integration is reported as
`disabled`. A configured failure returns HTTP 503. Checks have a bounded
`HEALTH_CHECK_TIMEOUT_SECONDS` (default 2 seconds, maximum 10).

Supported settings are `KAFKA_BOOTSTRAP_SERVERS`, `CHROMA_URL` (or
`CHROMA_HOST`), `S3_ENDPOINT_URL` (or `MINIO_ENDPOINT_URL`),
`OLLAMA_BASE_URL`, and `OLLAMA_MODEL`. Responses contain only status and
duration; endpoint URLs, credentials, and exception text are never returned.
`/healthz` and `/readyz` remain available for older deployments.

## Prometheus and LGTM

`/metrics` emits dependency-free Prometheus text with
`rag_health_checks_total`, `rag_health_check_duration_seconds`, and `rag_ready`.
Labels are limited to the fixed check name and status, so secrets and tenant
identifiers cannot become cardinality or disclosure problems. Scrape the API
service at `/metrics` with Prometheus, then use Grafana dashboards and Loki
logs, Tempo traces, and Mimir/Prometheus metrics (the LGTM stack) as desired.

Recommended alerts:

* `rag_ready == 0` for five minutes
* a rising `rag_health_checks_total{status="failed"}`
* dependency check duration approaching the configured timeout

## Scheduled verifier

`k8s/diagnostic-verifier.yaml` runs `python -m ops.diagnostic_verifier` every
five minutes. It performs bounded, non-destructive synthetic checks across
Kafka, Spark, the checkpoint path, telemetry sink, and vector store. It prints
Prometheus-compatible metrics and exits non-zero if a configured check fails.
Set `SPARK_HEALTH_URL`, `TELEMETRY_SINK_HEALTH_URL`, `CHROMA_HEALTH_URL`, and
`CHECKPOINT_PATH` for the deployment. Route the job output to the platform's
metrics collector (or run it with `--output` on a mounted collector volume).
