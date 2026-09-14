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

```plantuml
@startuml
title C4 Level 4 - Ingestion and retrieval dynamic flow
actor Client as client
participant "app/main.py" as api
participant "PIIRedactor" as redactor
participant "IngestionService / RetrievalService" as domain
participant "RetrievalStore" as store
participant "Ollama" as ollama
participant "AuditSink" as audit
queue "Kafka topics" as kafka
client -> api : POST /ingest-sample or /ask
api -> redactor : redact(payload)
redactor --> api : sanitized payload
api -> domain : invoke bounded-context service
domain -> store : add/query sanitized chunks
store -> ollama : embed/infer when enabled
store --> domain : retrieved context
domain --> api : answer and context
api -> audit : write request, prompt, output
audit --> api : immutable object key
api -> kafka : publish domain/audit event when enabled
api --> client : response and audit key
@enduml
```

```archimate
Business Actor "API Client" as client
Application Function "PII redaction" as redact
Application Function "Ingestion or retrieval service" as service
Application Service "Vector/search retrieval" as retrieval
Application Service "Immutable audit logging" as audit
Technology Service "Kafka event publication" as kafka
client --> redact
redact --> service
service --> retrieval
service --> audit
service --> kafka
```
