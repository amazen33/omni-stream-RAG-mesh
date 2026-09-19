# Deployment and infrastructure topology

## Local and container topology

`docker-compose.yml` defines the reference local topology:

- `rag-api` builds the application image and exposes port 8000.
- MinIO provides S3-compatible storage on ports 9000/9001.
- OpenSearch provides the local search service on port 9200.
- Ollama provides model inference on port 11434.
- ChromaDB provides the vector service on port 8001 (container port 8000).
- Kafka runs in single-node KRaft mode.
- Spark runs `streaming/spark_job.py` against Kafka and MinIO.
- TimescaleDB provides an optional time-series analytics store and EventStoreDB
  an optional immutable CQRS stream store.
- OpenTelemetry Collector receives OTLP and forwards traces to Tempo while
  exposing metrics to Prometheus.

Credentials and feature flags come from `.env`; `.env.example` contains
placeholders only. Compose is a development/reference deployment, not a
high-availability production topology.

## Kubernetes topology

The `k8s/` manifests provide:

- `k8s/rag.yaml`: `rag` namespace, two API replicas, ConfigMap/Secret
  references, probes, PVC, service, and default-deny/API NetworkPolicies.
- `k8s/kafka-kraft.yaml`: Kafka KRaft broker/controller resources.
- `k8s/spark-streaming.yaml`: Spark submission CronJob and job ConfigMap.
- `k8s/debezium.yaml`: CDC connector extension point.
- `k8s/mtls-cert-manager.yaml`: certificate-management extension point.
- `k8s/service-mesh.yaml`: sidecar-mode Istio STRICT mTLS, ingress
  authorization, and a narrowly selected SPIRE `ClusterSPIFFEID` for `rag-api`.
- `k8s/timescaledb-eventstore.yaml`: TimescaleDB, EventStoreDB, and an
  OpenTelemetry Collector.
- `k8s/velero-backup.yaml`: MinIO/S3 backup location and daily PVC snapshot
  schedule for the `rag` namespace.

The API image and placeholder secret values must be replaced by the deployment
pipeline and an external secret manager. The manifests do not provision a
complete production cluster or managed data services. `ansible/tasks/mesh.yaml`
installs Istio and the SPIRE hardened stack before it renders the service mesh
manifest; it validates the CSI driver and the `ClusterSPIFFEID` registration.
The `rag-api` NetworkPolicy allows only the Istio ingress namespace, istiod xDS,
and CoreDNS on UDP/TCP 53; all other traffic remains default-deny. The primary
kubeadm/containerd and cloud profiles require an organization/provider WAF to
forward to the gateway. K3s Traefik and Coraza are retained under
`ansible/tasks/onprem-waf.yaml` for the legacy lab only. See
[platform profiles](platform-profiles.md).

## Provisioning and GitOps

`terraform/aws/main.tf` and `terraform/azure/main.tf` are formatted,
provider-specific audit/search starters. They require a unique SPIFFE
trust domain, cluster name, and edge host, then output a provider-neutral mesh
contract for the Ansible task. They deliberately do not replace a reviewed
private EKS/AKS, VPC/VNet, WAF, or secret-management module.
`ansible/setup_hybrid.yml` prepares a hybrid host, including optional NVIDIA
tooling. `deploy/argocd/application.yaml` defines Argo CD synchronization and
`deploy/rollouts/rag-rollout.yaml` contains progressive delivery resources.

For production, use encrypted remote Terraform state, workload identity,
external secrets, replicated Kafka/PVC storage, managed object storage where
appropriate, and reviewed environment overlays.
