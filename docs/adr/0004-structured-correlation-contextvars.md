# ADR-0004: End-to-End Structured Correlation IDs via ContextVars and Kafka Headers

## Status
**Accepted**

## Context
In a distributed event-driven RAG mesh traversing FastAPI gateways, asynchronous Kafka brokers, ChromaDB vector stores, and Ollama LLM worker pods, pinpointing root causes of downstream failures requires an immutable correlation context preserved across thread, process, network, and queue boundaries.

## Decision
We implemented a multi-layer correlation propagation mechanism:
1. **Thread-Safe Async Context**:
   - Leveraged Python's standard `contextvars.ContextVar` (`correlation_id` and `causation_id`) to retain immutable request IDs across asynchronous coroutines without polluting function signatures.
2. **ASGI Middleware**:
   - `correlation_middleware` extracts incoming `X-Correlation-ID` or generates a UUIDv4, guarantees `X-Correlation-ID` and `X-Causation-ID` response headers, and initializes context variables.
3. **Kafka Binary Message Headers**:
   - Correlation IDs are serialized into Kafka message headers as UTF-8 binary tuples:
     ```python
     [
         ("correlation_id", correlation_id.encode("utf-8")),
         ("causation_id", causation_id.encode("utf-8")),
         ("event_type", event_type.encode("utf-8")),
         ("timestamp_ns", str(time.time_ns()).encode("utf-8")),
     ]
     ```
   - This decouples business payload parsing from infrastructure-level message routing and tracing.
4. **Structured JSON Logging**:
   - Standard logging outputs JSON lines enriched with `correlation_id` and `causation_id` for zero-friction ingestion by log aggregators (e.g. Grafana Loki).

## Consequences
### Positive
- Transparent end-to-end tracing across HTTP $\rightarrow$ Kafka $\rightarrow$ Vector Store $\rightarrow$ LLM boundaries.
- Immediate log correlation in Grafana Loki using single transaction queries.
- Zero signature pollution in business domain functions.

### Negative / Tradeoffs
- Background worker threads outside the ASGI request context must explicitly inherit or clone `contextvars`.
