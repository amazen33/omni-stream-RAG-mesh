# ADR-0005: Boundary Metrics, Bulkhead Isolation, and Self-Hosted LGTM Stack Monitoring

## Status
**Accepted**

## Context
Downstream services such as Ollama and ChromaDB are susceptible to compute saturation, GPU out-of-memory errors, and network partition latency. Without boundary isolation and real-time saturation metrics, a slow LLM worker will consume all upstream connection pools and crash the FastAPI gateway.

## Decision
We engineered a boundary protection and observability pattern composed of:
1. **Asynchronous Bulkheads (`AsyncBulkhead`)**:
   - Implemented an `asyncio.Semaphore` bulkhead per downstream service (default 5 concurrent operations for Ollama).
   - Tracks active slots with Prometheus Gauge `rag_bulkhead_active_slots` and saturated/queued requests with Counter `rag_bulkhead_saturated_total`.
2. **Circuit Breaking (`AsyncCircuitBreaker`)**:
   - Sliding-window failure counter tripping to `OPEN` after 2 consecutive failures.
   - Gauge `rag_circuit_breaker_state` (0=CLOSED, 1=HALF_OPEN, 2=OPEN) and Counter `rag_circuit_breaker_tripped_total`.
   - Fast-fails subsequent requests with HTTP 503, preventing resource exhaustion during downstream outages.
3. **Boundary Latency Histograms**:
   - `rag_downstream_boundary_latency_seconds` with quantile buckets (10ms to 30s) labeled by `boundary` and `status` (success/failure).
4. **LGTM Stack Integration**:
   - Exposed on `/metrics` via `prometheus_client`.
   - Kubernetes `ServiceMonitor` manifest scraping `/metrics` every 15s.
   - Pre-configured Grafana Dashboard ConfigMap tracking bulkhead saturation and latency quantiles (p50, p90, p99).

## Consequences
### Positive
- Strict failure isolation: Slow or failing Ollama pods cannot exhaust FastAPI connection pools.
- Instant visibility into saturation and circuit trips via Prometheus and Grafana.
- Fast-fail behavior allows compensating rollback transactions to initiate immediately.

### Negative / Tradeoffs
- Requires careful tuning of bulkhead concurrency limits and circuit recovery timeouts depending on model size and hardware specs.
