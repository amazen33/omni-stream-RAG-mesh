"""Check OCI blob hashes and the main profile before publication."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile


def verify(archive_path, digest, output):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        raise ValueError('Invalid expected OCI digest')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path) as archive:
        archive.extractall(output, filter='data')
    for blob in (output / 'blobs/sha256').iterdir():
        if hashlib.sha256(blob.read_bytes()).hexdigest() != blob.name:
            raise ValueError('OCI blob hash mismatch: ' + blob.name)
    index = (output / 'index.json').read_bytes()
    if hashlib.sha256(index).hexdigest() == digest[7:]:
        (output / 'blobs/sha256' / digest[7:]).write_bytes(index)
    manifest = json.loads((output / 'blobs/sha256' / digest[7:]).read_bytes())
    while 'manifests' in manifest:
        descriptors = [item for item in manifest['manifests'] if item.get('platform', {}).get('architecture', 'amd64') == 'amd64']
        if len(descriptors) != 1:
            raise ValueError('Expected exactly one linux/amd64 image')
        manifest = json.loads((output / 'blobs/sha256' / descriptors[0]['digest'][7:]).read_bytes())
    config = json.loads((output / 'blobs/sha256' / manifest['config']['digest'][7:]).read_bytes())
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
