# ADR-0001: Hybrid Infrastructure Provisioning via Hyper-V & Terraform

## Status
**Accepted**

## Context
We require a reproducible, local-first hybrid infrastructure capable of provisioning a 3-node Kubernetes cluster (1 control-plane node, 2 worker nodes) on Windows Hyper-V hosts. The environment must support deterministic static IP addressing, internal network isolation, public egress via host NAT, and fine-grained port-level security isolation before nodes are configured.

## Decision
We adopted **Terraform** using the community-standard `taliesins/hyperv` provider alongside native PowerShell automation for network fabric configuration:
1. **Network Segmentation**:
   - Internal Virtual Switch (`k8s-private-vswitch`) bounded to `192.168.100.0/24`.
   - External Virtual Switch (`k8s-public-vswitch`) attached to the physical host adapter.
   - Host NAT Gateway provisioned at `192.168.100.1` via `New-NetNat` to provide outbound egress.
2. **Static IP Allocation**:
   - Master node `k8s-master-01`: `192.168.100.10` (2 vCPUs, 4GB RAM, 50GB disk).
   - Worker node `k8s-worker-01`: `192.168.100.11` (4 vCPUs, 8GB RAM, 80GB disk).
   - Worker node `k8s-worker-02`: `192.168.100.12` (4 vCPUs, 8GB RAM, 80GB disk).
3. **Port ACL Security Groups**:
   - Hyper-V Network Adapter Port ACLs explicitly permit inbound traffic only on designated cluster ports (22 SSH, 6443 K8s API, 10250 Kubelet, 8472 Flannel VXLAN UDP, 80/443 Ingress, 30000-32767 NodePort) and enforce default inbound denial.
4. **Dynamic Inventory Handoff**:
   - Terraform `local_file` resource generates the Ansible inventory [`ansible/inventory/hosts.ini`](../../ansible/inventory/hosts.ini) dynamically upon completion.

## Consequences
### Positive
- Fully automated, declarative VM lifecycle without requiring cloud spend or external hypervisor licenses.
- Strict network isolation protecting control-plane APIs from unauthorized local subnets.
- Seamless handoff to configuration management via dynamic inventory generation.

### Negative / Tradeoffs
- Requires Windows Hyper-V management privileges and PowerShell execution permissions on the host.
- Differencing VHDX drives require a pre-existing golden OS base image template.
