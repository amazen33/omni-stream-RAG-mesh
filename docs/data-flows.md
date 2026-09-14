# End-to-end data flows

## Ingestion and retrieval

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant P as PIIRedactor
    participant I as IngestionService
    participant V as Vector/Search adapters
    participant K as Kafka
    participant M as MinIO/S3 audit

    C->>A: POST /ingest-sample
    A->>P: redact and tokenize text
    P-->>I: sanitized text and counts
    I->>I: split into DocumentChunk entities
    I->>K: TelemetryIngested (optional)
    I->>V: store sanitized chunks and embeddings
    A->>M: immutable ingest audit record
    A->>K: AuditRecordLogged (optional)
    A-->>C: request ID, chunk count, audit key

    C->>A: POST /ask
    A->>P: redact and tokenize question
    P-->>A: sanitized question
    A->>V: retrieve top_k context
    A->>A: optionally call Ollama with sanitized prompt
    A->>M: immutable prompt/context/output record
    A->>K: AuditRecordLogged (optional)
    A-->>C: answer, retrieved context, audit key
```

The audit write is part of the request success path. If the enabled audit
client fails, the API returns HTTP 503 rather than reporting a successful
request without an audit key. With `ENABLE_AUDIT_STORE=false`, a deterministic
audit key is returned and the record is logged as retained in the application
event stream rather than sent to S3.

## Streaming analytics

```mermaid
flowchart LR
    E[telemetry.ingested<br/>transaction.processed<br/>audit.record.logged] --> K[Kafka KRaft]
    K --> S[Spark Structured Streaming]
    S --> Parse[Parse common event envelope]
    Parse --> Window[10-minute watermark<br/>1-minute event windows]
    Window --> P[Parquet append output]
    P --> O[s3a://streaming/events]
    S --> C[s3a://streaming/checkpoints/domain-events]
```

`streaming/spark_job.py` is submitted with Spark connectors for Kafka and
Parquet/S3. The Compose service mounts the job; the Kubernetes manifest
provides a CronJob and ConfigMap placeholder for pipeline replacement.
`streaming/flink-job.yaml` remains an additional deployment extension point,
not an implementation used by the FastAPI process.
