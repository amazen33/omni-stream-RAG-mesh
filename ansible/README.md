# Ansible Multi-Node K3s Cluster Configuration & Bootstrapping

This Ansible repository automatically configures and bootstraps a 3-node Kubernetes (K3s) cluster across the provisioned Hyper-V / Linux VMs.

## What this Playbook Does
1. **OS Hardening & Prereqs (`roles/common`)**:
   - Disables swap immediately and persistently in `/etc/fstab`.
   - Enables and loads `overlay` and `br_netfilter` kernel modules.
   - Configures sysctl parameters:
     - `net.bridge.bridge-nf-call-iptables = 1`
     - `net.bridge.bridge-nf-call-ip6tables = 1`
     - `net.ipv4.ip_forward = 1`
   - Installs prerequisite networking packages (`socat`, `conntrack`, `ipset`, `iptables`).
2. **Container Runtime Engine (`roles/containerd`)**:
   - Installs `containerd.io`.
   - Configures systemd cgroups (`SystemdCgroup = true`).
   - Starts and enables the `containerd` systemd daemon.
3. **K3s Master Control Plane (`roles/k3s_server`)**:
   - Bootstraps K3s server with `--write-kubeconfig-mode 644` and containerd CRI socket.
   - Reads the cluster join token from `/var/lib/rancher/k3s/server/node-token`.
   - Broadcasts the token dynamically across all Ansible worker hosts in-memory.
   - Fetches `kubeconfig-cluster.yaml` to your local workstation.
4. **Automated Worker Joining (`roles/k3s_agent`)**:
   - Installs K3s agent on worker nodes pointing to `https://192.168.100.10:6443` using the retrieved token.
5. **Readiness Validation**:
   - Verifies all 3 nodes report status `Ready` via `kubectl get nodes -o wide`.

## Prerequisites
- SSH connectivity with key authentication to `ubuntu@192.168.100.10`, `11`, `12`.
- Sudo access without password prompts.

## Quickstart
```bash
# Verify SSH reachability to all nodes
ansible k8s_cluster -m ping

# Run complete cluster provisioning playbook
ansible-playbook site.yml
```
