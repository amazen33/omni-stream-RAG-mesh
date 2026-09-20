from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_manifests_do_not_use_mutable_latest_image_tags() -> None:
    files = [ROOT / "docker-compose.yaml"]
    for directory in ("deploy", "rag-chart", "k8s", "waf", "ansible"):
        files.extend((ROOT / directory).rglob("*.yaml"))
        files.extend((ROOT / directory).rglob("*.yml"))
    mutable = [
        path.relative_to(ROOT).as_posix()
        for path in files
        if re.search(r"(?m)^\s*image:\s*[^\s#]*:latest(?:\s|$)", path.read_text(encoding="utf-8"))
    ]
    assert mutable == []


def test_bootstrap_and_mesh_versions_are_explicitly_pinned() -> None:
    variables = (ROOT / "ansible/kubernetes-vars.yaml").read_text(encoding="utf-8")
    mesh = (ROOT / "ansible/mesh-vars.yaml").read_text(encoding="utf-8")

    assert "kubernetes_minor: v1.35" in variables
    assert "calico_version: v3.32.2" in variables
    assert "local_path_provisioner_version: v0.0.36" in variables
    for version in ('version: "1.31.0"', 'version: "0.5.0"', 'version: "0.30.0"'):
        assert version in mesh
