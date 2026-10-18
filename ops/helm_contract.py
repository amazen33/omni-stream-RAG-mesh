"""Render the O0 contract with Helm 3.19.0; preserve raw legacy profile bytes."""
import argparse
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from .tool_inputs import commit_sha, evidence_path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("lab", "generic", "onprem", "aws", "azure", "gcp")
WSL = 'wsl.exe'


def helm_command():
    binary = os.getenv("HELM_BINARY") or shutil.which("helm")
    if binary:
        return [binary]
    cached = ROOT / ".tools/helm/linux-amd64/helm"
    if os.name == "nt" and cached.is_file() and shutil.which(WSL):
        return [WSL, "--exec", linux_path(cached)]
    raise RuntimeError("Helm v3.19.0 is required; no usable executable was found")


def linux_path(path):
    value = str(Path(path).resolve()).replace('\\', '/')
    return '/mnt/' + value[0].lower() + value[2:] if os.name == "nt" else value


def verify_version():
    version = subprocess.check_output(helm_command() + ["version", "--short"], cwd=ROOT, text=True).strip()
    if version.split('+')[0] != "v3.19.0":
        raise RuntimeError(f"Required Helm v3.19.0, found {version}")
    return version


def render(profile, *, source=ROOT, extra=(), namespace="rag", check=True):
    source = Path(source).resolve()
    command = helm_command()
    convert = linux_path if command[0] == WSL else lambda p: str(p)
    values = 'values-twinfra.yaml' if profile == 'twinfra' else f'{profile}-values.yaml'
    args = ["template", "rag", convert(source / 'rag-chart'), "--namespace", namespace,
            '-f', convert(source / 'deploy' / values), '--set', 'ragApi.image.tag=o0-comparison', *extra]
    return subprocess.run(command + args, cwd=ROOT, capture_output=True, check=check, timeout=90)


def capture_baseline(base_ref, output):
    commit = commit_sha(base_ref)
    archive = subprocess.check_output(['git', 'archive', commit, 'rag-chart', 'deploy'], cwd=ROOT)
    source = output / 'source'
    source.mkdir(exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        files.extractall(source, filter='data')
    for profile in PROFILES:
        (output / f'{profile}.yaml').write_bytes(render(profile, source=source).stdout)
    return commit


def comparison_label(same, amended):
    if same:
        return 'byte-identical'
    if amended:
        return 'Amendment 4: ENABLE_VECTOR_STORE true -> false'
    return 'UNEXPECTED CHANGE'


def compare(base_ref=None, output=ROOT / 'test-results/o0-baseline'):
    output = evidence_path(output)
    output.mkdir(parents=True, exist_ok=True)
    version = verify_version()
    if base_ref:
        commit = capture_baseline(base_ref, output)
    else:
        commit = json.loads((output / 'manifest.json').read_text())['commit']
    summary = {'base': commit, 'helm': version, 'profiles': {}}
    changed = []
    for profile in PROFILES:
        baseline = (output / f'{profile}.yaml').read_bytes()
        current = render(profile).stdout
        (output / f'{profile}.current.yaml').write_bytes(current)
        difference = ''.join(difflib.unified_diff(baseline.decode().splitlines(True), current.decode().splitlines(True),
                                                fromfile=f'{profile}:baseline', tofile=f'{profile}:current'))
        (output / f'{profile}.diff').write_text(difference, encoding='utf-8')
        same = baseline == current
        # The sole allowed legacy difference is Amendment 4: the Kubernetes
        # lab profile runs the shipped main image, which excludes Chroma.
        before = b'ENABLE_VECTOR_STORE: "true"'
        after = b'ENABLE_VECTOR_STORE: "false"'
        amended = (profile == 'lab' and baseline.count(before) == 1
                   and baseline.replace(before, after) == current)
        summary['profiles'][profile] = {'identical': same, 'baselineSHA256': hashlib.sha256(baseline).hexdigest(),
                                        'currentSHA256': hashlib.sha256(current).hexdigest(),
                                        'amendment': 'A4: main image excludes Chroma; lab vector store disabled' if amended else None}
        print(f'{profile}: {comparison_label(same, amended)}')
        if not (same or amended):
            changed.append(profile)
    (output / 'comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
    if changed:
        raise SystemExit('Legacy profile render changed: ' + ', '.join(changed))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref')
    args = parser.parse_args()
    compare(args.base_ref)
