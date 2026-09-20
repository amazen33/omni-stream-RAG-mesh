from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_spire_stack_is_pinned_and_enables_required_components() -> None:
    values = _read("ansible/mesh-vars.yaml")

    assert "chart: spiffe/spire-crds" in values
    assert 'version: "0.5.0"' in values
    assert "chart: spiffe/spire" in values
    assert 'version: "0.30.0"' in values
    assert "strictMode: true" in values
    assert "controllerManager:\n          enabled: true" in values
    assert "trustDomain:" in values
    assert "clusterName:" in values
    assert "jwtIssuer:" in values
    assert "labels: {istio: ingressgateway}" in values


def test_spire_identity_defaults_are_nested_in_chart_values() -> None:
    values = yaml.safe_load(_read("ansible/mesh-vars.yaml"))
    spire = next(item for item in values["mesh_operator_releases"] if item["name"] == "spire")

    identities = spire["values"]["spire-server"]["controllerManager"]["identities"]
    assert identities["clusterSPIFFEIDs"]["default"]["enabled"] is False


def test_mesh_registration_is_narrow_and_portable() -> None:
    manifest = _read("ansible/templates/service-mesh.yaml.j2")

    assert "kind: ClusterSPIFFEID" in manifest
    assert "spiffeIDTemplate:" in manifest
    assert "{{ .TrustDomain }}" in manifest
    assert "namespaceSelector:" in manifest
    assert "app.kubernetes.io/name: rag-api" in manifest
    assert "workloadSelectorTemplates" not in manifest
    assert "mode: STRICT" in manifest
    assert "paths: [\"/stats/prometheus\"]" in manifest


def test_rag_workload_uses_the_spiffe_csi_volume_when_mesh_enabled() -> None:
    deployment = _read("rag-chart/templates/rag-api-deployment.yaml")
    values = _read("rag-chart/values.yaml")

    assert "sidecar.istio.io/inject" in deployment
    assert "driver: {{ .Values.mesh.spiffe.csiDriver | quote }}" in deployment
    assert "spiffe-workload-api" in deployment
    assert "enabled: false" in values
    assert "REQUIRE_SPIFFE_SVID" in deployment
    assert "SPIFFE_ENDPOINT_SOCKET" in deployment
    assert "socketFile: agent.sock" in values
    assert "annotations:\n        sidecar.istio.io/inject" not in deployment
    assert "automountServiceAccountToken: {{ .Values.serviceAccount.automountServiceAccountToken }}" in deployment


def test_cloud_network_policies_allow_required_identity_and_storage_egress() -> None:
    policy = _read("rag-chart/templates/network-policy.yaml")
    gcp = yaml.safe_load(_read("deploy/gcp-values.yaml"))
    for profile in ("aws", "azure", "gcp"):
        values = yaml.safe_load(_read(f"deploy/{profile}-values.yaml"))
        assert values["networkPolicy"]["egress"]["externalCIDRs"] == ["0.0.0.0/0"]
        assert values["networkPolicy"]["egress"]["externalPorts"] == [443]
    assert set(gcp["networkPolicy"]["egress"]["metadataCIDRs"]) == {
        "169.254.169.252/32", "169.254.169.254/32"
    }
    assert "externalCIDRs" in policy
    assert "metadataCIDRs" in policy
    assert ".Values.auditInit.hook" in _read("rag-chart/templates/audit-init.yaml")


def test_edge_waf_routes_to_istio_not_directly_to_the_workload() -> None:
    route = _read("waf/streaming-rag-ingress.yaml")
    config = _read("waf/traefik-helmchartconfig.yaml")

    assert "name: istio-ingress" in route
    assert "namespace: istio-ingress" in route
    assert "name: rag-api" not in route.split("services:", 1)[1]
    assert "allowCrossNamespace=true" in config


def test_cloud_profile_and_terraform_contract_are_documented() -> None:
    profile = _read("docs/ARCHITECTURE_AND_OPERATIONS.md")

    assert "ansible/configure-mesh.yaml" in profile
    assert "AWS EKS" in profile
    assert "Azure AKS" in profile
    assert "Google GKE" in profile
    for relative_path in ("terraform/aws/main.tf", "terraform/azure/main.tf", "terraform/gcp/main.tf"):
        terraform = _read(relative_path)
        assert "variable \"spire_trust_domain\"" in terraform
        assert "output \"mesh_deployment_contract\"" in terraform
    gcp_terraform = _read("terraform/gcp/main.tf")
    assert "is_locked        = true" in gcp_terraform
    assert "variable \"gke_workload_identity_pool\"" in gcp_terraform
    assert "local.gke_workload_identity_pool" in gcp_terraform


def test_portable_deployment_play_uses_helm_and_asserts_mesh_injection() -> None:
    deploy_play = _read("ansible/deploy-rag.yaml")

    assert "deployment_profile in ['onprem', 'aws', 'azure', 'gcp', 'generic']" in deploy_play
    assert "deploy/gcp-values.yaml" in deploy_play
    assert "gcp_workload_identity_service_account" in deploy_play
    assert "gcp-runtime-values.yaml.j2" in deploy_play
    gcp_runtime_values = _read("ansible/templates/gcp-runtime-values.yaml.j2")
    assert "iam.gke.io/gcp-service-account" in gcp_runtime_values
    assert "AUDIT_BUCKET" in gcp_runtime_values
    assert "Upgrade the application using Helm" in deploy_play
    assert "istio-proxy" in deploy_play
    assert "spiffe-workload-api" in deploy_play
    assert "exec', 'deployment/rag-api'" in deploy_play
    assert "service proxy" not in deploy_play
