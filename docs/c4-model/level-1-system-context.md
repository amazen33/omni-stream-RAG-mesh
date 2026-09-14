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
