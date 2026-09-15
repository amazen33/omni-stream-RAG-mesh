# C4 Model - Level 3: Component Diagram (FastAPI Gateway)

The Component diagram zooms into the **FastAPI Gateway** container to depict its internal software components, concurrency isolation layers, and failure compensation handlers.

```mermaid
C4Component
    title Component Diagram - FastAPI Gateway & Orchestration Boundary

    Container_Boundary(b1, "FastAPI Gateway Service") {
        Component(middleware, "Correlation Middleware", "ASGI Middleware", "Extracts/generates X-Correlation-ID and sets thread-safe contextvars.")
        Component(logger, "Structured JSON Formatter", "Python logging", "Injects correlation_id & causation_id into every log line.")
        
        Component(controller, "RAG Query & Ingest Router", "FastAPI Endpoints", "Receives /api/v1/query and /api/v1/ingest requests.")
        
        Component(bulkhead, "Async Bulkhead", "asyncio.Semaphore", "Restricts concurrent downstream operations to prevent thread starvation.")
        Component(breaker, "Async Circuit Breaker", "State Machine", "Monitors consecutive failures (threshold=2) and fast-fails requests when OPEN.")
        Component(metrics, "Boundary Metrics Engine", "Prometheus Client", "Exposes /metrics with bulkhead saturation, breaker trips, and latency histograms.")
        
        Component(audit, "Immutable Audit Logger", "SHA-256 Engine", "Commits state transitions to MinIO WORM storage with cryptographic checksums.")
        Component(compensator, "Compensating Event Publisher", "Kafka Client", "Serializes binary headers and publishes rollback events to rag.events.compensating upon failure.")
    }

    ContainerDb_Ext(kafka_ext, "Kafka Event Broker", "KRaft Topic: rag.events.compensating")
    ContainerDb_Ext(minio_ext, "MinIO Storage", "Bucket: rag-audit-trail [Object Lock]")
    Container_Ext(ollama_ext, "Ollama LLM Worker", "HTTP /api/generate")

    Rel(middleware, controller, "Injects correlation contextvars")
    Rel(controller, logger, "Logs state changes with correlation metadata")
    Rel(controller, audit, "Logs TRANSACTION_INITIATED")
    Rel(controller, breaker, "Checks allow_request() before downstream call")
    Rel(controller, bulkhead, "Acquires concurrency slot")
    
    Rel(bulkhead, ollama_ext, "Dispatches inference request [HTTP 11434]")
    Rel(bulkhead, metrics, "Observes boundary latency & active slots")
    
    Rel(controller, breaker, "Records success / failure")
    Rel(controller, compensator, "Fires compensating trigger on failure")
    Rel(compensator, kafka_ext, "Publishes compensating event [Binary Headers]")
    Rel(controller, audit, "Commits INFERENCE_FAILED & COMPENSATING_ROLLBACK")
    Rel(audit, minio_ext, "Stores WORM JSON record with SHA-256 checksum")
```

## Internal Component Details

1. **Correlation Middleware**:
   - Ensures zero untracked requests by binding `current_correlation_id` and `current_causation_id` to async coroutines.
2. **Async Bulkhead**:
   - Manages bounded concurrency (default 5 slots per Ollama replica). Increments `rag_bulkhead_saturated_total` when capacity is exceeded.
3. **Async Circuit Breaker**:
   - Enforces a 3-state machine (`CLOSED`, `HALF_OPEN`, `OPEN`). When 2 consecutive failures occur, it trips to `OPEN`, immediately fast-failing traffic to protect downstream pods.
4. **Immutable Audit Logger**:
   - Calculates a canonical SHA-256 hash over the transaction metadata before persisting to MinIO WORM storage (`rag-audit-trail`).
5. **Compensating Event Publisher**:
   - Binds binary correlation headers to rollback messages on `rag.events.compensating` to trigger cleanup in ChromaDB and notify upstream callers.
