#!/usr/bin/env python3
"""Authorize the new controller's public key; never handles private key material."""
from pathlib import Path
import sys

key = Path(sys.argv[1]).read_text().strip()
if not key.startswith('ssh-ed25519 ') or '\n' in key:
    raise SystemExit('Expected one Ed25519 public key')
directory = Path('/home/ubuntu/.ssh')
directory.mkdir(mode=0o700, exist_ok=True)
directory.chmod(0o700)
authorized = directory / 'authorized_keys'
existing = authorized.read_text().splitlines() if authorized.exists() else []
if key not in existing:
    with authorized.open('a') as destination:
        destination.write('\n' + key + '\n')
authorized.chmod(0o600)
