"""Exercise the admission rules against synthetic, deterministic findings."""
from datetime import date, timedelta
import json

import pytest

from ops.supply_chain import cvss3, evaluate, finding, identity, sha


TODAY = date(2026, 10, 19)
KEV = {'catalogVersion': 'synthetic', 'vulnerabilities': []}


def issue(severity='High', fixed=True):
    return finding('image:main', 'sample', '1.0', ['CVE-2026-0001', 'GHSA-synthetic'],
                   severity, ['2.0'] if fixed else [], 'grype')


def gate(value, previous=(), state=None, exceptions=(), kev=KEV):
    return evaluate([value], previous, kev, state or {}, exceptions, on=TODAY)[0][0]


def test_new_high_with_fix_and_any_kev_block():
    assert gate(issue())['blockReason'] == 'High introduced by PR'
    unfixed = issue('Low', False)
    result = gate(unfixed, kev={'catalogVersion': 'synthetic', 'vulnerabilities': [{'cveID': 'CVE-2026-0001'}]})
    assert result['blocked'] and result['blockReason'] == 'KEV'


def test_critical_requires_fix_and_lower_findings_are_reported():
    assert gate(issue('Critical'))['blocked']
    assert not gate(issue('Critical', False))['blocked']
    assert not gate(issue('High', False))['blocked']
    assert not gate(issue('Medium'))['blocked']


def test_high_first_seen_persists_across_version_changes_and_aliases():
    current = issue()
    previous = dict(current, version='0.9', vulnerability='GHSA-synthetic')
    key = sha(json.dumps(identity(current), separators=(',', ':')).encode())
    for age, blocked in [(13, False), (14, True)]:
        state = {key: (TODAY - timedelta(days=age)).isoformat()}
        result = gate(current, [previous], state)
        assert result['blocked'] is blocked
        assert result['introduced'] is False
        assert result['firstSeen'] == state[key]


def test_exceptions_require_exact_package_version_owner_and_expiry():
    value = issue('Critical')
    exception = {k: value[k] for k in ('target', 'package', 'version', 'vulnerability', 'severity')}
    exception.update(createdOn=TODAY.isoformat(), expires=(TODAY + timedelta(days=30)).isoformat(),
                     owner='owner', approvedBy='amazen33', reason='synthetic test only', workOrder='synthetic')
    assert not gate(value, exceptions=[exception])['blocked']
    assert gate(dict(value, version='1.1'), exceptions=[exception])['blocked']
    for changes in ({'approvedBy': 'automatic'}, {'expires': (TODAY - timedelta(days=1)).isoformat()},
                    {'expires': (TODAY + timedelta(days=31)).isoformat()}, {'workOrder': ''}):
        with pytest.raises(ValueError):
            gate(value, exceptions=[dict(exception, **changes)])


def test_invalid_kev_is_not_a_pass_and_cvss_is_calculated():
    with pytest.raises(ValueError):
        gate(issue(), kev={})
    assert cvss3('CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H') == 9.8
