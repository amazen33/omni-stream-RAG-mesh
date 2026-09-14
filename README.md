# Hybrid Streaming RAG

Production-oriented reference implementation for on-prem and AWS/Azure deployments.

## Quick start
1. Copy `.env.example` to `.env` and replace every value marked `replace` with local secrets.
2. `docker compose up --build`; create the audit bucket in MinIO and enable object locking before use.
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

## Domain layout
`contexts/ingestion`, `contexts/ai`, and `contexts/governance` are bounded contexts.
The immutable integration events `TelemetryIngested`, `TransactionProcessed`, and
`AuditRecordLogged` map to the Kafka topics `telemetry.ingested`,
`transaction.processed`, and `audit.record.logged`. Kafka, Ollama, Chroma,
Elasticsearch/OpenSearch, and MinIO adapters are opt-in through environment
variables, so health checks remain usable during dependency outages.
