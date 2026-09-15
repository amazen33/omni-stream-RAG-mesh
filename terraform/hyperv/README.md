# Terraform Hyper-V 3-Node Kubernetes Infrastructure

This directory contains Terraform scripts to provision a 3-node Linux VM cluster on Windows Hyper-V:
- **1 Control-Plane Node**: `k8s-master-01` (2 vCPUs, 4GB RAM, Static IP `192.168.100.10`)
- **2 Worker Nodes**: `k8s-worker-01`, `k8s-worker-02` (4 vCPUs, 8GB RAM each, Static IPs `192.168.100.11`, `192.168.100.12`)

## Features
- **Network Segmentation**:
  - **Internal Private vSwitch** (`k8s-private-vswitch`): Isolated CIDR `192.168.100.0/24`.
  - **External Public vSwitch** (`k8s-public-vswitch`): Attached to host NIC for public ingress/egress.
  - **Host NAT Gateway**: Automatically sets up Windows NAT routing for `192.168.100.0/24`.
- **Security Group / Port ACLs**:
  - Master Node: Port 22 (SSH), 6443 (Kubernetes API), 10250 (Kubelet), 8472 (Flannel VXLAN UDP), 2379-2380 (etcd).
  - Worker Nodes: Port 22 (SSH), 10250 (Kubelet), 8472 (Flannel VXLAN UDP), 80/443 (HTTP/HTTPS), 30000-32767 (NodePort range).
  - Explicit Deny on all other unsolicited inbound traffic.
- **Automated Inventory**: Generates `ansible/inventory/hosts.ini` ready for immediate bootstrapping.

## Usage
1. Ensure Hyper-V is enabled and PowerShell is running as Administrator.
2. Copy `terraform.tfvars.example` to `terraform.tfvars` and update paths:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```
3. Initialize and apply:
   ```bash
   terraform init
   terraform plan -out=tfplan
   terraform apply tfplan
   ```
4. Once completed, proceed to the `ansible/` directory to run the node configuration and K3s bootstrap playbook.
