# Infrastructure blueprints

This directory contains cloud-agnostic examples only. It is the contract
between provisioning and the Kubernetes/GitOps layer; it is not a replacement
for a reviewed provider module or an environment's policy.

`config.example.yaml` documents the values an environment must provide. Keep
credentials in a cloud secret manager, External Secrets, or CI/Jenkins
credential store. Do not copy them into this file, Terraform state, manifests,
or `.env` committed to Git.

The existing `terraform/aws` and `terraform/azure` directories remain
provider-specific starting points. Run `terraform fmt`, `validate`, and a
reviewed `plan` with remote encrypted state before applying. The Ansible
playbook is for host preparation; application delivery remains Kubernetes and
Argo CD. No cloud, cluster, registry, or secret manager is assumed by these
examples.
