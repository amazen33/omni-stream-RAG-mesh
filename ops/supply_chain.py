"""Pinned scanner orchestration and the ADR-0049 KEV/fix/first-seen gate.

Scan on Linux. Reports and digest-keyed SBOMs stay in ignored test-results.
No scanner receives a repository secret. This module never approves exceptions.
"""
import argparse
from datetime import date
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCKS = ('requirements.txt', 'requirements-lab.txt', 'requirements-dev.txt', 'ansible/requirements-controller.txt')
INITIAL_DATE = date(2026, 10, 19)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'omni-o0-supply-chain'}), timeout=90) as response:
        return response.read()


def tools(directory):
    directory.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / 'ops/scanner-tools.lock.json').read_text())
    result = {}
    for name in ('syft', 'grype', 'osv-scanner'):
        entry = lock[name]
        binary = directory / name
        if not binary.is_file() or sha(binary.read_bytes()) != entry['binarySHA256']:
            raw = fetch(entry['url'])
            if sha(raw) != entry['sha256']:
                raise ValueError('Scanner archive checksum mismatch: ' + name)
            if entry.get('member'):
                with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                    raw = archive.extractfile(entry['member']).read()
            if sha(raw) != entry['binarySHA256']:
                raise ValueError('Scanner binary checksum mismatch: ' + name)
            binary.write_bytes(raw)
            binary.chmod(0o755)
        result[name] = str(binary.resolve())
    return result, {name: {k: lock[name][k] for k in ('version', 'sha256', 'binarySHA256')} for name in result}


def run(command, output, allowed=(0,), env=None):
    with Path(output).open('wb') as stdout, Path(str(output) + '.stderr.log').open('wb') as stderr:
        result = subprocess.run([str(x) for x in command], stdout=stdout, stderr=stderr, env=env, timeout=1200)
    if result.returncode not in allowed:
        raise RuntimeError(f'{Path(command[0]).name} failed ({result.returncode}); see {output}')
    return result.returncode


def cvss3(vector):
    values = dict(x.split(':', 1) for x in vector.split('/')[1:])
    scope = values['S'] == 'C'
    av = {'N': .85, 'A': .62, 'L': .55, 'P': .2}[values['AV']]
    ac = {'L': .77, 'H': .44}[values['AC']]
    pr = {'N': .85, 'L': .68 if scope else .62, 'H': .5 if scope else .27}[values['PR']]
    ui = {'N': .85, 'R': .62}[values['UI']]
    impacts = {'H': .56, 'L': .22, 'N': 0}
    iss = 1 - math.prod(1 - impacts[values[x]] for x in 'CIA')
    impact = 7.52 * (iss - .029) - 3.25 * (iss - .02) ** 15 if scope else 6.42 * iss
    if impact <= 0:
        return 0
    score = min(1.08 * (impact + 8.22 * av * ac * pr * ui) if scope else impact + 8.22 * av * ac * pr * ui, 10)
    return math.ceil(round(score, 10) * 10) / 10


def severity(vulnerability, group):
    known = vulnerability.get('database_specific', {}).get('severity', '').title()
    if known in ('Critical', 'High', 'Medium', 'Low', 'Negligible'):
        return known
    scores = []
    for item in vulnerability.get('severity', []):
        raw = str(item.get('score', ''))
        if raw.startswith(('CVSS:3.0/', 'CVSS:3.1/')):
            scores.append(cvss3(raw))
        elif re.fullmatch(r'\d+(?:\.\d+)?', raw):
            scores.append(float(raw))
    maximum = str(group.get('max_severity', ''))
    if re.fullmatch(r'\d+(?:\.\d+)?', maximum):
        scores.append(float(maximum))
    score = max(scores, default=-1)
    return 'Critical' if score >= 9 else 'High' if score >= 7 else 'Medium' if score >= 4 else 'Low' if score > 0 else 'Negligible' if score == 0 else 'Unknown'


def finding(target, package, version, aliases, level, fixes, scanner):
    ids = sorted(set(aliases))
    if not ids:
        raise ValueError('Vulnerability identity missing')
    vulnerability = next((x for x in ids if x.startswith('CVE-')), ids[0])
    return dict(target=target, package=package, version=version, vulnerability=vulnerability,
                aliases=ids, severity=level, fixAvailable=bool(fixes), fixVersions=sorted(set(fixes)), scanner=scanner)


def grype_findings(raw):
    if not isinstance(raw.get('matches'), list):
        raise ValueError('Invalid Grype result')
    values = []
    for match in raw['matches']:
        vuln, artifact = match['vulnerability'], match['artifact']
        fix = vuln.get('fix', {})
        values.append(finding('image:main', artifact['name'], artifact['version'],
            [vuln['id'], *[item['id'] for item in match.get('relatedVulnerabilities', [])]],
            vuln['severity'].title(), fix.get('versions', []) if fix.get('state') == 'fixed' else [], 'grype'))
    return values


def osv_findings(raw, aliases):
    if not isinstance(raw.get('results'), list):
        raise ValueError('Invalid OSV result')
    values = []
    for source in raw['results']:
        target = 'lockfile:' + aliases[str(Path(source['source']['path']).resolve())]
        for package in source.get('packages', []):
            pkg = package['package']
            for vuln in package.get('vulnerabilities', []):
                group = next((g for g in package.get('groups', []) if vuln['id'] in g.get('ids', [])), {})
                fixes = [event['fixed'] for affected in vuln.get('affected', [])
                         if affected.get('package', {}).get('name') == pkg['name']
                         and affected.get('package', {}).get('ecosystem') == pkg.get('ecosystem')
                         for span in affected.get('ranges', []) for event in span.get('events', []) if event.get('fixed')]
                values.append(finding(target, pkg['name'], pkg.get('version', ''),
                    [vuln['id'], *vuln.get('aliases', []), *group.get('ids', [])], severity(vuln, group), fixes, 'osv'))
    return values


def identity(value):
    return (value['target'], value['package'], value['vulnerability'])


def evaluate(findings, previous, kev, state, exceptions, on=None):
    on = on or date.today()
    if not isinstance(kev.get('catalogVersion'), str) or not isinstance(kev.get('vulnerabilities'), list):
        raise ValueError('Invalid KEV catalogue')
    kev_ids = {item['cveID'] for item in kev['vulnerabilities']}
    validated = []
    for entry in exceptions:
        created, expires = date.fromisoformat(entry['createdOn']), date.fromisoformat(entry['expires'])
        maximum = {'Critical': 30, 'High': 60}.get(entry['severity'], 90)
        if not (created <= on <= expires and 0 <= (expires - created).days <= maximum):
            raise ValueError('Expired/invalid exception: ' + entry['vulnerability'])
        if not entry.get('owner') or not entry.get('reason') or entry.get('approvedBy') != 'amazen33':
            raise ValueError('Owner approval missing for exception')
        validated.append(entry)
    history = dict(state)
    result = []
    for raw in findings:
        value = dict(raw)
        # Match aliases, not merely a scanner-specific primary advisory name.
        introduced = not any(p['target'] == value['target'] and p['package'] == value['package']
                             and set(p['aliases']) & set(value['aliases']) for p in previous)
        key = sha(json.dumps(identity(value), separators=(',', ':')).encode())
        first = date.fromisoformat(history.get(key, on.isoformat() if introduced else min(INITIAL_DATE, on).isoformat()))
        if first > on:
            raise ValueError('Future first-seen date')
        history[key] = first.isoformat()
        is_kev = bool(kev_ids & set(value['aliases']))
        reason = ('KEV' if is_kev else 'Critical with fix' if value['severity'] == 'Critical' and value['fixAvailable']
                  else ('High introduced by PR' if introduced else 'High with fix aged 14 days')
                  if value['severity'] == 'High' and value['fixAvailable'] and (introduced or (on - first).days >= 14)
                  else '')
        exception = next((e for e in validated if all(e[k] == value[k]
                         for k in ('target', 'package', 'version', 'vulnerability'))), None)
        if exception and (exception['severity'] != value['severity'] or (value['fixAvailable'] and not exception.get('workOrder'))):
            raise ValueError('Exception severity or remediation work order is invalid')
        value.update(introduced=introduced, firstSeen=first.isoformat(), kev=is_kev,
                     blockReason=reason, exception=exception, blocked=bool(reason and not exception))
        result.append(value)
    return result, history


def scan_locks(binaries, source, out):
    aliases = {}
    command = [binaries['osv-scanner'], 'scan', 'source', '--no-resolve', '--no-call-analysis=go', '--format=json']
    for relative in LOCKS:
        path = (source / relative).resolve()
        if path.is_file():
            aliases[str(path)] = relative
            command += ['--lockfile', 'requirements.txt:' + str(path)]
    run(command, out, allowed=(0, 1))
    return osv_findings(json.loads(out.read_text()), aliases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--image-digest', required=True)
    parser.add_argument('--baseline-image')
    parser.add_argument('--base-ref')
    parser.add_argument('--baseline-source', type=Path, help='Previously git-archived base lock files (for offline Git access)')
    parser.add_argument('--out', type=Path, default=ROOT / 'test-results/supply-chain')
    args = parser.parse_args()
    if args.base_ref and args.baseline_source:
        raise ValueError('Choose a git base ref or an archived baseline source, not both')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', args.image_digest):
        raise ValueError('An exact local image ID or OCI digest is required')
    args.out.mkdir(parents=True, exist_ok=True)
    binaries, versions = tools(ROOT / '.tools/scanners')
    env = dict(os.environ, GRYPE_DB_CACHE_DIR=str((ROOT / '.tools/grype-db').resolve()), GRYPE_DB_AUTO_UPDATE='false')
    run([binaries['grype'], 'db', 'update'], args.out / 'database-update.log', env=env)
    run([binaries['grype'], 'db', 'status', '-o', 'json'], args.out / 'database.json', env=env)
    sbom = args.out / (args.image_digest[7:] + '.syft.json')
    run([binaries['syft'], 'scan', args.image, '--platform', 'linux/amd64', '-o', 'syft-json'], sbom)
    run([binaries['syft'], 'convert', sbom, '-o', 'cyclonedx-json'], sbom.with_suffix('.cdx.json'))
    raw = args.out / 'grype.json'
    run([binaries['grype'], 'sbom:' + str(sbom), '-o', 'json'], raw, env=env)
    findings = grype_findings(json.loads(raw.read_text())) + scan_locks(binaries, ROOT, args.out / 'osv.json')
    previous = []
    if args.baseline_image:
        run([binaries['syft'], 'scan', args.baseline_image, '--platform', 'linux/amd64', '-o', 'syft-json'], args.out / 'base.syft.json')
        run([binaries['grype'], 'sbom:' + str(args.out / 'base.syft.json'), '-o', 'json'], args.out / 'base.grype.json', env=env)
        previous += grype_findings(json.loads((args.out / 'base.grype.json').read_text()))
    if args.base_ref:
        source = args.out / 'base-source'
        source.mkdir(exist_ok=True)
        available = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', args.base_ref], cwd=ROOT, text=True).splitlines()
        for path in LOCKS:
            if path in available:
                target = source / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(subprocess.check_output(['git', 'show', args.base_ref + ':' + path], cwd=ROOT))
        previous += scan_locks(binaries, source, args.out / 'base.osv.json')
    elif args.baseline_source:
        previous += scan_locks(binaries, args.baseline_source, args.out / 'base.osv.json')
    state_path = ROOT / '.tools/supply-chain-state.json'
    state = json.loads(state_path.read_text()) if state_path.is_file() else {}
    kev_raw = fetch('https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json')
    kev = json.loads(kev_raw)
    exceptions = json.loads((ROOT / 'security/vulnerability-exceptions.json').read_text())['exceptions']
    evaluated, state = evaluate(findings, previous, kev, state, exceptions)
    write(state_path, state)
    report = {'image': args.image, 'imageDigest': args.image_digest, 'baseRef': args.base_ref,
              'baselineSource': str(args.baseline_source) if args.baseline_source else None,
              'date': date.today().isoformat(), 'tools': versions, 'database': json.loads((args.out / 'database.json').read_text()),
              'kev': {'catalogVersion': kev['catalogVersion'], 'sha256': sha(kev_raw)}, 'findings': evaluated,
              'status': 'failed' if any(item['blocked'] for item in evaluated) else 'passed'}
    write(args.out / 'report.json', report)
    print(f"ADR-0049: {report['status']}; {sum(item['blocked'] for item in evaluated)} blocking / {len(evaluated)} findings")
    if report['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
