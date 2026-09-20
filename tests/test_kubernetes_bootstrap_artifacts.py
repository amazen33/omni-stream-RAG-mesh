from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_primary_playbook_selects_upstream_kubernetes_not_k3s() -> None:
    playbook = _read("playbook.yaml")

    assert "ansible/bootstrap-kubernetes.yaml" in playbook
    assert "ansible/provision.yaml" in playbook
    assert "K3s application-lab workflow remains" in playbook


def test_kubeadm_bootstrap_installs_a_safe_standard_stack() -> None:
    bootstrap = _read("ansible/bootstrap-kubernetes.yaml")
    variables = _read("ansible/kubernetes-vars.yaml")

    assert "containerd" in bootstrap
    assert "kubelet, kubeadm, kubectl" in bootstrap
    assert "SystemdCgroup = true" in bootstrap
    assert "kubeadm, init" in bootstrap
    assert "kubeadm token create --ttl 30m --print-join-command" in bootstrap
    assert "Existing K3s or kubeadm state was found" in bootstrap
    assert "calico_crds_manifest_url" in bootstrap
    assert "calico_operator_manifest_url" in bootstrap
    assert "kubernetes_minor: v1.35" in variables
    assert "calico_version: v3.32.2" in variables
    assert "calico/{{ calico_version }}" in variables


def test_mesh_namespace_is_created_before_mesh_resources() -> None:
    mesh_play = _read("ansible/configure-mesh.yaml")

    namespace_step = mesh_play.index("Ensure the application namespace exists")
    mesh_step = mesh_play.index("Configure Istio and SPIRE")
    assert namespace_step < mesh_step


def test_multipass_uses_kubeadm_by_default_and_keeps_k3s_explicit() -> None:
    launcher = _read("ops/new-multipass-cluster.ps1")

    assert "[string]$KubernetesMode = 'kubeadm'" in launcher
    assert "ValidateSet('kubeadm', 'k3s')" in launcher
    assert "bootstrap-kubernetes.yaml" in launcher
