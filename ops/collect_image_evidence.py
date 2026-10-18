"""Record local image IDs, sizes, package lists and upstream licence notices."""
import argparse
import json
from pathlib import Path
import subprocess


def collect(docker, main, lab, output):
    output.mkdir(parents=True, exist_ok=True)
    receipts = {}
    for profile, image in [('main', main), ('lab', lab)]:
        info = json.loads(subprocess.check_output([docker, 'image', 'inspect', image]))[0]
        receipts[profile] = {'reference': image, 'id': info['Id'], 'sizeBytes': info['Size'], 'user': info['Config']['User']}
        print(f"{profile}: {info['Id']} {info['Size']} bytes ({info['Size'] / 1048576:.2f} MiB)", flush=True)
        for command, filename in [(['-m', 'pip', 'list', '--format=json'], f'{profile}-pip-list.json'),
                                  (['-m', 'ops.image_inventory'], f'{profile}-licenses.json')]:
            result = subprocess.check_output([docker, 'run', '--rm', image, 'python', *command])
            json.loads(result)
            (output / filename).write_bytes(result)
        subprocess.run([docker, 'run', '--rm', image, 'python', '-m', 'ops.verify_adapters', '--profile', profile], check=True)
    (output / 'images.json').write_text(json.dumps(receipts, indent=2) + '\n')
    print(subprocess.check_output([docker, 'run', '--rm', main, 'python', '-m', 'pip', 'list'], text=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', default='docker')
    parser.add_argument('--main', default='local/omni-o0:main')
    parser.add_argument('--lab', default='local/omni-o0:lab')
    parser.add_argument('--output', type=Path, default=Path('test-results/o0-baseline'))
    args = parser.parse_args()
    collect(args.docker, args.main, args.lab, args.output)
