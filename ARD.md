# Architecture Decision Record (ADR)

## Scope

Hybrid on-prem/cloud RAG for regulated transaction workloads. Data stays in the
selected region; only redacted text leaves trusted boundaries.

## Decisions

| Decision | Status | Rationale and boundary |
| --- | --- | --- |
| Sanitization before external processing | Accepted | Recognised email, phone, payment-card, and SSN values become versioned, canonicalized 128-bit HMAC tokens before chunking, embeddings, retrieval, model inference, events, search, or audit writes. Source and payment identifiers are also HMAC-tokenized before metadata/events leave the RAG ingress boundary. |
| Object-locked audit evidence | Accepted | S3/MinIO Object Lock, Azure Blob locked immutability, and GCS Bucket Lock support a governed retention period when their adapters are enabled. Audit records retain server correlation IDs, HMAC tokens, and operational metadata—not raw request content or identifiers. The in-memory fallback is bounded and development/test-only. |
| Server-owned correlation and compensation | Accepted | The server issues immutable request, correlation, and W3C trace identifiers and discards caller-supplied trace headers. Successful and failed flows record lifecycle transitions and compensations. |
| Bounded compensation, not event-sourcing claim | Accepted | The implementation removes newly indexed chunks when its following audit write fails and emits compensating events. It does not provide durable event sourcing, atomic outbox delivery, or universal rollback; those require a separate append-only event store, projector, idempotency, and recovery design. |
| Python resilience policy | Accepted | Bounded bulkheads, queues, retries, transport timeouts, and histogram metrics protect retrieval/model/event boundaries and return safe fallback results where possible. |
| kubeadm primary on-prem platform | Accepted | Upstream Kubernetes with containerd and Calico is the portable on-prem production target. Managed EKS/AKS/GKE use the same Helm workload contract. K3s is legacy lab/edge only. |
| SPIRE + Istio sidecars | Accepted | SPIRE CSI bind-mounts the Workload API socket directory. Application readiness verifies that the local `SPIFFE_ENDPOINT_SOCKET` is connectable without reading SVID files or key material. Istio independently enforces Envoy STRICT mTLS. Neither replaces the other. |
| Helm as deployment source | Accepted | The Helm chart is the one source for `rag-api`; Ansible and Argo CD render it, and delivery never mutates a Deployment with `kubectl set image`. |
| Private gateway edge contract | Accepted | WAF → private Istio gateway → `rag-api` is required for on-prem and cloud. Direct WAF/load-balancer access to the workload is prohibited. |

## Core tradeoffs

Chroma is the local low-latency vector store while OpenSearch is an operational
search/analytics adapter. Configured stores fail visibly rather than silently
falling back to per-pod memory. AWS uses SigV4 with a least-privilege workload
role; non-AWS search uses a protected basic-auth secret when selected.

Kafka, EventStoreDB, TimescaleDB, Spark/Flink, and cloud integrations are
optional extension points. A manifest or Compose service does not establish a
durable event projection, exactly-once delivery, RTO/RPO, PCI compliance, or
production readiness without live evidence.

## Mesh and recovery decision

`ansible/configure-mesh.yaml` installs the pinned SPIRE CRDs/hardened stack and
Istio in dependency order for a prepared Kubernetes target. It validates a
non-example trust domain, durable StorageClass, CSI driver, and selected
`rag-api` `ClusterSPIFFEID` before `ansible/deploy-rag.yaml` rolls out Helm.
Each environment must provide its approved trust domain, cluster name, CA
subject, JWT issuer, DNS, WAF route, credentials, and mTLS/SVID acceptance
evidence.

Velero schedules encrypted object-store backups with CSI snapshots and a
filesystem fallback. Operators must provide the plugin, credentials,
VolumeSnapshotClass, and tested isolated restore; the manifest alone cannot
guarantee recovery objectives.

See the [architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md)
for platform prerequisites and deployment evidence, the
[TOGAF/ADM implementation](docs/TOGAF_Architecture_Definition.md) for governance,
and the [C4 model](docs/c4-model/C4_MODEL.md) for structural and dynamic views.
