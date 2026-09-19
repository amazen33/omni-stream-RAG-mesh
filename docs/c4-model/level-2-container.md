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

## Resilience, observability, and state containers

```mermaid
flowchart TB
    API[FastAPI domain service] --> Kafka[Kafka + MirrorMaker 2]
    API --> Audit[MinIO/S3 Object-Lock]
    API --> OTel[OpenTelemetry Collector]
    OTel --> Tempo[Tempo traces]
    OTel --> Prom[Prometheus metrics]
    TS[TimescaleDB analytics] --> Grafana[Grafana]
    ES[EventStoreDB CQRS streams] --> Projector[Read-model projector]
    Velero[Velero] --> PVCs[MinIO/Kafka/TimescaleDB/OpenSearch PVCs]
```

`EventStoreDB` and `TimescaleDB` are delivered as optional stateful containers
in Compose and Kubernetes. A production projector is intentionally not
hard-wired into the Python API: its replay and schema ownership must be
approved by the deployment team. The collector transports OTLP telemetry; the
API's dependency-free Prometheus endpoint remains directly scrapeable.

## Workload identity and edge containers

```mermaid
flowchart LR
    WAF[On-prem Coraza or cloud WAF] --> Gateway[Istio ingress gateway]
    Gateway -->|STRICT sidecar mTLS| API[rag-api]
    SPIRE[SPIRE Server / Controller Manager] --> Agent[SPIRE Agent]
    Agent --> CSI[SPIFFE CSI driver]
    CSI -->|X.509 SVID mount| API
    Istiod[istiod] -->|xDS| API
```

`ansible/configure-mesh.yaml` creates this topology on a prepared Kubernetes
target. Its `ClusterSPIFFEID` selects only `rag-api` by namespace and stable
labels, and its CSI volume is part of the Helm deployment when the mesh profile
is enabled. The WAF is platform-specific but has a common invariant: it cannot
bypass the Istio gateway to reach the application service directly. SPIRE SVID
issuance and Istio mTLS are distinct controls.

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
