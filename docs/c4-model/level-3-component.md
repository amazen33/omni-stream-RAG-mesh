# C4 Level 3 — Component

This view expands the FastAPI Domain Service into the implemented DDD
components. The middleware marks the boundary; route/domain services perform
the actual redaction before external adapters are called.

```mermaid
flowchart TB
    HTTP[HTTP routes<br/>app/main.py] --> Ingest[Ingestion Handlers<br/>IngestionService]
    HTTP --> Redact[PII Redaction Interceptors<br/>PIIRedactor + middleware]
    Redact --> Ingest
    Redact --> Retrieve[Vector Retrieval Service<br/>RetrievalService]
    Ingest --> Split[DocumentChunk entities<br/>domain/entities.py]
    Ingest --> Publish[Domain Event Publisher<br/>EventPublisher]
    Retrieve --> Store[RetrievalStore]
    Store --> Chroma[ChromaDB + Ollama embeddings]
    Store --> Search[OpenSearch / Elasticsearch adapters]
    HTTP --> Audit[Audit Logging Middleware / sink<br/>AuditSink]
    Audit --> ObjectLock[Object-lock S3 API]
    Publish --> Topics[Kafka topic contracts]
```

The `MetadataIndex` adapter is available for Elasticsearch metadata indexing,
while `RetrievalStore` uses the configured OpenSearch endpoint for the current
search path. `AuditRecordLogged` is published after a successful audit write.

```plantuml
@startuml
title C4 Level 3 - FastAPI components
component "HTTP routes\napp/main.py" as http
component "Ingestion Handlers\nIngestionService" as ingest
component "PII Redaction Interceptors\nPIIRedactor" as redact
component "Vector Retrieval Service\nRetrievalService" as retrieval
component "RetrievalStore" as store
component "Domain Event Publisher\nEventPublisher" as publisher
component "Audit Logging Middleware / sink\nAuditSink" as audit
database "ChromaDB + Ollama" as chroma
database "OpenSearch / Elasticsearch" as search
database "Object-lock S3 API" as object
queue "Kafka topic contracts" as topics
http --> redact
redact --> ingest
redact --> retrieval
ingest --> publisher
ingest --> store
retrieval --> store
store --> chroma
store --> search
http --> audit
audit --> object
publisher --> topics
@enduml
```

```archimate
Application Component "HTTP routes" as http
Application Component "Ingestion Handlers" as ingest
Application Component "PII Redaction Interceptors" as redact
Application Component "Vector Retrieval Service" as retrieval
Application Component "RetrievalStore" as store
Application Component "Audit Logging Middleware / sink" as audit
Technology Service "Kafka topics" as kafka
Technology Object "Object-lock S3 API" as object
http --> redact
redact --> ingest
redact --> retrieval
ingest --> store
retrieval --> store
ingest --> kafka
http --> audit
audit --> object
```
