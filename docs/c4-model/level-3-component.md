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
