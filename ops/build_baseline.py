"""Build only the PR base's tracked source in a disposable local image."""
import argparse
import io
from pathlib import Path
import subprocess
import tarfile
from .tool_inputs import commit_sha, docker_executable

ROOT = Path(__file__).resolve().parents[1]


def build(base_ref, docker='docker'):
    commit = commit_sha(base_ref)
    docker = docker_executable(docker)
    source = ROOT / 'test-results/o0-baseline/image-source' / (commit + '-runtime')
    source.mkdir(parents=True, exist_ok=True)
    # Archive only Docker build inputs. Historical tracked pytest symlinks are
    # unrelated to the image and may point outside the repository.
    paths = ('.dockerignore', 'Dockerfile', 'requirements.txt', 'requirements-lab.txt',
             'app', 'domain', 'contexts', 'ops')
    available = subprocess.check_output(['git', 'ls-tree', '--name-only', commit], cwd=ROOT, text=True).splitlines()
    data = subprocess.check_output(['git', 'archive', commit, '--', *[p for p in paths if p in available]], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(source, filter='data')
    tag = 'local/omni-o0-baseline:' + commit[:12]
    subprocess.run([docker, 'build', '--tag', tag, str(source)], cwd=ROOT, check=True)
    return tag


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref', required=True)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    print(build(args.base_ref, args.docker))
