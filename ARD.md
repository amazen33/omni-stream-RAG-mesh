# Architecture Decision Record (ADR)

## Scope

Hybrid on-prem/cloud RAG for regulated transaction workloads. Data stays in the
selected region; only redacted text leaves trusted boundaries.

## Decisions

| Decision | Status | Rationale and boundary |
| --- | --- | --- |
| Sanitization before external processing | Accepted | Recognised email, phone, payment-card, and SSN values become versioned, canonicalized 128-bit HMAC tokens before chunking, embeddings, retrieval, model inference, events, search, or audit writes. Source and payment identifiers are also HMAC-tokenized before metadata/events leave the RAG ingress boundary. |
| Object-locked audit evidence | Accepted | S3/MinIO Object Lock, Azure Blob locked immutability, and GCS Bucket Lock support a governed retention period when their adapters are enabled. Audit records retain server correlation IDs, HMAC tokens, and operational metadata—not raw request content or identifiers. The in-memory fallback is bounded and development/test-only. |
| Server-owned correlation and compensation | Accepted | The server issues immutable request, correlation, and W3C trace identifiers and discards caller-supplied trace headers. Successful and failed flows record lifecycle transitions and compensations. |
| Bounded compensation, not event-sourcing claim | Accepted | The implementation removes newly indexed chunks when its following audit write fails and emits compensating events. It does not provide durable event sourcing, atomic outbox delivery, or universal rollback; those require a separate append-only event store, projector, idempotency, and recovery design. |
| Python resilience policy | Accepted | Bounded bulkheads, queues, retries, transport timeouts, and histogram metrics protect retrieval/model/event boundaries and return safe fallback results where possible. |
| kubeadm primary on-prem platform | Accepted | Upstream Kubernetes with containerd and Calico is the portable on-prem production target. Managed EKS/AKS/GKE use the same Helm workload contract. K3s is legacy lab/edge only. |
| SPIRE + Istio sidecars | Accepted | SPIRE CSI bind-mounts the Workload API socket directory. Application readiness verifies that the local `SPIFFE_ENDPOINT_SOCKET` is connectable without reading SVID files or key material. Istio independently enforces Envoy STRICT mTLS. Neither replaces the other. |
| Helm as deployment source | Accepted | The Helm chart is the one source for `rag-api`; Ansible and Argo CD render it, and delivery never mutates a Deployment with `kubectl set image`. |
| Private gateway edge contract | Accepted | WAF → private Istio gateway → `rag-api` is required for on-prem and cloud. Direct WAF/load-balancer access to the workload is prohibited. |
| Twinfra dev O0/O1 boundary | Accepted, O1 pending | The no-mesh Twinfra profile uses the existing APISIX gateway in `platform-services`, one ephemeral replica, no PDB and no ServiceAccount API token. O0 is local/CI evidence only; authenticated hosting requires O1's owner-run receipt. |
| Main and local lab images (D-O12) | Accepted | Main excludes Chroma, NumPy, ONNX Runtime and Chroma-only dependencies. Only main may be published. The separate hashed lab lock is local development only; it retains Chroma's native licence notices in THIRD-PARTY.md. |
| Safe runtime defaults | Accepted | Production is the default profile, requires a validated non-default HMAC key shared by audit and events, disables API documentation URLs and suppresses exception messages/tracebacks. Local/test entry points declare their profile. |
| Digest delivery and authority | Accepted | Build main once as OCI, scan it with the pinned ADR-0049 tools, publish the same digest with GITHUB_TOKEN, and sign provenance. Twinfra is Argo CD only; no Twinfra kubeconfig in GitHub. Legacy push deployment requires ENABLE_PUSH_DEPLOY=true and a stable-tag dispatch. |
| Source visibility and third-party register | Licence choice pending | GitHub reports public visibility; the owner explicitly authorized proceeding on 2026-10-19 after the discrepancy was reported. No source licence is inferred or added. THIRD-PARTY.md records actual main/lab packages, base-os once, and models; the current Llama default fails G3.5 and is not approved for Twinfra hosting. |

## Core tradeoffs

Chroma is the local lab vector store; the shipped main image omits it under
D-O12. OpenSearch is the planned Twinfra search/vector adapter. Configured stores fail visibly rather than silently
falling back to per-pod memory. AWS uses SigV4 with a least-privilege workload
role; non-AWS search uses a protected basic-auth secret when selected.

Kafka, EventStoreDB, TimescaleDB, Spark/Flink, and cloud integrations are
optional extension points. A manifest or Compose service does not establish a
durable event projection, exactly-once delivery, RTO/RPO, PCI compliance, or
production readiness without live evidence.

## Mesh and recovery decision

`ansible/configure-mesh.yaml` installs the pinned SPIRE CRDs/hardened stack and
Istio in dependency order for a prepared Kubernetes target. It validates a
non-example trust domain, durable StorageClass, CSI driver, and selected
`rag-api` `ClusterSPIFFEID` before `ansible/deploy-rag.yaml` rolls out Helm.
Each environment must provide its approved trust domain, cluster name, CA
subject, JWT issuer, DNS, WAF route, credentials, and mTLS/SVID acceptance
evidence.

Velero schedules encrypted object-store backups with CSI snapshots and a
filesystem fallback. Operators must provide the plugin, credentials,
VolumeSnapshotClass, and tested isolated restore; the manifest alone cannot
guarantee recovery objectives.

See the [architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md)
for platform prerequisites and deployment evidence, the
[TOGAF/ADM implementation](docs/TOGAF_Architecture_Definition.md) for governance,
and the [C4 model](docs/c4-model/C4_MODEL.md) for structural and dynamic views.
