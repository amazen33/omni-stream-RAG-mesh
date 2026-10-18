"""Collect exact installed Python distributions and their bundled licence notices."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import re


def inventory():
    result = []
    for dist in importlib.metadata.distributions():
        notices = []
        for file in dist.files or ():
            if re.search(r'(?:^|/)(?:LICEN[CS]E|COPYING|COPYRIGHT|NOTICE|ThirdPartyNotices)(?:[._-]|$)', str(file), re.I):
                path = dist.locate_file(file)
                if path.is_file():
                    notices.append({'path': str(file), 'text': path.read_text(encoding='utf-8', errors='replace')})
        result.append({'name': dist.metadata['Name'].lower().replace('_', '-'), 'version': dist.version,
                       'expression': dist.metadata.get('License-Expression'),
                       'license': dist.metadata.get('License'), 'notices': notices})
    return sorted(result, key=lambda item: item['name'])


def check_register(items, profile, register):
    text = Path(register).read_text(encoding='utf-8')
    section = text.split(f'<!-- {profile}-packages -->', 1)[1].split(f'<!-- /{profile}-packages -->', 1)[0]
    registered = set(re.findall(r'^\| ([\w.-]+) \| ([^ |]+) \|', section, re.M))
    missing = {(item['name'], item['version']) for item in items} - registered
    if missing:
        raise SystemExit('Unregistered image packages: ' + ', '.join(f'{n}=={v}' for n, v in sorted(missing)))
    if profile == 'main':
        from .verify_adapters import CHROMA_ONLY
        assert not (CHROMA_ONLY & {item['name'] for item in items})
        for item in items:
            if 'GCC-exception-3.1' in json.dumps(item):
                raise SystemExit('Unapproved bundled GCC exception in main: ' + item['name'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', metavar='REGISTER')
    parser.add_argument('--profile', choices=('main', 'lab'), default='main')
    parser.add_argument('--inventory', metavar='JSON')
    args = parser.parse_args()
    items = json.loads(Path(args.inventory).read_text()) if args.inventory else inventory()
    if args.check:
        check_register(items, args.profile, args.check)
        print(f'{args.profile}: all {len(items)} installed distributions registered')
    else:
        print(json.dumps(items, indent=2))
