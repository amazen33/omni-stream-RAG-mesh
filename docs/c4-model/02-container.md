# C4 Model - Level 2: Container Diagram

The Container diagram zooms into the **Omni-Stream RAG Mesh**, illustrating the major deployable software containers, storage systems, and communication protocols.

```mermaid
C4Container
    title Container Diagram - Omni-Stream RAG Mesh

    Person(user, "Enterprise Analyst", "Sends queries & ingests documents")

    Container_Boundary(c1, "Omni-Stream RAG Mesh (K3s Cluster)") {
        Container(ingress, "Traefik Ingress Controller", "Go / Reverse Proxy", "Routes traffic from rag-mesh.local to internal ClusterIP services.")
        
        Container(fastapi, "FastAPI Gateway & Orchestrator", "Python 3.11 / Uvicorn", "Handles REST endpoints, correlation context, bulkheads, circuit breakers, and metrics exposition.")
        
        ContainerDb(kafka, "Apache Kafka (KRaft Mode)", "Java / Kafka 3.7", "Distributed streaming event mesh handling ingestion topics and compensating rollback events.")
        
        ContainerDb(minio, "MinIO Object Storage", "Go / MinIO S3", "Houses raw documents and object-locked WORM compliance audit trails (rag-audit-trail).")
        
        ContainerDb(chroma, "ChromaDB Vector Store", "Python / Chroma", "Stores chunk embeddings and executes cosine similarity searches.")
        
        Container(ollama, "Ollama LLM Workers (x2)", "Go / C++ / Ollama", "Runs local quantized LLMs (llama3.2:1b, nomic-embed-text) distributed across worker nodes.")
    }

    Rel(user, ingress, "Sends HTTPS queries with X-Correlation-ID", "Port 443/80")
    Rel(ingress, fastapi, "Forwards API traffic", "HTTP / Port 8000")
    Rel(ingress, minio, "Routes S3 console traffic", "HTTP / Port 9001")
    Rel(ingress, ollama, "Routes direct LLM test API", "HTTP / Port 11434")

    Rel(fastapi, kafka, "Publishes/consumes document events and compensating rollbacks", "TCP 9092 [Binary Headers]")
    Rel(fastapi, minio, "Reads/writes raw docs and commits WORM audit records", "S3 API / Port 9000")
    Rel(fastapi, chroma, "Queries top-k vector chunks", "HTTP / Port 8000")
    Rel(fastapi, ollama, "Executes inference within Bulkhead & Circuit Breaker", "HTTP / Port 11434")
```

## Container Specifications

| Container | Technology | Replicas | Persistent Storage | Description |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI Gateway** | Python 3.11-slim, PyTorch CPU, FastAPI | 2 | Stateless | Orchestrates ingestion, inference, boundary metrics, and audit logging. |
| **Kafka Broker** | Apache Kafka 3.7.0 (KRaft) | 1 (or 3) | 10Gi PVC | Event broker for document streams (`rag.documents.raw`) and rollbacks (`rag.events.compensating`). |
| **MinIO** | MinIO RELEASE.2024-03-30 | 1 | 20Gi PVC | S3 object store with WORM Compliance Object Lock enabled. |
| **ChromaDB** | chromadb/chroma:0.4.24 | 1 | 10Gi PVC | Vector embeddings database for RAG chunk search. |
| **Ollama Workers** | ollama/ollama:0.3.10 | 2 | $2 \times \text{30Gi}$ PVC | Scaled StatefulSet with `podAntiAffinity` enforcing distribution across worker nodes. |
