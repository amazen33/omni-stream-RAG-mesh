# C4 Level 2 — Container

Containers are logical deployable/runtime responsibilities. The names reflect
the current repository components and optional adapters.

```mermaid
flowchart LR
    User[Financial Analyst / IoT Operator] --> API[FastAPI Domain Service]
    API --> Kafka[Kafka Cluster<br/>KRaft topics]
    Kafka --> Spark[Spark Streaming Engine<br/>windowed Parquet]
    API --> Chroma[ChromaDB Vector Store]
    API --> ES[Elasticsearch Audit Index<br/>OpenSearch adapter in Compose]
    API --> Minio[MinIO Object Storage<br/>S3-compatible audit/lakehouse]
    API --> Ollama[Ollama]
    Spark --> Minio
```

`FastAPI Domain Service` corresponds to `app/` plus `contexts/` and `domain/`.
The event publisher and streaming engine are disabled or deployed separately
unless their environment/deployment flags are enabled.
