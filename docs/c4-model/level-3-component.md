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

## Correlation and compensation components

```mermaid
flowchart LR
    Middleware[HTTP correlation middleware] --> Routes[FastAPI routes]
    Routes --> Lifecycle[StateTransitionLogged]
    Routes --> Policy[ResiliencePolicy]
    Policy --> Metrics[Prometheus boundary metrics]
    Policy --> Failure[Compensating event]
    Lifecycle --> Publisher[Kafka header publisher]
    Failure --> Publisher
    Lifecycle --> Audit[AuditSink transitions]
    Failure --> Audit[AuditSink compensation]
```

`DomainEvent` owns the immutable payload identity and Kafka header contract.
`EventPublisher` permits non-reserved custom headers but will not allow an
injected header to replace correlation, causation, event type, event ID, or
trace context. The routes use the detailed retrieval outcome to retain a safe
answer while recording failure compensation.

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

## Payment bounded-context components

```mermaid
flowchart TB
    Route[Payment ingestion handler] --> Validate[Payment envelope validator]
    Validate --> Tokenize[PII tokenization interceptor]
    Tokenize --> Serialize[Avro/Protobuf serializer]
    Serialize --> Registry[Schema Registry client]
    Serialize --> Publisher[Payment topic publisher]
    Publisher --> Risk[Anomaly and risk scoring service]
    Risk --> Resilience[Bulkhead, rate limiter, timeout]
    Risk --> Audit[AuditRecordLogged publisher]
```

```plantuml
@startuml
title C4 Level 3 - payment components
component "Payment ingestion handler" as route
component "Payment envelope validator" as validate
component "PII tokenization interceptor" as tokenize
component "Avro/Protobuf serializer" as serializer
component "Schema Registry client" as registry
component "Payment topic publisher" as publisher
component "Anomaly and risk scoring service" as risk
component "Bulkhead / rate limiter / timeout" as resilience
component "AuditRecordLogged publisher" as audit
route --> validate
validate --> tokenize
tokenize --> serializer
serializer --> registry
serializer --> publisher
publisher --> risk
risk --> resilience
risk --> audit
@enduml
```
