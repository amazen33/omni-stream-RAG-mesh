<<<<<<< HEAD
# Omni-Stream RAG Mesh: Enterprise Architecture & Documentation

Welcome to the architectural documentation for the **Omni-Stream RAG Mesh** platform. This repository contains complete architectural blueprints, formal decision records, and deployment models structured according to international industry standards.

---

## Documentation Structure

```
docs/
├── README.md                                 # Architecture documentation portal (this file)
│
├── adr/                                      # Architecture Decision Records (MADR Format)
│   ├── README.md                             # Decision Log & Index
│   ├── 0001-hybrid-infrastructure-hyperv-terraform.md
│   ├── 0002-node-configuration-k3s-ansible.md
│   ├── 0003-event-driven-rag-mesh-orchestration.md
│   ├── 0004-structured-correlation-contextvars.md
│   ├── 0005-boundary-metrics-lgtm-observability.md
│   └── 0006-immutable-audit-trail-minio-worm-compensating-rollbacks.md
│
├── togaf/                                    # TOGAF Standard Architecture Deliverables
│   ├── architecture-definition-document.md   # Complete Architecture Definition Document (ADD)
│   └── architecture-principles.md            # TOGAF Principles (Statement, Rationale, Implications)
│
└── c4-model/                                 # C4 Software Architecture Model (Mermaid Diagrams)
    ├── README.md                             # C4 Model Overview
    ├── 01-system-context.md                  # Level 1: System Context Diagram
    ├── 02-container.md                       # Level 2: Container Diagram
    ├── 03-component.md                       # Level 3: Component Diagram (FastAPI Gateway)
    └── 04-deployment.md                      # Level 4: Deployment Diagram (Hyper-V & K3s)
```

---

## Architectural Pillars

### 1. Hybrid Infrastructure as Code (Terraform & Ansible)
- Provisions a 3-node cluster on Windows Hyper-V (`k8s-master-01`, `k8s-worker-01`, `k8s-worker-02`).
- Establishes private/public virtual switches, host NAT routing, and port-level security ACLs.
- Hardens Linux nodes (swap permanently disabled, kernel modules `overlay` and `br_netfilter`, sysctl CRI settings), configures `containerd.io`, and bootstraps K3s with automated dynamic token joining.

### 2. Distributed Event-Driven RAG Mesh (Helm & Kubernetes)
- Custom Helm chart (`omni-stream-RAG-mesh`) orchestrating:
  - **FastAPI Gateway**: Stateless, non-root, multi-replica REST orchestrator.
  - **Apache Kafka (KRaft Mode)**: ZooKeeperless streaming event mesh.
  - **MinIO Object Storage**: S3-compatible document storage with WORM compliance.
  - **ChromaDB**: Dedicated vector similarity search database.
  - **Ollama LLM Workers**: StatefulSet with `podAntiAffinity` on `kubernetes.io/hostname` to distribute inference workloads across separate worker nodes.

### 3. Downstream Failure Survival & Observability
- **Structured Correlation IDs**: End-to-end `contextvars` context propagation, binary Kafka headers, and structured JSON logs.
- **Boundary Metrics & LGTM Monitoring**: Bulkhead concurrency limiters, sliding-window circuit breakers, and boundary latency histograms exposed on `/metrics` with Prometheus `ServiceMonitor` and Grafana dashboards.
- **Audit & Rollback Verification**: MinIO Object Lock WORM retention (`rag-audit-trail`), SHA-256 integrity hashing, and automated compensating rollback events dispatched to Kafka on failure.
=======
# omni-RAG-mesh architecture

This documentation describes the implementation in this repository: a
platform-agnostic streaming RAG reference stack for regulated workloads. It
is intentionally explicit about what is enabled by default and what is an
environment-driven integration.

## Documentation map

- [System context and components](system-context.md)
- [Domain model and event contracts](domain-events.md)
- [Data flows](data-flows.md)
- [Deployment and infrastructure topology](deployment-topology.md)
- [Security and trust boundaries](security.md)
- [Delivery and operations](delivery-operations.md)
- [Windows Python support](windows-python.md)
- [Python compatibility policy](python-compatibility.md)
- [Fintech payment streaming](fintech-payments.md)
- [DDD naming compatibility](ddd-compatibility.md)
- [TOGAF Architecture Definition](TOGAF_Architecture_Definition.md)

## C4 model

- [C4 notation and rendering guide](c4-model/README.md)
- [Level 1: System context](c4-model/level-1-system-context.md)
- [Level 2: Container](c4-model/level-2-container.md)
- [Level 3: Component](c4-model/level-3-component.md)
- [Level 4: Code and dynamic flow](c4-model/level-4-code-dynamic.md)

## Source of truth

The executable configuration is in the repository root and its subdirectories:
`app/`, `contexts/`, `domain/`, `streaming/`, `docker-compose.yml`, `k8s/`,
`terraform/`, `ansible/`, `deploy/`, and `Jenkinsfile`. These pages document
those files; they do not imply that optional integrations are active in every
deployment.

CI is defined in `.github/workflows/ci.yml` (tests, image build, and Trivy
image/IaC gates). `.github/workflows/publish-deploy.yml` is an explicit,
secret-driven GHCR publish and optional production deployment workflow.

For bootstrap and troubleshooting procedures, see the root
[README](../README.md), [architecture decisions](../ARD.md), and
[operations runbook](../LAB_OPERATIONS.md).
>>>>>>> 326eae92028aa5e56d0e35de134f27355dcba79d
