# Lab and Operations Runbook

## Windows, WSL2, Hyper-V
Use WSL2 Ubuntu with Docker Desktop WSL integration; allocate at least 8 CPU/16 GB RAM and enable virtualization in BIOS. Hyper-V users should avoid nested Docker Desktop; run Docker Engine inside the Linux VM. Store repositories and bind mounts on the Linux filesystem for performance. Verify `docker compose ps`, `curl localhost:8000/healthz`, and GPU with `nvidia-smi` then `docker run --gpus all ...`.

## Bootstrap
Copy `.env.example` to `.env`, use a password manager, create MinIO bucket with object locking at creation, then `docker compose up -d`. In Kubernetes, install cert-manager, Strimzi, Flink operator, ArgoCD, Argo
Rollouts, and External Secrets Operator; configure the provider-specific
`ClusterSecretStore` before enabling Argo sync. Apply `k8s/rag.yaml`,
`k8s/external-secret.yaml`, Kafka, and streaming manifests. The ExternalSecret
maps the provider object `rag/runtime` into the runtime Secret; no placeholder
credentials are committed.

## Terraform and Ansible
Run `terraform fmt`, `init`, `plan`, and reviewed `apply` from the provider directory with remote encrypted state and state locking. Use least-privilege cloud identities. Run `ansible-playbook -i inventory ansible/setup_hybrid.yml --ask-become-pass`; pin OS packages and review the NVIDIA repository before production use.

## Networking and mTLS
Expose only ingress 443. Keep MinIO, OpenSearch, Kafka and Ollama on private networks. Add cert-manager issuer and service certificates; configure ingress and clients to verify the cluster CA. NetworkPolicies are default deny; explicitly add DNS, metrics, ingress, and egress rules for your CNI.

## GPU, state, and troubleshooting
Check Ollama model availability and memory; lower model size or set CPU fallback when VRAM is insufficient. A 503 on ingest usually means audit S3 endpoint/credentials or object-lock capability is unavailable. Kafka lag: inspect consumer groups, disk/PVC pressure, replication and ISR. Flink failures: inspect checkpoints/savepoints and schema compatibility. OpenSearch red cluster: inspect PVC capacity, shard allocation, and snapshots. Never delete audit buckets to repair a lab.

## Compliance
Financial workloads require data classification, PCI/PII minimization, access reviews, immutable audit retention, key rotation, backup restore tests, incident response, separation of duties, and evidence of Terraform/Jenkins/Argo approvals. Validate retention and residency with counsel; defaults here are not certification. Redaction is defense-in-depth, not a substitute for DLP and database controls.
