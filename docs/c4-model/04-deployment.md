# C4 Model - Level 4: Deployment Diagram

The Deployment diagram illustrates the physical and virtual infrastructure topology, showing how containers, persistent volumes, and networks map onto the Hyper-V host and K3s virtual machine cluster.

```mermaid
C4Deployment
    title Deployment Diagram - Local Hyper-V / Hybrid Kubernetes Cluster

    Deployment_Node(host, "Physical Host / Hyper-V Server", "Windows Server / Windows 11") {
        Deployment_Node(vswitch_pub, "External Virtual Switch", "k8s-public-vswitch") {
            Container_Ext(nat, "Host NAT Gateway", "IP: 192.168.100.1", "Routes outbound internet traffic")
        }

        Deployment_Node(vswitch_priv, "Internal Private Virtual Switch", "k8s-private-vswitch (192.168.100.0/24)") {
            
            Deployment_Node(vm_master, "VM: k8s-master-01", "Ubuntu 22.04 | IP: 192.168.100.10 | 2 vCPUs, 4GB RAM") {
                Deployment_Node(k3s_ctrl, "K3s Control Plane Node") {
                    Container(k3s_api, "K3s Supervisor & Kube-API", "Port 6443", "Control-plane supervisor")
                    Container(traefik, "Traefik Ingress Controller", "Ports 80/443", "Cluster Ingress router")
                }
            }

            Deployment_Node(vm_w1, "VM: k8s-worker-01", "Ubuntu 22.04 | IP: 192.168.100.11 | 4 vCPUs, 8GB RAM") {
                Deployment_Node(k3s_w1, "K3s Worker Node 1") {
                    Container(fastapi_1, "FastAPI Pod (Replica 1)", "Port 8000")
                    ContainerDb(kafka_pod, "Kafka Pod (KRaft Mode)", "Port 9092 | 10Gi PVC")
                    ContainerDb(minio_pod, "MinIO S3 Pod", "Ports 9000/9001 | 20Gi PVC")
                    Container(ollama_1, "Ollama LLM Pod (ollama-0)", "Port 11434 | 30Gi PVC", "Scheduled via Anti-Affinity")
                }
            }

            Deployment_Node(vm_w2, "VM: k8s-worker-02", "Ubuntu 22.04 | IP: 192.168.100.12 | 4 vCPUs, 8GB RAM") {
                Deployment_Node(k3s_w2, "K3s Worker Node 2") {
                    Container(fastapi_2, "FastAPI Pod (Replica 2)", "Port 8000")
                    ContainerDb(chroma_pod, "ChromaDB Pod", "Port 8000 | 10Gi PVC")
                    Container(ollama_2, "Ollama LLM Pod (ollama-1)", "Port 11434 | 30Gi PVC", "Scheduled via Anti-Affinity")
                }
            }
        }
    }

    Rel(k3s_ctrl, k3s_w1, "Orchestration & Flannel VXLAN", "UDP 8472 / TCP 10250")
    Rel(k3s_ctrl, k3s_w2, "Orchestration & Flannel VXLAN", "UDP 8472 / TCP 10250")
    Rel(traefik, fastapi_1, "Load balances ingress traffic", "ClusterIP")
    Rel(traefik, fastapi_2, "Load balances ingress traffic", "ClusterIP")
    Rel(fastapi_1, ollama_1, "Local LLM inference", "ClusterIP")
    Rel(fastapi_2, ollama_2, "Local LLM inference", "ClusterIP")
```

## Infrastructure & Scheduling Highlights

1. **Deterministic Static IP Fabric**:
   - Master node (`192.168.100.10`) acts as the K3s supervisor and API endpoint.
   - Worker nodes (`192.168.100.11` and `192.168.100.12`) run containerized stateful workloads.
2. **Pod Anti-Affinity Distribution**:
   - The Ollama StatefulSet defines `podAntiAffinity` on topology key `kubernetes.io/hostname`. This forces Kubernetes to distribute `ollama-0` to `k8s-worker-01` and `ollama-1` to `k8s-worker-02`, preventing GPU/CPU thrashing on a single hypervisor VM.
3. **Hypervisor Port Isolation**:
   - Hyper-V Network Adapter ACLs restrict cross-node and external traffic strictly to permitted ports (22, 6443, 10250, 8472 UDP, 80, 443, 30000-32767).
