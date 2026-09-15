# TOGAF 10 Architecture Definition Document (ADD)

**Project Name**: Omni-Stream RAG Mesh Platform  
**Target Horizon**: Hybrid Cloud-Native Infrastructure & Distributed Inference  
**Document Version**: 1.0.0  
**Architect**: Lead Cloud & Enterprise Systems Architect  
**Status**: Approved  

---

## 1. Scope and Executive Summary

The **Omni-Stream RAG Mesh** architecture provides an enterprise-grade, resilient, event-driven Retrieval-Augmented Generation (RAG) platform operating on a local-first hybrid virtualized infrastructure (Windows Hyper-V) orchestrated by Kubernetes (K3s). 

This Architecture Definition Document formalizes the structural decisions across the TOGAF Architecture Development Method (ADM) phases:
- **Business Architecture**: Scalable, verifiable AI inference with non-repudiable audit compliance.
- **Data Architecture**: S3-compatible document storage, distributed vector indexing, and WORM-compliant immutable audit trails.
- **Application Architecture**: Decoupled event streaming, boundary bulkheads, circuit-breaker isolation, and saga-style compensating rollbacks.
- **Technology Architecture**: Infrastructure as Code (Terraform), declarative node hardening (Ansible), and GitOps deployment (Helm/ArgoCD).

---

## 2. Phase B: Business Architecture

### 2.1 Business Goals & Drivers
- **Resilience & High Availability**: Zero cascading outages from downstream LLM latency or hardware saturation.
- **Regulatory Compliance & Data Integrity**: Non-repudiable proof of data ingestion, processing states, and LLM inference generation via WORM storage.
- **Cost & Resource Efficiency**: Local-first hybrid infrastructure leveraging existing on-premise hypervisors without recurring cloud hosting fees.

### 2.2 Business Actors & Capabilities
```
[ External Consumers / Analysts ]
               │
               ▼ (Submit Document / Ask Contextual Query)
┌─────────────────────────────────────────────────────────────┐
│                    Business Capabilities                    │
├──────────────────────────────┬──────────────────────────────┤
│ 1. Real-Time Document Stream │ Ingestion, chunking, dedupe  │
│ 2. Semantic Vector Indexing  │ High-speed vector embeddings │
│ 3. Contextual LLM Inference  │ Retrieval-augmented answers  │
│ 4. Audit & Reconciliation    │ WORM logging & compensation  │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 3. Phase C: Data Architecture

### 3.1 Data Entities & Lifecycles
1. **Raw Document Entity**: Stored in MinIO bucket `rag-documents` (PDF, DOCX, text blobs).
2. **Vector Chunk Entity**: Embedded representation stored in ChromaDB collections (`/chroma/chroma`), linked via document metadata.
3. **Event Stream Record**: Kafka messages (`rag.documents.raw`, `rag.events.compensating`) enveloped with immutable binary correlation headers (`correlation_id`, `causation_id`, `timestamp_ns`).
4. **WORM Audit Trail Entity**: Stored in MinIO bucket `rag-audit-trail` with 30-day Compliance Object Lock retention. Every state transition record includes a SHA-256 integrity signature.

### 3.2 State Transition Lifecycle
$$\text{TRANSACTION\_INITIATED} \longrightarrow \text{DOC\_INGESTED} \longrightarrow \text{VECTOR\_INDEXED} \longrightarrow \text{INFERENCE\_REQUESTED}$$
$$\Big\downarrow \text{Downstream Failure Triggered}$$
$$\text{INFERENCE\_FAILED} \longrightarrow \text{COMPENSATING\_ROLLBACK\_TRIGGERED} \longrightarrow \text{COMPENSATED\_FINAL}$$

---

## 4. Phase C: Application Architecture

### 4.1 Service Catalog
- **FastAPI Gateway**: Multi-replica (2 replicas) ingestion and query API. Enforces ASGI correlation middleware, manages async bulkheads, monitors circuit breakers, and serves `/metrics`.
- **Apache Kafka (KRaft Mode)**: High-throughput distributed event broker operating without ZooKeeper dependencies.
- **MinIO Object Store**: High-performance S3-compatible object engine with native Object Lock WORM capability.
- **ChromaDB**: Vector similarity search database.
- **Ollama LLM Workers**: StatefulSet running quantized open-weights models (`llama3.2:1b`, `nomic-embed-text`) scaled across cluster worker nodes with `podAntiAffinity`.

### 4.2 Failure Survival & Boundary Resilience
```
                                 [ Inbound Request ]
                                          │ (X-Correlation-ID)
                                          ▼
                         ┌─────────────────────────────────┐
                         │   FastAPI Gateway Boundary      │
                         └────────────────┬────────────────┘
                                          │
                        ┌─────────────────┴─────────────────┐
                        ▼                                   ▼
             [ Bulkhead Semaphore ]             [ Circuit Breaker ]
            (Limits active concurrent)         (Trips upon 2 failures)
                        │                                   │
                        ▼                                   ▼
          [ Call Downstream: Ollama ]          [ Fast-Fail (HTTP 503) ]
          ┌─────────────┴─────────────┐                     │
       Success                     Failure                  │
          │                           │                     │
          ▼                           ▼                     ▼
    [ Record p50/p99 ]    ┌───────────────────────────────────────┐
    [ Audit Completed ]   │ 1. Trip Breaker to OPEN               │
                          │ 2. Emit Boundary Failure Metrics      │
                          │ 3. Dispatch Kafka Compensating Event  │
                          │ 4. Write WORM SHA-256 Audit Record    │
                          └───────────────────────────────────────┘
```

---

## 5. Phase D: Technology Architecture

### 5.1 Infrastructure & Virtualization Fabric
- **Hypervisor**: Windows Server / Windows 11 Hyper-V (Generation 2 VMs).
- **Virtual Switches**:
  - `k8s-private-vswitch`: Isolated internal switch (`192.168.100.0/24`).
  - `k8s-public-vswitch`: External switch with host-level NAT gateway routing (`192.168.100.1`).
- **VM Topology**:
  - `k8s-master-01`: `192.168.100.10` (2 vCPUs, 4GB RAM, 50GB VHDX)
  - `k8s-worker-01`: `192.168.100.11` (4 vCPUs, 8GB RAM, 80GB VHDX)
  - `k8s-worker-02`: `192.168.100.12` (4 vCPUs, 8GB RAM, 80GB VHDX)
- **Port ACL Firewalls**: Stateful Hyper-V port ACLs explicitly restricting ingress traffic to cluster operational ports (22, 6443, 10250, 8472 UDP, 80/443, 30000-32767).

### 5.2 Operating System & Runtime Environment
- **OS**: Ubuntu 22.04 LTS / Debian 12 cloud-init baseline.
- **Kernel Tuning**: Swap permanently disabled, `overlay` and `br_netfilter` loaded, `net.bridge.bridge-nf-call-iptables = 1`, `net.ipv4.ip_forward = 1`.
- **CRI**: `containerd.io` configured with `SystemdCgroup = true`.
- **Kubernetes Distribution**: K3s v1.28+ with automated dynamic token bootstrapping.

### 5.3 GitOps & Continuous Reconciliation
- **ArgoCD**: Continuous reconciliation engine monitoring Git repository path `k8s/charts/omni-stream-RAG-mesh` with automated self-healing, pruning, and retry backoff.
- **LGTM Observability Stack**: Prometheus `ServiceMonitor` scraping `/metrics` every 15s; pre-packaged Grafana dashboards tracking bulkhead saturation and latency quantiles.

---

## 6. Architecture Governance & Compliance Review
- **Traceability**: All architectural changes trace back to approved Architecture Decision Records (ADRs 0001 through 0006).
- **Security**: Strict least-privilege non-root container users (UID 10001), port-level hypervisor ACLs, and compliance WORM object locking.
- **Verification**: Validated via automated chaos tests asserting correlation propagation, circuit-breaker trips, and SHA-256 audit integrity.
