# TOGAF Architecture Principles

This document defines the core architecture principles governing the Omni-Stream RAG Mesh platform, formulated according to the TOGAF standard structure: **Name, Statement, Rationale, and Implications**.

---

### Principle 1: Immutability of Correlation Context
- **Statement**: Every transaction entering the mesh must be assigned an immutable correlation identity that propagates across network, protocol, thread, and storage boundaries.
- **Rationale**: In asynchronous and distributed event-driven systems, isolating the root cause of downstream failures is impossible without deterministic correlation.
- **Implications**:
  - All HTTP endpoints must inspect and propagate `X-Correlation-ID`.
  - Kafka message producers must inject `correlation_id` and `causation_id` as binary headers.
  - All logging formatters must output correlation IDs as structured JSON attributes.

---

### Principle 2: Graceful Degradation & Boundary Bulkheading
- **Statement**: A failure or compute saturation in a downstream dependency (e.g. LLM inference) must never cascade upstream or exhaust cluster capacity.
- **Rationale**: Heavy inference engines (Ollama/PyTorch) exhibit variable latency under load; isolating them behind bulkheads and circuit breakers ensures gateway availability.
- **Implications**:
  - Downstream calls must be guarded by async concurrency semaphores (Bulkheads).
  - Sliding-window circuit breakers must fast-fail requests when failure rates exceed predefined thresholds.
  - Saturated or tripped boundaries must trigger automated fallback and compensating actions.

---

### Principle 3: Non-Repudiable WORM Audit Trails
- **Statement**: State transitions and compensating operations must be written to append-only, object-locked storage with cryptographic integrity verification.
- **Rationale**: Enterprise RAG platforms require verifiable proof of document provenance, inference parameters, and state reconciliation to satisfy regulatory compliance.
- **Implications**:
  - Audit buckets must enforce MinIO Object Lock in `COMPLIANCE` mode.
  - Every audit log entry must store a canonical SHA-256 payload checksum.
  - Audit records cannot be modified or purged prior to retention expiry.

---

### Principle 4: Declarative Infrastructure & GitOps Singularity
- **Statement**: Infrastructure, node configurations, and application states must be declared in version-controlled repositories and reconciled automatically.
- **Rationale**: Manual configuration drift leads to unreproducible states, configuration rot, and extended mean time to recovery (MTTR).
- **Implications**:
  - Hyper-V VMs, switches, and ACLs must be declared via Terraform.
  - Node hardening and K3s bootstrapping must be managed via Ansible.
  - Cluster workloads must be reconciled continuously by ArgoCD from Helm charts.
