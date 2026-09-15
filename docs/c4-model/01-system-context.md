# C4 Model - Level 1: System Context

The System Context diagram illustrates the Omni-Stream RAG Mesh platform in relation to its human users, external document sources, and enterprise observability systems.

```mermaid
C4Context
    title System Context Diagram - Omni-Stream RAG Mesh

    Person(user, "Enterprise Analyst", "Submits research queries and consumes AI-augmented synthesis.")
    Person(admin, "Platform SRE", "Monitors cluster health, boundary saturation, and audit trails.")

    System_Ext(doc_source, "Document Sources", "Raw enterprise documents, PDFs, tickets, and feeds.")
    System_Ext(lgtm_stack, "Self-Hosted LGTM Stack", "Loki (logs), Grafana (dashboards), Tempo (traces), Mimir/Prometheus (metrics).")

    System(rag_mesh, "Omni-Stream RAG Mesh", "Distributed event-driven RAG platform running on K3s Kubernetes with failure survival, WORM audit, and local Ollama inference.")

    Rel(user, rag_mesh, "Queries and retrieves answers [HTTPS / JSON]", "X-Correlation-ID")
    Rel(doc_source, rag_mesh, "Streams raw documents for ingestion [HTTPS / Kafka]")
    Rel(admin, rag_mesh, "Deploys via GitOps (ArgoCD) and inspects WORM logs")
    Rel(rag_mesh, lgtm_stack, "Exports boundary metrics (/metrics) and structured JSON logs")
    Rel(admin, lgtm_stack, "Visualizes bulkhead saturation, circuit trips, and p99 latencies")
```

## Description of Interactions
- **Enterprise Analyst**: Sends natural language queries to the FastAPI Gateway with client-provided or auto-generated `X-Correlation-ID`.
- **Document Sources**: Ingests files into the MinIO document repository and triggers asynchronous chunking/embedding events over Kafka.
- **Platform SRE**: Monitors infrastructure and boundary resilience dashboards, and triggers GitOps synchronization via ArgoCD.
- **Self-Hosted LGTM Stack**: Continuously scrapes Prometheus metrics at `/metrics` (via Kubernetes `ServiceMonitor`) and aggregates structured JSON logs containing correlation IDs for root-cause analysis.
