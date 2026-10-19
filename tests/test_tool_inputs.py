"""Reject CLI option injection, executable substitution and output escape."""
import pytest

from ops.tool_inputs import ROOT, commit_sha, docker_executable, evidence_path, image_reference, scan_source
from ops.verify_oci import read_blob
from ops.supply_chain import archive_base_locks, osv_arguments, run, scanner_command, write


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


def test_scanner_json_cannot_overwrite_application_source(tmp_path):
    source = tmp_path / 'app/main.py'
    source.parent.mkdir()
    source.write_text('application source sentinel\n')
    with pytest.raises(ValueError, match='Scanner JSON'):
        write(source, {'synthetic': True})
    assert source.read_text() == 'application source sentinel\n'


def test_scanner_rejects_unexpected_options_before_execution():
    with pytest.raises(ValueError, match='Unexpected scanner option'):
        run([str(ROOT / '.tools/scanners/grype'), '--config=/untrusted'], ROOT / 'test-results/unused.json')


def test_base_lock_extraction_requires_a_commit_before_any_git_call():
    with pytest.raises(ValueError, match='immutable commit SHA'):
        archive_base_locks('--format=untrusted', ROOT / 'test-results')


def test_scanner_command_is_rebuilt_from_the_closed_operation_set():
    binary = str(ROOT / '.tools/scanners/grype')
    assert scanner_command([binary, 'db', 'update']) == [binary, 'db', 'update']
    with pytest.raises(ValueError, match='Unexpected scanner option'):
        scanner_command([binary, 'db', 'delete'])


def test_even_repository_evidence_cannot_replace_the_fixed_report_file(tmp_path):
    unrelated = tmp_path / 'unrelated.json'
    unrelated.write_text('unrelated evidence sentinel\n')
    with pytest.raises(ValueError, match='fixed report'):
        write(unrelated, {'synthetic': True})
    assert unrelated.read_text() == 'unrelated evidence sentinel\n'


def test_missing_baseline_locks_cannot_fall_back_to_scanning_current_sources():
    with pytest.raises(ValueError, match='explicit OSV lock file'):
        osv_arguments([])
