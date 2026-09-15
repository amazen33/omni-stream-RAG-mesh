# ADR-0002: Multi-Node K3s Cluster Bootstrapping with Dynamic Token Join

## Status
**Accepted**

## Context
Provisioned virtual machines must be configured with production-grade operating system hardening, container runtimes, Kubernetes prerequisites, and an automated multi-node Kubernetes control plane and worker topology without manual credential passing or static secrets checked into source control.

## Decision
We chose **Ansible** to orchestrate node bootstrapping and **K3s** as the lightweight Kubernetes distribution:
1. **OS Hardening & Prerequisite Enforcement (`roles/common`)**:
   - Immediately and persistently disable swap (`swapoff -a` + fstab regex commenting).
   - Load essential kernel modules on boot: `overlay` and `br_netfilter`.
   - Configure sysctl parameters for bridge netfilter and IPv4 forwarding (`/etc/sysctl.d/99-kubernetes-cri.conf`).
2. **Container Runtime Engine (`roles/containerd`)**:
   - Deploy `containerd.io` with systemd cgroups explicitly enabled (`SystemdCgroup = true`).
3. **Dynamic Token Propagation (`roles/k3s_server` & `roles/k3s_agent`)**:
   - Control-plane bootstraps via `k3s server --write-kubeconfig-mode 644`.
   - Node token is retrieved dynamically from `/var/lib/rancher/k3s/server/node-token` and registered as an in-memory runtime fact across all cluster hosts (`set_fact delegate_to: "{{ item }}"`).
   - Worker nodes join using `K3S_URL=https://192.168.100.10:6443` and `K3S_TOKEN={{ k3s_token }}` without exposing tokens on disk or in repository commits.
4. **Readiness Verification**:
   - Automated polling on `kubectl get nodes` until all 3 nodes report `Ready`.

## Consequences
### Positive
- Zero manual token handling or insecure shared secret storage.
- Standardized containerd runtime compatible with all upstream OCI workloads.
- Minimal resource overhead (<512MB RAM for K3s control plane).

### Negative / Tradeoffs
- K3s defaults to SQLite for single-server control planes unless configured with external etcd.
