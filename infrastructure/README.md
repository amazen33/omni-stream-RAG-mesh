# Infrastructure blueprints

This directory contains cloud-agnostic examples only. It is the contract
between provisioning and the Kubernetes/GitOps layer; it is not a replacement
for a reviewed provider module or an environment's policy.

`config.example.yaml` documents the values an environment must provide. Keep
credentials in a cloud secret manager, External Secrets, or CI/Jenkins
credential store. Do not copy them into this file, Terraform state, manifests,
or `.env` committed to Git.

The `terraform/aws` and `terraform/azure` directories are provider-specific
audit/search starters. Each requires a non-example SPIFFE trust domain, target
cluster name, and edge hostname and outputs the contract used by
`ansible/configure-mesh.yaml`. The AWS starter also requires private OpenSearch
subnets/security groups; neither starter creates a Kubernetes cluster, private
network module, WAF, registry, or secret manager.

Run `terraform fmt`, `validate`, and a reviewed `plan` with remote encrypted
state before applying. On new on-prem nodes, use `playbook.yaml` to install the
primary kubeadm/containerd/Calico target. Use `ansible/provision.yaml` only for
the legacy K3s lab. For EKS, AKS, bare-metal, or other prepared Kubernetes
clusters, run the provider-neutral mesh play from a bastion/CI runner with the
target kubeconfig. Application delivery remains Helm/GitOps. See
[platform profiles](../docs/platform-profiles.md).
