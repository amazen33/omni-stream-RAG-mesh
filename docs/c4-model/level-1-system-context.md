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

```plantuml
@startuml
title C4 Level 1 - System context
actor "Financial Analyst" as analyst
actor "IoT Device / Operator" as operator
rectangle "omni-stream-RAG-mesh" as system
rectangle "Ollama\nLLM and embeddings" as ollama
cloud "Cloud object storage\nMinIO or S3" as storage
queue "External or managed brokers\nKafka-compatible" as brokers
analyst --> system : ingest evidence / ask questions
operator --> system : publish telemetry
system --> ollama : sanitized prompts and embeddings
system --> storage : audit JSON and Parquet
system --> brokers : domain events
@enduml
```

```archimate
Business Actor "Financial Analyst" as analyst
Business Actor "IoT Device / Operator" as operator
Application Component "omni-stream-RAG-mesh" as system
Application Component "Ollama" as ollama
Technology Object "MinIO or S3 object storage" as storage
Technology Service "Kafka-compatible broker" as broker
analyst --> system
operator --> system
system --> ollama
system --> storage
system --> broker
```

## Payment streaming extension

```mermaid
flowchart LR
    PSP[Payment Service Provider] --> RAG[omni-stream-RAG-mesh]
    Merchant[Merchant / Risk Analyst] --> RAG
    RAG --> Kafka[Primary Kafka KRaft]
    Kafka -. MirrorMaker 2 .-> DR[DR Kafka]
    RAG --> Registry[Schema Registry]
    RAG --> LLM[Local or remote governed LLM]
```

```plantuml
@startuml
title C4 Level 1 - payment system context
actor "Payment Service Provider" as psp
actor "Merchant / Risk Analyst" as analyst
rectangle "omni-stream-RAG-mesh" as system
queue "Primary Kafka KRaft" as kafka
queue "DR Kafka via MirrorMaker 2" as dr
component "Schema Registry" as registry
component "Local or remote governed LLM" as llm
psp --> system : payment events
analyst --> system : review and evidence
system --> kafka
kafka --> dr
system --> registry
system --> llm : sanitized prompts
@enduml
```

## Resilience and recovery context

```mermaid
flowchart LR
    Client[API client] -->|TLS + correlation ID + traceparent| Edge[On-prem or cloud WAF]
    Edge -->|private HTTP route| Gateway[Istio ingress gateway]
    Gateway -->|sidecar mTLS| RAG[omni-stream-RAG-mesh]
    SPIRE[SPIRE Server + Agent] -->|CSI workload SVID| RAG
    Istiod[Istio control plane] -->|xDS / mesh identity| RAG
    RAG --> Kafka[Kafka event mesh]
    RAG --> Audit[MinIO/S3 Object-Lock audit]
    RAG --> LGTM[OTel Collector → Tempo/Prometheus]
    Kafka -. replicated events .-> DR[DR Kafka]
    Velero[Velero snapshots] --> Audit
    Velero --> State[Stateful PVCs]
```

The client-visible contract is a returned correlation ID and W3C traceparent.
The platform records either a completed or compensated state transition. The
edge is an organization/provider WAF in the primary kubeadm and cloud profiles;
the retained K3s lab uses Traefik/Coraza. All route only to the private Istio
gateway. SPIRE provides an application SVID through the CSI driver while Istio
sidecars enforce workload mTLS. Kafka, Object Lock, and LGTM are separate system
boundaries; Velero protects the Kubernetes/PVC recovery path rather than
replacing immutable audit retention.
