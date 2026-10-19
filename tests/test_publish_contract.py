"""Keep release authority, artifact identity and the local image split explicit."""
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

import pytest

from ops.verify_oci import verify


def test_every_external_action_is_pinned_with_a_version_comment():
    for path in Path('.github/workflows').glob('*.y*ml'):
        for line in path.read_text().splitlines():
            if re.search(r'\buses:\s*[^.\s]', line):
                assert re.search(r'uses: [\w.-]+/[\w./-]+@[a-f0-9]{40}\s+#\s+v\d', line), (path, line)


def test_publish_and_deploy_have_separate_authority():
    text = Path('.github/workflows/publish-deploy.yml').read_text()
    import yaml
    workflow = yaml.safe_load(text)
    jobs = workflow['jobs']
    assert "vars.ENABLE_PUSH_DEPLOY == 'true' &&" in jobs['deploy']['if']
    assert "github.ref_type == 'tag'" in jobs['deploy']['if']
    assert "!contains(github.ref_name, '-')" in jobs['deploy']['if']
    assert jobs['publish']['needs'] == ['build', 'scan']
    assert jobs['publish']['permissions']['id-token'] == 'write'
    assert jobs['scan'].get('permissions', workflow['permissions']) == {'contents': 'read'}
    assert 'PROFILE=lab' not in text
    assert 'PROFILE=main' in text and 'push-to-registry: true' in text
    assert 'secrets.GITHUB_TOKEN' in text and 'oras cp --from-oci-layout' in text
    assert 'type=oci,dest=' in text and 'IMAGE_NAME@$IMAGE_DIGEST' in text
    assert 'docker build' not in str(jobs['publish'])


def oci_archive(tmp_path, profile='main', corrupt=False):
    blobs = {}
    def blob(value):
        raw = json.dumps(value).encode()
        digest = hashlib.sha256(raw).hexdigest()
        blobs['blobs/sha256/' + digest] = raw
        return 'sha256:' + digest
    config = blob({'config': {'Env': ['OMNI_IMAGE_PROFILE=' + profile]}})
    digest = blob({'schemaVersion': 2, 'config': {'digest': config}, 'layers': []})
    blobs['index.json'] = json.dumps({'schemaVersion': 2, 'manifests': [{'digest': digest}]}).encode()
    if corrupt:
        blobs['blobs/sha256/' + config[7:]] = b'tampered'
    path = tmp_path / 'image.tar'
    with tarfile.open(path, 'w') as archive:
        for name, content in blobs.items():
            item = tarfile.TarInfo(name)
            item.size = len(content)
            archive.addfile(item, io.BytesIO(content))
    return path, digest


@pytest.mark.parametrize('profile,corrupt,allowed', [('main', False, True), ('lab', False, False), ('main', True, False)])
def test_oci_profile_and_blob_integrity(tmp_path, profile, corrupt, allowed):
    archive, digest = oci_archive(tmp_path, profile, corrupt)
    if allowed:
        verify(archive, digest, tmp_path / 'layout')
    else:
        with pytest.raises(ValueError):
            verify(archive, digest, tmp_path / 'layout')
