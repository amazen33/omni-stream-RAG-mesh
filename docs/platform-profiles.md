# On-prem and cloud platform profiles

The application and its Helm chart use one Kubernetes workload contract across
on-prem, AWS, Azure, and other conformant clusters. Profile differences stop at
the platform boundary: storage class, Kubernetes client, edge WAF, DNS, and
the approved SPIFFE trust domain. They must not change the API, event, audit,
or `rag-api` identity contract.

## SPIFFE/SPIRE prerequisites

Enable the mesh profile only after the target cluster has a working Kubernetes
control plane, Helm access, cluster-admin-equivalent installation permission,
a durable StorageClass, DNS, and a private path from the edge WAF to the Istio
gateway. Select a unique lowercase `spire_trust_domain` and
`spire_cluster_name` for each environment; never use an example domain or
reuse a lab trust domain in production. Update the CA subject and JWT issuer
to approved organization values.

`ansible/tasks/mesh.yaml` installs the SPIRE CRDs first, then the hardened
SPIRE chart (server, agents, controller manager, CSI driver, and OIDC
discovery provider), followed by the rendered `ClusterSPIFFEID` for `rag-api`.
It validates the controller-created registration and CSI driver before the app
is installed. The chart configuration disables the broad default identity and
registers only the workload selected by both stable `rag-api` labels.

The application receives an X.509 SVID at `/run/spiffe/workload` through the
SPIFFE CSI driver. Istio runs in **sidecar mode** and independently supplies
the Envoy workload mTLS policy. SPIRE therefore provides application workload
identity; it is not represented as a replacement for Istio's certificate
authority. Ambient Istio is deliberately out of scope because its SPIRE
integration is not supported by Istio's migration guidance.

The installation uses the official [SPIRE hardened-chart installation
sequence](https://spiffe.io/docs/latest/spire-helm-charts-hardened-about/installation/)
and [ClusterSPIFFEID model](https://spiffe.io/docs/latest/spire-helm-charts-hardened-about/identifiers/).
Istio is installed base, control plane, then gateway as prescribed by the
[Istio Helm guide](https://istio.io/latest/docs/setup/install/helm/). STRICT
peer authentication follows the [Istio policy
reference](https://istio.io/latest/docs/reference/config/security/peer_authentication/).

## Profiles and commands

| Profile | Provisioning entry point | Edge path | Required overrides |
| --- | --- | --- | --- |
| On-prem Kubernetes (primary) | `playbook.yaml` → `ansible/bootstrap-kubernetes.yaml` | Organization WAF → private Istio gateway → `rag-api` | A durable CSI StorageClass, trust domain, cluster name, ingress host, CA subject, JWT issuer, and WAF route |
| AWS EKS | `ansible/configure-mesh.yaml` from a bastion/CI runner | AWS WAF (or equivalent) → private Istio gateway → `rag-api` | `deployment_profile=aws`, `kubeconfig`, `storage_class`, all SPIRE values and WAF/LB routing |
| Azure AKS | `ansible/configure-mesh.yaml` from a bastion/CI runner | Azure WAF (or equivalent) → private Istio gateway → `rag-api` | `deployment_profile=azure`, `kubeconfig`, `storage_class`, all SPIRE values and WAF/LB routing |
| Other conformant Kubernetes | `ansible/configure-mesh.yaml` | Organization WAF → private Istio gateway → `rag-api` | `deployment_profile=generic`, Kubernetes client, storage and all SPIRE values |
| K3s lab/edge (legacy) | `ansible/provision.yaml` | Traefik + Coraza → private Istio gateway → `rag-api` | Lab-only local-path storage and the legacy K3s client |

`playbook.yaml` now bootstraps the primary on-prem target: a new Debian/Ubuntu
cluster running containerd, kubeadm/kubelet/kubectl from the Kubernetes 1.35
repository, and pinned Calico 3.32.2 for NetworkPolicy. It refuses any node
that already contains K3s or kubeadm state. This bootstrap has one control
plane for the supplied lab topology; production must use an HA control-plane
endpoint and a reviewed CSI StorageClass before the mesh is enabled.

For a new on-prem cluster, bootstrap first and then configure mesh identity
only after the CSI StorageClass and edge WAF are in place:

```bash
ansible-playbook -i inventory.ini playbook.yaml
ansible-playbook -i inventory.ini ansible/configure-mesh.yaml \
  -e deployment_profile=onprem \
  -e kubeconfig=/etc/kubernetes/admin.conf \
  -e storage_class=your-csi-storage-class \
  -e spire_trust_domain=prod.example \
  -e spire_cluster_name=prod-onprem-01 \
  -e spire_jwt_issuer=https://oidc-discovery.prod.example \
  -e mesh_ingress_host=rag.prod.example
```

After bootstrap, or for a prepared cloud/bare-metal Kubernetes target, place
the controller in the `mesh_controller` inventory group and run, after
replacing every example:

```bash
ansible-playbook -i cloud-inventory.ini ansible/configure-mesh.yaml \
  -e deployment_profile=aws \
  -e kubeconfig=/secure/path/cluster.kubeconfig \
  -e storage_class=gp3 \
  -e spire_trust_domain=prod.example \
  -e spire_cluster_name=prod-eks-01 \
  -e spire_jwt_issuer=https://oidc-discovery.prod.example \
  -e mesh_ingress_host=rag.prod.example
```

Use `deployment_profile=azure` and the AKS StorageClass for Azure. For an
on-prem kubeadm controller, use `deployment_profile=onprem`,
`kubeconfig=/etc/kubernetes/admin.conf`, a durable CSI StorageClass, and
`kube_cli_argv=[kubectl]`. The K3s workflow is deliberately separate and is
not the default production path.

`terraform/aws` and `terraform/azure` establish audit/search starter resources
and expose the exact values required by the mesh task. The AWS starter requires
private OpenSearch subnet/security-group inputs and blocks public S3 access;
the Azure starter prevents public nested blobs. They do not silently create a
public ingress, VPC/VNet, AKS/EKS cluster, PrivateLink/private endpoint, or
provider WAF. Those must be organization-reviewed modules with private
networking and provider-specific identity policies.

## Acceptance checks

Before allowing application traffic, prove all of the following in the target
profile:

1. `kubectl get csidriver csi.spiffe.io` and `kubectl get clusterspiffeid rag-api`
   succeed; the registration resolves to the target trust domain.
2. A `rag-api` pod contains `istio-proxy` and the `spiffe-workload-api` volume.
3. `PeerAuthentication/rag-api-strict-mtls` is STRICT and direct plaintext
   traffic is rejected.
4. The WAF forwards only to the Istio gateway; neither WAF nor load balancer
   can reach `rag-api` directly.
5. Service-account/namespace/label changes are reviewed because they change
   the SPIFFE registration selector.

The raw `k8s/service-mesh.yaml` and `waf/streaming-rag-ingress.yaml` are
portable reference manifests with a lab host. The Ansible templates render the
actual environment host. Do not apply the raw files unmodified to a different
environment.
