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

The API image and placeholder secret values must be replaced by the deployment
pipeline and an external secret manager. The manifests do not provision a
complete production cluster or managed data services.

## Provisioning and GitOps

`terraform/aws/main.tf` and `terraform/azure/main.tf` are intentionally small
provider-specific starting points. `ansible/setup_hybrid.yml` prepares a
hybrid host, including optional NVIDIA tooling. `deploy/argocd/application.yaml`
defines Argo CD synchronization and `deploy/rollouts/rag-rollout.yaml`
contains progressive delivery resources.

For production, use encrypted remote Terraform state, workload identity,
external secrets, replicated Kafka/PVC storage, managed object storage where
appropriate, and reviewed environment overlays.
