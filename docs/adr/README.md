# Architecture Decision Records (ADRs)

This directory maintains the immutable decision log for the Omni-Stream RAG Mesh platform, capturing design rationale, context, tradeoffs, and consequences in MADR (Markdown Architectural Decision Records) format.

## Decision Log

| ID | Title | Status | Date |
| :--- | :--- | :--- | :--- |
| [ADR-0001](0001-hybrid-infrastructure-hyperv-terraform.md) | Hybrid Infrastructure Provisioning via Hyper-V & Terraform | **Accepted** | 2026-09-15 |
| [ADR-0002](0002-node-configuration-k3s-ansible.md) | Multi-Node K3s Cluster Bootstrapping with Dynamic Token Join | **Accepted** | 2026-09-15 |
| [ADR-0003](0003-event-driven-rag-mesh-orchestration.md) | Distributed RAG Mesh Orchestration with ZooKeeperless Kafka | **Accepted** | 2026-09-15 |
| [ADR-0004](0004-structured-correlation-contextvars.md) | End-to-End Structured Correlation IDs via ContextVars and Kafka Headers | **Accepted** | 2026-09-15 |
| [ADR-0005](0005-boundary-metrics-lgtm-observability.md) | Boundary Metrics, Bulkhead Isolation, and Self-Hosted LGTM Stack Monitoring | **Accepted** | 2026-09-15 |
| [ADR-0006](0006-immutable-audit-trail-minio-worm-compensating-rollbacks.md) | Immutable Audit Trail via MinIO WORM Object Lock & Compensating Rollbacks | **Accepted** | 2026-09-15 |
