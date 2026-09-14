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

```plantuml
@startuml
title C4 Level 2 - Containers
actor "Financial Analyst / IoT Operator" as user
component "FastAPI Domain Service" as api
queue "Kafka Cluster\nKRaft topics" as kafka
component "Spark Streaming Engine\nwindowed Parquet" as spark
database "ChromaDB Vector Store" as chroma
database "Elasticsearch Audit Index\nOpenSearch adapter in Compose" as elastic
database "MinIO Object Storage\nS3-compatible" as minio
component "Ollama" as ollama
user --> api
api --> kafka
kafka --> spark
api --> chroma
api --> elastic
api --> minio
api --> ollama
spark --> minio
@enduml
```

```archimate
Business Actor "Financial Analyst / IoT Operator" as user
Application Component "FastAPI Domain Service" as api
Application Component "Kafka Cluster" as kafka
Application Component "Spark Streaming Engine" as spark
Application Component "ChromaDB Vector Store" as chroma
Application Component "Elasticsearch Audit Index" as elastic
Technology Object "MinIO Object Storage" as minio
Application Component "Ollama" as ollama
user --> api
api --> kafka
kafka --> spark
api --> chroma
api --> elastic
api --> minio
api --> ollama
spark --> minio
```

## Payment containers

```mermaid
flowchart LR
    PSP[Payment provider] --> API[FastAPI Domain Service]
    API --> Registry[Schema Registry]
    API --> Kafka[Kafka KRaft payment topics]
    Kafka --> MM2[MirrorMaker 2]
    Kafka --> Risk[Risk and anomaly scoring worker]
    Risk --> Audit[Governance audit sink]
    Risk --> Chroma[ChromaDB vector store]
    Audit --> Minio[MinIO object lock]
```

```plantuml
@startuml
title C4 Level 2 - payment containers
actor "Payment provider" as psp
component "FastAPI Domain Service" as api
component "Schema Registry" as registry
queue "Kafka KRaft payment topics" as kafka
component "MirrorMaker 2" as mm2
component "Risk and anomaly scoring worker" as risk
database "ChromaDB vector store" as chroma
database "Governance audit sink\nMinIO object lock" as audit
psp --> api
api --> registry
api --> kafka
kafka --> mm2
kafka --> risk
risk --> chroma
risk --> audit
@enduml
```
