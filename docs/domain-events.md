# DDD bounded contexts and event contracts

## Bounded contexts

```mermaid
flowchart TB
    Ingestion[Ingestion / Streaming context<br/>contexts/ingestion]
    AI[AI / Retrieval context<br/>contexts/ai]
    Governance[Governance / Compliance context<br/>contexts/governance]
    Domain[Shared domain contracts<br/>domain/]
    Ingestion --> Domain
    AI --> Domain
    Governance --> Domain
    Ingestion --> AI
    AI --> Governance
```

### Ingestion / Streaming

`IngestionService` receives text, applies the `PIIRedactor`, creates
`DocumentChunk` entities, and emits `TelemetryIngested`. The service uses the
LangChain recursive splitter when installed and a bounded fallback splitter
otherwise.

### AI / Retrieval

`RetrievalService` retrieves from `RetrievalStore` and optionally invokes an
Ollama model. `RetrievalStore` supports ChromaDB with Ollama embeddings,
OpenSearch keyword/full-text retrieval, and an in-process memory fallback for
development and tests.

### Governance / Compliance

`EventPublisher` is an optional Kafka producer. `AuditSink` serializes request
IDs, sanitized prompts/questions, retrieved context, model output, and
ingestion metadata to object storage. `MetadataIndex` is an independent,
opt-in Elasticsearch adapter for create-only metadata indexing.

## Kafka event/topic mapping

Events are frozen dataclasses in `domain/events.py`. Their `topic` class
variable is the integration contract.

| Event | Kafka topic | Emitted by | Key payload |
| --- | --- | --- | --- |
| `TelemetryIngested` | `telemetry.ingested` | `IngestionService` | request ID, source, chunk count, PII counts |
| `TransactionProcessed` | `transaction.processed` | Domain/integration producers | request and transaction IDs, status, metadata |
| `AuditRecordLogged` | `audit.record.logged` | API after audit write | request ID, object key, record type |

`DomainEvent.to_dict()` adds `event_type` and `topic`, while `to_json()` emits
stable sorted JSON. Kafka publication is disabled unless `ENABLE_KAFKA=true`.

## Contract evolution

Consumers should treat event names and topics as stable integration contracts.
Additive fields are preferred; changes to field meaning or topic names require
coordinated consumer updates. The Spark job currently parses the common
`event_id`, `event_type`, `occurred_at`, and `request_id` fields.
