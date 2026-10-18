"""Validate the small CLI surface of the local/CI evidence tools."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def evidence_path(value):
    path = Path(value).resolve()
    roots = [ROOT / 'test-results', ROOT / '.tools', Path(tempfile.gettempdir())]
    if os.getenv('RUNNER_TEMP'):
        roots.append(Path(os.environ['RUNNER_TEMP']))
    if not any(path.is_relative_to(root.resolve()) and path != root.resolve() for root in roots):
        raise ValueError('Evidence paths must stay inside test-results, .tools or the temporary directory')
    return path


def docker_executable(value):
    candidates = []
    if shutil.which('docker'):
        candidates.append(Path(shutil.which('docker')).resolve())
    if os.name == 'nt':
        if os.getenv('LOCALAPPDATA'):
            candidates.append((Path(os.environ['LOCALAPPDATA']) /
                'Programs/Rancher Desktop/resources/resources/win32/bin/docker.exe').resolve())
        if os.getenv('ProgramFiles'):
            candidates.append((Path(os.environ['ProgramFiles']) / 'Docker/Docker/resources/bin/docker.exe').resolve())
    if value == 'docker':
        if not candidates:
            raise ValueError('Docker is not on PATH; supply the installed Rancher Desktop executable')
        return str(candidates[0])
    candidate = Path(value).resolve()
    if candidate not in candidates or not candidate.is_file():
        raise ValueError('Docker executable must be the installed Docker/Rancher Desktop client')
    return str(candidate)


def image_reference(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._:/@-]{0,254}', value):
        raise ValueError('Invalid image reference')
    return value


def scan_source(value):
    if value.startswith('docker:'):
        return 'docker:' + image_reference(value[7:])
    for prefix in ('oci-archive:', 'docker-archive:'):
        if value.startswith(prefix):
            path = evidence_path(value[len(prefix):])
            if not path.is_file():
                raise ValueError('Image archive does not exist')
            return prefix + str(path)
    raise ValueError('Scanner source must be docker:, oci-archive: or docker-archive:')


def commit_sha(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._/-]{0,199}', value) or '..' in value:
        raise ValueError('Invalid base git ref')
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', '--end-of-options', value + '^{commit}'],
                                     cwd=ROOT, text=True).strip()
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Expected a git commit SHA')
    return commit
