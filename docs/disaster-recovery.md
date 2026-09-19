# Downstream resilience and disaster recovery

## Runtime contract

The API middleware creates or accepts `X-Request-ID`, `X-Correlation-ID`, and
W3C `traceparent`. It returns them in the response. Every event retains
`correlation_id`, `causation_id`, and `traceparent` in the JSON payload; Kafka
publication mirrors them in headers along with `event_id` and `event_type`.
`causation_id` points to the event that triggered a child event, while a root
event receives a generated immutable value.

Boundary policies in `contexts/ai/resilience.py` have a named boundary and
protect synchronous calls with a token bucket, bulkhead, and timeout. Their
Prometheus metrics are `rag_bulkhead_active`,
`rag_bulkhead_rejections_total`, `rag_ratelimit_rejections_total`,
`rag_boundary_duration_seconds`, `rag_downstream_failures_total`, and
`rag_compensating_events_total`. The OpenTelemetry Collector deployment accepts
OTLP traces and metrics; it routes traces to Tempo and exposes metrics for
Prometheus. The Python core propagates W3C context but deliberately does not
require an OpenTelemetry SDK.

## Compensation and audit

The route lifecycle is `INITIALIZED → PROCESSING → COMPLETED` on success or
`INITIALIZED → PROCESSING → COMPENSATED` when a downstream boundary fails.
`IngestionCompensated`, `TransactionCompensated`, and `PaymentCompensated` are
Kafka contracts. Payment risk scoring fails closed to `review` with
`DOWNSTREAM_TIMEOUT_FAIL_CLOSED`.

`AuditSink` writes normal records, transitions, and compensation records below
`AUDIT_PREFIX`, retaining each S3/MinIO object in Object Lock `COMPLIANCE` mode
for seven years. Enable it only after creating an object-lock-capable bucket:

```text
ENABLE_AUDIT_STORE=true
AUDIT_BUCKET=rag-audit
S3_ENDPOINT_URL=https://minio.example.internal
```

The disabled audit-store fallback is for development/test inspection only. It
is not a substitute for immutable remote storage.

## Backup and restore runbook

1. Install Velero, its AWS/S3 plugin, and a CSI/cloud volume snapshot provider.
   Create `velero-minio-credentials` in the `velero` namespace and an encrypted
   `rag-velero-backups` Object-Lock bucket. Apply
   `k8s/velero-backup.yaml` after reviewing bucket endpoint and retention.
2. Verify the schedule and a completed backup:

   ```bash
   velero schedule get
   velero backup get
   velero backup describe rag-daily-stateful-backup-<timestamp> --details
   ```

3. At least quarterly, restore into an isolated namespace first. Validate the
   audit bucket/object-lock retention, Kafka topic offsets, TimescaleDB data,
   EventStoreDB streams, and OpenSearch indices before any production cutover.
4. For a declared recovery, quiesce writers, restore the Kubernetes resources
   and PVC snapshots, then bring up MinIO, Kafka, TimescaleDB, EventStoreDB,
   OpenSearch, and finally the API. Reconcile Kafka replication via
   MirrorMaker 2 before accepting writes. Preserve correlation IDs; never
   replay a compensating event as a new transaction.

The Velero manifest is a schedule, not proof of recoverability. Record the
measured RPO/RTO and backup/restore evidence in the change record.

## Mesh and identity prerequisites

Install the provider-neutral SPIRE/ISTIO profile before restoring or enabling
the mesh manifests. `ansible/tasks/mesh.yaml` installs SPIRE CRDs, server,
agents, controller manager, SPIFFE CSI driver, Istio, and the gateway in order;
it refuses example trust domains and verifies the CSI driver/registration.
For on-prem, `ansible/tasks/onprem-waf.yaml` places Traefik/Coraza before the
Istio gateway. For cloud, the managed WAF must forward only to that private
gateway. Restore the target's approved trust domain, cluster name, CA subject,
JWT issuer and ingress host; do not copy the lab values into a recovery
environment. Exercise rejected plaintext traffic and verify that `rag-api`
retains `app: rag-api`, `app.kubernetes.io/name: rag-api`, and service account
`rag-api`, because the SPIRE selectors and policy depend on them.
