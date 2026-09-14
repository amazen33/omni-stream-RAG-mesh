# C4 Level 4 — Code and dynamic flow

The repository is Python rather than a single compiled-code diagram, so this
level traces the concrete functions/classes used by the two primary flows.

## Ingestion sequence

```mermaid
sequenceDiagram
    participant Client
    participant API as app/main.py
    participant Redactor as PIIRedactor
    participant Ingest as IngestionService
    participant Store as RetrievalStore
    participant Kafka as EventPublisher
    participant Audit as AuditSink

    Client->>API: POST /ingest-sample(text, source)
    API->>Redactor: redact(text)
    Redactor-->>API: sanitized text + PII counts
    API->>Ingest: ingest(sanitized text, source, request_id)
    Ingest->>Ingest: split and create DocumentChunk
    Ingest->>Kafka: TelemetryIngested (if ENABLE_KAFKA)
    API->>Store: add(chunk IDs, sanitized documents)
    Store->>Store: embed with Ollama (if enabled)
    Store->>Store: write ChromaDB/OpenSearch (if enabled)
    API->>Audit: write(request_id, sanitized payload)
    Audit-->>API: immutable object key
    API->>Kafka: AuditRecordLogged (if enabled)
    API-->>Client: request_id, chunk count, audit key
```

## Retrieval sequence

```mermaid
sequenceDiagram
    participant Client
    participant API as app/main.py
    participant Redactor as PIIRedactor
    participant Retrieval as RetrievalService
    participant Store as RetrievalStore
    participant Ollama
    participant Audit as AuditSink

    Client->>API: POST /ask(question, top_k)
    API->>Redactor: redact(question)
    Redactor-->>API: sanitized question
    API->>Retrieval: ask(sanitized question, top_k, request_id)
    Retrieval->>Store: query(question, top_k)
    Store->>Store: embed query when configured
    Store-->>Retrieval: Chroma/OpenSearch/memory matches
    Retrieval->>Ollama: invoke(sanitized prompt) if enabled
    Ollama-->>Retrieval: model output
    Retrieval-->>API: answer and retrieved chunks
    API->>Audit: write(question, context, prompt, output)
    Audit-->>API: immutable object key
    API-->>Client: answer, retrieved chunks, audit key
```

## Concrete code map

| Concern | Code |
| --- | --- |
| HTTP schemas/routes | `app/main.py` |
| Pattern matching/token generation | `app/redaction.py` |
| Chunk entity | `domain/entities.py` |
| Event serialization/topic mapping | `domain/events.py` |
| Chunking and telemetry event | `contexts/ingestion/services.py` |
| Retrieval and optional LLM | `contexts/ai/services.py` |
| Vector/search adapters | `app/storage.py` |
| Immutable audit write | `app/audit.py` |
