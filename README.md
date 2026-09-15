<<<<<<< HEAD
# Omni-Stream RAG Mesh

[![CI/CD Test, Build, Scan](https://github.com/amazen33/omni-stream-RAG-mesh/actions/workflows/ci.yml/badge.svg)](https://github.com/amazen33/omni-stream-RAG-mesh/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-K3s_v1.28-326CE5?logo=kubernetes&logoColor=white)](https://k3s.io)
[![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-orange?logo=argo&logoColor=white)](https://argoproj.github.io/cd/)
[![Argo Rollouts](https://img.shields.io/badge/Canary-Argo_Rollouts-blue?logo=argo&logoColor=white)](https://argoproj.github.io/rollouts/)

Enterprise-grade, distributed Retrieval-Augmented Generation (RAG) mesh platform engineered for local-first hybrid virtualization (Windows Hyper-V) and Kubernetes (K3s), featuring down-to-the-wire failure survival, immutable WORM audit trails, and progressive canary rollouts.

---

## Architecture Overview

```
[ Physical Host / Hyper-V Server ]
  ├── Public vSwitch (Host NAT: 192.168.100.1)
  └── Private vSwitch (192.168.100.0/24)
       ├── VM: k8s-master-01 (192.168.100.10) - K3s Control Plane & Ingress
       ├── VM: k8s-worker-01 (192.168.100.11) - FastAPI, Kafka (KRaft), MinIO, Ollama (ollama-0)
       └── VM: k8s-worker-02 (192.168.100.12) - FastAPI, ChromaDB, Ollama (ollama-1)
             │
             ▼
     [ ArgoCD GitOps ] ──> [ Helm Chart: omni-stream-RAG-mesh ]
             │
             ▼
     [ Argo Rollouts ] ──> Progressive Canary Deployment with Metric Analysis
```

---

## Core Components

1. **Infrastructure as Code (`terraform/hyperv/`)**:
   - Automated 3-node VM provisioning on Windows Hyper-V.
   - Internal/external virtual switches, host NAT routing, and port ACL security groups.
   - Deterministic static IP allocations (`192.168.100.10-12`) and dynamic Ansible inventory output.

2. **Configuration Management (`ansible/`)**:
   - System hardening, swap disablement, and kernel modules (`overlay`, `br_netfilter`).
   - `containerd.io` runtime with systemd cgroups.
   - Automated 3-node K3s cluster deployment with in-memory token dispatching.

3. **Microservice & GitOps (`app/`, `deploy/`)**:
   - Multi-stage Dockerfile based on `python:3.11-slim` with CPU-optimized PyTorch wheels.
   - ArgoCD `Application` manifest with automated self-healing, pruning, and retry backoff.
   - Argo Rollouts canary deployment with automated Prometheus analysis templates.

4. **Distributed RAG Helm Chart (`k8s/charts/omni-stream-RAG-mesh/`)**:
   - **FastAPI Gateway**: 2 Replicas, non-root (UID 10001), liveness/readiness probes.
   - **Kafka (KRaft)**: ZooKeeperless event mesh with 10Gi PVC.
   - **MinIO**: S3-compatible document storage with 30-day WORM Object Locking.
   - **ChromaDB**: Dedicated vector database with 10Gi PVC.
   - **Ollama LLM Workers**: StatefulSet with `podAntiAffinity` on `kubernetes.io/hostname` to distribute across worker nodes, 30Gi model storage, and auto-model pre-caching.

5. **Failure Survival & Boundary Observability**:
   - **Structured Correlation IDs**: Async `contextvars` context propagation across HTTP headers, Kafka binary headers, and structured JSON logs.
   - **Boundary Metrics & LGTM Monitoring**: Bulkhead concurrency limiters, sliding-window circuit breakers, and Prometheus latency histograms exposed on `/metrics`.
   - **WORM Audit Trails**: MinIO Compliance Object Lock recording state transitions with cryptographic SHA-256 signatures and automated compensating rollbacks.

---

## Quickstart

### 1. Run Tests & Validation
```bash
python -m unittest discover -s tests -v
```

### 2. Deploy via ArgoCD
```bash
kubectl apply -f deploy/argocd/application.yaml
```

### 3. Deploy via Argo Rollouts
```bash
kubectl apply -f deploy/rollouts/analysis-template.yaml
kubectl apply -f deploy/rollouts/rollout.yaml
```

### 4. Documentation
- [Architecture Decision Records (ADRs)](docs/adr/README.md)
- [TOGAF 10 Architecture Definition Document](docs/togaf/architecture-definition-document.md)
- [C4 Architecture Model](docs/c4-model/README.md)
=======
# Hybrid Streaming RAG

Production-oriented reference implementation for on-prem and AWS/Azure deployments.

## Quick start
1. Copy `.env.example` to `.env` and replace every value marked `replace` with local secrets.
2. `docker compose up --build`; create the audit bucket in MinIO and enable object locking before use.
3. `curl -H 'Content-Type: application/json' -d '{"text":"sample"}' http://localhost:8000/ingest-sample`.

The API redacts PII before chunking and writes deterministic request/audit metadata to immutable S3-compatible storage. Chroma, Ollama, and OpenSearch adapters are deployment extension points; all endpoints are environment variables. Never commit `.env`, keys, certificates, or state.

See `ARD.md` for architecture decisions and `LAB_OPERATIONS.md` for operations, compliance, and troubleshooting.
See [`docs/README.md`](docs/README.md) for the system context, domain events,
data flows, deployment topology, security boundaries, and delivery/operations
architecture documentation.

CI configuration lives in `.github/workflows/`: pull requests run tests,
Docker build, and Trivy image/IaC gates. Publishing and deployment are
explicit, secret-driven operations; see
[`docs/delivery-operations.md`](docs/delivery-operations.md). `docker compose
exec rag-api sh` is the supported local debugging shell; the image does not
include or run an SSH daemon.

For Windows local development, use Python 3.12 (preferred) or 3.13. Python
3.14 is not supported for the pinned native dependencies; see
[`docs/windows-python.md`](docs/windows-python.md). The local-only PowerShell
launcher accepts `-PythonPath` to select an installed supported interpreter.
The same Python 3.12/3.13 policy applies to Ubuntu/Linux, GitHub Actions,
Docker, and Kubernetes; changing the host OS does not make Python 3.14
compatible. See [`docs/python-compatibility.md`](docs/python-compatibility.md).

## Domain layout
`contexts/ingestion`, `contexts/ai`, and `contexts/governance` are bounded contexts.
The immutable integration events `TelemetryIngested`, `TransactionProcessed`, and
`AuditRecordLogged` map to the Kafka topics `telemetry.ingested`,
`transaction.processed`, and `audit.record.logged`. Kafka, Ollama, Chroma,
Elasticsearch/OpenSearch, and MinIO adapters are opt-in through environment
variables, so health checks remain usable during dependency outages.
>>>>>>> 326eae92028aa5e56d0e35de134f27355dcba79d
