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

## Downstream-failure sequence

```mermaid
sequenceDiagram
    participant Client
    participant MW as correlation middleware
    participant API as route
    participant Policy as ResiliencePolicy
    participant Audit as AuditSink
    participant Kafka as EventPublisher

    Client->>MW: request + optional correlation/trace headers
    MW->>API: request_id, correlation_id, traceparent
    API->>Audit: INITIALIZED → PROCESSING
    API->>Policy: call downstream boundary
    alt succeeds
        Policy-->>API: result + duration metric
        API->>Audit: PROCESSING → COMPLETED
    else rejects, times out, or fails
        Policy-->>API: safe failure signal + failure metric
        API->>Audit: PROCESSING → COMPENSATED + record
        API->>Kafka: compensating event + immutable headers
    end
    API-->>Client: safe response + correlation/trace headers
```

The concrete implementation is `app/main.py` (middleware/routes and audit
coordination), `domain/events.py` (event contract),
`contexts/ai/resilience.py` (boundary policy), and
`contexts/governance/publisher.py` (Kafka headers). Payment risk scoring uses
the same path and returns `review` when its boundary fails.

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

## Payment ingestion and risk sequence

```mermaid
sequenceDiagram
    participant PSP as Payment Provider
    participant Handler as PaymentIngestionService
    participant PII as Tokenization Interceptor
    participant SR as Schema Registry
    participant Kafka as payments.transaction.ingested.v1
    participant Risk as RiskScoringService
    participant Audit as Immutable AuditSink
    PSP->>Handler: payment envelope
    Handler->>PII: validate and tokenize sensitive identifiers
    PII-->>Handler: sanitized envelope
    Handler->>SR: verify schema subject/version
    Handler->>Kafka: publish keyed event with acks=all
    Kafka->>Risk: consume transaction event
    Risk->>Risk: bounded model/anomaly inference
    Risk->>Audit: score, model metadata, decision
    Audit-->>Risk: object-lock key
```

```plantuml
@startuml
title C4 Level 4 - payment dynamic flow
actor "Payment Provider" as psp
participant "PaymentIngestionService" as handler
participant "PII tokenization" as pii
participant "Schema Registry" as registry
queue "payments.transaction.ingested.v1" as kafka
participant "RiskScoringService" as risk
database "Immutable AuditSink" as audit
psp -> handler : payment envelope
handler -> pii : validate/tokenize
pii --> handler : sanitized envelope
handler -> registry : subject/version check
handler -> kafka : keyed publish (acks=all)
kafka -> risk : consume event
risk -> risk : timeout/bulkhead guarded inference
risk -> audit : score and model metadata
audit --> risk : object-lock key
@enduml
```
