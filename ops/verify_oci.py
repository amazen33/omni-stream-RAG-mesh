"""Check OCI blob hashes and the main profile before publication."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
from .tool_inputs import evidence_path

BLOBS = 'blobs/sha256'


def read_blob(output, digest):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        raise ValueError('Invalid OCI descriptor digest')
    raw = (output / BLOBS / digest[7:]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest[7:]:
        raise ValueError('OCI descriptor hash mismatch')
    return json.loads(raw)


def verify(archive_path, digest, output):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        raise ValueError('Invalid expected OCI digest')
    archive_path = evidence_path(archive_path)
    output = evidence_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path) as archive:
        archive.extractall(output, filter='data')
    for blob in (output / BLOBS).iterdir():
        if hashlib.sha256(blob.read_bytes()).hexdigest() != blob.name:
            raise ValueError('OCI blob hash mismatch: ' + blob.name)
    index = (output / 'index.json').read_bytes()
    if hashlib.sha256(index).hexdigest() == digest.removeprefix('sha256:'):
        (output / BLOBS / digest[7:]).write_bytes(index)
    manifest = read_blob(output, digest)
    while 'manifests' in manifest:
        descriptors = [item for item in manifest['manifests'] if item.get('platform', {}).get('architecture', 'amd64') == 'amd64']
        if len(descriptors) != 1:
            raise ValueError('Expected exactly one linux/amd64 image')
        manifest = read_blob(output, descriptors[0]['digest'])
    config = read_blob(output, manifest['config']['digest'])
    if 'OMNI_IMAGE_PROFILE=main' not in config['config']['Env']:
        raise ValueError('Only the main image may be published')
    print('Verified main OCI artifact: ' + digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('digest')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    verify(args.archive, args.digest, args.output)
