# omni-stream-RAG-mesh Helm Chart

A production-ready Helm chart orchestrating a distributed, event-driven Retrieval-Augmented Generation (RAG) mesh on Kubernetes.

## Architecture Components

| Component | Role | Scalability & Persistence |
| :--- | :--- | :--- |
| **FastAPI Gateway** | REST API gateway, orchestration, context augmentation | 2 Replicas, stateless Deployment |
| **Kafka (KRaft Mode)** | Event mesh for real-time document ingestion & vector updates | StatefulSet with 10Gi PVC (ZooKeeperless) |
| **MinIO** | S3-compatible object storage for PDFs, raw docs, and dumps | Deployment with 20Gi PVC |
| **ChromaDB** | High-performance vector embeddings database | Deployment with 10Gi PVC |
| **Ollama LLM Worker** | Local model inference (`llama3.2:1b`, `nomic-embed-text`) | 2 Replicas StatefulSet with `podAntiAffinity` and 30Gi model PVCs |

## Key Features
- **Anti-Affinity Distribution**: Ollama worker pods enforce `podAntiAffinity` on `kubernetes.io/hostname`, guaranteeing workers are scheduled across separate physical/virtual nodes for resilience and throughput.
- **ZooKeeperless Kafka**: Built natively on Apache Kafka KRaft mode for low resource footprint and fast recovery.
- **Automated Model Pulling**: Ollama containers automatically pull and cache specified models upon initial boot.
- **GitOps Ready**: Fully wired to be reconciled continuously by ArgoCD.

## Manual Installation
```bash
# Add to cluster in namespace rag-mesh
helm upgrade --install omni-stream-rag-mesh ./k8s/charts/omni-stream-RAG-mesh \
  --namespace rag-mesh \
  --create-namespace \
  --values ./k8s/charts/omni-stream-RAG-mesh/values.yaml
```

## Testing Endpoints
```bash
# Port-forward FastAPI Gateway
kubectl port-forward svc/omni-stream-rag-mesh-fastapi 8000:8000 -n rag-mesh

# Query RAG Gateway
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the status of the K3s cluster?", "model": "llama3.2:1b"}'
```
