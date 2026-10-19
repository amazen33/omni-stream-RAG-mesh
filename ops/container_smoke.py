"""Exercise only uniquely named containers created by this invocation."""
import argparse
import json
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid
from .tool_inputs import docker_executable, image_reference


def docker(binary, *args, check=True):
    binary = docker_executable(binary)
    result = subprocess.run([binary, *args], capture_output=True, text=True, timeout=120)
    if check and result.returncode:
        raise RuntimeError(f'docker {args[0]} failed: {result.stderr}')
    return (result.stdout + (result.stderr if args[0] == 'logs' else '')).strip()


def wait_live(request):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            status = request('/health/live')[0]
        except OSError:
            status = 0
        if status == 200:
            return
        time.sleep(0.25)
    raise RuntimeError('Container did not become live')


def exercise(binary, image, vector=False):
    binary, image = docker_executable(binary), image_reference(image)
    name = 'omni-o0-smoke-' + uuid.uuid4().hex
    created = False
    try:
        docker(binary, 'create', '--name', name, '--read-only', '--cap-drop=ALL',
               '--security-opt=no-new-privileges:true', '--tmpfs', '/tmp:rw,nosuid,noexec,size=64m,mode=1777',
               '--publish', '127.0.0.1::8000', '--env', 'RUNTIME_PROFILE=production',
               '--env', 'PII_TOKEN_SALT=synthetic-o0-container-check', '--env',
               f'ENABLE_VECTOR_STORE={str(vector).lower()}', image)
        created = True
        docker(binary, 'start', name)
        info = json.loads(docker(binary, 'inspect', name))[0]
        assert info['HostConfig']['ReadonlyRootfs'] is True
        assert info['Config']['User'] not in ('', '0', 'root')
        port = info['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort']
        base = 'http://127.0.0.1:' + port

        def request(path, body=None):
            data = json.dumps(body).encode() if body is not None else None
            req = Request(base + path, data=data, headers={'Content-Type': 'application/json'})
            try:
                with urlopen(req, timeout=10) as response:
                    return response.status, response.read()
            except HTTPError as error:
                return error.code, error.read()

        wait_live(request)
        probe = '''import errno,os
assert os.getuid() != 0
try:
    open('/app/.o0-root-write-check', 'w')
except OSError as error:
    assert error.errno == errno.EROFS, error.errno
else:
    raise AssertionError('application root is writable')
print('non-root and read-only application root verified')
'''
        print(docker(binary, 'exec', name, 'python', '-c', probe))
        if vector:
            status, body = request('/health/startup')
            assert status == 503 and b'Chroma is available only in the lab image' in body
            assert 'Traceback' not in docker(binary, 'logs', name)
            print('main image: lab-only Chroma produces clear 503 readiness, process stays live')
        else:
            assert request('/health/ready')[0] == 200
            for path in ('/docs', '/redoc', '/openapi.json'):
                assert request(path)[0] == 404
            assert request('/ingest-sample', {'text': 'synthetic container evidence'})[0] == 200
            status, body = request('/ask', {'question': 'synthetic container evidence'})
            assert status == 200 and json.loads(body)['retrieved']
            assert request('/payments/transactions', {'transaction_id': 'synthetic-transaction',
                'merchant_id': 'synthetic-merchant', 'amount_minor': 1, 'currency': 'USD'})[0] == 200
            status, body = request('/metrics')
            assert status == 200
            text = body.decode()
            for family, kind in (
                ('rag_http_requests_total', 'counter'),
                ('rag_http_request_duration_seconds', 'histogram'),
                ('rag_http_requests_in_flight', 'gauge'),
                ('process_resident_memory_bytes', 'gauge'),
                ('process_cpu_seconds_total', 'counter'),
                ('process_open_fds', 'gauge'),
            ):
                assert f'# HELP {family} ' in text
                assert f'# TYPE {family} {kind}\n' in text
            assert 'route="/payments/transactions",status_class="2xx"' in text
            print('Linux /metrics sample:\n' + '\n'.join(
                line for line in text.splitlines()
                if line.startswith(('process_', 'rag_http_requests_total{', 'rag_http_requests_in_flight '))
            ))
            print('main container HTTP smoke passed: health, docs denied, ingest, ask, payments, metrics')
    except BaseException:
        if created:
            print(docker(binary, 'logs', name, check=False))
        raise
    finally:
        if created:
            docker(binary, 'stop', '--time', '5', name, check=False)
            docker(binary, 'rm', name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', default='docker')
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    exercise(args.docker, args.image)
    exercise(args.docker, args.image, vector=True)
