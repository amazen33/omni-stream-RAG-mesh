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

## Decision: correlation, compensation, and auditable state transitions

**Status: accepted and implemented.** Every `DomainEvent` is an immutable
dataclass carrying `event_id`, `correlation_id`, `causation_id`, and optional
W3C `traceparent`. The payload preserves this metadata and the publisher adds
the same values as UTF-8 Kafka headers. HTTP middleware establishes a stable
correlation ID for each request (derived from its request ID when the caller
does not supply one) and returns it to the client.

Downstream boundaries use a bulkhead, token bucket, and timeout policy. They
emit Prometheus-compatible boundary metrics without putting payloads, tenant
identifiers, URLs, or error messages into labels. A failure creates an explicit
compensating event and an `INITIALIZED → PROCESSING → COMPENSATED` audit
transition; successful work ends at `COMPLETED`. MinIO/S3 writes use Object
Lock `COMPLIANCE` mode for seven years. When the audit adapter is disabled,
the in-process audit record list supports local testing but is not a durable
production audit system.

EventStoreDB and TimescaleDB are supplied as optional stateful Kubernetes and
Compose services. EventStoreDB must be connected through a reviewed event
projection/connector before it is treated as the production system of record;
Kafka and object-locked audit data remain the active application contracts.

## Decision: mesh identity and disaster recovery

**Status: accepted and automated for prepared Kubernetes targets.** The
provider-neutral `ansible/configure-mesh.yaml` installs the SPIRE CRDs followed
by the pinned hardened SPIRE chart (server, agent, Controller Manager, SPIFFE
CSI driver, and OIDC discovery provider) and the Istio base, control plane, and
private gateway. It validates a non-example SPIFFE trust domain, the CSI driver,
and the reconciled `rag-api` `ClusterSPIFFEID` before the application rollout.
`k8s/service-mesh.yaml` remains the portable raw reference; Ansible renders its
ingress host per environment.

`rag-api` receives an X.509 SVID through the CSI volume and is selected by its
namespace, service account, and both stable labels. Istio runs in sidecar mode
and enforces STRICT mTLS with its own Envoy identity path; SPIRE application
identity is intentionally not claimed to replace istiod. The primary on-prem
profile uses kubeadm/containerd and requires an organization WAF to forward
only to the Istio gateway. AWS, Azure, and generic profiles use the same
private-gateway path. K3s/Traefik/Coraza remains a legacy lab/edge option.
Each target supplies an approved trust domain,
cluster name, CA subject, JWT issuer, StorageClass, DNS, WAF, and live mTLS
acceptance evidence. The node/image-building K3s play must not be run against
managed Kubernetes; use the mesh play instead.

Velero configuration schedules daily namespace backups with CSI snapshots and
filesystem backup fallback to encrypted MinIO/S3 storage. The target cluster
must provide the Velero AWS/S3 plugin, credentials Secret, volume snapshot
class, and a tested restore drill; a manifest alone cannot guarantee an RPO or
RTO.
