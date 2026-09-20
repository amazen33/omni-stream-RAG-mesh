# Hybrid Streaming RAG

Production-oriented reference implementation for kubeadm-based on-prem and
managed AWS/Azure/GKE Kubernetes deployments. K3s is retained only as a legacy
resource-constrained lab/edge workflow.

## Downstream-failure resilience

Every API request receives server-issued immutable `request_id`,
`correlation_id`, and W3C `traceparent` values. Caller-supplied tracing headers
are discarded; they never become audit, event, or downstream identifiers. The
server values are returned in HTTP headers, carried in domain-event payloads,
and published as Kafka headers. If a downstream
vector store, inference/risk scorer, Kafka broker, or audit sink fails, the
application records an `INITIALIZED → PROCESSING → COMPLETED` or
`INITIALIZED → PROCESSING → COMPENSATED` lifecycle and publishes the matching
compensating event. The audit sink uses S3/MinIO Object Lock, Azure Blob locked
immutability, or GCS Bucket Lock with an approved retention period when
enabled; bounded in-memory diagnostics remain available only for local
development and tests.
This is a bounded compensating-transaction design, not a complete durable
event-sourcing rollback system: production event sourcing needs an append-only
event store, transactional outbox, replay projectors, and restore evidence.

`/metrics` includes bounded-cardinality Prometheus metrics for bulkhead activity
and rejections, rate-limit rejections, boundary duration, downstream failures,
and compensating events. `docker-compose.yaml` supplies the local LGTM
(Prometheus, Grafana, Loki, Tempo) topology together with an OpenTelemetry
Collector, TimescaleDB, and EventStoreDB. Those stateful services are optional
deployment extensions, not mandatory core-Python dependencies.

## Quick start
1. Run `docker compose -f docker-compose.local.yaml up --build` for the standalone demonstration.
2. This profile uses ephemeral memory storage and disables external integrations. For the full integration blueprint, copy `.env.example` to `.env`, replace secrets, provision the missing integration configuration described in the assessment, and create an object-lock audit bucket before enabling audit storage.
3. `curl -H 'Content-Type: application/json' -d '{"text":"sample"}' http://localhost:8000/ingest-sample`.

The RAG ingress boundary replaces recognised PII with versioned, canonicalized
128-bit HMAC tokens before chunking, indexing, model inference, events, or
audit writes. Source and payment identifiers are HMAC-tokenized before their
metadata/events leave that boundary; immutable audit records contain only
tokens, server-issued correlation identifiers, and operational metadata.
Chroma, Ollama, and OpenSearch adapters are deployment extension points; all
endpoints are environment variables. Never commit `.env`, keys, certificates,
or state.

## Documentation

The `docs/` directory has four focused documents:

1. [API and contributor guide](docs/API_AND_CONTRIBUTOR_GUIDE.md) — HTTP
   contract, examples, tracing, errors, and endpoint-design rules.
2. [Architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md) —
   implementation architecture, security, platform profiles, delivery, and
   recovery.
3. [TOGAF Architecture Definition](docs/TOGAF_Architecture_Definition.md) —
   ADM governance plan, diagrams, migration, and implementation traceability.
4. [C4 model](docs/c4-model/C4_MODEL.md) — combined Level 1–4 structural and dynamic
   views plus the process for maintaining them.

The root [architecture decision record (ADR)](ARD.md) captures durable technical
decisions. [LAB_OPERATIONS.md](LAB_OPERATIONS.md) is the concise operational
entry point.

CI configuration lives in `.github/workflows/`: pull requests run tests,
Docker build, and Trivy image/IaC gates. Publishing and deployment are
explicit, secret-driven operations; see the
[architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md). `docker compose
exec rag-api sh` is the supported local debugging shell; the image does not
include or run an SSH daemon.

For Windows local development, use Python 3.12 (preferred) or 3.13. Python
3.14 is not supported for the pinned native dependencies. The local-only PowerShell
launcher accepts `-PythonPath` to select an installed supported interpreter.
The same Python 3.12/3.13 policy applies to Ubuntu/Linux, GitHub Actions,
Docker, and Kubernetes; changing the host OS does not make Python 3.14
compatible.

To run directly with Python 3.12: `python -m venv .venv`, activate the
environment, run `python -m pip install -r requirements.txt`, then
`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
Run `python -m pytest -q` for all tests, including deterministic failure injection.
Run `python -m pytest -v tests/chaos/test_lifecycle_downstream_failure.py` to
verify correlation propagation, metrics, audit transitions, and fail-closed
compensation.
See the [architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md)
for verified behavior, production gaps, and acceptance work.

## Domain layout
`contexts/ingestion`, `contexts/ai`, and `contexts/governance` are bounded contexts.
The immutable integration events `TelemetryIngested`, `TransactionProcessed`, and
`AuditRecordLogged` map to the Kafka topics `telemetry.ingested`,
`transaction.processed`, and `audit.record.logged`. Kafka, Ollama, Chroma,
Elasticsearch/OpenSearch, and MinIO adapters are opt-in through environment
variables, so health checks remain usable during dependency outages.

## Infrastructure and recovery

The Kubernetes deployment labels `rag-api` consistently for Istio/SPIRE and
mounts its SPIFFE SVID using the CSI driver; its scoped default-deny
NetworkPolicies permit only the Istio gateway, Prometheus metrics, required
workload dependencies, Istio control plane, and DNS. The
provider-neutral mesh task installs SPIRE (CRDs, server, agent, controller
manager, CSI driver) and Istio before rendering the workload registration and
STRICT mTLS policy. The primary on-prem target is upstream Kubernetes installed
with kubeadm/containerd and Calico; cloud targets are managed EKS, AKS, or GKE. The
legacy K3s lab routes Traefik/Coraza through the Istio gateway; primary on-prem
and cloud WAFs use the same private gateway contract. See the
[architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md) for
prerequisites and commands.
`k8s/velero-backup.yaml`
defines a daily, encrypted MinIO/S3-targeted Velero backup schedule with volume
snapshots. The recovery procedure is in the
[architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md).

## Source location

The source currently being updated is located at
`D:\project\Rag-Mesh\omni-stream-RAG-mesh`. The repository root is the source
of truth for application code, tests, manifests, and these documents.
