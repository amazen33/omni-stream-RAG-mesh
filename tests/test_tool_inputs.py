"""Reject CLI option injection, executable substitution and output escape."""
import pytest

from ops.tool_inputs import ROOT, commit_sha, docker_executable, evidence_path, image_reference, scan_source
from ops.verify_oci import read_blob
from ops.supply_chain import archive_base_locks, run, write


@pytest.mark.parametrize('value', ['--output=/tmp/foreign', '-v', 'image\n--privileged', 'image;command'])
def test_image_reference_rejects_option_and_command_text(value):
    with pytest.raises(ValueError):
        image_reference(value)


@pytest.mark.parametrize('value', ['--upload-pack=command', '../foreign', 'main..other', 'main\n--output=foreign'])
def test_git_ref_rejects_options_and_ambiguous_ranges(value):
    with pytest.raises(ValueError):
        commit_sha(value)


def test_git_ref_is_resolved_to_an_immutable_commit():
    assert len(commit_sha('HEAD')) == 40


def test_evidence_cannot_overwrite_source_or_select_arbitrary_executable():
    with pytest.raises(ValueError):
        evidence_path(ROOT / 'app/main.py')
    with pytest.raises(ValueError):
        docker_executable(str(ROOT / 'untrusted-docker'))
    assert evidence_path(ROOT / 'test-results/report.json').is_relative_to(ROOT)


def test_scanner_sources_require_an_explicit_validated_transport():
    assert scan_source('docker:local/omni-o0:main') == 'docker:local/omni-o0:main'
    with pytest.raises(ValueError):
        scan_source('--file=/etc/passwd')
    with pytest.raises(ValueError):
        scan_source('oci-archive:' + str(ROOT / 'app/main.py'))


def test_oci_descriptor_cannot_escape_blob_directory(tmp_path):
    with pytest.raises(ValueError, match='descriptor digest'):
        read_blob(tmp_path, 'sha256:../../foreign.json')


def test_scanner_json_cannot_overwrite_application_source():
    with pytest.raises(ValueError, match='Scanner JSON'):
        write(ROOT / 'app/main.py', {'synthetic': True})


def test_scanner_rejects_unexpected_options_before_execution():
    with pytest.raises(ValueError, match='Unexpected scanner option'):
        run([str(ROOT / '.tools/scanners/grype'), '--config=/untrusted'], ROOT / 'test-results/unused.json')


def test_base_lock_extraction_requires_a_commit_before_any_git_call():
    with pytest.raises(ValueError, match='immutable commit SHA'):
        archive_base_locks('--format=untrusted', ROOT / 'test-results')
