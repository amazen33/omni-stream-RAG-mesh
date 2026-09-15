# ADR-0003: Distributed RAG Mesh Orchestration with ZooKeeperless Kafka

## Status
**Accepted**

## Context
A distributed Retrieval-Augmented Generation (RAG) architecture requires high-throughput document ingestion, asynchronous event decoupling, vector storage, document blob storage, and local LLM inference scaled across distinct compute nodes. Traditional Kafka architectures incur heavy operational friction due to Apache ZooKeeper dependencies.

## Decision
We implemented a custom Helm chart (`omni-stream-RAG-mesh`) composing five core components:
1. **FastAPI Gateway**: Multi-replica (2 replicas) stateless REST ingestion and inference orchestrator running lightweight Python 3.11 with CPU-optimized PyTorch wheels.
2. **Apache Kafka in KRaft Mode**: ZooKeeperless Kafka 3.7+ running as a StatefulSet with a 10Gi PVC. Kafka brokers handle metadata quorums internally via Raft consensus (`KAFKA_PROCESS_ROLES=broker,controller`).
3. **MinIO Object Storage**: S3-compatible document storage supporting raw PDF/DOC ingestion and web console management (20Gi PVC).
4. **ChromaDB**: Dedicated vector database storing embeddings generated during document ingestion (10Gi PVC).
5. **Distributed Ollama LLM Workers**:
   - Scaled across worker nodes using a Kubernetes StatefulSet with individual 30Gi PVCs for model weights (`/root/.ollama`).
   - Enforces `podAntiAffinity` on `kubernetes.io/hostname` to guarantee worker pods are scheduled across separate VMs (`k8s-worker-01` and `k8s-worker-02`).
   - Automated model pull on boot for `llama3.2:1b` and `nomic-embed-text`.

## Consequences
### Positive
- Removing ZooKeeper eliminates JVM overhead and simplifies state recovery.
- Node anti-affinity ensures LLM inference capacity scales horizontally across hypervisor cores and RAM.
- Complete microservice encapsulation governed by GitOps (ArgoCD).

### Negative / Tradeoffs
- Multi-replica Ollama StatefulSets require independent PVC storage on each worker node rather than shared RWO volumes.
