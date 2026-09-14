# Hybrid Streaming RAG

Production-oriented reference implementation for on-prem and AWS/Azure deployments.

## Quick start
1. Copy `.env.example` to `.env` and replace every value marked `replace` with local secrets.
2. `docker compose up --build`; create the audit bucket in MinIO and enable object locking before use.
3. `curl -H 'Content-Type: application/json' -d '{"text":"sample"}' http://localhost:8000/ingest-sample`.

The API redacts PII before chunking and writes deterministic request/audit metadata to immutable S3-compatible storage. Chroma, Ollama, and OpenSearch adapters are deployment extension points; all endpoints are environment variables. Never commit `.env`, keys, certificates, or state.

See `ARD.md` for architecture decisions and `LAB_OPERATIONS.md` for operations, compliance, and troubleshooting.
