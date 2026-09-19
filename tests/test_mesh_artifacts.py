from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_spire_stack_is_pinned_and_enables_required_components() -> None:
    values = _read("ansible/lab-vars.yaml")

    assert "chart: spiffe/spire-crds" in values
    assert 'version: "0.5.0"' in values
    assert "chart: spiffe/spire" in values
    assert 'version: "0.30.0"' in values
    assert "strictMode: true" in values
    assert "controllerManager:\n          enabled: true" in values
    assert "trustDomain:" in values
    assert "clusterName:" in values
    assert "jwtIssuer:" in values


def test_mesh_registration_is_narrow_and_portable() -> None:
    manifest = _read("k8s/service-mesh.yaml")

    assert "kind: ClusterSPIFFEID" in manifest
    assert "spiffe://{{ .TrustDomain }}/ns/{{ .PodMeta.Namespace }}/sa/{{ .PodSpec.ServiceAccountName }}" in manifest
    assert "namespaceSelector:" in manifest
    assert "app.kubernetes.io/name: rag-api" in manifest
    assert "workloadSelectorTemplates" not in manifest
    assert "mode: STRICT" in manifest


def test_rag_workload_uses_the_spiffe_csi_volume_when_mesh_enabled() -> None:
    deployment = _read("rag-chart/templates/rag-api-deployment.yaml")
    values = _read("rag-chart/values.yaml")

    assert "sidecar.istio.io/inject" in deployment
    assert "driver: {{ .Values.mesh.spiffe.csiDriver | quote }}" in deployment
    assert "spiffe-workload-api" in deployment
    assert "enabled: false" in values


def test_edge_waf_routes_to_istio_not_directly_to_the_workload() -> None:
    route = _read("waf/streaming-rag-ingress.yaml")
    config = _read("waf/traefik-helmchartconfig.yaml")

    assert "name: istio-ingress" in route
    assert "namespace: istio-ingress" in route
    assert "name: rag-api" not in route.split("services:", 1)[1]
    assert "allowCrossNamespace=true" in config


def test_cloud_profile_and_terraform_contract_are_documented() -> None:
    profile = _read("docs/platform-profiles.md")

    assert "ansible/configure-mesh.yaml" in profile
    assert "AWS EKS" in profile
    assert "Azure AKS" in profile
    for relative_path in ("terraform/aws/main.tf", "terraform/azure/main.tf"):
        terraform = _read(relative_path)
        assert "variable \"spire_trust_domain\"" in terraform
        assert "output \"mesh_deployment_contract\"" in terraform
