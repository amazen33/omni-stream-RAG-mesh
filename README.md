# Hybrid Streaming RAG

Production-oriented reference implementation for kubeadm-based on-prem and
managed AWS/Azure Kubernetes deployments. K3s is retained only as a legacy
resource-constrained lab/edge workflow.

## Downstream-failure resilience

Every API request now establishes an immutable `correlation_id`, `causation_id`
chain, and W3C `traceparent`. The values are returned in HTTP headers, carried
in the domain-event payload, and published as Kafka headers. If a downstream
vector store, inference/risk scorer, Kafka broker, or audit sink fails, the
application records an `INITIALIZED → PROCESSING → COMPLETED` or
`INITIALIZED → PROCESSING → COMPENSATED` lifecycle and publishes the matching
compensating event. The audit sink uses S3/MinIO Object Lock in `COMPLIANCE`
mode with a seven-year retention period when enabled; the dependency-free
in-memory fallback remains available for local development and tests.

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

The API redacts PII before chunking and writes deterministic request/audit metadata to immutable S3-compatible storage. Chroma, Ollama, and OpenSearch adapters are deployment extension points; all endpoints are environment variables. Never commit `.env`, keys, certificates, or state.

See `ARD.md` for architecture decisions and `LAB_OPERATIONS.md` for operations, compliance, and troubleshooting.
See [`docs/README.md`](docs/README.md) for the system context, domain events,
data flows, deployment topology, security boundaries, and delivery/operations
architecture documentation.

CI configuration lives in `.github/workflows/`: pull requests run tests,
Docker build, and Trivy image/IaC gates. Publishing and deployment are
explicit, secret-driven operations; see
[`docs/delivery-operations.md`](docs/delivery-operations.md). `docker compose
exec rag-api sh` is the supported local debugging shell; the image does not
include or run an SSH daemon.

For Windows local development, use Python 3.12 (preferred) or 3.13. Python
3.14 is not supported for the pinned native dependencies; see
[`docs/windows-python.md`](docs/windows-python.md). The local-only PowerShell
launcher accepts `-PythonPath` to select an installed supported interpreter.
The same Python 3.12/3.13 policy applies to Ubuntu/Linux, GitHub Actions,
Docker, and Kubernetes; changing the host OS does not make Python 3.14
compatible. See [`docs/python-compatibility.md`](docs/python-compatibility.md).

To run directly with Python 3.12: `python -m venv .venv`, activate the
environment, run `python -m pip install -r requirements.txt`, then
`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
Run `python -m pytest -q` for all tests, including deterministic failure injection.
Run `python -m pytest -v tests/chaos/test_lifecycle_downstream_failure.py` to
verify correlation propagation, metrics, audit transitions, and fail-closed
compensation.
See [architecture assessment and acceptance plan](docs/architecture-assessment.md)
for verified behavior, production gaps, and GitHub execution blockers.

## Domain layout
`contexts/ingestion`, `contexts/ai`, and `contexts/governance` are bounded contexts.
The immutable integration events `TelemetryIngested`, `TransactionProcessed`, and
`AuditRecordLogged` map to the Kafka topics `telemetry.ingested`,
`transaction.processed`, and `audit.record.logged`. Kafka, Ollama, Chroma,
Elasticsearch/OpenSearch, and MinIO adapters are opt-in through environment
variables, so health checks remain usable during dependency outages.

## Infrastructure and recovery

The Kubernetes deployment labels `rag-api` consistently for Istio/SPIRE and
mounts its SPIFFE SVID using the CSI driver; default-deny NetworkPolicies permit
only the Istio gateway, Istio control plane, and DNS as required. The
provider-neutral mesh task installs SPIRE (CRDs, server, agent, controller
manager, CSI driver) and Istio before rendering the workload registration and
STRICT mTLS policy. The primary on-prem target is upstream Kubernetes installed
with kubeadm/containerd and Calico; cloud targets are managed Kubernetes. The
legacy K3s lab routes Traefik/Coraza through the Istio gateway; primary on-prem
and cloud WAFs use the same private gateway contract. See
[platform profiles](docs/platform-profiles.md) for prerequisites and commands.
`k8s/velero-backup.yaml`
defines a daily, encrypted MinIO/S3-targeted Velero backup schedule with volume
snapshots. See [the disaster-recovery runbook](docs/disaster-recovery.md).

## Source location

The source currently being updated is located at
`D:\project\Rag-Mesh\omni-stream-RAG-mesh`. The repository root is the source
of truth for application code, tests, manifests, and these documents.
