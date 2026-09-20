# Lab and operations runbook

## Local development

Use the local Compose profile only as a demonstration environment:

```bash
docker compose -f docker-compose.local.yaml up --build
curl http://localhost:8000/healthz
```

It uses ephemeral/in-memory behavior unless optional integrations are configured.
Do not expose development ports or credentials to a production network. Use
Python 3.12 (preferred) or 3.13 for direct development; Python 3.14 is not
supported by the pinned native dependencies.

## Kubernetes and mesh preparation

The primary on-prem target is a new upstream kubeadm/containerd/Calico cluster:

```bash
ansible-playbook -i inventory.ini playbook.yaml
```

The supplied bootstrap refuses hosts with existing K3s or kubeadm state and has
a single control plane for a lab topology. Production requires an approved HA
control-plane endpoint, durable CSI StorageClass, capacity plan, and recovery
design. Do not run the legacy `ansible/provision.yaml` K3s play against managed
Kubernetes.

Before enabling SPIFFE/SPIRE manifests, supply a working Kubernetes control
plane, Helm access, a durable StorageClass, DNS, an approved trust domain and
cluster name, CA subject, JWT issuer, and private WAF-to-Istio-gateway path.
Then run the provider-neutral mesh configuration from a configured controller:

```bash
ansible-playbook -i cloud-inventory.ini ansible/configure-mesh.yaml -e deployment_profile=aws -e kubeconfig=/secure/path/cluster.kubeconfig -e storage_class=gp3 -e spire_trust_domain=prod.example -e spire_cluster_name=prod-eks-01 -e spire_jwt_issuer=https://oidc-discovery.prod.example -e mesh_ingress_host=rag.prod.example
ansible-playbook -i cloud-inventory.ini ansible/deploy-rag.yaml -e deployment_profile=aws -e kubeconfig=/secure/path/cluster.kubeconfig -e rag_image=registry.example/rag-api -e rag_image_tag=immutable-image-sha
```

Use `deployment_profile=onprem` with
`kubeconfig=/etc/kubernetes/admin.conf` for kubeadm, or
`deployment_profile=azure` with an approved AKS storage class and immutable
Azure Blob audit container. The Helm deploy play selects the matching
`deploy/<profile>-values.yaml` overlay. Do not reuse lab trust domains in
production.

## Release checks

Before release, run:

```bash
python -m pytest -q
python -m pytest -v tests/chaos/test_lifecycle_downstream_failure.py
```

CI and Jenkins add Docker build and Trivy image/IaC gates. Publishing and
deployment are credentialed operations; use immutable tags and a protected
deployment environment.

## Operating and recovering

Keep Kafka, object storage, search, vector store, and model services on private
networks. The platform must enforce authentication and authorization at the
edge; the application does not implement end-user identity. Verify the SPIRE
CSI driver and registration, the Istio sidecar, STRICT peer authentication, and
rejected direct plaintext traffic before production admission.

Configure encrypted Velero object-store backup and CSI snapshots, then restore
to an isolated namespace at least quarterly. Preserve Object Lock retention,
validate event schemas before replay, and prove recovery of dependent PVCs
before declaring RPO/RTO. Never delete an audit bucket to repair a lab.

For full procedures and acceptance evidence, see the
[architecture and operations guide](docs/ARCHITECTURE_AND_OPERATIONS.md).
