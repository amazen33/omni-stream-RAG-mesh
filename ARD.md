# Architecture Decision Record

## Scope
Hybrid on-prem/cloud RAG for regulated transaction workloads. Data stays in the selected region; only redacted text leaves trusted boundaries.

## Flow
CDC (Debezium/Postgres) -> Kafka KRaft (TLS/SASL in production) -> Flink windows/anomaly detector -> MinIO/S3 Parquet + OpenSearch time series. API receives documents, redacts PII, chunks with LangChain-compatible settings, embeds with Ollama, and dual-writes Chroma plus OpenSearch. Retrieval context, prompt, output, request ID and model versions are written to object-locked audit storage.

## Boundaries and security
Private subnets/VPC/VNet, default-deny Kubernetes NetworkPolicies, workload identity (IRSA/Azure federated identity), KMS/Key Vault encryption, no public buckets, TLS 1.2+, and mTLS hooks via cert-manager (`Certificate`/`Issuer`) or service mesh (Istio/Linkerd). Secrets are external-secrets/Vault references, never Git. Tokenized PII is irreversible with a rotated salt stored in KMS. Audit retention is compliance controlled and delete-protected.

## Reliability
Stateless API replicas behind ingress; PVCs for MinIO/OpenSearch/Kafka; Kafka replication factor 3 and min.insync.replicas 2; Flink savepoints and checkpointing; S3 versioning/object lock; OpenSearch snapshots. Rollouts use Argo Rollouts canary steps and automatic rollback on probe/metric failure.

## Portability
S3-compatible endpoint makes MinIO, AWS S3, and Azure Blob S3 gateway interchangeable. Terraform modules are intentionally small and provider-specific. Configuration is environment/Secret driven. GPU is optional: Ollama uses CPU fallback; NVIDIA toolkit is installed by Ansible where available.

## Decisions and tradeoffs
Chroma is the local low-latency vector store; OpenSearch is the operational/search and analytics index. Dual-write is observable and retryable, with audit events as source of truth. LangChain splitter and Ollama avoid vendor lock-in while allowing managed model replacement.
