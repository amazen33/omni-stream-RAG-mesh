# C4 Level 1 — System context

The system context shows the people, devices, external model service, object
storage, and broker boundary around omni-stream-RAG-mesh.

```mermaid
flowchart LR
    FA[Financial Analyst] --> RAG[omni-stream-RAG-mesh]
    IO[IoT Device / Operator] --> RAG
    RAG --> Ollama[Ollama<br/>LLM and embeddings]
    RAG --> Storage[Cloud object storage<br/>MinIO or S3]
    RAG --> Broker[External or managed brokers<br/>Kafka-compatible]
    FA -. queries and evidence .-> RAG
```

Financial analysts use the API for evidence ingestion and retrieval questions.
IoT devices/operators contribute telemetry through the event boundary.
Ollama, object storage, and Kafka are replaceable deployment dependencies.
